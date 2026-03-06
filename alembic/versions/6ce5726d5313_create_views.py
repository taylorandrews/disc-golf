"""create_dashboard_views

Revision ID: 6ce5726d5313
Revises: b90ec0cb8a47
Create Date: 2025-12-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '6ce5726d5313'
down_revision: Union[str, Sequence[str], None] = 'b90ec0cb8a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create views optimized for the dashboard."""
    
    # --------------------------------------------------------
    # 1. Tournament classifications per season (for pie chart)
    # --------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE VIEW vw_classifications_per_season AS
            SELECT
                season,
                classification,
                COUNT(*) AS tournament_count
            FROM tournament
            GROUP BY season, classification
            ORDER BY season, classification;
    """)
    
    # --------------------------------------------------------
    # 2. Tournament summary (champion, prize, course, dates)
    # --------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE VIEW vw_tournament_summary AS
        WITH player_totals AS (
            SELECT
                r.tournament_id,
                r.player_id,
                SUM(r.round_score) AS total_score,
                MAX(r.prize) AS prize,
                MAX(r.won_playoff) AS won_playoff
            FROM round r
            GROUP BY r.tournament_id, r.player_id
        ),
        ranked_players AS (
            SELECT
                pt.*,
                RANK() OVER (
                    PARTITION BY pt.tournament_id
                    ORDER BY pt.total_score ASC, pt.won_playoff DESC
                ) AS finish_rank
            FROM player_totals pt
        ),
        champions AS (
            SELECT
                rp.tournament_id,
                rp.player_id,
                rp.total_score,
                rp.prize
            FROM ranked_players rp
            WHERE rp.finish_rank = 1
        ),
        final_courses AS (
            SELECT DISTINCT ON (r.tournament_id)
                r.tournament_id,
                c.course_name
            FROM round r
            JOIN course c ON r.course_id = c.course_id
            ORDER BY r.tournament_id, r.tournament_round_num DESC
        )
        SELECT
            t.season,
            t.tournament_id,
            t.name AS event_name,
            t.classification,
            t.is_worlds,
            fc.course_name AS finishing_course_name,
            p.first_name || ' ' || p.last_name AS champion,
            ch.total_score AS total_score,
            ch.prize AS prize_usd,
            t.start_date,
            (t.start_date + (t.total_rounds - 1)) AS end_date
        FROM tournament t
        JOIN champions ch ON t.tournament_id = ch.tournament_id
        JOIN player p ON ch.player_id = p.player_id
        LEFT JOIN final_courses fc ON t.tournament_id = fc.tournament_id
        ORDER BY t.start_date;
    """)

    # --------------------------------------------------------
    # 3. Player season summary (tournaments, rounds)
    # --------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE VIEW vw_player_season AS
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
    """)

    # --------------------------------------------------------
    # 4. Anomaly checks (data QA)
    # --------------------------------------------------------
    op.execute("""
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
        )

def downgrade() -> None:
    """Drop all dashboard views."""
    views = [
        "vw_classifications_per_season",
        "vw_tournament_summary",
        "vw_player_season",
        "vw_anomaly"
    ]
    for view in views:
        op.execute(f"DROP VIEW IF EXISTS {view} CASCADE;")
        