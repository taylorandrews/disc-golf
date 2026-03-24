"""
Podcast RSS scraper.

Fetches the most recent episode from each tracked show and upserts into
podcast_episodes. One row per episode_guid — ON CONFLICT DO NOTHING so
historical episodes are never overwritten.

Retention: keeps last 5 episodes per show, deleting older ones to prevent
unbounded growth while preserving a small backlog.
"""
import logging
import re
import xml.etree.ElementTree as ET

import requests
from sqlalchemy import text

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "disc-golf-stats/0.1", "Accept": "application/rss+xml,*/*"}

SHOWS = [
    ("The Upshot", "https://www.spreaker.com/show/1765686/episodes/feed"),
    ("Tour Life", "https://feeds.simplecast.com/kkFf91zi"),
    ("Grip Locked", "https://feeds.simplecast.com/WCZ5a8oV"),
    ("Course Maintenance", "https://media.rss.com/coursemaintenance/feed.xml"),
]

_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def _parse_duration(raw: str) -> int | None:
    """Convert itunes:duration to seconds. Handles HH:MM:SS, MM:SS, and raw seconds."""
    if not raw:
        return None
    raw = raw.strip()
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(raw)
    except (ValueError, IndexError):
        return None


def _best_link(item: ET.Element) -> str:
    """Return the best episode URL from an RSS item."""
    # Prefer <link> text; fall back to enclosure url attribute
    link = item.findtext("link", "").strip()
    if link:
        return link
    enclosure = item.find("enclosure")
    if enclosure is not None:
        return enclosure.get("url", "").strip()
    return ""


def fetch_show(show_name: str, feed_url: str) -> list[dict]:
    resp = requests.get(feed_url, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    return _parse_feed(resp.text, show_name)


def _parse_feed(xml_text: str, show_name: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []

    episodes = []
    for item in channel.findall("item")[:5]:
        guid = (item.findtext("guid") or "").strip()
        title = (item.findtext("title") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        duration_raw = (
            item.findtext(f"{{{_ITUNES}}}duration") or
            item.findtext("itunes:duration") or
            ""
        )
        url = _best_link(item)

        if not guid or not title or not pub_date or not url:
            continue

        episodes.append({
            "episode_guid": guid,
            "show_name": show_name,
            "episode_title": title,
            "published_at": pub_date,
            "duration_secs": _parse_duration(duration_raw),
            "episode_url": url,
        })

    return episodes


def fetch_all_shows() -> list[dict]:
    all_episodes = []
    for show_name, feed_url in SHOWS:
        try:
            episodes = fetch_show(show_name, feed_url)
            logger.info("Fetched %d episodes from %s", len(episodes), show_name)
            all_episodes.extend(episodes)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", show_name, exc)
    return all_episodes


def save_podcast_episodes(engine, episodes: list[dict]) -> None:
    if not episodes:
        logger.warning("No podcast episodes to save")
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO podcast_episodes
                    (episode_guid, show_name, episode_title, published_at,
                     duration_secs, episode_url)
                VALUES
                    (:episode_guid, :show_name, :episode_title, :published_at,
                     :duration_secs, :episode_url)
                ON CONFLICT (episode_guid) DO NOTHING
                """
            ),
            episodes,
        )
        # Keep only the 5 most recent episodes per show
        conn.execute(
            text(
                """
                DELETE FROM podcast_episodes
                WHERE episode_guid IN (
                    SELECT episode_guid FROM (
                        SELECT episode_guid,
                               ROW_NUMBER() OVER (
                                   PARTITION BY show_name
                                   ORDER BY published_at DESC
                               ) AS rn
                        FROM podcast_episodes
                    ) ranked
                    WHERE rn > 5
                )
                """
            )
        )
    logger.info("Saved %d podcast episodes", len(episodes))
