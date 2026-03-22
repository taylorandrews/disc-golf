"""
Database connection and upsert helpers for the ETL pipeline.

Supports two credential modes:
  - DATABASE_URL env var (local dev / manual runs)
  - DB_SECRET_ARN + DB_HOST env vars (Lambda — credentials fetched from Secrets Manager)
"""
import json
import os

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from helpers.disc_golf_schema import schema


def get_engine():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        secret_arn = os.environ["DB_SECRET_ARN"]
        region = os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        secret = json.loads(
            client.get_secret_value(SecretId=secret_arn)["SecretString"]
        )
        db_url = (
            f"postgresql+pg8000://{secret['username']}:{secret['password']}"
            f"@{os.environ['DB_HOST']}:5432/{os.environ.get('DB_NAME', 'pdga_data')}"
        )
    return create_engine(db_url, pool_pre_ping=True)


def get_loaded_round_nums(engine, tournament_id: int) -> set[int]:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT DISTINCT tournament_round_num FROM round WHERE tournament_id = :tid"
            ),
            {"tid": tournament_id},
        )
        return {row[0] for row in result}


def get_active_tournaments(engine, year: int) -> list:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT tournament_id, season, name, start_date, total_rounds, has_finals"
                " FROM tournament WHERE season = :year AND start_date <= CURRENT_DATE ORDER BY start_date"
            ),
            {"year": year},
        )
        return result.mappings().all()


def get_current_jomez_playlist_url(engine, year: int) -> str | None:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT jomez_playlist_url FROM tournament"
                " WHERE season = :year AND start_date <= CURRENT_DATE"
                "   AND jomez_playlist_url IS NOT NULL"
                " ORDER BY start_date DESC LIMIT 1"
            ),
            {"year": year},
        )
        row = result.first()
        return row[0] if row else None


def upsert_all(
    engine,
    courses: list[dict],
    players: list[dict],
    rounds: list[dict],
    holes: list[dict],
) -> None:
    with engine.begin() as conn:
        for table_name, rows, pk in [
            ("course", courses, "course_id"),
            ("player", players, "player_id"),
            ("round", rounds, "round_id"),
            ("hole", holes, "hole_id"),
        ]:
            if rows:
                stmt = pg_insert(schema[table_name]).values(rows)
                conn.execute(stmt.on_conflict_do_nothing(index_elements=[pk]))
