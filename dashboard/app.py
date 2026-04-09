import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import calendar as cal_mod
import datetime

from search import run_search, queries_remaining
from queries import (
    get_available_seasons,
    get_coverage_videos,
    get_events_for_season,
    get_last_result,
    get_latest_podcast_episodes,
    get_next_event,
    get_preview_videos,
    get_recent_results,
    get_schedule_strip,
    get_season_standings_top5,
    get_season_summary_metrics,
    get_stat_callout,
    get_top_winners,
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
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&display=swap');

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
        background: {GREEN};
        padding: 28px 0 0 0;
        margin-bottom: 0;
    }}
    .dg-brand-inner {{
        display: flex;
        align-items: flex-end;
        gap: 8px;
        padding: 0 0 14px 16px;
    }}
    .dg-brand-title {{
        font-weight: 800;
        font-size: 22px;
        color: {WHITE};
        letter-spacing: -0.3px;
        line-height: 1;
    }}
    .dg-brand-divider {{
        width: 1px;
        height: 16px;
        background: rgba(255,255,255,0.35);
        margin-bottom: 2px;
        flex-shrink: 0;
    }}
    .dg-brand-sub {{
        font-size: 12px;
        font-weight: 500;
        color: rgba(255,255,255,0.65);
        letter-spacing: 0.5px;
        margin-bottom: 1px;
    }}

    /* ── st.tabs styled as nav bar ── */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: {GREEN};
        border-bottom: none;
        gap: 0;
        padding: 0;
        margin-bottom: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.15);
    }}
    .stTabs [data-baseweb="tab"] {{
        background: none;
        border: none;
        border-radius: 0;
        color: rgba(255,255,255,0.65);
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        height: 44px;
        padding: 0 20px;
        border-bottom: 3px solid transparent;
        margin-bottom: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {WHITE};
        background: rgba(255,255,255,0.08);
    }}
    .stTabs [aria-selected="true"] {{
        color: {WHITE} !important;
        border-bottom: 3px solid {AMBER} !important;
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

    /* ── Landing page — triptych ── */
    .trip-row {{
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
        align-items: stretch;
    }}
    @media (max-width: 768px) {{
        .trip-row {{ flex-direction: column; }}
        .trip-card {{ width: 100%; }}
    }}
    .trip-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 20px 24px 24px 24px;
        flex: 1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        display: flex;
        flex-direction: column;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .trip-label {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 14px;
    }}
    .trip-title {{
        font-size: 18px;
        font-weight: 800;
        color: {TEXT};
        line-height: 1.2;
        margin-bottom: 6px;
        letter-spacing: -0.3px;
    }}
    .trip-title-amber {{
        font-size: 18px;
        font-weight: 800;
        color: {AMBER};
        line-height: 1.2;
        margin-bottom: 6px;
        letter-spacing: -0.3px;
    }}
    .trip-meta {{
        font-size: 13px;
        color: {MUTED};
        margin-bottom: 4px;
    }}
    .trip-score {{
        font-size: 32px;
        font-weight: 800;
        color: {TEXT};
        letter-spacing: -1px;
        margin: 8px 0 4px 0;
    }}
    .trip-badge {{
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 3px;
        margin-bottom: 10px;
    }}
    .trip-link {{
        margin-top: auto;
        padding-top: 16px;
        font-size: 12px;
        font-weight: 700;
        color: {GREEN};
        text-decoration: none;
        letter-spacing: 0.3px;
    }}
    .trip-link a {{
        color: {GREEN};
        text-decoration: none;
    }}
    .trip-placeholder {{
        font-size: 14px;
        color: {MUTED};
        font-style: italic;
        margin-top: 12px;
    }}

    /* ── Landing page — standings rows ── */
    .trip-standing-row {{
        display: flex;
        align-items: baseline;
        gap: 8px;
        padding: 5px 0;
        border-bottom: 1px solid {BORDER};
        font-size: 13px;
    }}
    .trip-standing-row:last-of-type {{
        border-bottom: none;
    }}
    .trip-standing-rank {{
        font-size: 11px;
        font-weight: 700;
        color: {MUTED};
        width: 16px;
        flex-shrink: 0;
    }}
    .trip-standing-rank-1 {{
        font-size: 11px;
        font-weight: 700;
        color: {AMBER};
        width: 16px;
        flex-shrink: 0;
    }}
    .trip-standing-name {{
        flex: 1;
        font-weight: 600;
        color: {TEXT};
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .trip-standing-name-amber {{
        flex: 1;
        font-weight: 700;
        color: {AMBER};
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .trip-standing-pts {{
        font-size: 12px;
        font-weight: 600;
        color: {MUTED};
        flex-shrink: 0;
    }}

    /* ── Landing page — schedule strip ── */
    .sched-strip {{
        display: flex;
        overflow-x: auto;
        gap: 8px;
        padding: 8px 0 12px 0;
        scrollbar-width: thin;
        min-height: 200px;
    }}
    .sched-pill {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 14px 14px;
        border-radius: 6px;
        border: 1px solid {BORDER};
        background: {WHITE};
        cursor: pointer;
        flex: none;
        align-self: stretch;
        border-left-width: 4px;
        border-left-style: solid;
    }}
    .sched-pill-name {{
        font-size: 12px;
        font-weight: 700;
        display: block;
        margin-bottom: 2px;
    }}
    .sched-pill-location {{
        font-size: 11px;
        color: {MUTED};
        display: block;
        margin-bottom: 2px;
    }}
    .sched-pill-date {{
        font-size: 11px;
        color: {MUTED};
        display: block;
    }}
    a.sched-link {{ text-decoration: none; color: inherit; display: flex; flex: none; align-self: stretch; }}
    a.sched-link:hover .sched-pill {{ box-shadow: 0 2px 6px rgba(0,0,0,0.12); }}
    .sched-completed .sched-pill-name {{ color: {MUTED}; }}
    .sched-current {{ background: {LIGHT_GREEN}; }}
    .sched-current .sched-pill-name {{ color: {GREEN}; }}

    /* ── Landing page — month calendar ── */
    .cal-grid {{ width: 100%; border-collapse: collapse; }}
    .cal-grid th {{
        font-size: 11px;
        color: {MUTED};
        text-align: center;
        padding: 4px 0 8px 0;
        font-weight: 600;
    }}
    .cal-grid td {{ text-align: center; padding: 3px 0; }}
    .cal-day {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        font-size: 13px;
        color: {TEXT};
    }}
    .cal-today {{ background: {TEXT}; color: {WHITE} !important; font-weight: 700; }}
    .cal-event {{ color: {WHITE} !important; font-weight: 600; }}

    /* ── Landing page — video section ── */
    .vid-section-label {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        color: {MUTED};
        margin: 28px 0 12px 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .vid-strip {{
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding-bottom: 8px;
        scrollbar-width: thin;
        margin-bottom: 8px;
    }}
    .vid-card {{
        flex: 0 0 200px;
        text-decoration: none;
        color: {TEXT};
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .vid-card:hover {{
        text-decoration: none;
        color: {TEXT};
    }}
    .vid-thumb-wrap {{
        position: relative;
        width: 200px;
        height: 112px;
        border-radius: 6px;
        overflow: hidden;
        background: {BORDER};
        margin-bottom: 8px;
    }}
    .vid-thumb {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    .vid-play {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 36px;
        height: 36px;
        background: rgba(29,107,68,0.88);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.18s ease;
        color: {WHITE};
        font-size: 14px;
        padding-left: 2px;
    }}
    .vid-card:hover .vid-play {{
        opacity: 1;
    }}
    .vid-title {{
        font-size: 12px;
        font-weight: 600;
        color: {TEXT};
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 4px;
    }}
    .vid-meta {{
        font-size: 11px;
        color: {MUTED};
    }}

    /* ── Landing page — stat callout ── */
    .stat-callout {{
        background: {LIGHT_GREEN};
        border-radius: 8px;
        padding: 40px 32px;
        text-align: center;
        margin-bottom: 24px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .stat-callout-number {{
        font-size: 72px;
        font-weight: 800;
        color: {GREEN};
        line-height: 1;
        margin-bottom: 12px;
        letter-spacing: -3px;
        font-family: 'Playfair Display', Georgia, serif;
    }}
    .stat-callout-subject {{
        font-size: 15px;
        font-weight: 700;
        color: {TEXT};
        margin-bottom: 4px;
    }}
    .stat-callout-detail {{
        font-size: 13px;
        color: {MUTED};
    }}

    /* ── Landing page — podcast section ── */
    .pod-strip {{
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding-bottom: 8px;
        scrollbar-width: thin;
        margin-bottom: 8px;
    }}
    .pod-card {{
        flex: 0 0 220px;
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    .pod-show {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 8px;
    }}
    .pod-title {{
        font-size: 13px;
        font-weight: 600;
        color: {TEXT};
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 10px;
        min-height: 54px;
    }}
    .pod-meta {{
        font-size: 11px;
        color: {MUTED};
        margin-bottom: 10px;
    }}
    a.pod-listen {{
        display: inline-block;
        font-size: 11px;
        font-weight: 700;
        color: {GREEN};
        text-decoration: none;
        letter-spacing: 0.3px;
    }}
    a.pod-listen:hover {{ text-decoration: underline; }}

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


# ── Landing page helpers ────────────────────────────────────────────────────────

def _classification_color(classification: str, is_worlds: bool) -> str:
    if is_worlds:
        return "#8B1A1A"
    return {
        "Elite Series": GREEN,
        "Elite Series Plus": "#2E8B57",
        "Major": AMBER,
        "Tour Championship": TEXT,
    }.get(classification, MUTED)


def _score_str(score) -> str:
    try:
        s = int(score)
        return f"{s:+d}" if s != 0 else "E"
    except (TypeError, ValueError):
        return "—"


def _prize_str(prize) -> str:
    try:
        return f"${int(prize):,}" if prize and pd.notna(prize) else "—"
    except (TypeError, ValueError):
        return "—"


def _days_away(start_date) -> str:
    try:
        dt = pd.to_datetime(start_date).date()
        delta = (dt - datetime.date.today()).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "Tomorrow"
        if delta < 0:
            return "In progress"
        return f"{delta} days away"
    except Exception:
        return ""


def _date_range_str(start, end) -> str:
    try:
        s = pd.to_datetime(start)
        e = pd.to_datetime(end)
        if s.month == e.month:
            return f"{s.strftime('%b %-d')}–{e.strftime('%-d')}"
        return f"{s.strftime('%b %-d')}–{e.strftime('%b %-d')}"
    except Exception:
        return str(start) if start else "—"


def _render_triptych(last: dict, nxt: dict, standings: pd.DataFrame) -> None:
    # Compute all values as Python variables first, then emit one flat f-string.
    # Never embed pre-built HTML strings — blank lines in nested f-strings end
    # the CommonMark HTML block and cause Streamlit to render content as code.

    # ── Last Result values ────────────────────────────────────────────────────
    if last:
        l_event = last.get("event_name") or "—"
        l_champ = last.get("champion") or "—"
        l_name_cls = "trip-title-amber" if bool(last.get("is_worlds")) else "trip-title"
        l_score = _score_str(last.get("total_score"))
        l_rounds = last.get("total_rounds") or ""
        l_prize = _prize_str(last.get("prize_usd"))
        l_dates = _date_range_str(last.get("start_date"), last.get("end_date"))
        l_playlist = last.get("jomez_playlist_url") or ""
        l_watch = (f'<div class="trip-link"><a href="{l_playlist}" target="_blank">Watch Coverage ↗</a></div>'
                   if l_playlist else "")
        last_html = (f'<div class="trip-card">'
                     f'<div class="trip-label">Last Result</div>'
                     f'<div class="trip-meta">{l_event}</div>'
                     f'<div class="{l_name_cls}">{l_champ}</div>'
                     f'<div class="trip-score">{l_score}</div>'
                     f'<div class="trip-meta">{l_rounds} rounds &middot; {l_prize} &middot; {l_dates}</div>'
                     f'{l_watch}'
                     f'</div>')
    else:
        last_html = ('<div class="trip-card">'
                     '<div class="trip-label">Last Result</div>'
                     '<div class="trip-placeholder">No results yet this season.</div>'
                     '</div>')

    # ── Next Event values ─────────────────────────────────────────────────────
    if nxt:
        n_cls = nxt.get("classification") or ""
        n_worlds = bool(nxt.get("is_worlds"))
        n_color = _classification_color(n_cls, n_worlds)
        n_label = "Worlds" if n_worlds else n_cls
        n_location = nxt.get("location") or ""
        n_days = _days_away(nxt.get("start_date"))
        n_start = pd.to_datetime(nxt.get("start_date")).strftime("%b %-d")
        n_pdga = f"https://www.pdga.com/tour/event/{nxt.get('tournament_id', '')}"
        n_name = nxt.get("event_name") or "—"
        next_html = (f'<div class="trip-card">'
                     f'<div class="trip-label">Next Event</div>'
                     f'<span class="trip-badge" style="background:{n_color}20;color:{n_color};">{n_label}</span>'
                     f'<div class="trip-title">{n_name}</div>'
                     f'<div class="trip-meta">{n_location}</div>'
                     f'<div class="trip-meta">{n_start} &middot; {n_days}</div>'
                     f'<div class="trip-link"><a href="{n_pdga}" target="_blank">View Field ↗</a></div>'
                     f'</div>')
    else:
        next_html = ('<div class="trip-card">'
                     '<div class="trip-label">Next Event</div>'
                     '<div class="trip-placeholder">Season complete.</div>'
                     '</div>')

    # ── Standings card ─────────────────────────────────────────────────────────
    if not standings.empty:
        st_sublabel = (f"Before {nxt.get('event_name', '')}" if nxt
                       else f"Final {datetime.date.today().year} Standings")
        rows_html = ""
        for _, row in standings.iterrows():
            s_rank = int(row["rank"])
            s_name = row["player_name"]
            s_pts = row["total_points"]
            pts_str = str(int(s_pts)) if s_pts == int(s_pts) else str(s_pts)
            rank_cls = "trip-standing-rank-1" if s_rank == 1 else "trip-standing-rank"
            name_cls = "trip-standing-name-amber" if s_rank == 1 else "trip-standing-name"
            rows_html += (f'<div class="trip-standing-row">'
                          f'<span class="{rank_cls}">{s_rank}</span>'
                          f'<span class="{name_cls}">{s_name}</span>'
                          f'<span class="trip-standing-pts">{pts_str}</span>'
                          f'</div>')
        standings_html = (f'<div class="trip-card">'
                          f'<div class="trip-label">Season Standings</div>'
                          f'<div class="trip-meta">{st_sublabel}</div>'
                          f'{rows_html}'
                          f'<div class="trip-link"><a href="https://www.dgpt.com/full-standings/" target="_blank">Full Standings ↗</a></div>'
                          f'</div>')
    else:
        standings_html = ('<div class="trip-card">'
                          '<div class="trip-label">Season Standings</div>'
                          '<div class="trip-placeholder">Standings not yet available.</div>'
                          '</div>')

    st.markdown(
        f'<div class="trip-row">{last_html}{next_html}{standings_html}</div>',
        unsafe_allow_html=True,
    )


def _build_calendar_html(df: pd.DataFrame) -> str:
    today = datetime.date.today()
    year, month = today.year, today.month

    # Map day -> (color, event_name) for every tournament day in this month
    day_info: dict[int, tuple[str, str]] = {}
    for _, row in df.iterrows():
        start = pd.to_datetime(row["start_date"]).date()
        end = pd.to_datetime(row["end_date"]).date()
        color = _classification_color(row["classification"], bool(row["is_worlds"]))
        name = row["event_name"]
        d = start
        while d <= end:
            if d.year == year and d.month == month:
                day_info[d.day] = (color, name)
            d += datetime.timedelta(days=1)

    month_label = today.strftime("%B %Y")
    weeks = cal_mod.monthcalendar(year, month)

    headers = "".join(f"<th>{h}</th>" for h in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"])
    rows_html = ""
    for week in weeks:
        cells = ""
        for day in week:
            if day == 0:
                cells += "<td></td>"
            elif day == today.day and day in day_info:
                color, name = day_info[day]
                cells += (f'<td title="{name}">'
                          f'<span class="cal-day cal-event" style="background:{color};outline:2px solid {TEXT};outline-offset:2px;">'
                          f'{day}</span></td>')
            elif day == today.day:
                cells += f'<td><span class="cal-day cal-today">{day}</span></td>'
            elif day in day_info:
                color, name = day_info[day]
                cells += (f'<td title="{name}">'
                          f'<span class="cal-day cal-event" style="background:{color};">'
                          f'{day}</span></td>')
            else:
                cells += f'<td><span class="cal-day">{day}</span></td>'
        rows_html += f"<tr>{cells}</tr>"

    return (f'<div class="table-card">'
            f'<div class="dg-section-header">{month_label}</div>'
            f'<table class="cal-grid"><thead><tr>{headers}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table>'
            f'</div>')


def _render_schedule_strip(season: int) -> None:
    df = get_schedule_strip(season)
    if df.empty:
        return

    today = datetime.date.today()

    def _pill_html(row: pd.Series, state_cls: str, name_color: str) -> str:
        color = _classification_color(row["classification"], bool(row["is_worlds"]))
        date_str = pd.to_datetime(row["start_date"]).strftime("%b %-d")
        location = row.get("location") or ""
        pill = (f'<span class="sched-pill {state_cls}" style="border-left-color:{color};">'
                f'<span class="sched-pill-name" style="color:{name_color};">{row["event_name"]}</span>'
                f'<span class="sched-pill-location">{location}</span>'
                f'<span class="sched-pill-date">{date_str}</span>'
                f'</span>')
        dgpt_url = row.get("dgpt_url") or ""
        if dgpt_url:
            return f'<a class="sched-link" href="{dgpt_url}" target="_blank" rel="noopener">{pill}</a>'
        return pill

    pills = ""
    for _, row in df.iterrows():
        end = pd.to_datetime(row["end_date"]).date()
        start = pd.to_datetime(row["start_date"]).date()
        if end < today:
            continue
        state_cls = "sched-current" if start <= today <= end else ""
        name_color = GREEN if state_cls else TEXT
        pills += _pill_html(row, state_cls, name_color)

    col_strip, col_cal = st.columns([3, 2])
    with col_strip:
        st.markdown(f"""
        <div class="table-card">
            <div class="dg-section-header">{season} Schedule</div>
            <div class="sched-strip">{pills}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_cal:
        st.markdown(_build_calendar_html(df), unsafe_allow_html=True)


def _render_video_section(last: dict, nxt: dict) -> None:
    # ── 3A: Recent coverage (JomezPro, gated on jomez_playlist_url) ───────────
    if last and last.get("jomez_playlist_url"):
        event_name = last.get("event_name") or ""
        coverage = get_coverage_videos(event_name)
        if not coverage.empty:
            cards = ""
            for _, row in coverage.iterrows():
                pub = pd.to_datetime(row["published_at"]).strftime("%b %-d")
                title = str(row["title"]).replace("'", "&#39;").replace('"', "&quot;")
                cards += (f'<a class="vid-card" href="{row["video_url"]}" target="_blank">'
                          f'<div class="vid-thumb-wrap">'
                          f'<img class="vid-thumb" src="{row["thumbnail_url"]}" />'
                          f'<div class="vid-play">&#9654;</div>'
                          f'</div>'
                          f'<div class="vid-title">{title}</div>'
                          f'<div class="vid-meta">{row["channel_name"]} &middot; {pub}</div>'
                          f'</a>')
            st.markdown(
                f'<div class="vid-section-label">Recent Coverage &mdash; {event_name}</div>'
                f'<div class="vid-strip">{cards}</div>',
                unsafe_allow_html=True,
            )

    # ── 3B: Preview content (4 creator channels, within 7 days of next event) ─
    if nxt and nxt.get("start_date"):
        preview = get_preview_videos(nxt["start_date"])
        if not preview.empty:
            nxt_name = nxt.get("event_name") or ""
            cards = ""
            for _, row in preview.iterrows():
                pub = pd.to_datetime(row["published_at"]).strftime("%b %-d")
                title = str(row["title"]).replace("'", "&#39;").replace('"', "&quot;")
                cards += (f'<a class="vid-card" href="{row["video_url"]}" target="_blank">'
                          f'<div class="vid-thumb-wrap">'
                          f'<img class="vid-thumb" src="{row["thumbnail_url"]}" />'
                          f'<div class="vid-play">&#9654;</div>'
                          f'</div>'
                          f'<div class="vid-title">{title}</div>'
                          f'<div class="vid-meta">{row["channel_name"]} &middot; {pub}</div>'
                          f'</a>')
            st.markdown(
                f'<div class="vid-section-label">Preview &mdash; {nxt_name}</div>'
                f'<div class="vid-strip">{cards}</div>',
                unsafe_allow_html=True,
            )


_PODCAST_SHOW_URLS = {
    "Course Maintenance": "https://rss.com/podcasts/coursemaintenance/",
    "Tour Life": "https://rss.com/podcasts/tourlife/",
    "Grip Locked": "https://rss.com/podcasts/griplocked/",
    "The Upshot": "https://rss.com/podcasts/thediscgolfupshot/",
}


def _render_podcast_section() -> None:
    df = get_latest_podcast_episodes()
    if df.empty:
        return

    cards = ""
    for _, row in df.iterrows():
        pub = pd.to_datetime(row["published_at"])
        date_str = pub.strftime("%b %-d")
        dur = row.get("duration_secs")
        dur_str = f" · {dur // 60} min" if dur else ""
        title = (row["episode_title"] or "").replace("'", "&#39;").replace('"', "&quot;")
        show_url = _PODCAST_SHOW_URLS.get(row["show_name"], row["episode_url"] or "#")
        cards += f"""<div class="pod-card"><div class="pod-show">{row["show_name"]}</div><div class="pod-title">{title}</div><div class="pod-meta">{date_str}{dur_str}</div><a class="pod-listen" href="{show_url}" target="_blank" rel="noopener">Listen ↗</a></div>"""

    st.markdown(
        f'<div class="vid-section-label">Latest Podcast Episodes</div>'
        f'<div class="pod-strip">{cards}</div>',
        unsafe_allow_html=True,
    )


def _render_stat_callout(season: int) -> None:
    stat = get_stat_callout(season)
    if not stat:
        return

    st.markdown(f"""
    <div class="stat-callout">
        <div class="stat-callout-number">{stat["number"]}</div>
        <div class="stat-callout-subject">{stat["subject"]}'s {stat["context"]}</div>
        <div class="stat-callout-detail">{stat["detail"]}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_recent_results() -> None:
    df = get_recent_results(limit=4)
    if df.empty:
        return

    rows = ""
    for _, row in df.iterrows():
        date_str = _date_range_str(row.get("start_date"), row.get("end_date"))
        score = _score_str(row.get("total_score"))
        rounds = row.get("total_rounds") or ""
        prize = _prize_str(row.get("prize_usd"))
        rows += f"""
        <tr>
            <td class="date-cell">{date_str}</td>
            <td><div class="event-name">{row.get("event_name") or "—"}</div></td>
            <td class="champ-cell">{row.get("champion") or "—"}</td>
            <td class="right" style="font-variant-numeric:tabular-nums;color:{MUTED};font-size:13px;">
                {score} ({rounds}R)
            </td>
            <td class="prize-cell right">{prize}</td>
        </tr>"""

    st.markdown(f"""
    <div class="table-card">
        <div class="dg-section-header">Recent Results</div>
        <table class="dg-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Event</th>
                    <th>Champion</th>
                    <th class="right">Score</th>
                    <th class="right">Prize</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


def render_landing_page() -> None:
    season = datetime.date.today().year
    last = get_last_result()
    nxt = get_next_event()
    standings = get_season_standings_top5(season)
    _render_triptych(last, nxt, standings)
    _render_schedule_strip(season)
    _render_video_section(last, nxt)
    _render_podcast_section()
    _render_stat_callout(season)
    _render_recent_results()


# ── About page ─────────────────────────────────────────────────────────────────
def render_about() -> None:
    st.markdown(f"""
    <div class="table-card" style="max-width:680px;margin:0 auto;">
        <div class="dg-section-header">About</div>
        <p style="font-size:15px;color:{TEXT};line-height:1.7;margin-bottom:20px;">
            An unofficial stats and content hub for the Disc Golf Pro Tour (DGPT), focused on the
            MPO division. Stats are updated nightly from the PDGA live results API. Standings are
            scraped from the official DGPT site. Video coverage and podcast links surface
            automatically from YouTube and RSS feeds.
        </p>
        <div style="font-size:12px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:{MUTED};margin-bottom:10px;">Data Sources</div>
        <ul style="font-size:14px;color:{TEXT};line-height:2;margin:0;padding-left:20px;">
            <li><a href="https://www.pdga.com" target="_blank" style="color:{GREEN};">PDGA</a> — tournament results, player data, round scores</li>
            <li><a href="https://www.dgpt.com" target="_blank" style="color:{GREEN};">DGPT</a> — official points standings</li>
            <li><a href="https://www.youtube.com/@JomezPro" target="_blank" style="color:{GREEN};">JomezPro</a> — tournament video coverage</li>
            <li>The Upshot · Tour Life · Grip Locked · Course Maintenance — podcast episodes</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


# ── Search tab ─────────────────────────────────────────────────────────────────
def render_search():
    remaining = queries_remaining()

    st.markdown("""
    <div style="max-width:720px;margin:32px auto 0;">
    """, unsafe_allow_html=True)

    question = st.chat_input(
        "Ask anything about DGPT MPO stats (2020–2026)",
        disabled=(remaining == 0),
    )

    if remaining > 0:
        st.markdown(
            f'<p style="color:#6B7280;font-size:0.82rem;margin:6px 0 24px;">'
            f'{remaining} question{"s" if remaining != 1 else ""} remaining this session</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color:#6B7280;font-size:0.82rem;margin:6px 0 24px;">'
            'Session limit reached — refresh to ask more questions.</p>',
            unsafe_allow_html=True,
        )

    if question:
        with st.spinner(""):
            result = run_search(question)

        path = result["path"]
        response = result["response"]
        df = result.get("df", pd.DataFrame())

        # Question echo
        st.markdown(
            f'<div style="font-weight:600;margin-bottom:8px;color:#1C1C1E;">{question}</div>',
            unsafe_allow_html=True,
        )

        # Response card
        border_color = "#1D6B44" if path == "answered" else "#E5E7EB"
        st.markdown(
            f'<div style="background:#fff;border:1px solid {border_color};border-radius:8px;'
            f'padding:16px 20px;margin-bottom:16px;line-height:1.6;color:#1C1C1E;">'
            f'{response}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Data table (answered path with results)
        if path == "answered" and not df.empty:
            # Build a clean HTML table
            headers = "".join(
                f'<th style="text-align:left;padding:6px 12px;border-bottom:2px solid #E5E7EB;'
                f'font-size:0.8rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em;background:#fff;">'
                f'{col}</th>'
                for col in df.columns
            )
            rows = ""
            for _, row in df.iterrows():
                cells = "".join(
                    f'<td style="padding:6px 12px;border-bottom:1px solid #F3F4F6;font-size:0.9rem;color:#1C1C1E;background:#fff;">'
                    f'{val}</td>'
                    for val in row
                )
                rows += f"<tr>{cells}</tr>"
            st.markdown(
                f'<div style="overflow-x:auto;margin-bottom:24px;">'
                f'<table style="width:100%;border-collapse:collapse;background:#fff;'
                f'border:1px solid #E5E7EB;border-radius:8px;overflow:hidden;">'
                f'<thead><tr>{headers}</tr></thead>'
                f'<tbody>{rows}</tbody>'
                f'</table></div>',
                unsafe_allow_html=True,
            )

        # Updated session counter
        new_remaining = result.get("remaining", 0)
        if path not in ("rate_limit",):
            st.markdown(
                f'<p style="color:#6B7280;font-size:0.82rem;">'
                f'{new_remaining} question{"s" if new_remaining != 1 else ""} remaining this session</p>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ── Shell pages ─────────────────────────────────────────────────────────────────
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
        '<div class="dg-brand"><div class="dg-brand-inner">'
        '<span class="dg-brand-title">Disc Golf Pro Tour</span>'
        '<span class="dg-brand-divider"></span>'
        '<span class="dg-brand-sub">MPO Stats &amp; Coverage</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Top-level nav tabs ────────────────────────────────────────────────────
    tab_landing, tab_season, tab_search, tab_about = st.tabs(
        ["This Week", "Season", "Search", "About"]
    )

    with tab_landing:
        render_landing_page()

    # ── Season tab ────────────────────────────────────────────────────────────
    with tab_season:
        col_year, _ = st.columns([2, 8])
        with col_year:
            season_options = list(reversed(seasons))
            current_year = datetime.date.today().year
            default_idx = 1 if len(season_options) > 1 and season_options[0] == current_year else 0
            selected = st.selectbox(
                "Year",
                options=season_options,
                index=default_idx,
                label_visibility="collapsed",
            )
        render_season(int(selected))

    with tab_search:
        render_search()

    with tab_about:
        render_about()


if __name__ == "__main__":
    main()
