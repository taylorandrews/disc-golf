import requests
import json
from pathlib import Path

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
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    # 2025 MPO World Championships
    # tourn_id = 90947
    # division = "MPO"
    # rounds = [1, 2, 3, 4, 12]

    # 2025 Supreme Flight Open
    tourn_id = 88276
    division = "MPO"
    rounds = [1, 2, 3]

    for round in rounds:
        round_data = fetch_pdga_round(tourn_id, division, round)

        # Pick a filename that encodes what this file is
        out_path = Path(f"data/tournament_{tourn_id}_{division}_round_{round}.json")

        # Save to file with pretty-printing
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(round_data, f, indent=2)

        print(f"Saved JSON to {out_path.resolve()}")