"""add season_standings table

Revision ID: a3f1e8c2d904
Revises: f8a3d2c1b9e7
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3f1e8c2d904"
down_revision: Union[str, Sequence[str], None] = "f8a3d2c1b9e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "season_standings",
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("player.player_id"), nullable=True),
        sa.Column("total_points", sa.Numeric(8, 2), nullable=False),
        sa.Column("events_played", sa.Integer(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("season", "rank"),
    )


def downgrade() -> None:
    op.drop_table("season_standings")
