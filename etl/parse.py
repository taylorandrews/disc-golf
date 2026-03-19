"""
Parse PDGA live-results JSON into dicts ready for DB upsert.

Extracted from alembic/versions/b90ec0cb8a47_load_data.py so that the same
logic can be used by the Lambda ETL without importing Alembic.
"""
import datetime


def get_courses(data: list, year: int, round_num: int) -> list[dict]:
    courses = []
    for pool in data:
        for layout in pool["layouts"]:
            courses.append({
                "course_id": int(str(layout["LayoutID"]) + str(year) + str(round_num)),
                "course_name": layout["CourseName"],
                "name": layout["Name"],
                "holes": layout["Holes"],
                "units": layout["Units"],
            })
    return courses


def get_players(data: list) -> list[dict]:
    players = []
    for pool in data:
        for scores in pool["scores"]:
            if scores["HasPDGANum"] == 1:
                players.append({
                    "first_name": scores["FirstName"],
                    "last_name": scores["LastName"],
                    "city": scores["City"],
                    "country": scores["Country"],
                    "state": scores["StateProv"],
                    "player_id": scores.get("PDGANum"),
                    "division": scores["Division"],
                })
    return players


def get_holes_and_rounds(
    data: list,
    round_date: datetime.date,
    tournament_round_num: int,
    year: int,
    round_num: int,
) -> tuple[list[dict], list[dict]]:
    holes = []
    rounds = []
    for pool in data:
        round_id = pool["live_round_id"]
        for layout in pool["layouts"]:
            course_id = int(str(layout["LayoutID"]) + str(year) + str(round_num))
            layout_id = layout["LayoutID"]
            tournament_id = layout["TournID"]
            hole_detail = layout["Detail"]
            length_units = layout["Units"]
            hole_reference = {hole["Hole"]: hole for hole in hole_detail}
            for person_round in pool["scores"]:
                if person_round["HasPDGANum"] == 1 and (
                    person_round["RoundStarted"] == 1 or person_round["Completed"] == 1
                ):
                    person_round_id = (
                        person_round["ScoreID"]
                        if person_round["ScoreID"]
                        else int(f"{person_round['ResultID']}{tournament_round_num}")
                    )
                    player_id = person_round["PDGANum"]
                    prize_raw = person_round["Prize"]
                    prize = (
                        prize_raw.replace("$", "").replace(",", "").replace("&euro;", "")
                        if prize_raw
                        else None
                    )
                    prize_currency = "EUR" if "euro" in str(prize_raw) else "USD"
                    rounds.append({
                        "round_id": person_round_id,
                        "layout_id": layout_id,
                        "course_id": course_id,
                        "player_id": player_id,
                        "tournament_id": tournament_id,
                        "tournament_round_id": round_id,
                        "tournament_round_num": tournament_round_num,
                        "won_playoff": person_round["WonPlayoff"],
                        "prize": prize,
                        "prize_currency": prize_currency,
                        "round_status": person_round["RoundStatus"],
                        "hole_count": person_round["Holes"],
                        "card_number": person_round["CardNum"],
                        "tee_time": person_round["TeeTime"],
                        "round_rating": person_round["RoundRating"],
                        "round_score": person_round["RoundtoPar"],
                        "round_date": round_date,
                    })
                    for i, hole_score in enumerate(
                        [hs for hs in person_round["HoleScores"] if hs != ""]
                    ):
                        hole_ref = hole_reference[f"H{i+1}"]
                        holes.append({
                            "hole_id": str(person_round_id) + "_H" + str(i + 1),
                            "round_id": person_round_id,
                            "player_id": player_id,
                            "hole_number": hole_ref["HoleOrdinal"],
                            "par": hole_ref["Par"],
                            "length": (
                                hole_ref["Length"]
                                if length_units == "Feet"
                                else hole_ref["Length"] * 3.280833
                            ),
                            "score": hole_score,
                        })
    return holes, rounds
