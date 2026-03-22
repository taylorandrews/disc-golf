# dashboard/queries.py

import datetime
import re

import pandas as pd
import streamlit as st

from helpers.db_config import engine

# --------------------------------------------------------
# Utility: Cached queries for Streamlit
# --------------------------------------------------------
@st.cache_data
def run_query(query: str, params=None) -> pd.DataFrame:
    return pd.read_sql(query, engine, params=params)


# --------------------------------------------------------
# 1. Available seasons
# --------------------------------------------------------
def get_available_seasons():
    query = """
        SELECT DISTINCT season
        FROM tournament
        ORDER BY season;
    """
    return run_query(query)["season"].tolist()


# --------------------------------------------------------
# 2. Classification counts (pie chart)
# --------------------------------------------------------
def get_classifications_for_season(season: int):
    query = f"""
        SELECT classification, tournament_count
        FROM vw_classifications_per_season
        WHERE season = {season};
    """
    return run_query(query, {"season": season})


# --------------------------------------------------------
# 3. Season summary metrics (top right)
# --------------------------------------------------------
def get_season_summary_metrics(season: int):
    query = f"""
        SELECT
            SUM(prize_usd) AS total_prize,
            MAX(CASE WHEN is_worlds THEN champion END) AS world_champ,
            MAX(CASE WHEN classification='Tour Championship' THEN champion END) AS pro_tour_champ
        FROM vw_tournament_summary
        WHERE season = {season};
    """
    return run_query(query, {"season": season}).iloc[0]


# --------------------------------------------------------
# 4. Winners and prize bar chart
# --------------------------------------------------------
def get_top_winners(season: int, limit: int = 10):
    query = f"""
        SELECT champion, COUNT(*) AS wins, SUM(prize_usd) AS total_prize
        FROM vw_tournament_summary
        WHERE season = {season}
        GROUP BY champion
        ORDER BY wins DESC
        LIMIT {limit};
    """
    return run_query(query, {"season": season, "limit": limit})


# --------------------------------------------------------
# 5. Event list for table
# --------------------------------------------------------
def get_events_for_season(season: int):
    query = f"""
        SELECT
            event_name,
            finishing_course_name,
            champion,
            prize_usd,
            start_date,
            end_date
        FROM vw_tournament_summary
        WHERE season = {season}
        ORDER BY start_date;
    """
    return run_query(query, {"season": season})


# --------------------------------------------------------
# Landing page queries — 5-minute cache (feels live)
# --------------------------------------------------------

@st.cache_data(ttl=300)
def get_last_result() -> dict:
    query = """
        SELECT
            ts.event_name,
            ts.champion,
            ts.total_score,
            ts.prize_usd,
            ts.start_date,
            ts.end_date,
            ts.is_worlds,
            ts.classification,
            t.total_rounds,
            t.location,
            t.jomez_playlist_url
        FROM vw_tournament_summary ts
        JOIN tournament t ON ts.tournament_id = t.tournament_id
        WHERE ts.end_date < CURRENT_DATE
        ORDER BY ts.end_date DESC
        LIMIT 1;
    """
    df = run_query(query)
    return df.iloc[0].to_dict() if not df.empty else {}


@st.cache_data(ttl=300)
def get_next_event() -> dict:
    query = """
        SELECT
            tournament_id,
            name AS event_name,
            classification,
            is_worlds,
            start_date,
            location,
            total_rounds
        FROM tournament
        WHERE start_date >= CURRENT_DATE
        ORDER BY start_date
        LIMIT 1;
    """
    df = run_query(query)
    return df.iloc[0].to_dict() if not df.empty else {}


@st.cache_data(ttl=300)
def get_schedule_strip(season: int) -> pd.DataFrame:
    query = f"""
        SELECT
            tournament_id,
            name AS event_name,
            classification,
            is_worlds,
            start_date,
            (start_date + (total_rounds - 1)) AS end_date,
            location
        FROM tournament
        WHERE season = {season}
        ORDER BY start_date;
    """
    return run_query(query)


@st.cache_data(ttl=300)
def get_recent_results(limit: int = 4) -> pd.DataFrame:
    query = f"""
        SELECT
            ts.event_name,
            ts.champion,
            ts.total_score,
            ts.prize_usd,
            ts.start_date,
            ts.end_date,
            t.total_rounds
        FROM vw_tournament_summary ts
        JOIN tournament t ON ts.tournament_id = t.tournament_id
        WHERE ts.end_date < CURRENT_DATE
        ORDER BY ts.end_date DESC
        LIMIT {limit};
    """
    return run_query(query)


_JOMEZ_CHANNEL = "UCmGyCEbHfY91NFwHgioNLMQ"
_PREVIEW_CHANNELS = (
    "UCJ5qQfW0IPRGunN3hIrrKKA",  # Ezra Aderhold
    "UCnTnv0pSDJjZRQlppkp0qUg",  # Aaron Goosage
    "UC4WJMNjQdQMwuIanr1Dfy3w",  # Anthony Barela
    "UCsKzQ6cQfiFrq3JRUQQKxfQ",  # Ricky Wysocki
)
_PREVIEW_CHANNEL_ORDER = {ch: i for i, ch in enumerate(_PREVIEW_CHANNELS)}

# Words too common in tournament names to be useful for matching
_STOP = frozenset(
    {"the", "a", "an", "of", "at", "in", "for", "and", "by", "to", "pro", "open",
     "presented", "disc", "golf", "dgpt", "tour"}
)


def _event_keywords(name: str) -> list[str]:
    """Return significant stems for fuzzy title matching.

    Strips stop words, removes punctuation, and drops the trailing 's' from
    each word so 'Championship' matches 'Championships' and vice versa.
    Words shorter than 3 chars after stemming are also dropped.
    """
    words = re.sub(r"[^a-z0-9 ]", "", name.lower()).split()
    stems = [w.rstrip("s") for w in words if w not in _STOP]
    return [s for s in stems if len(s) >= 3]


@st.cache_data(ttl=3600)
def get_coverage_videos(event_name: str) -> pd.DataFrame:
    """JomezPro videos whose title fuzzy-matches the given event name.

    Uses AND logic across all keyword stems so results are specific to
    the event. Returns empty DataFrame if no keywords or no matches.
    """
    keywords = _event_keywords(event_name)
    if not keywords:
        return pd.DataFrame()
    # Strip trailing 's' in the DB title too via LIKE on the stem
    # %% escapes the percent sign for psycopg2's parameter processing
    conditions = " AND ".join(
        f"LOWER(title) LIKE '%%{kw}%%'" for kw in keywords
    )
    query = f"""
        SELECT video_id, channel_name, title, published_at, thumbnail_url, video_url
        FROM media_youtube
        WHERE channel_id = '{_JOMEZ_CHANNEL}'
          AND LOWER(title) LIKE '%%mpo%%'
          AND {conditions}
        ORDER BY published_at ASC;
    """
    return run_query(query)


@st.cache_data(ttl=3600)
def get_preview_videos(start_date) -> pd.DataFrame:
    """Most recent video per preview channel posted in the 7 days before start_date.

    Returns up to 4 rows (one per channel) sorted by channel priority:
    Aderhold → Goosage → Barela → Wysocki.
    """
    ch_list = ", ".join(f"'{c}'" for c in _PREVIEW_CHANNELS)
    query = f"""
        SELECT DISTINCT ON (channel_id)
            channel_id, channel_name, title, published_at, thumbnail_url, video_url
        FROM media_youtube
        WHERE channel_id IN ({ch_list})
          AND published_at >= '{start_date}'::date - INTERVAL '6 days'
          AND published_at <  '{start_date}'::date + INTERVAL '1 day'
        ORDER BY channel_id, published_at DESC;
    """
    df = run_query(query)
    if not df.empty:
        df["_order"] = df["channel_id"].map(_PREVIEW_CHANNEL_ORDER)
        df = df.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return df


@st.cache_data(ttl=300)
def get_season_standings_top5(season: int) -> pd.DataFrame:
    query = f"""
        SELECT rank, player_name, total_points
        FROM season_standings
        WHERE season = {season}
        ORDER BY rank
        LIMIT 5;
    """
    return run_query(query)


@st.cache_data(ttl=300)
def get_stat_callout(season: int) -> dict:
    """Returns the most interesting derived stat for the season.
    Priority: lowest winning score, then highest round rating.
    Returns empty dict if no data exists yet.
    """
    query = f"""
        SELECT
            ts.champion,
            ts.event_name,
            ts.total_score,
            t.total_rounds
        FROM vw_tournament_summary ts
        JOIN tournament t ON ts.tournament_id = t.tournament_id
        WHERE ts.season = {season}
        ORDER BY ts.total_score ASC
        LIMIT 1;
    """
    df = run_query(query)
    if df.empty:
        return {}
    row = df.iloc[0]
    score = int(row["total_score"])
    score_str = f"{score:+d}" if score != 0 else "E"
    rounds = int(row["total_rounds"])
    return {
        "number": score_str,
        "subject": row["champion"],
        "context": f"winning score at the {row['event_name']}",
        "detail": f"The lowest {rounds * 18}-hole winning total of the {season} season",
    }