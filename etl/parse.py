"""
Parse PDGA live-results JSON into dicts ready for DB upsert.

Extracted from alembic/versions/b90ec0cb8a47_load_data.py so that the same
logic can be used by the Lambda ETL without importing Alembic.
"""
import datetime
import logging

logger = logging.getLogger(__name__)


def get_courses(data: list, year: int, round_num: int) -> list[dict]:
    courses = []
    for pool_idx, pool in enumerate(data):
        for layout in pool.get("layouts", []):
            try:
                courses.append({
                    "course_id": int(str(layout["LayoutID"]) + str(year) + str(round_num)),
                    "course_name": layout["CourseName"],
                    "name": layout["Name"],
                    "holes": layout["Holes"],
                    "units": layout["Units"],
                })
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping layout in pool %d (round %d): %s — raw: %s",
                    pool_idx, round_num, exc, layout,
                )
    return courses


def get_players(data: list) -> list[dict]:
    players = []
    for pool_idx, pool in enumerate(data):
        for scores in pool.get("scores", []):
            if scores.get("HasPDGANum") != 1:
                continue
            try:
                players.append({
                    "first_name": scores["FirstName"],
                    "last_name": scores["LastName"],
                    "city": scores.get("City"),
                    "country": scores.get("Country"),
                    "state": scores.get("StateProv"),
                    "player_id": scores["PDGANum"],
                    "division": scores["Division"],
                })
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "Skipping player in pool %d: %s — name: %s %s",
                    pool_idx, exc,
                    scores.get("FirstName"), scores.get("LastName"),
                )
    return players


def _parse_prize(prize_raw) -> int | None:
    if not prize_raw:
        return None
    try:
        cleaned = (
            str(prize_raw)
            .replace("$", "")
            .replace(",", "")
            .replace("&euro;", "")
            .strip()
        )
        return int(float(cleaned)) if cleaned else None
    except (ValueError, TypeError):
        logger.warning("Could not parse prize value %r — storing None", prize_raw)
        return None


def get_holes_and_rounds(
    data: list,
    round_date: datetime.date,
    tournament_round_num: int,
    year: int,
    round_num: int,
) -> tuple[list[dict], list[dict]]:
    holes = []
    rounds = []
    for pool_idx, pool in enumerate(data):
        round_id = pool.get("live_round_id")
        if round_id is None:
            logger.warning("Pool %d missing live_round_id — skipping pool", pool_idx)
            continue

        layouts = pool.get("layouts", [])
        if not layouts:
            logger.warning("Pool %d (round_id=%s) has no layouts", pool_idx, round_id)
            continue

        for layout in layouts:
            try:
                course_id = int(str(layout["LayoutID"]) + str(year) + str(round_num))
                layout_id = layout["LayoutID"]
                tournament_id = layout["TournID"]
                hole_detail = layout.get("Detail", [])
                length_units = layout.get("Units", "Feet")
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping layout in pool %d (round_id=%s): %s", pool_idx, round_id, exc
                )
                continue

            hole_reference = {hole["Hole"]: hole for hole in hole_detail if "Hole" in hole}

            for person_round in pool.get("scores", []):
                if person_round.get("HasPDGANum") != 1:
                    continue
                if not (person_round.get("RoundStarted") == 1 or person_round.get("Completed") == 1):
                    continue

                player_id = person_round.get("PDGANum")
                player_name = f"{person_round.get('FirstName')} {person_round.get('LastName')}"

                try:
                    score_id = person_round.get("ScoreID")
                    result_id = person_round.get("ResultID")
                    if score_id:
                        person_round_id = score_id
                    elif result_id:
                        person_round_id = int(f"{result_id}{tournament_round_num}")
                    else:
                        logger.warning(
                            "Player %s (pool %d) has no ScoreID or ResultID — skipping",
                            player_name, pool_idx,
                        )
                        continue

                    rounds.append({
                        "round_id": person_round_id,
                        "layout_id": layout_id,
                        "course_id": course_id,
                        "player_id": player_id,
                        "tournament_id": tournament_id,
                        "tournament_round_id": round_id,
                        "tournament_round_num": tournament_round_num,
                        "won_playoff": person_round.get("WonPlayoff"),
                        "prize": _parse_prize(person_round.get("Prize")),
                        "prize_currency": (
                            "EUR" if "euro" in str(person_round.get("Prize", "")) else "USD"
                        ),
                        "round_status": person_round.get("RoundStatus"),
                        "hole_count": person_round.get("Holes"),
                        "card_number": person_round.get("CardNum"),
                        "tee_time": person_round.get("TeeTime"),
                        "round_rating": person_round.get("RoundRating"),
                        "round_score": person_round.get("RoundtoPar"),
                        "round_date": round_date,
                    })
                except Exception as exc:
                    logger.warning(
                        "Skipping round for player %s (pool %d): %s",
                        player_name, pool_idx, exc,
                    )
                    continue

                hole_scores = person_round.get("HoleScores", [])
                for i, hole_score in enumerate(hs for hs in hole_scores if hs != ""):
                    hole_key = f"H{i + 1}"
                    hole_ref = hole_reference.get(hole_key)
                    if hole_ref is None:
                        logger.warning(
                            "Missing hole reference %s for player %s round %s — skipping hole",
                            hole_key, player_name, person_round_id,
                        )
                        continue
                    try:
                        raw_length = hole_ref.get("Length") or 0
                        length = (
                            raw_length if length_units == "Feet" else raw_length * 3.280833
                        )
                        holes.append({
                            "hole_id": f"{person_round_id}_H{i + 1}",
                            "round_id": person_round_id,
                            "player_id": player_id,
                            "hole_number": hole_ref["HoleOrdinal"],
                            "par": hole_ref["Par"],
                            "length": length,
                            "score": hole_score,
                        })
                    except Exception as exc:
                        logger.warning(
                            "Skipping hole %s for player %s: %s", hole_key, player_name, exc
                        )

    return holes, rounds
