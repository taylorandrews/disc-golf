# dashboard/search.py
#
# Phase 4 — Natural language search.
# One Claude API call classifies the question and optionally generates SQL.
# SQL is validated, executed via the read-only dg_reader connection, and the
# result is logged to search_log with every query attempt.

import os
import re
import time
import uuid

import anthropic
import pandas as pd
import sqlalchemy as sa
import streamlit as st

from helpers.db_config import engine, reader_engine

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_QUERIES_PER_SESSION = 10
COOLDOWN_SECS = 3
MAX_SQL_LENGTH = 2000

_FORBIDDEN = re.compile(
    r"\b(drop|delete|update|insert|truncate|alter|copy|pg_|information_schema)\b",
    re.IGNORECASE,
)

# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a disc golf stats assistant for disc-golf-data.com.
You answer questions about MPO (Men's Pro Open) DGPT tournament statistics from 2020–2026.

## What you can answer
- Tournament results: winner, score, prize, dates, classification
- Player round scores and ratings
- Hole-by-hole scores (2021 onward only — 2020 has no hole data)
- Season standings (DGPT points — 2026 only, scraped weekly)
- Schedule and tournament metadata

## What is out of scope
- FPO, amateur, or junior divisions
- PDGA player ratings or rating history
- Live or in-progress rounds
- Player biography (age, hometown, sponsors, equipment)
- Hole-by-hole data for the 2020 season
- Results from before 2020

## Database schema

**tournament** — one row per event
- tournament_id (integer PK, from PDGA URL)
- season (integer year)
- name (short display name, e.g. "Champions Cup")
- long_name (full name)
- start_date (date)
- classification: "Elite Series", "Elite Series Plus", "Elite Series Playoffs", "Major", "Tour Championship"
- is_worlds (boolean) — TRUE only for PDGA Pro World Championships
- has_finals (boolean)
- total_rounds (integer)
- location (text, "City, ST")

**player** — one row per PDGA member
- player_id (integer, PDGA number)
- first_name, last_name
- city, state, country
- division (always "MPO" in this dataset)

**round** — one row per player per round
- round_id (PK)
- tournament_id (FK)
- player_id (FK)
- course_id (FK)
- tournament_round_num (1-based round number)
- prize (integer USD, only set on final round for winners)
- round_rating (integer, PDGA rating for the round; 1000 = scratch)
- round_score (integer, score relative to par; negative = under par)
- round_status (text)
- round_date (date)

**hole** — one row per hole per player per round (2021+ only)
- hole_id (text PK)
- round_id (FK)
- player_id (FK)
- hole_number (1-18)
- par (integer)
- score (integer, strokes played)
- length (float, feet)

**course** — one row per layout
- course_id (text PK)
- course_name (venue name)
- name (full layout name)
- holes (integer)

**Views (prefer these over raw tables):**

vw_tournament_summary — one row per tournament, join-friendly:
- tournament_id, season, event_name, champion (player who won),
  total_score (winning score relative to par), prize_usd, finishing_course_name,
  start_date, end_date, classification, is_worlds

vw_player_season — player activity by season:
- player_id, first_name, last_name, season, tournaments_played, rounds_played

vw_classifications_per_season — event counts by classification per season:
- season, classification, tournament_count

## SQL rules
- SELECT only — no INSERT, UPDATE, DELETE, DROP, or DDL
- No semicolons
- No system tables (pg_, information_schema)
- Always LIMIT 200
- Use views (vw_*) where they have the data you need
- Player name searches: use ILIKE with % wildcards
  Example: WHERE first_name ILIKE '%paul%' AND last_name ILIKE '%mcbeth%'

## Response format
Respond with valid JSON only. No markdown, no explanation outside the JSON.

For off-topic questions (nothing to do with disc golf stats):
{"path": "off_topic", "response": "This tool answers disc golf stats questions — try asking about players, scores, tournaments, or season results."}

For in-scope but unanswerable questions (data we don't have):
{"path": "out_of_scope", "response": "Brief explanation of what we have and what we don't, 1-2 sentences."}

For answerable questions:
{"path": "answered", "sql": "SELECT ...", "response": "Conversational answer in 1-3 sentences."}
"""

# ── SQL validation ─────────────────────────────────────────────────────────────

def _validate_sql(sql: str) -> str | None:
    """Return None if valid, or an error string describing why it failed."""
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        return "query does not start with SELECT"
    if ";" in stripped:
        return "query contains semicolon"
    if _FORBIDDEN.search(stripped):
        return "query contains forbidden keyword"
    if len(stripped) > MAX_SQL_LENGTH:
        return f"query exceeds {MAX_SQL_LENGTH} character limit"
    return None


# ── Session state helpers ──────────────────────────────────────────────────────

def _init_session() -> None:
    if "search_query_count" not in st.session_state:
        st.session_state.search_query_count = 0
    if "search_last_at" not in st.session_state:
        st.session_state.search_last_at = 0.0
    if "search_session_id" not in st.session_state:
        st.session_state.search_session_id = str(uuid.uuid4())


def queries_remaining() -> int:
    _init_session()
    return max(0, MAX_QUERIES_PER_SESSION - st.session_state.search_query_count)


# ── Logging ────────────────────────────────────────────────────────────────────

def _log(
    *,
    session_id: str,
    question: str,
    path: str,
    generated_sql: str | None = None,
    row_count: int | None = None,
    error_msg: str | None = None,
    latency_ms: int | None = None,
) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO search_log
                        (session_id, question, path, generated_sql, row_count, error_msg, latency_ms)
                    VALUES
                        (:session_id, :question, :path, :generated_sql, :row_count, :error_msg, :latency_ms)
                    """
                ),
                {
                    "session_id": session_id,
                    "question": question,
                    "path": path,
                    "generated_sql": generated_sql,
                    "row_count": row_count,
                    "error_msg": error_msg,
                    "latency_ms": latency_ms,
                },
            )
    except Exception:
        pass  # logging failure must never surface to the user


# ── Core query function ────────────────────────────────────────────────────────

def run_search(question: str) -> dict:
    """
    Run a natural language search query.

    Returns a dict with keys:
      path        — "off_topic" | "out_of_scope" | "answered" | "error" | "rate_limit"
      response    — human-readable text for the user
      df          — DataFrame with results (only when path == "answered")
      remaining   — queries remaining this session
    """
    _init_session()

    session_id = st.session_state.search_session_id

    # Rate limit: session cap
    if st.session_state.search_query_count >= MAX_QUERIES_PER_SESSION:
        return {
            "path": "rate_limit",
            "response": "You've reached the limit for this session. Refresh the page to ask more questions.",
            "remaining": 0,
        }

    # Rate limit: cooldown
    since_last = time.time() - st.session_state.search_last_at
    if since_last < COOLDOWN_SECS:
        wait = COOLDOWN_SECS - since_last
        return {
            "path": "rate_limit",
            "response": f"Please wait {wait:.0f} second(s) before asking another question.",
            "remaining": queries_remaining(),
        }

    t_start = time.time()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "path": "error",
            "response": "Search is not available right now.",
            "remaining": queries_remaining(),
        }

    # ── Claude API call ────────────────────────────────────────────────────────
    import json

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        raw = message.content[0].text.strip()
        # Extract JSON — Claude sometimes prefixes with prose or wraps in a code fence.
        # Find the first '{' and use raw_decode to parse exactly one JSON object.
        brace_idx = raw.find("{")
        if brace_idx == -1:
            raise ValueError("No JSON object found in Claude response")
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(raw, brace_idx)
    except Exception as exc:
        latency_ms = int((time.time() - t_start) * 1000)
        _log(
            session_id=session_id,
            question=question,
            path="error",
            error_msg=f"Claude API error: {exc}",
            latency_ms=latency_ms,
        )
        st.session_state.search_query_count += 1
        st.session_state.search_last_at = time.time()
        return {
            "path": "error",
            "response": "Something went wrong. Please try again.",
            "remaining": queries_remaining(),
        }

    path = parsed.get("path", "error")
    response_text = parsed.get("response", "")
    generated_sql = parsed.get("sql")

    # ── SQL path ───────────────────────────────────────────────────────────────
    df = pd.DataFrame()
    row_count = None
    error_msg = None

    if path == "answered" and generated_sql:
        validation_error = _validate_sql(generated_sql)
        if validation_error:
            path = "error"
            response_text = "I couldn't run that query. Please try rephrasing your question."
            error_msg = f"SQL validation failed: {validation_error}"
        else:
            db = reader_engine if reader_engine else engine
            try:
                df = pd.read_sql(sa.text(generated_sql), db)
                row_count = len(df)
            except Exception as exc:
                path = "error"
                response_text = "I couldn't run that query. Please try rephrasing your question."
                error_msg = f"SQL execution error: {exc}"

    latency_ms = int((time.time() - t_start) * 1000)

    _log(
        session_id=session_id,
        question=question,
        path=path,
        generated_sql=generated_sql if path in ("answered", "error") else None,
        row_count=row_count,
        error_msg=error_msg,
        latency_ms=latency_ms,
    )

    st.session_state.search_query_count += 1
    st.session_state.search_last_at = time.time()

    return {
        "path": path,
        "response": response_text,
        "df": df,
        "remaining": queries_remaining(),
    }
