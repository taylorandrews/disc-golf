"""add location and jomez_playlist_url to tournament

Revision ID: f8a3d2c1b9e7
Revises: 6ce5726d5313
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f8a3d2c1b9e7"
down_revision: Union[str, Sequence[str], None] = "6ce5726d5313"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tournament", sa.Column("location", sa.Text, nullable=True))
    op.add_column("tournament", sa.Column("jomez_playlist_url", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("tournament", "jomez_playlist_url")
    op.drop_column("tournament", "location")
