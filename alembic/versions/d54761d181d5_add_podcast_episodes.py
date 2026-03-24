"""add podcast_episodes table

Stores the most recent episodes from each tracked podcast show.
Populated nightly by etl/podcast.py.

Revision ID: d54761d181d5
Revises: f6c9c626215e
Create Date: 2026-03-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d54761d181d5"
down_revision: Union[str, Sequence[str], None] = "f6c9c626215e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "podcast_episodes",
        sa.Column("episode_guid", sa.Text(), nullable=False),
        sa.Column("show_name", sa.Text(), nullable=False),
        sa.Column("episode_title", sa.Text(), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("duration_secs", sa.Integer(), nullable=True),
        sa.Column("episode_url", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("episode_guid"),
    )
    op.create_index("ix_podcast_episodes_show", "podcast_episodes", ["show_name"])


def downgrade() -> None:
    op.drop_index("ix_podcast_episodes_show", table_name="podcast_episodes")
    op.drop_table("podcast_episodes")
