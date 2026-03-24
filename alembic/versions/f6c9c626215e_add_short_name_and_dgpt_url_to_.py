"""add short_name and dgpt_url to tournament

Adds short_name (e.g. "SFO", "BEO") for compact display and dgpt_url
for linking schedule strip pills to the official DGPT event page.

Revision ID: f6c9c626215e
Revises: e1b9d3f7a048
Create Date: 2026-03-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6c9c626215e"
down_revision: Union[str, Sequence[str], None] = "e1b9d3f7a048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tournament", sa.Column("short_name", sa.Text(), nullable=True))
    op.add_column("tournament", sa.Column("dgpt_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tournament", "dgpt_url")
    op.drop_column("tournament", "short_name")
