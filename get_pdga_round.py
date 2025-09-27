import requests
import json
from pathlib import Path

def fetch_pdga_round(tourn_id: int, division: str, round_num: int):
    """
    Fetch PDGA live JSON data for a given tournament, division, and round.
    """
    url = (
        "https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round"
        f"?TournID={tourn_id}&Division={division}&Round={round_num}"
    )
    headers = {
        "User-Agent": "my-pdga-scraper/0.1 (your_email@example.com)",
        "Accept": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    tourn_id = 90947
    division = "MPO"
    round_num = 12

    data = fetch_pdga_round(tourn_id, division, round_num)

    # Pick a filename that encodes what this file is
    out_path = Path(f"tournament_{tourn_id}_{division}_round{round_num}.json")

    # Save to file with pretty-printing
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Saved JSON to {out_path.resolve()}")