import requests
import json
import csv
from pathlib import Path

path_to_tournament_seed = "data/seed/tournament_data.csv"
data_path = "data"
dry_run = False
downloaded_tournaments = [
    "88276",
    "88277",
    "88279",
    "88282",
    "88283",
    "88638",
    "88284",
    "88285",
    "88286",
    "88287",
    "88357",
    "88288",
    "88289",
    "90652",
    "89546",
    "90947",
    "88290",
    "88293",
    "88294",
    "88296",
    "88299",
    "88301",
    "88302",
    "88656",
    "77775",
    "77758",
    "77759",
    "77760",
    "77761",
    "77762",
    "77099",
    "77763",
    "78193",
    "77764",
    "77765",
    "77766",
    "78194",
    "78271",
    "78195",
    "77768",
    "78196",
    "77750",
    "78197",
    "77769",
    "77771",
    "71315",
    "77772",
    "82419",
    "77773",
    "77098",
    "77774",
    "68353",
    "64036",
    "67202",
    "65115",
    "66174",
    "65116",
    "68748",
    "65291",
    "64957",
    "74356",
    "65206",
    "66457",
    "65288",
    "65208",
    "64955",
    "66458",
    "65207",
    "69022",
    "65289",
    "67392",
    "55589",
    "56013",
    "55590",
    "55591",
    "55592",
    "55460",
    "55593",
    "55594",
    "55454",
    "55595",
    "55580",
    "55582",
    "55583",
    "55451",
    "55584",
    "55585",
    "55586",
    "55587",
    "55588",
    "48338",
    "48687",
    "47981",
    "48688",
    "47520",
    "49214",
    "48690",
    "47541",
    "47518",
    "48691",
    "47877",
    "48685",
    "47512",
    "48567",
    "47516",
    "48172",
    "47514",
    "48686",
    "47784",
    "52009",
    "44118",
    "44144",
    "45796",
    "45795",
    "44224",
    "43983",
    "43452",
    "44114",
    "44653",
    "43778",
    "43487",
    "43838",
    "44743",
    "38343",
    "38761",
    "38890",
    "38682",
    "38471",
    "39807",
    "40686",
    "38977",
    "38717",
    "39325",
    "38397",
    "38723",
    "38709",
    "38851",
    "38873"
    "40853",
    "39018",
    "38694",
    "42360",
    "38873",
    "40853",
    "33918",
    "34199",
    "34296",
    "34148",
    "33792",
    "34183",
    "34075",
    "34700",
    "34230",
    "34293",
    "34137",
    "34303",
    "35080",
    "33793",
    "34029",
    "33791",
    "35294",
    "30419",
    "30420",
    "30465",
    "30708",
    "30418",
    "30675",
    "30323",
    "30813",
    "31709",
    "30714",
    "30783",
    "30581",
    "30556",
    "30695",
    "31940",
    "30560",
    "31385",
    "31343",
    "32553",
    "33862",
    "22242",
    "22228",
    "22243",
    "22230",
    "22229",
    "24333",
    "22296",
    "24341",
    "24339",
    "22317",
    "25011",
    "22313",
    "24684",
    "24328",
    "26568"
]

skip_for_now = [
]

def to_bool(value: str) -> bool:
    return value.lower() in ("yes", "true", "t", "1")

def get_rounds_nums_list(total_rounds, has_finals):
    round_list = []
    for i in range(1, int(total_rounds)+1):
        round_list.append(str(i))
    
    if to_bool(has_finals):
        round_list = round_list[:-1]
        round_list.append("12")
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
                        "long_name": tournament["long_name"],
                        "start_date": tournament["start_date"],
                        "classification": tournament["classification"],
                        "director": tournament["director"],
                        "is_worlds": to_bool(tournament["is_worlds"]),
                        "total_rounds": tournament["total_rounds"],
                        "has_finals": tournament["has_finals"],
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
        if tournament_id in downloaded_tournaments or tournament_id in skip_for_now:
            continue
        round_list = get_rounds_nums_list(tournament["total_rounds"], tournament["has_finals"])
        for i, api_round_num in enumerate(round_list):
            division = "MPO"
            round_data = fetch_pdga_round(tournament_id, division, api_round_num)
            write_path = Path(f"{data_path}/temp/tournament_{tournament_id}_{division}_round_{i+1}.json")
            write_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to file with pretty-printing
            with write_path.open("w", encoding="utf-8") as f:
                json.dump(round_data, f, indent=2)

            print(f"Saved JSON to {write_path.resolve()}")