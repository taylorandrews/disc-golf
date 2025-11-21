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
    def read_round(file_path):
        with open(file_path, "r") as file:
            data_str = file.read()
            data = json.loads(data_str)
        return data

    def get_courses(data):
        courses = []
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
        for pool in data:
            for scores in pool["scores"]:
                players.append(
                    {
                        "first_name": scores["FirstName"],
                        "last_name": scores["LastName"],
                        "city": scores["City"],
                        "country": scores["Country"],
                        "state": scores["StateProv"],
                        "pdga_number": scores.get("PDGANum"),
                        "division": scores["Division"],
                    }
                )
        return players

    def run_inserts(courses):
        tables = {
            "course": schema["course"]
        }
        op.bulk_insert(tables["course"], courses)

    def run_upserts(courses):
        # Courses
        courses_insert = postgresql.insert(schema["course"]).values(courses)
        courses_upsert = courses_insert.on_conflict_do_nothing(
            index_elements=['course_id']
        )

        # Players
        players_insert = postgresql.insert(schema["player"]).values(players)
        players_upsert = players_insert.on_conflict_do_nothing(
            index_elements=['pdga_number']
        )

        op.execute(courses_upsert)
        op.execute(players_upsert)

    for file_name in os.listdir(path_to_data):
        # read 1 round of data
        round_data = read_round("/".join([path_to_data, file_name]))

        # make list of dicts for each table
        preprocessed_round_data = round_data["data"]
        if type(preprocessed_round_data) is not list:
            preprocessed_round_data = [preprocessed_round_data]
        courses = get_courses(preprocessed_round_data)
        players = get_players(preprocessed_round_data)

        # alembic bulk inserts/upserts
        run_upserts(courses)
        # run_inserts(players)


def downgrade() -> None:
    """Truncating Tables."""
    op.execute("TRUNCATE TABLE course CASCADE;")
