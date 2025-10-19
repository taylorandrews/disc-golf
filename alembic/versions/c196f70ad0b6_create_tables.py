"""create tables for new PDGA schema

Revision ID: c196f70ad0b6
Revises:
Create Date: 2025-10-18 16:45:00.000000

"""

from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa

from helpers.disc_golf_schema import schema

# revision identifiers, used by Alembic.
revision: str = "c196f70ad0b6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # with open(path_to_schema, "r") as file:
    #     schema_str = file.read()
    #     schema = json.loads(schema_str)

    # # Player table
    # op.create_table(
    #     "player",
    #     sa.Column("player_id", sa.Integer, primary_key=True),
    #     sa.Column("name", sa.Text, nullable=False),
    #     sa.Column("state", sa.Text),
    #     sa.Column("dob", sa.Date),
    # )

    # Course table
    op.create_table(
        "course",
        schema["courses"]
    )

    # # Tournament table
    # op.create_table(
    #     "tournament",
    #     sa.Column("tournament_id", sa.Integer, primary_key=True),
    #     sa.Column("name", sa.Text, nullable=False),
    #     sa.Column("year", sa.Integer),
    #     sa.Column("classification", sa.Text),
    #     sa.Column("total_rounds", sa.Integer),
    #     sa.Column("cutoff_score", sa.Integer),
    #     sa.Column("cutoff_day", sa.Text),
    # )

    # # Round table
    # op.create_table(
    #     "round",
    #     sa.Column("round_id", sa.Integer, primary_key=True),
    #     sa.Column(
    #         "tournament_id",
    #         sa.Integer,
    #         sa.ForeignKey("tournament.tournament_id"),
    #         nullable=False,
    #     ),
    #     sa.Column("tournament_round_num", sa.Integer, nullable=False),
    #     sa.Column("tee_time", sa.DateTime, nullable=False),
    #     sa.Column("course_id", sa.Integer, sa.ForeignKey("course.course_id"), nullable=False),
    #     sa.Column("player_id", sa.Integer, sa.ForeignKey("player.player_id"), nullable=False),
    #     sa.Column("score", sa.Integer),
    #     sa.Column("date", sa.Date),
    # )

    # # Hole table
    # op.create_table(
    #     "hole",
    #     sa.Column("hole_id", sa.Integer, primary_key=True),
    #     sa.Column("course_id", sa.Integer, sa.ForeignKey("course.course_id"), nullable=False),
    #     sa.Column("round_id", sa.Integer, sa.ForeignKey("round.round_id"), nullable=False),
    #     sa.Column("hole_number", sa.Integer, nullable=False),
    #     sa.Column("par", sa.Integer),
    #     sa.Column("distance", sa.Integer),
    #     sa.Column("score", sa.Integer),
    # )


def downgrade():
    # op.drop_table("hole")
    # op.drop_table("round")
    # op.drop_table("tournament")
    op.drop_table("course")
    # op.drop_table("player")
