import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from queries import (
    get_available_seasons,
    get_season_summary_metrics,
    get_top_winners,
    get_events_for_season,
)

# ── Palette ────────────────────────────────────────────────────────────────────
GREEN       = "#1D6B44"
AMBER       = "#E8A838"
BG          = "#F8F9FA"
WHITE       = "#FFFFFF"
TEXT        = "#1C1C1E"
MUTED       = "#6B7280"
BORDER      = "#E5E7EB"
LIGHT_GREEN = "#EAF4EE"


# ── CSS ────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>

    /* ── Streamlit chrome ── */
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stDeployButton {{ display: none !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}

    /* ── Page ── */
    .stApp {{
        background-color: {BG};
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 60px;
        max-width: 1100px;
    }}

    /* ── Brand bar ── */
    .dg-brand {{
        background: {WHITE};
        border-bottom: 1px solid {BORDER};
        padding: 0 4px;
        margin-bottom: 0;
        display: flex;
        align-items: center;
        height: 44px;
    }}
    .dg-brand-logo {{
        font-weight: 800;
        font-size: 14px;
        color: {GREEN};
        letter-spacing: 1px;
        text-transform: uppercase;
    }}

    /* ── st.tabs styled as nav bar ── */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: {WHITE};
        border-bottom: 3px solid {GREEN};
        gap: 0;
        padding: 0 0 0 0;
        margin-bottom: 1.5rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: none;
        border: none;
        border-radius: 0;
        color: {MUTED};
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        height: 48px;
        padding: 0 20px;
        border-bottom: 3px solid transparent;
        margin-bottom: -3px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {GREEN};
        background: none;
    }}
    .stTabs [aria-selected="true"] {{
        color: {GREEN} !important;
        border-bottom: 3px solid {GREEN} !important;
        background: none !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display: none !important; }}
    .stTabs [data-baseweb="tab-border"]    {{ display: none !important; }}

    /* ── Year selector ── */
    .year-selector-label {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 4px;
    }}
    [data-testid="stSelectbox"] > div > div {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 3px;
        font-weight: 700;
        font-size: 15px;
        color: {TEXT};
    }}

    /* ── Hero block ── */
    .hero-block {{
        background: {WHITE};
        border-radius: 3px;
        padding: 36px 44px 32px 44px;
        margin-bottom: 12px;
        border-left: 5px solid {GREEN};
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .hero-season-label {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 20px;
    }}
    .hero-champ-eyebrow {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {AMBER};
        margin-bottom: 10px;
    }}
    .hero-champ-name {{
        font-size: 54px;
        font-weight: 800;
        color: {TEXT};
        letter-spacing: -1.5px;
        line-height: 1.0;
        margin-bottom: 8px;
    }}
    .hero-champ-sub {{
        font-size: 14px;
        color: {MUTED};
        font-weight: 400;
    }}

    /* ── Stat cards row ── */
    .stat-row {{
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .stat-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 3px;
        padding: 22px 28px;
        flex: 1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .stat-card-label {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 10px;
    }}
    .stat-card-value {{
        font-size: 26px;
        font-weight: 800;
        color: {TEXT};
        letter-spacing: -0.5px;
        line-height: 1.1;
    }}
    .stat-card-value-sm {{
        font-size: 20px;
        font-weight: 800;
        color: {TEXT};
        letter-spacing: -0.3px;
        line-height: 1.2;
    }}
    .stat-card-value-green {{
        font-size: 26px;
        font-weight: 800;
        color: {GREEN};
        letter-spacing: -0.5px;
        line-height: 1.1;
    }}
    .stat-card-sub {{
        font-size: 12px;
        color: {MUTED};
        margin-top: 5px;
    }}

    /* ── Chart wrapper (visual card behind the plotly chart) ── */
    [data-testid="stPlotlyChart"] {{
        background: {WHITE};
        border-radius: 0 0 3px 3px;
        padding: 4px 8px 8px 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }}
    .chart-header {{
        background: {WHITE};
        border-radius: 3px 3px 0 0;
        padding: 20px 32px 0 32px;
        box-shadow: 0 -1px 4px rgba(0,0,0,0.04);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .chart-header-title {{
        font-size: 16px;
        font-weight: 800;
        color: {TEXT};
        letter-spacing: -0.2px;
        padding-bottom: 12px;
        border-bottom: 2px solid {BORDER};
        margin-bottom: 0;
    }}

    /* ── Events table card ── */
    .table-card {{
        background: {WHITE};
        border-radius: 3px;
        padding: 20px 32px 24px 32px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .dg-section-header {{
        font-size: 16px;
        font-weight: 800;
        color: {TEXT};
        letter-spacing: -0.2px;
        padding-bottom: 12px;
        border-bottom: 2px solid {BORDER};
        margin-bottom: 20px;
    }}
    .dg-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}
    .dg-table th {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: {MUTED};
        padding: 0 16px 12px 0;
        text-align: left;
        border-bottom: 2px solid {BORDER};
    }}
    .dg-table th.right {{ text-align: right; padding-right: 0; }}
    .dg-table td {{
        padding: 13px 16px 13px 0;
        color: {TEXT};
        border-bottom: 1px solid {BORDER};
        vertical-align: middle;
        line-height: 1.4;
    }}
    .dg-table td.right {{ text-align: right; padding-right: 0; }}
    .dg-table tbody tr:last-child td {{ border-bottom: none; }}
    .dg-table tbody tr:hover td {{ background: {LIGHT_GREEN}; }}
    .event-name  {{ font-weight: 700; color: {TEXT}; font-size: 14px; }}
    .event-course {{ color: {MUTED}; font-size: 12px; margin-top: 2px; }}
    .date-cell  {{ color: {MUTED}; font-size: 13px; white-space: nowrap; min-width: 88px; }}
    .champ-cell {{ font-weight: 600; white-space: nowrap; }}
    .prize-cell {{ font-weight: 700; color: {GREEN}; white-space: nowrap; font-variant-numeric: tabular-nums; }}

    /* ── Shell placeholder ── */
    .shell-block {{
        background: {WHITE};
        border-radius: 3px;
        padding: 100px 32px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-top: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .shell-title {{
        font-size: 22px;
        font-weight: 800;
        color: {TEXT};
        margin-bottom: 10px;
        letter-spacing: -0.3px;
    }}
    .shell-desc {{ font-size: 15px; color: {MUTED}; }}

    </style>
    """, unsafe_allow_html=True)


# ── Build events table HTML (returns string, not renders) ──────────────────────
def _build_events_table_html(df):
    rows = ""
    for _, row in df.iterrows():
        start_raw = row.get("start_date")
        end_raw   = row.get("end_date")
        try:
            start_dt = pd.to_datetime(start_raw)
            end_dt   = pd.to_datetime(end_raw)
            if start_dt.month == end_dt.month:
                date_str = f"{start_dt.strftime('%b %-d')}–{end_dt.strftime('%-d')}"
            else:
                date_str = f"{start_dt.strftime('%b %-d')}–{end_dt.strftime('%b %-d')}"
        except Exception:
            date_str = str(start_raw) if start_raw else "—"

        event_name  = row.get("event_name") or "—"
        course_name = row.get("finishing_course_name") or ""
        champion    = row.get("champion") or "—"
        prize_raw   = row.get("prize_usd")
        prize_str   = f"${prize_raw:,.0f}" if pd.notna(prize_raw) and prize_raw else "—"
        course_html = f'<div class="event-course">{course_name}</div>' if course_name else ""

        rows += f"""
        <tr>
            <td class="date-cell">{date_str}</td>
            <td><div class="event-name">{event_name}</div>{course_html}</td>
            <td class="champ-cell">{champion}</td>
            <td class="prize-cell right">{prize_str}</td>
        </tr>"""

    return f"""
    <table class="dg-table">
        <thead>
            <tr>
                <th>Date</th>
                <th>Event</th>
                <th>Champion</th>
                <th class="right">Prize</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


# ── Season page ────────────────────────────────────────────────────────────────
def render_season(season):
    metrics    = get_season_summary_metrics(season)
    df_events  = get_events_for_season(season)
    df_winners = get_top_winners(season)

    world_champ    = metrics.get("world_champ") or "—"
    pro_tour_champ = metrics.get("pro_tour_champ") or "—"
    total_prize    = metrics.get("total_prize")
    n_events       = len(df_events)
    prize_fmt      = f"${total_prize:,.0f}" if pd.notna(total_prize) and total_prize else "—"

    # ── Hero: single complete HTML block ──────────────────────────────────────
    st.markdown(f"""
    <div class="hero-block">
        <div class="hero-season-label">{season} Season &middot; MPO</div>
        <div class="hero-champ-eyebrow">&#11044;&ensp;World Champion</div>
        <div class="hero-champ-name">{world_champ}</div>
        <div class="hero-champ-sub">Disc Golf World Championships &middot; {season}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Stat cards: single complete HTML block ────────────────────────────────
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card">
            <div class="stat-card-label">Tour Champion</div>
            <div class="stat-card-value-sm">{pro_tour_champ}</div>
            <div class="stat-card-sub">DGPT Championship</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Total Prize Money</div>
            <div class="stat-card-value-green">{prize_fmt}</div>
            <div class="stat-card-sub">Across all events</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Events</div>
            <div class="stat-card-value">{n_events}</div>
            <div class="stat-card-sub">DGPT events this season</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Top performers chart ──────────────────────────────────────────────────
    # Section header is a standalone HTML block (no wrapping div around chart)
    st.markdown(
        '<div class="chart-header"><div class="chart-header-title">Top Performers</div></div>',
        unsafe_allow_html=True,
    )

    if not df_winners.empty:
        bar_colors = [AMBER if i == 0 else GREEN for i in range(len(df_winners))]

        hover_text = [
            f"<b>{r['champion']}</b><br>"
            f"{int(r['wins'])} win{'s' if r['wins'] != 1 else ''}<br>"
            f"${r['total_prize']:,.0f} prize"
            for _, r in df_winners.iterrows()
        ]

        fig = go.Figure(go.Bar(
            x=df_winners["wins"],
            y=df_winners["champion"],
            orientation="h",
            marker_color=bar_colors,
            marker_line_width=0,
            text=df_winners["wins"].astype(int),
            textposition="outside",
            textfont=dict(size=13, color=TEXT, family="-apple-system, sans-serif"),
            hovertext=hover_text,
            hoverinfo="text",
        ))
        fig.update_layout(
            margin=dict(l=0, r=60, t=16, b=8),
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            height=max(260, len(df_winners) * 40),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False,
                       range=[0, df_winners["wins"].max() * 1.2]),
            yaxis=dict(autorange="reversed", showgrid=False,
                       tickfont=dict(size=13, color=TEXT, family="-apple-system, sans-serif"),
                       ticksuffix="  "),
            font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                      color=TEXT),
            bargap=0.38,
            hoverlabel=dict(bgcolor=WHITE, bordercolor=BORDER, font_size=13,
                            font_family="-apple-system, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Events table: one complete HTML block ─────────────────────────────────
    if not df_events.empty:
        table_html = _build_events_table_html(df_events)
        st.markdown(f"""
        <div class="table-card">
            <div class="dg-section-header">{season} Results</div>
            {table_html}
        </div>
        """, unsafe_allow_html=True)


# ── Shell pages ────────────────────────────────────────────────────────────────
def render_shell(title, description):
    st.markdown(f"""
    <div class="shell-block">
        <div class="shell-title">{title}</div>
        <div class="shell-desc">{description}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Disc Golf Pro Tour · Stats",
        page_icon="🥏",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    inject_css()

    seasons = get_available_seasons()

    # ── Brand bar (above tabs) ────────────────────────────────────────────────
    st.markdown(
        '<div class="dg-brand"><span class="dg-brand-logo">Disc Golf Pro Tour</span></div>',
        unsafe_allow_html=True,
    )

    # ── Top-level nav tabs ────────────────────────────────────────────────────
    tab_season, tab_landing, tab_search, tab_state, tab_about = st.tabs(
        ["Season", "Landing Page", "Search", "State of Disc Golf", "About"]
    )

    # ── Season tab ────────────────────────────────────────────────────────────
    with tab_season:
        col_year, _ = st.columns([2, 8])
        with col_year:
            season_options = list(reversed(seasons))
            selected = st.selectbox(
                "Year",
                options=season_options,
                index=0,
                label_visibility="collapsed",
            )
        render_season(int(selected))

    # ── Shell tabs ────────────────────────────────────────────────────────────
    with tab_landing:
        render_shell("Landing Page", "Coming soon.")

    with tab_search:
        render_shell("Search", "Player and event search — coming soon.")

    with tab_state:
        render_shell("State of Disc Golf", "Coming soon.")

    with tab_about:
        render_shell("About", "Coming soon.")


if __name__ == "__main__":
    main()
