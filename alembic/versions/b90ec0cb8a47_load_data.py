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
import datetime


# revision identifiers, used by Alembic.
revision: str = "b90ec0cb8a47"
down_revision: Union[str, Sequence[str], None] = "c196f70ad0b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

path_to_pdga_data = "data/pdga/"
path_to_seeds = "data/seed/"
verbose = False

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
                        "player_id": scores.get("PDGANum"),
                        "division": scores["Division"],
                    }
                )
        return players
    
    def to_bool(value: str) -> bool:
        return value.lower() in ("yes", "true", "t", "1")
    
    def get_round_info_from_file_name(file_name, tournaments):
        file_name_parts = file_name.split("_")
        tournament_id = file_name_parts[1]
        for tournament in tournaments:
            if tournament["tournament_id"] == tournament_id:
                tournament_name = tournament["name"]
                tournament_start_date = tournament["start_date"]
                year = int(tournament_start_date.split("-")[0])
                month = int(tournament_start_date.split("-")[1])
                day = int(tournament_start_date.split("-")[2])
                tournament_start_date = datetime.date(year, month, day)
                tournament_rounds = int(tournament["total_rounds"])
        round_num = file_name_parts[-1].replace(".json", "")
        round_date = tournament_start_date + datetime.timedelta(days=int(round_num)-1)
        round_info = {
            "tournament_name": tournament_name,
            "round_num": tournament_rounds if round_num == "12" else int(round_num),
            "round_date": round_date
        }
        return round_info
    
    def get_tournaments(path_to_tournament_seed):
        with open(path_to_tournament_seed, mode='r', newline='') as seed_file:
            dictreader = csv.DictReader(seed_file)
            tournaments = []
            for tournament in dictreader:
                tournaments.append(
                    {
                        "tournament_id": tournament["tournament_id"],
                        "name": tournament["name"],
                        "long_name": tournament["long_name"],
                        "start_date": tournament["start_date"],
                        "classification": tournament["classification"],
                        "director": tournament["director"],
                        "is_worlds": to_bool(tournament["is_worlds"]),
                        "total_rounds": tournament["total_rounds"],
                        "has_finals": to_bool(tournament["has_finals"]),
                    }
                )
            return tournaments
    
    def get_holes_and_rounds(data, round_date, tournament_round_num):
        holes = []
        rounds = []
        for pool in data:
            round_id = pool["live_round_id"]
            if len(pool["layouts"]) > 1:
                print('There is an issue!!')
                break
            for layout in pool["layouts"]:
                course_id = layout["CourseID"]
                layout_id = layout["LayoutID"]
                tournament_id = layout["TournID"]
                hole_detail = layout["Detail"]
                length_units = layout["Units"]
                hole_reference = {}
                for hole in hole_detail:
                    hole_reference[hole["Hole"]] = hole
                for person_round in pool["scores"]:
                    if person_round["HasRoundScore"] == 1:
                        person_round_id = person_round["ScoreID"]
                        player_id = person_round["PDGANum"]
                        won_playoff = person_round["WonPlayoff"]
                        prize = person_round["Prize"]
                        round_status = person_round["RoundStatus"]
                        hole_count = person_round["Holes"]
                        card_number = person_round["CardNum"]
                        tee_time = person_round["TeeTime"]
                        round_to_par = person_round["RoundtoPar"]
                        round_rating = person_round["RoundRating"]
                        rounds.append(
                            {
                                "round_id": person_round_id,
                                "layout_id": layout_id,
                                "course_id": course_id,
                                "player_id": player_id,
                                "tournament_id": tournament_id,
                                "tournament_round_id": round_id,
                                "tournament_round_num": tournament_round_num,
                                "won_playoff": won_playoff,
                                "prize": prize,
                                "round_status": round_status,
                                "hole_count": hole_count,
                                "card_number": card_number,
                                "tee_time": tee_time,
                                "round_rating": round_rating,
                                "round_score": round_to_par,
                                "round_date": round_date
                            }
                        )
                        for i, hole_score in enumerate(person_round["HoleScores"]):
                            hole_ref = hole_reference[f"H{i+1}"]
                            holes.append(
                                {
                                    "hole_id": str(person_round_id) + "_H" + str(i+1),
                                    "round_id": person_round_id,
                                    "player_id": player_id,
                                    "hole_number": hole_ref["HoleOrdinal"],
                                    "par": hole_ref["Par"],
                                    "length": hole_ref["Length"] if length_units == "Feet" else hole_ref["Length"]*3.280833,
                                    "score": hole_score,
                                }
                            )
        return holes, rounds

    def run_upserts(
        tournaments,
        courses,
        players,
        rounds,
        holes
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
            index_elements=['player_id']
        )

        # Rounds
        rounds_insert = postgresql.insert(schema["round"]).values(rounds)
        rounds_upsert = rounds_insert.on_conflict_do_nothing(
            index_elements=['round_id']
        )

        # Holes
        holes_insert = postgresql.insert(schema["hole"]).values(holes)
        holes_upsert = holes_insert.on_conflict_do_nothing(
            index_elements=['hole_id']
        )
        
        op.execute(tournaments_upsert)
        op.execute(courses_upsert)
        op.execute(players_upsert)
        op.execute(rounds_upsert)
        op.execute(holes_upsert)

    tournaments = get_tournaments(path_to_seeds + "tournament_data.csv")
    print("Found", len(tournaments) , "tournaments in the seed file")

    for file_name in os.listdir(path_to_pdga_data):
        # read 1 round of data
        round_data = read_round("/".join([path_to_pdga_data, file_name]))
        preprocessed_round_data = round_data["data"]
        if type(preprocessed_round_data) is not list:
            preprocessed_round_data = [preprocessed_round_data]

        round_info = get_round_info_from_file_name(file_name, tournaments)
        if verbose:
            print("Processing", round_info["tournament_name"], "round", round_info["round_num"])
        
        # make list of dicts for each table
        courses = get_courses(preprocessed_round_data)
        if verbose:
            print("Found", len(courses) , "course(s)")
        players = get_players(preprocessed_round_data)
        if verbose:
            print("Found", len(players) , "players")
        holes, rounds = get_holes_and_rounds(preprocessed_round_data, round_info["round_date"], round_info["round_num"])
        if verbose:
            print("Found", len(rounds) , "rounds played")
            print("Found", len(holes) , "holes played")

        # alembic bulk upserts
        run_upserts(
            tournaments,
            courses,
            players,
            rounds,
            holes
        )


def downgrade() -> None:
    """Truncating Tables."""
    op.execute("TRUNCATE TABLE course CASCADE;")
