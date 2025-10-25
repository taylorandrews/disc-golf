"""Create insert statements from data

Revision ID: b90ec0cb8a47
Revises: c196f70ad0b6
Create Date: 2025-10-18 16:30:52.717929

"""

from typing import Sequence, Union
from helpers.disc_golf_schema import schema

from alembic import op
import sqlalchemy as sa
import os
import json


# revision identifiers, used by Alembic.
revision: str = "b90ec0cb8a47"
down_revision: Union[str, Sequence[str], None] = "c196f70ad0b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

path_to_data = "data/tournament_90947_MPO_round12.json"


def upgrade() -> None:
    """Loading Data."""

    def read_data():
        with open(path_to_data, "r") as file:
            data_str = file.read()
            data = json.loads(data_str)
        return data

    def get_courses(data):
        courses = []
        for pool in data["data"]:
            for layout in pool["layouts"]:
                if not layout["Name"] == "Default Layout":
                    courses.append(
                        {
                            "course_id": layout["CourseID"],
                            "course_name": layout["CourseName"],
                            "name": layout["Name"],
                            "holes": layout["Holes"],
                            "par": layout["Par"],
                            "length": layout["Length"],
                            "units": layout["Units"],
                        }
                    )
        return courses

    def run_inserts(courses):
        tables = {
            "course": schema["course"]
        }
        op.bulk_insert(tables["course"], courses)

    data = read_data()
    courses = get_courses(data)
    # TODO: add more get functions here

    run_inserts(courses)


def downgrade() -> None:
    """Truncating Tables."""
    op.execute("TRUNCATE TABLE course CASCADE;")
