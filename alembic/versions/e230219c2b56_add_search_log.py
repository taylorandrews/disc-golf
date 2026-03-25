"""add_search_log

Revision ID: e230219c2b56
Revises: d54761d181d5
Create Date: 2026-03-25 18:41:03.308168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e230219c2b56'
down_revision: Union[str, Sequence[str], None] = 'd54761d181d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("asked_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_search_log_asked_at", "search_log", ["asked_at"])
    op.create_index("ix_search_log_path", "search_log", ["path"])


def downgrade() -> None:
    op.drop_index("ix_search_log_path", table_name="search_log")
    op.drop_index("ix_search_log_asked_at", table_name="search_log")
    op.drop_table("search_log")
