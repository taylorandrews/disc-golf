import requests
import json
import csv
from pathlib import Path

path_to_tournament_seed = "data/seed/tournament_data.csv"
data_path = "data"
dry_run = True

def to_bool(value: str) -> bool:
    return value.lower() in ("yes", "true", "t", "1")

def get_rounds_nums_list(total_rounds):
    round_list = ["1", "2"]
    if total_rounds == "3":
        round_list += ["3"]
    elif total_rounds == "4":
        round_list += ["3", "4"]
    elif total_rounds == "5":
        round_list += ["3", "4", "12"]
    
    return round_list
    

def get_round_seed_data(path_to_tournament_seed):
    tournaments = []
    with open(path_to_tournament_seed, mode='r', newline='') as seed_file:
        dictreader = csv.DictReader(seed_file)
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

def fetch_pdga_round(tourn_id: int, division: str, round: int):
    """
    Fetch PDGA live JSON data for a given tournament, division, and round.
    """
    url = (
        "https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round"
        f"?TournID={tourn_id}&Division={division}&Round={round}"
    )
    headers = {
        "User-Agent": "my-pdga-scraper/0.1 (your_email@example.com)",
        "Accept": "application/json",
    }
    if not dry_run:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    else:
        print(f"requests.get({url}, headers=headers, timeout=20)")
        return {}

if __name__ == "__main__":
    tournaments = get_round_seed_data(path_to_tournament_seed)

    for tournament in tournaments:
        tournament_id = tournament["tournament_id"]
        round_list = get_rounds_nums_list(tournament["total_rounds"])
        for round in round_list:
            division = "MPO"
            round_data = fetch_pdga_round(tournament_id, division, round)
            write_path = Path(f"{data_path}/test/tournament_{tournament_id}_{division}_round_{round}.json")

            # Save to file with pretty-printing
            with write_path.open("w", encoding="utf-8") as f:
                json.dump(round_data, f, indent=2)

            print(f"Saved JSON to {write_path.resolve()}")