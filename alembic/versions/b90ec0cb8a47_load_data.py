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
import csv


# revision identifiers, used by Alembic.
revision: str = "b90ec0cb8a47"
down_revision: Union[str, Sequence[str], None] = "c196f70ad0b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

path_to_pdga_data = "data/pdga/"
path_to_seeds = "data/seed/"


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
    
    def to_bool(value: str) -> bool:
        return value.lower() in ("yes", "true", "t", "1")
    
    def get_tournaments(path_to_tournament_seed):
        with open(path_to_tournament_seed, mode='r', newline='') as seed_file:
            dictreader = csv.DictReader(seed_file)
            tournaments = []
            for tournament in dictreader:
                tournaments.append(
                    {
                        "tournament_id": tournament["tournament_id"],
                        "name": tournament["name"],
                        "start_date": tournament["start_date"],
                        "classification": tournament["classification"],
                        "director": tournament["director"],
                        "is_worlds": to_bool(tournament["is_worlds"]),
                        "total_rounds": tournament["total_rounds"],
                    }
                )
            return tournaments

    def run_upserts(
        tournaments,
        courses,
        players
    ):
        # Tournaments
        tournaments_insert = postgresql.insert(schema["tournament"]).values(tournaments)
        tournaments_upsert = tournaments_insert.on_conflict_do_nothing(
            index_elements=['tournament_id']
        )

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
        
        op.execute(tournaments_upsert)
        op.execute(courses_upsert)
        op.execute(players_upsert)
        

    tournaments = get_tournaments(path_to_seeds + "tournament_data.csv")

    for file_name in os.listdir(path_to_pdga_data):
        # read 1 round of data
        round_data = read_round("/".join([path_to_pdga_data, file_name]))

        # make list of dicts for each table
        preprocessed_round_data = round_data["data"]
        if type(preprocessed_round_data) is not list:
            preprocessed_round_data = [preprocessed_round_data]
        courses = get_courses(preprocessed_round_data)
        players = get_players(preprocessed_round_data)

        # alembic bulk upserts
        run_upserts(
            tournaments,
            courses,
            players
        )


def downgrade() -> None:
    """Truncating Tables."""
    op.execute("TRUNCATE TABLE course CASCADE;")
