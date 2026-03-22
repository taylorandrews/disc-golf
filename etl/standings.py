"""
DGPT Points Standings scraper.

POSTs to the DGPT.com WordPress AJAX endpoint and parses the returned HTML
fragment to extract the current MPO season standings.

No API key required. No extra dependencies — uses stdlib re + requests
(already in etl/requirements.txt via the PDGA fetch module).
"""
import logging
import re

import requests
from sqlalchemy import text

logger = logging.getLogger(__name__)

DGPT_AJAX_URL = "https://www.dgpt.com/wp-admin/admin-ajax.php"
_PAGE_ID = "29445"
_HEADERS = {"User-Agent": "disc-golf-stats/0.1", "Accept": "text/html,*/*"}

_ROW_RE = re.compile(r'<tr[^>]+data-pdgaid="(\d+)"[^>]*>(.*?)</tr>', re.DOTALL)
_RANK_RE = re.compile(r'data-tied="(\d+)"')
_NAME_RE = re.compile(
    r'class="DGPTStandings--table_name"[^>]*>.*?<span>(.*?)</span>', re.DOTALL
)
_POINTS_RE = re.compile(r'data-sort-value="([0-9.]+)"')


def fetch_standings(season: int) -> list[dict]:
    """Return parsed standings rows for the given season."""
    resp = requests.post(
        DGPT_AJAX_URL,
        data={
            "action": "get_standings",
            "page_id": _PAGE_ID,
            "division": "MPO",
            "season": str(season),
        },
        headers=_HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    rows = _parse(resp.text)
    logger.info("Parsed %d standings rows for season %d", len(rows), season)
    return rows


def _parse(html: str) -> list[dict]:
    rows = []
    for pdga_id_str, row_html in _ROW_RE.findall(html):
        rank_m = _RANK_RE.search(row_html)
        name_m = _NAME_RE.search(row_html)
        pts_m = _POINTS_RE.search(row_html)
        if not (rank_m and name_m and pts_m):
            continue
        rows.append(
            {
                "pdga_id": int(pdga_id_str),
                "rank": int(rank_m.group(1)),
                "player_name": name_m.group(1).strip(),
                "total_points": float(pts_m.group(1)),
            }
        )
    return rows


def save_standings(engine, season: int, rows: list[dict]) -> None:
    """Delete current season standings and insert fresh rows in one transaction."""
    if not rows:
        logger.warning("No standings rows returned for season %d — skipping", season)
        return
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM season_standings WHERE season = :season"),
            {"season": season},
        )
        conn.execute(
            text(
                """
                INSERT INTO season_standings
                    (season, rank, player_name, player_id, total_points)
                VALUES (
                    :season, :rank, :player_name,
                    (SELECT player_id FROM player
                     WHERE LOWER(first_name || ' ' || last_name) = LOWER(:player_name)
                     LIMIT 1),
                    :total_points
                )
                """
            ),
            [
                {
                    "season": season,
                    "rank": r["rank"],
                    "player_name": r["player_name"],
                    "total_points": r["total_points"],
                }
                for r in rows
            ],
        )
    logger.info("Saved %d standings rows for season %d", len(rows), season)
