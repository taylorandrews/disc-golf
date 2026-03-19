"""
Standalone ETL runner for local use.

Reads DATABASE_URL from environment (or .env via python-dotenv) and processes
all 2026 tournaments the same way the Lambda does — without needing AWS.

Usage:
    DATABASE_URL=postgresql+psycopg://postgres:<pw>@<host>:5432/pdga_data \\
        python -m etl.run
"""
import datetime
import logging

from etl.db import get_engine, get_loaded_round_nums, get_2026_tournaments, upsert_all
from etl.parse import get_courses, get_players, get_holes_and_rounds
from etl.pdga import api_round_num, fetch_round

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    engine = get_engine()
    tournaments = get_2026_tournaments(engine)
    logger.info("Found %d 2026 tournaments", len(tournaments))

    for t in tournaments:
        tournament_id = t["tournament_id"]
        total_rounds = t["total_rounds"]
        has_finals = t["has_finals"]
        start_date = t["start_date"]
        year = t["season"]

        loaded = get_loaded_round_nums(engine, tournament_id)

        for seq in range(1, total_rounds + 1):
            if seq in loaded:
                logger.info("Tournament %s round %s already loaded — skipping", tournament_id, seq)
                continue

            pdga_round = api_round_num(seq, total_rounds, has_finals)
            logger.info("Fetching tournament %s round %s (PDGA round %s)", tournament_id, seq, pdga_round)

            raw = fetch_round(tournament_id, pdga_round)
            data = raw.get("data", [])
            if not data:
                logger.info("No data yet for tournament %s round %s — skipping", tournament_id, seq)
                continue
            if not isinstance(data, list):
                data = [data]

            round_date = start_date + datetime.timedelta(days=seq - 1)
            courses = get_courses(data, year=year, round_num=seq)
            players = get_players(data)
            holes, rounds = get_holes_and_rounds(
                data, round_date, seq, year=year, round_num=seq
            )

            upsert_all(engine, courses, players, rounds, holes)
            logger.info(
                "Loaded tournament %s round %s: %d player-rounds, %d holes",
                tournament_id, seq, len(rounds), len(holes),
            )


if __name__ == "__main__":
    main()
