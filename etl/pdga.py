"""
PDGA API fetch and S3 persistence helpers.
"""
import json
import time

import boto3
import requests

PDGA_LIVE_API = (
    "https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round"
    "?TournID={tourn_id}&Division=MPO&Round={round_num}"
)
HEADERS = {
    "User-Agent": "disc-golf-stats/0.1",
    "Accept": "application/json",
}
REQUEST_DELAY = 0.5  # seconds between PDGA API calls


def api_round_num(sequential: int, total_rounds: int, has_finals: bool) -> int:
    """Map sequential round number (1..N) to the PDGA API round number.
    Finals are always round 12 in the PDGA API regardless of their sequential position.
    """
    if has_finals and sequential == total_rounds:
        return 12
    return sequential


def fetch_round(tourn_id: int, pdga_round: int) -> dict:
    url = PDGA_LIVE_API.format(tourn_id=tourn_id, round_num=pdga_round)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY)
    return resp.json()


def s3_key(tourn_id: int, sequential: int) -> str:
    return f"raw/pdga/2026/{tourn_id}/tournament_{tourn_id}_MPO_round_{sequential}.json"


def save_to_s3(data: dict, bucket: str, tourn_id: int, sequential: int) -> None:
    key = s3_key(tourn_id, sequential)
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType="application/json",
    )
