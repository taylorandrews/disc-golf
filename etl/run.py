"""
Standalone ETL runner for local use.

Reads DATABASE_URL from .env (or environment) and processes all current-year
tournaments the same way the Lambda does — without needing AWS.

Usage:
    python -m etl.run
"""
import datetime
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from etl.db import get_active_tournaments, get_engine, get_loaded_round_nums, upsert_all
from etl.parse import get_courses, get_holes_and_rounds, get_players
from etl.pdga import api_round_num, fetch_round

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    year = datetime.date.today().year
    engine = get_engine()
    tournaments = get_active_tournaments(engine, year)
    logger.info("Found %d tournaments for %d", len(tournaments), year)

    for t in tournaments:
        tournament_id = t["tournament_id"]
        total_rounds = t["total_rounds"]
        has_finals = t["has_finals"]
        start_date = t["start_date"]
        t_year = t["season"]

        loaded = get_loaded_round_nums(engine, tournament_id)

        for seq in range(1, total_rounds + 1):
            if seq in loaded:
                logger.info(
                    "Tournament %s round %s already loaded — skipping", tournament_id, seq
                )
                continue

            pdga_round = api_round_num(seq, total_rounds, has_finals)
            logger.info(
                "Fetching tournament %s round %s (PDGA round %s)", tournament_id, seq, pdga_round
            )

            try:
                raw = fetch_round(tournament_id, pdga_round)
            except Exception as exc:
                logger.warning(
                    "PDGA API error for tournament %s round %s: %s", tournament_id, seq, exc
                )
                continue

            data = raw.get("data", [])
            if not data:
                logger.info(
                    "No data yet for tournament %s round %s — skipping", tournament_id, seq
                )
                continue
            if not isinstance(data, list):
                data = [data]

            try:
                round_date = start_date + datetime.timedelta(days=seq - 1)
                courses = get_courses(data, year=t_year, round_num=seq)
                players = get_players(data)
                holes, rounds = get_holes_and_rounds(
                    data, round_date, seq, year=t_year, round_num=seq
                )
                upsert_all(engine, courses, players, rounds, holes)
                logger.info(
                    "Loaded tournament %s round %s: %d player-rounds, %d holes",
                    tournament_id, seq, len(rounds), len(holes),
                )
            except Exception as exc:
                logger.error(
                    "Failed to parse/upsert tournament %s round %s: %s",
                    tournament_id, seq, exc,
                    exc_info=True,
                )


if __name__ == "__main__":
    main()
