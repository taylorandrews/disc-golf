"""create_views

Revision ID: 6ce5726d5313
Revises: b90ec0cb8a47
Create Date: 2025-12-02 20:34:57.400110

"""
from typing import Sequence, Union
from helpers.disc_golf_schema import schema

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ce5726d5313'
down_revision: Union[str, Sequence[str], None] = 'b90ec0cb8a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Views"""

    create_vw_round = """
        CREATE VIEW vw_round AS
            SELECT
                r.round_id,
                r.player_id,
                p.first_name,
                p.last_name,
                r.course_id,
                c.course_name,
                r.tournament_id,
                t.name AS tournament_name,
                t.long_name AS tournament_long_name,
                t.classification,
                t.season,
                t.total_rounds,
                t.is_worlds,
                r.tournament_round_num,
                r.round_rating,
                r.round_score,
                r.round_date,
                r.card_number
            FROM round r
            JOIN player p ON r.player_id = p.player_id
            JOIN course c ON r.course_id = c.course_id
            JOIN tournament t ON r.tournament_id = t.tournament_id;
    """
    op.execute(create_vw_round)

    create_vw_hole = """
        CREATE VIEW vw_hole AS
            SELECT
                h.hole_id,
                h.round_id,
                h.player_id,
                p.first_name,
                p.last_name,
                h.hole_number,
                h.par,
                h.length,
                h.score,
                r.tournament_round_num,
                r.round_rating,
                r.round_score,
                r.course_id,
                c.course_name,
                r.tournament_id,
                t.name AS tournament_name,
                t.long_name AS tournament_long_name,
                t.season,
                t.classification,
                t.is_worlds,
                r.round_date
            FROM hole h
            JOIN round r ON h.round_id = r.round_id
            JOIN player p ON h.player_id = p.player_id
            JOIN course c ON r.course_id = c.course_id
            JOIN tournament t ON r.tournament_id = t.tournament_id;
    """
    op.execute(create_vw_hole)

    create_vw_tournament_result = """
        CREATE VIEW vw_tournament_result AS
            SELECT
                r.player_id,
                p.first_name,
                p.last_name,
                r.tournament_id,
                t.name AS tournament_name,
                t.long_name AS tournament_long_name,
                t.classification,
                t.season,
                SUM(r.round_score) AS total_score,
                SUM(r.round_rating) AS total_ratings_sum,
                COUNT(*) AS rounds_played
            FROM round r
            JOIN player p ON r.player_id = p.player_id
            JOIN tournament t ON r.tournament_id = t.tournament_id
            GROUP BY
                r.player_id, p.first_name, p.last_name,
                r.tournament_id, t.name, t.long_name, t.classification, t.season;
    """
    op.execute(create_vw_tournament_result)

    create_vw_player_season = """
        CREATE VIEW vw_player_season AS
            SELECT
                p.player_id,
                p.first_name,
                p.last_name,
                t.season,
                COUNT(DISTINCT r.tournament_id) AS tournaments_played,
                COUNT(DISTINCT r.round_id) AS rounds_played
            FROM round r
            JOIN player p ON r.player_id = p.player_id
            JOIN tournament t ON r.tournament_id = t.tournament_id
            GROUP BY p.player_id, p.first_name, p.last_name, t.season;
    """
    op.execute(create_vw_player_season)


def downgrade() -> None:
    """Downgrade schema."""
    views = ["vw_round", "vw_hole", "vw_tournament_result", "vw_player_season"]
    for view in views:
        op.execute(f"DROP VIEW IF EXISTS {view};")
