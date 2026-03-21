"""
Enrich tournament seed data and upsert into the tournament table.

Reads data/seed/{year}_tournaments.csv (6 columns you maintain):
    tournament_id, name, start_date, classification, is_worlds, total_rounds, has_finals

For each row:
  - Fetches round 1 from the PDGA live API to extract long_name from the layout Name field
  - Derives season from start_date year
  - Upserts into the tournament table (ON CONFLICT DO NOTHING — safe to re-run)

Usage:
    DATABASE_URL=postgresql+psycopg://postgres:<pw>@<host>:5432/pdga_data \\
        python scripts/enrich_tournaments.py [--year YEAR]

Run this locally whenever you add new rows to {year}_tournaments.csv.
"""
import argparse
import csv
import datetime
import logging
import os
import sys
import time

# Allow running from the repo root without PYTHONPATH=.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

import requests
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from helpers.disc_golf_schema import schema

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

seed_csv_TEMPLATE = "data/seed/{year}_tournaments.csv"
PDGA_ROUND1_API = (
    "https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round"
    "?TournID={tourn_id}&Division=MPO&Round=1"
)
HEADERS = {"User-Agent": "disc-golf-stats/0.1", "Accept": "application/json"}


def fetch_long_name(tourn_id: str) -> str:
    """Pull the layout Name field from round 1 — this is the full event title."""
    try:
        resp = requests.get(
            PDGA_ROUND1_API.format(tourn_id=tourn_id), headers=HEADERS, timeout=20
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return ""
        if not isinstance(data, list):
            data = [data]
        for pool in data:
            for layout in pool.get("layouts", []):
                name = layout.get("Name", "").strip()
                if name:
                    return name
    except Exception as exc:
        logger.warning("Could not fetch long_name for tournament %s: %s", tourn_id, exc)
    return ""


def to_bool(value: str) -> bool:
    return value.strip().lower() in ("yes", "true", "t", "1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=datetime.date.today().year)
    args = parser.parse_args()

    seed_csv = seed_csv_TEMPLATE.format(year=args.year)

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL environment variable is required")

    engine = create_engine(db_url)

    with open(seed_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        logger.info("No rows in %s — nothing to do", seed_csv)
        return

    logger.info("Processing %d tournament(s) from %s", len(rows), seed_csv)
    tournaments = []

    for row in rows:
        tourn_id = row["tournament_id"].strip()
        start_date = datetime.date.fromisoformat(row["start_date"].strip())

        logger.info("Fetching PDGA metadata for tournament %s (%s)...", tourn_id, row["name"])
        long_name = fetch_long_name(tourn_id)
        if long_name:
            logger.info("  long_name: %s", long_name)
        else:
            long_name = row["name"].strip()
            logger.warning(
                "  Could not fetch long_name for %s — using short name as fallback", tourn_id
            )
        time.sleep(0.5)

        tournaments.append({
            "tournament_id": int(tourn_id),
            "season": start_date.year,
            "name": row["name"].strip(),
            "long_name": long_name,
            "start_date": start_date,
            "classification": row["classification"].strip(),
            "director": None,
            "is_worlds": to_bool(row["is_worlds"]),
            "total_rounds": int(row["total_rounds"].strip()),
            "has_finals": to_bool(row["has_finals"]),
        })

    with engine.begin() as conn:
        stmt = pg_insert(schema["tournament"]).values(tournaments)
        conn.execute(stmt.on_conflict_do_nothing(index_elements=["tournament_id"]))

    logger.info("Upserted %d tournament(s) into tournament table", len(tournaments))


if __name__ == "__main__":
    main()
