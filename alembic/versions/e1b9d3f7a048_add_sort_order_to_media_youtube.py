"""add sort_order to media_youtube

Stores the video's position in its source playlist (0-based).
NULL for RSS-fetched videos; set for playlist-scraped videos.
Used to order Jomez coverage cards in the correct round sequence.

Revision ID: e1b9d3f7a048
Revises: c5e2a8f1d047
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1b9d3f7a048"
down_revision: Union[str, Sequence[str], None] = "c5e2a8f1d047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_youtube", sa.Column("sort_order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_youtube", "sort_order")
