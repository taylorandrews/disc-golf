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

    create_vw_anomaly = """
    CREATE OR REPLACE VIEW vw_anomaly AS

    /* ---------------------------------------------------------
    CHECK 1 — Hole count mismatch vs course.holes
    --------------------------------------------------------- */
        SELECT
            'HOLE_COUNT_MISMATCH' AS check_name,
            r.round_id::text AS entity_id,
            jsonb_build_object(
                'course_id', r.course_id,
                'expected_holes', c.holes,
                'actual_holes', r.hole_count,
                'tournament_id', r.tournament_id,
                'player_id', r.player_id
            ) AS detail
        FROM round r
        JOIN course c USING (course_id)
        WHERE r.hole_count IS NOT NULL
        AND r.hole_count != c.holes

        UNION ALL

        /* ---------------------------------------------------------
        CHECK 2 — Hole rows count doesn’t match round.hole_count
        --------------------------------------------------------- */
        SELECT
            'ROUND_HOLE_ROW_MISMATCH' AS check_name,
            r.round_id::text AS entity_id,
            jsonb_build_object(
                'expected_holes', r.hole_count,
                'actual_holes', hc.actual_holes,
                'tournament_id', r.tournament_id,
                'player_id', r.player_id
            ) AS detail
        FROM round r
        LEFT JOIN (
            SELECT
                round_id,
                COUNT(*) AS actual_holes
            FROM hole
            GROUP BY round_id
        ) hc USING (round_id)
        WHERE r.hole_count IS NOT NULL
        AND hc.actual_holes IS NOT NULL
        AND hc.actual_holes != r.hole_count

        UNION ALL

        /* ---------------------------------------------------------
        CHECK 3 — Missing or NULL critical hole fields
        --------------------------------------------------------- */
        SELECT
            'HOLE_NULL_FIELDS' AS check_name,
            h.hole_id::text AS entity_id,
            jsonb_build_object(
                'round_id', h.round_id,
                'player_id', h.player_id,
                'hole_number', h.hole_number,
                'par', h.par,
                'length', h.length,
                'score', h.score
            ) AS detail
        FROM hole h
        WHERE h.hole_number IS NULL
        OR h.par IS NULL
        OR h.score IS NULL
        OR h.length IS NULL

        UNION ALL

        /* ---------------------------------------------------------
        CHECK 4 — Daily player counts swing > 5 players, no cut allowed
        --------------------------------------------------------- */

        SELECT
            'PLAYER_COUNT_DELTA' AS check_name,
            (t.tournament_id || '-' || d.day_num)::text AS entity_id,
            jsonb_build_object(
                'tournament_id', t.tournament_id,
                'day_num', d.day_num,
                'players_today', d.players_today,
                'players_prev', d.players_prev,
                'delta', d.delta,
                'tournament_name', t.name
            ) AS detail
        FROM (
            SELECT
                d1.tournament_id,
                d1.day_num,
                d1.players AS players_today,
                d2.players AS players_prev,
                (d1.players - d2.players) AS delta
            FROM (
            SELECT
                tournament_id,
                tournament_round_num AS day_num,
                COUNT(DISTINCT player_id) AS players
            FROM round
            GROUP BY tournament_id, tournament_round_num
        ) as d1
            JOIN (
            SELECT
                tournament_id,
                tournament_round_num AS day_num,
                COUNT(DISTINCT player_id) AS players
            FROM round
            GROUP BY tournament_id, tournament_round_num
        ) as d2
            ON d1.tournament_id = d2.tournament_id
            AND d2.day_num = d1.day_num - 1
        ) d
        JOIN tournament t ON t.tournament_id = d.tournament_id
        WHERE ABS(d.delta) > 5
        AND t.has_finals = FALSE

        UNION ALL

        /* ---------------------------------------------------------
        CHECK 5 — Duplicate rounds for same player/day/tournament
        --------------------------------------------------------- */
        SELECT
            'DUPLICATE_ROUND' AS check_name,
            (tournament_id || '-' || player_id || '-' || tournament_round_num)::text AS entity_id,
            jsonb_build_object(
                'tournament_id', tournament_id,
                'player_id', player_id,
                'day_num', tournament_round_num,
                'round_ids', array_agg(round_id)
            ) AS detail
        FROM round
        GROUP BY tournament_id, player_id, tournament_round_num
        HAVING COUNT(*) > 1

        UNION ALL

        /* ---------------------------------------------------------
        CHECK 6 — Hole count outside typical range (catch weird data)
        Use this only if hole_count exists and course lookup didn't catch it.
        --------------------------------------------------------- */
        SELECT
            'UNUSUAL_HOLE_COUNT' AS check_name,
            r.round_id::text AS entity_id,
            jsonb_build_object(
                'hole_count', r.hole_count,
                'expected', 'typically 18',
                'tournament_id', r.tournament_id,
                'player_id', r.player_id
            ) AS detail
        FROM round r
        WHERE r.hole_count IS NOT NULL
        AND r.hole_count NOT IN (9, 18, 24);
        """
    op.execute(create_vw_anomaly)


def downgrade() -> None:
    """Downgrade schema."""
    views = ["vw_round", "vw_hole", "vw_tournament_result", "vw_player_season", "create_vw_anomaly"]
    for view in views:
        op.execute(f"DROP VIEW IF EXISTS {view};")
