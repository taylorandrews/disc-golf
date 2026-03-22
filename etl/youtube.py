"""
YouTube channel RSS scraper + JomezPro playlist scraper.

RSS feeds (15 most recent per channel) cover the preview creator channels
and supplement the Jomez coverage. The playlist scraper supplements the RSS
by fetching all videos from the current event's JomezPro playlist, which
ensures R1 and early-round videos aren't lost when Jomez posts 20+ videos
in an event week.

sort_order (from playlist index) is used for display ordering in the
coverage strip so rounds appear chronologically: R1 F9 → R1 B9 → R2 …
"""
import json
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

import requests
from sqlalchemy import text

logger = logging.getLogger(__name__)

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
_RSS_HEADERS = {"User-Agent": "disc-golf-stats/0.1", "Accept": "application/atom+xml,*/*"}
# Playlist page fetch needs a browser-like UA or YouTube returns a redirect/bot page
_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_JOMEZ_CHANNEL_ID = "UCmGyCEbHfY91NFwHgioNLMQ"
_JOMEZ_CHANNEL_NAME = "JomezPro"

CHANNELS = [
    (_JOMEZ_CHANNEL_ID, _JOMEZ_CHANNEL_NAME),
    ("UCJ5qQfW0IPRGunN3hIrrKKA", "Ezra Aderhold"),
    ("UCnTnv0pSDJjZRQlppkp0qUg", "Aaron Goosage"),
    ("UC4WJMNjQdQMwuIanr1Dfy3w", "Anthony Barela"),
    ("UCsKzQ6cQfiFrq3JRUQQKxfQ", "Ricky Wysocki"),
]

_ATOM = "http://www.w3.org/2005/Atom"
_YT = "http://www.youtube.com/xml/schemas/2015"


# ── RSS channel feed ────────────────────────────────────────────────────────

def fetch_channel(channel_id: str, channel_name: str) -> list[dict]:
    url = YOUTUBE_FEED_URL.format(channel_id=channel_id)
    resp = requests.get(url, headers=_RSS_HEADERS, timeout=15)
    resp.raise_for_status()
    return _parse_feed(resp.text, channel_id, channel_name)


def _parse_feed(xml_text: str, channel_id: str, channel_name: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    videos = []
    for entry in root.findall(f"{{{_ATOM}}}entry"):
        vid_el = entry.find(f"{{{_YT}}}videoId")
        title_el = entry.find(f"{{{_ATOM}}}title")
        pub_el = entry.find(f"{{{_ATOM}}}published")
        if vid_el is None or title_el is None or pub_el is None:
            continue
        video_id = vid_el.text.strip()
        videos.append(
            {
                "video_id": video_id,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "title": (title_el.text or "").strip(),
                "published_at": pub_el.text.strip(),
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "sort_order": None,
            }
        )
    return videos


def fetch_all_channels() -> list[dict]:
    videos = []
    for channel_id, channel_name in CHANNELS:
        try:
            channel_videos = fetch_channel(channel_id, channel_name)
            logger.info("Fetched %d videos from %s", len(channel_videos), channel_name)
            videos.extend(channel_videos)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", channel_name, exc)
    return videos


# ── JomezPro playlist scraper ───────────────────────────────────────────────

def _to_playlist_url(url: str) -> str:
    """Normalize any YouTube playlist URL to youtube.com/playlist?list=ID format.

    Handles both watch URLs (watch?v=...&list=...) and playlist URLs.
    The playlist page serves playlistVideoRenderer entries; the watch URL
    serves only a sidebar panel (playlistPanelVideoRenderer) which is harder
    to parse and may be truncated.
    """
    parsed = urlparse(url)
    list_id = parse_qs(parsed.query).get("list", [None])[0]
    if list_id:
        return f"https://www.youtube.com/playlist?list={list_id}"
    return url


def fetch_jomez_playlist(playlist_url: str) -> list[dict]:
    """Fetch all videos from a JomezPro YouTube playlist page.

    Uses ytInitialData embedded in the page HTML — no API key required.
    Returns videos with sort_order set to their playlist index so that
    R1 F9 (index 0) always sorts before R4 B9 regardless of publish date.
    """
    url = _to_playlist_url(playlist_url)
    resp = requests.get(url, headers=_PAGE_HEADERS, timeout=20)
    resp.raise_for_status()
    return _parse_playlist_page(resp.text)


def _parse_playlist_page(html: str) -> list[dict]:
    marker = "ytInitialData = "
    idx = html.find(marker)
    if idx < 0:
        logger.warning("ytInitialData not found in YouTube playlist page")
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html, idx + len(marker))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Failed to parse ytInitialData from playlist: %s", exc)
        return []

    videos = []
    for renderer in _find_key(data, "playlistVideoRenderer"):
        video_id = renderer.get("videoId", "")
        if not video_id:
            continue
        title_runs = renderer.get("title", {}).get("runs", [])
        title = title_runs[0].get("text", "").strip() if title_runs else ""
        # index is a simpleText dict e.g. {"simpleText": "3"}
        index_val = renderer.get("index", {})
        try:
            sort_order = int(
                index_val.get("simpleText", 0)
                if isinstance(index_val, dict)
                else index_val
            )
        except (ValueError, TypeError):
            sort_order = len(videos)  # fallback: insertion order

        videos.append(
            {
                "video_id": video_id,
                "channel_id": _JOMEZ_CHANNEL_ID,
                "channel_name": _JOMEZ_CHANNEL_NAME,
                "title": title,
                # published_at required by schema; sort_order drives display order
                "published_at": "2000-01-01T00:00:00+00:00",
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "sort_order": sort_order,
            }
        )

    logger.info("Parsed %d videos from JomezPro playlist", len(videos))
    return videos


def _find_key(obj, key):
    """Recursively yield all values for a given key in a nested structure."""
    if isinstance(obj, dict):
        if key in obj:
            yield obj[key]
        for v in obj.values():
            yield from _find_key(v, key)
    elif isinstance(obj, list):
        for item in obj:
            yield from _find_key(item, key)


# ── Persistence ─────────────────────────────────────────────────────────────

def save_youtube_videos(engine, videos: list[dict]) -> None:
    if not videos:
        logger.warning("No YouTube videos to save")
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO media_youtube
                    (video_id, channel_id, channel_name, title, published_at,
                     thumbnail_url, video_url, sort_order)
                VALUES
                    (:video_id, :channel_id, :channel_name, :title, :published_at,
                     :thumbnail_url, :video_url, :sort_order)
                ON CONFLICT (video_id) DO UPDATE
                    SET sort_order = COALESCE(EXCLUDED.sort_order, media_youtube.sort_order),
                        fetched_at = NOW()
                """
            ),
            videos,
        )
        result = conn.execute(
            text(
                "DELETE FROM media_youtube WHERE published_at < NOW() - INTERVAL '30 days'"
                " AND sort_order IS NULL"
            )
        )
        if result.rowcount:
            logger.info("Purged %d videos older than 30 days", result.rowcount)
    logger.info("Saved %d YouTube videos", len(videos))
