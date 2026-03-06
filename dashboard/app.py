import streamlit as st
import plotly.express as px

from queries import (
    get_available_seasons,
    get_classifications_for_season,
    get_season_summary_metrics,
    get_top_winners,
    get_events_for_season,
)

# ----------------------------
# Main Streamlit App
# ----------------------------
def main():
    st.set_page_config(page_title="Disc Golf Dashboard", layout="wide")
    st.title("Disc Golf Dashboard")

    # ----------------------------
    # Tabs for seasons
    # ----------------------------
    seasons = get_available_seasons()
    latest_season_idx = len(seasons) - 1  # latest season index
    tabs = st.tabs([str(s) for s in seasons])

    for i, tab in enumerate(tabs):
        with tab:
            season = seasons[i]
            st.header(f"{season} Season")

            # ----------------------------
            # Top row: Pie chart + season metrics
            # ----------------------------
            col1, col2 = st.columns([1, 1])

            # Pie chart: classifications
            with col1:
                df_class = get_classifications_for_season(season)
                fig = px.pie(df_class, names="classification", values="tournament_count",
                             title="Event Categories")
                st.plotly_chart(fig, use_container_width=True)

            # Season summary metrics
            with col2:
                metrics = get_season_summary_metrics(season)
                st.metric("World Champion", metrics["world_champ"])
                st.metric("Pro Tour Champion", metrics["pro_tour_champ"])
                st.metric("Total Prize $", metrics["total_prize"])

            # ----------------------------
            # Winners bar chart (top 10)
            # ----------------------------
            st.subheader("Top Winners")
            df_winners = get_top_winners(season)
            fig2 = px.bar(df_winners, x="champion", y="wins", text="total_prize",
                          labels={"wins": "Wins", "champion": "Player"},
                          title="Top 10 Winners & Total Prize")
            st.plotly_chart(fig2, use_container_width=True)

            # ----------------------------
            # Event list table
            # ----------------------------
            st.subheader("Events")
            df_events = get_events_for_season(season)
            st.dataframe(df_events)


if __name__ == "__main__":
    main()