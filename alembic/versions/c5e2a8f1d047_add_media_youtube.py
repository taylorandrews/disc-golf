"""add media_youtube table

Revision ID: c5e2a8f1d047
Revises: b7d4c91f3a02
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5e2a8f1d047"
down_revision: Union[str, Sequence[str], None] = "b7d4c91f3a02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_youtube",
        sa.Column("video_id", sa.Text(), primary_key=True),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("channel_name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=False),
        sa.Column("video_url", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
    )
    op.create_index("ix_media_youtube_channel_id", "media_youtube", ["channel_id"])
    op.create_index("ix_media_youtube_published_at", "media_youtube", ["published_at"])


def downgrade() -> None:
    op.drop_table("media_youtube")
