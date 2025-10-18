"""Create insert statements from data

Revision ID: b90ec0cb8a47
Revises: c196f70ad0b6
Create Date: 2025-10-18 16:30:52.717929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b90ec0cb8a47'
down_revision: Union[str, Sequence[str], None] = 'c196f70ad0b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Loading Data."""
    pass


def downgrade() -> None:
    """Truncating Tables."""
    pass
