"""
Lambda entrypoint for the nightly ETL.

Triggered by EventBridge cron (06:00 UTC daily) or manually via:
    make invoke-etl

Behavior:
  - Reads all season=2026 tournaments from RDS
  - For each tournament, checks which rounds are already loaded
  - Fetches missing rounds from the PDGA API
  - Saves raw JSON to S3 (raw/pdga/2026/{tourn_id}/tournament_{id}_MPO_round_{n}.json)
  - Parses and upserts into course, player, round, hole tables
  - Exits cleanly (503) if RDS is unreachable (e.g. stopped between sessions)
"""
import datetime
import logging
import os

from etl.db import get_engine, get_loaded_round_nums, get_active_tournaments, upsert_all
from etl.parse import get_courses, get_players, get_holes_and_rounds
from etl.pdga import api_round_num, fetch_round, save_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get("S3_BUCKET", "")


def handler(event, context):
    try:
        year = datetime.date.today().year
        engine = get_engine()
        tournaments = get_active_tournaments(engine, year)
    except Exception as exc:
        logger.error("Could not connect to RDS (may be stopped): %s", exc)
        return {"statusCode": 503, "body": "RDS unavailable — is the instance running?"}

    logger.info("Found %d tournaments to check for %d", len(tournaments), year)
    total_new = 0

    for t in tournaments:
        tournament_id = t["tournament_id"]
        total_rounds = t["total_rounds"]
        has_finals = t["has_finals"]
        start_date = t["start_date"]
        year = t["season"]

        loaded = get_loaded_round_nums(engine, tournament_id)

        for seq in range(1, total_rounds + 1):
            if seq in loaded:
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

            has_scores = any(
                p.get("scores") and any(
                    s.get("RoundStarted") == 1 or s.get("Completed") == 1
                    for s in p["scores"]
                )
                for p in data
            )
            if not has_scores:
                logger.info(
                    "Round not yet started for tournament %s round %s — skipping",
                    tournament_id, seq,
                )
                continue

            if S3_BUCKET:
                try:
                    save_to_s3(raw, S3_BUCKET, tournament_id, seq, year)
                    logger.info("Saved to S3: tournament %s round %s", tournament_id, seq)
                except Exception as exc:
                    logger.warning(
                        "S3 save failed for tournament %s round %s: %s", tournament_id, seq, exc
                    )

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
            total_new += 1

    msg = f"ETL complete. Loaded {total_new} new round(s)."
    logger.info(msg)
    return {"statusCode": 200, "body": msg}
