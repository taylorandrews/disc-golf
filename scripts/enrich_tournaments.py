"""
Enrich tournament seed data and upsert into the tournament table.

Reads data/seed/{year}_tournaments.csv (6 columns you maintain):
    tournament_id, name, start_date, classification, is_worlds, total_rounds, has_finals

For each row:
  - Fetches round 1 from the PDGA live API to extract long_name from the layout Name field
  - Derives season from start_date year
  - Upserts into the tournament table (ON CONFLICT DO NOTHING — safe to re-run)

Usage:
    python scripts/enrich_tournaments.py             # local Docker DB
    python scripts/enrich_tournaments.py --prod      # RDS via Secrets Manager
    python scripts/enrich_tournaments.py --year 2025 # override year

Run this locally whenever you add new rows to {year}_tournaments.csv.
For RDS, run `make print-rds-config` first to populate DB_SECRET_ARN and DB_HOST in .env.
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


def get_engine(prod: bool):
    """Return a SQLAlchemy engine.

    local (default): reads DATABASE_URL from .env
    --prod: pulls credentials from Secrets Manager (same path as the Lambda),
            requires DB_SECRET_ARN and DB_HOST in .env
    """
    if prod:
        # Unset DATABASE_URL so etl.db.get_engine() falls through to Secrets Manager.
        os.environ.pop("DATABASE_URL", None)
        from etl.db import get_engine as _get_engine
        return _get_engine()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "DATABASE_URL not set. Add it to .env for local, or use --prod for RDS."
        )
    return create_engine(db_url, pool_pre_ping=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

SEED_CSV_TEMPLATE = "data/seed/{year}_tournaments.csv"
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
    parser.add_argument(
        "--prod", action="store_true",
        help="Connect to RDS via Secrets Manager (requires DB_SECRET_ARN + DB_HOST in .env)"
    )
    args = parser.parse_args()

    seed_csv = SEED_CSV_TEMPLATE.format(year=args.year)
    engine = get_engine(args.prod)

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
        # Only update jomez_playlist_url on conflict — all other fields are manually
        # maintained in the CSV and should not be overwritten on re-runs.
        conn.execute(
            stmt.on_conflict_do_update(
                index_elements=["tournament_id"],
                set_={"jomez_playlist_url": stmt.excluded.jomez_playlist_url},
            )
        )

    logger.info("Upserted %d tournament(s) into tournament table", len(tournaments))


if __name__ == "__main__":
    main()
