"""create tables for new PDGA schema

Revision ID: c196f70ad0b6
Revises:
Create Date: 2025-10-18 16:45:00.000000

"""

from typing import Sequence, Union
from helpers.disc_golf_schema import schema

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c196f70ad0b6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """
    Create Table
    Based on the schema defined in helpers/disc_golf_schema.py
    """

    for table_name in schema:
        op.create_table(table_name, *schema[table_name].columns)

def downgrade():
    op.drop_table("hole")
    op.drop_table("round")
    op.drop_table("tournament")
    op.drop_table("course")
    op.drop_table("player")
