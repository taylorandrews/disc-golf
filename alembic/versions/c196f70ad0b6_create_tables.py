"""create tables in initial schema for PDGA data

Revision ID: c196f70ad0b6
Revises: 
Create Date: 2025-09-25 18:48:41.088355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c196f70ad0b6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # tournaments (basic stub, expand later)
    op.create_table(
        "tournament",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pdga_event_id", sa.Integer, nullable=False, unique=True),
        sa.Column("name", sa.Text),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
    )

    # layouts (course setup per round/division)
    op.create_table(
        "layout",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("layout_id", sa.Integer, nullable=False),
        sa.Column("course_id", sa.Integer),
        sa.Column("course_name", sa.Text),
        sa.Column("tourn_id", sa.Integer, nullable=False),
        sa.Column("name", sa.Text),
        sa.Column("holes", sa.Integer),
        sa.Column("par", sa.Integer),
        sa.Column("length", sa.Integer),
        sa.Column("units", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("update_date", sa.DateTime),
    )

    # holes (each hole within a layout)
    op.create_table(
        "hole",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("layout_id", sa.Integer, sa.ForeignKey("layout.id"), nullable=False),
        sa.Column("hole_ordinal", sa.Integer, nullable=False),
        sa.Column("label", sa.Text),
        sa.Column("par", sa.Integer),
        sa.Column("length", sa.Integer),
    )

    # rounds
    op.create_table(
        "round",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("round_id", sa.Integer, nullable=False, unique=True),  # live_round_id
        sa.Column("tourn_id", sa.Integer, nullable=False),
        sa.Column("division", sa.Text),
        sa.Column("round_number", sa.Integer),
        sa.Column("tee_times", sa.Boolean),
        sa.Column("shotgun_time", sa.Text),
    )

    # players
    op.create_table(
        "player",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pdga_num", sa.Integer, unique=True, nullable=True),
        sa.Column("first_name", sa.Text),
        sa.Column("last_name", sa.Text),
        sa.Column("full_name", sa.Text),
        sa.Column("rating", sa.Integer),
        sa.Column("city", sa.Text),
        sa.Column("state_prov", sa.Text),
        sa.Column("country", sa.Text),
        sa.Column("profile_url", sa.Text),
        sa.Column("avatar_url", sa.Text),
    )

    # round_scores (per-player per-round aggregate)
    op.create_table(
        "round_score",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("result_id", sa.Integer, nullable=False, unique=True),
        sa.Column("round_id", sa.Integer, sa.ForeignKey("round.id"), nullable=False),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("player.id"), nullable=False),
        sa.Column("layout_id", sa.Integer, sa.ForeignKey("layout.id")),
        sa.Column("round_number", sa.Integer),
        sa.Column("card_num", sa.Integer),
        sa.Column("tee_time", sa.Time),
        sa.Column("round_score", sa.Integer),
        sa.Column("round_to_par", sa.Integer),
        sa.Column("to_par", sa.Integer),
        sa.Column("grand_total", sa.Integer),
        sa.Column("round_rating", sa.Integer),
        sa.Column("running_place", sa.Integer),
        sa.Column("prize", sa.Text),
        sa.Column("round_status", sa.Text),
        sa.Column("update_date", sa.DateTime),
        sa.Column("raw_scores", sa.Text),  # e.g. "3,2,4,..."
        sa.Column("hole_scores", postgresql.JSONB),  # normalized as list of ints
        sa.Column("player_throw_status", postgresql.JSONB),
    )

    # hole_scores (optional: normalized table for analytics)
    op.create_table(
        "hole_score",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("round_score_id", sa.Integer, sa.ForeignKey("round_score.id"), nullable=False),
        sa.Column("hole_ordinal", sa.Integer, nullable=False),
        sa.Column("strokes", sa.Integer, nullable=False),
    )


def downgrade():
    op.drop_table("hole_score")
    op.drop_table("round_score")
    op.drop_table("player")
    op.drop_table("round")
    op.drop_table("hole")
    op.drop_table("layout")
    op.drop_table("tournament")