"""fix season_standings primary key to (season, pdga_id)

Allows multiple players at the same rank (ties). Adds pdga_id column.

Revision ID: b7d4c91f3a02
Revises: a3f1e8c2d904
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7d4c91f3a02"
down_revision: Union[str, Sequence[str], None] = "a3f1e8c2d904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("season_standings")
    op.create_table(
        "season_standings",
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("pdga_id", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("season", "pdga_id"),
    )


def downgrade() -> None:
    op.drop_table("season_standings")
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
