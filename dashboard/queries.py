# dashboard/queries.py

import pandas as pd
from helpers.db_config import engine
import streamlit as st

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