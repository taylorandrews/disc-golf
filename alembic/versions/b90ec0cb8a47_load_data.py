"""Create insert statements from data

Revision ID: b90ec0cb8a47
Revises: c196f70ad0b6
Create Date: 2025-10-18 16:30:52.717929

"""

from typing import Sequence, Union
from helpers.disc_golf_schema import schema

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import os
import json


# revision identifiers, used by Alembic.
revision: str = "b90ec0cb8a47"
down_revision: Union[str, Sequence[str], None] = "c196f70ad0b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

path_to_data = "data/"


def upgrade() -> None:
    """Loading Data."""
    # setup
    # meta = sa.MetaData(bind=op.get_bind())

    def read_round(file_path):
        with open(file_path, "r") as file:
            data_str = file.read()
            data = json.loads(data_str)
        return data

    def get_courses(data):
        courses = []
        data = data["data"]
        if type(data) is not list:
            data = [data]
        for pool in data:
            for layout in pool["layouts"]:
                if not layout["Name"] == "Default Layout":
                    courses.append(
                        {
                            "course_id": layout["CourseID"],
                            "course_name": layout["CourseName"],
                            "name": layout["Name"],
                            "holes": layout["Holes"],
                            "units": layout["Units"],
                        }
                    )
        return courses
    
    def get_players(data):
        players = []
        for player in data["players"]:
            players.append(
                {
                }
            )
        return players

    def run_inserts(courses):
        tables = {
            "course": schema["course"]
        }
        op.bulk_insert(tables["course"], courses)

    def run_upserts(courses):
        insert_stmt = postgresql.insert(schema["course"]).values(courses)

        on_conflict_stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=['course_id'] # Specify the column(s) that define uniqueness
        )

        op.execute(on_conflict_stmt)

    for file_name in os.listdir(path_to_data):
        # read 1 round of data
        round_data = read_round("/".join([path_to_data, file_name]))

        # make list of dicts for each table
        courses = get_courses(round_data)
        # players = get_players(round_data)

        # alembic bulk inserts
        run_upserts(courses)
        # run_inserts(players)


def downgrade() -> None:
    """Truncating Tables."""
    op.execute("TRUNCATE TABLE course CASCADE;")
