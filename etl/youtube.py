"""
YouTube channel RSS scraper.

Fetches the 15 most recent videos from each tracked channel via YouTube's
public Atom feeds (no API key required) and upserts into media_youtube.

Channels:
  - JomezPro          (recent tournament coverage — 3A)
  - Ezra Aderhold     (course previews — 3B)
  - Aaron Goosage     (course previews — 3B)
  - Anthony Barela    (course previews — 3B)
  - Ricky Wysocki     (course previews — 3B)
"""
import logging
import xml.etree.ElementTree as ET

import requests
from sqlalchemy import text

logger = logging.getLogger(__name__)

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
HEADERS = {"User-Agent": "disc-golf-stats/0.1", "Accept": "application/atom+xml,*/*"}

CHANNELS = [
    ("UCmGyCEbHfY91NFwHgioNLMQ", "JomezPro"),
    ("UCJ5qQfW0IPRGunN3hIrrKKA", "Ezra Aderhold"),
    ("UCnTnv0pSDJjZRQlppkp0qUg", "Aaron Goosage"),
    ("UC4WJMNjQdQMwuIanr1Dfy3w", "Anthony Barela"),
    ("UCsKzQ6cQfiFrq3JRUQQKxfQ", "Ricky Wysocki"),
]

_ATOM = "http://www.w3.org/2005/Atom"
_YT = "http://www.youtube.com/xml/schemas/2015"


def fetch_channel(channel_id: str, channel_name: str) -> list[dict]:
    url = YOUTUBE_FEED_URL.format(channel_id=channel_id)
    resp = requests.get(url, headers=HEADERS, timeout=15)
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


def save_youtube_videos(engine, videos: list[dict]) -> None:
    if not videos:
        logger.warning("No YouTube videos to save")
        return
    with engine.begin() as conn:
        # Upsert — update fetched_at on re-fetch so retention logic works correctly
        conn.execute(
            text(
                """
                INSERT INTO media_youtube
                    (video_id, channel_id, channel_name, title, published_at,
                     thumbnail_url, video_url)
                VALUES
                    (:video_id, :channel_id, :channel_name, :title, :published_at,
                     :thumbnail_url, :video_url)
                ON CONFLICT (video_id) DO UPDATE
                    SET fetched_at = NOW()
                """
            ),
            videos,
        )
        # Purge videos older than 30 days to prevent unbounded growth
        result = conn.execute(
            text(
                "DELETE FROM media_youtube WHERE published_at < NOW() - INTERVAL '30 days'"
            )
        )
        if result.rowcount:
            logger.info("Purged %d videos older than 30 days", result.rowcount)
    logger.info("Saved %d YouTube videos", len(videos))
