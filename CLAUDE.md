# CLAUDE.md — Disc Golf Pro Tour Stats

This file is read by Claude Code at the start of every session.
Keep it current as decisions are made. It is the authoritative reference for how this project works.

---

## Project Purpose

A stats and content dashboard for the Disc Golf Pro Tour (DGPT), focused on the MPO (Men's Pro Open) division.
Data comes from the PDGA website. The site surfaces season stats, event results, player performance,
and eventually a "this week in disc golf" content hub.

**Current domain**: `get-your-disc-golf-data.com` (stealth/placeholder — intentionally silly)

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Streamlit + Plotly | Custom HTML/CSS via `st.markdown(unsafe_allow_html=True)` |
| Database | PostgreSQL 15 | Local: Docker. Prod: RDS PostgreSQL (not Aurora) |
| ORM / schema | SQLAlchemy (core, not ORM) | Table definitions in `helpers/disc_golf_schema.py` |
| Migrations | Alembic | **Schema changes only** — not for data loading |
| ETL | Standalone Python scripts (target state) | Currently embedded in Alembic — being refactored out |
| IaC | AWS CDK (Python) | us-east-1, ECS Fargate + RDS PostgreSQL |
| CI/CD | GitHub Actions (to be built) | |
| Hosting | ECS Fargate | Containerized Streamlit app |

---

## Repository Structure

```
disc-golf/
├── CLAUDE.md                        # This file
├── README.md
├── requirements.txt                 # No version pinning yet — add pins when deploying
├── docker-compose.yml               # Local PostgreSQL (postgres:secret, port 5432, db: pdga_data)
├── alembic.ini
├── get_pdga_round.py                # Fetches JSON from pdga.com — see Data Pipeline section
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── c196f70ad0b6_create_tables.py   # Schema only — CREATE TABLE statements
│       ├── b90ec0cb8a47_load_data.py       # LEGACY: data load in migration — being replaced
│       └── 6ce5726d5313_create_views.py    # Analytical views for dashboard
├── dashboard/
│   ├── app.py                       # Streamlit entrypoint — all UI lives here
│   ├── queries.py                   # SQL query functions, all @st.cache_data cached
│   └── helpers/
│       └── db_config.py             # SQLAlchemy engine from DATABASE_URL env var
├── helpers/
│   └── disc_golf_schema.py          # SQLAlchemy Table definitions (5 tables)
└── data/                            # GITIGNORED
    ├── seed/
    │   └── tournament_data.csv      # Manually maintained tournament registry
    └── pdga/                        # JSON round files fetched from pdga.com
```

---

## Database Schema

### Tables

**`tournament`** — One row per tournament event
- `tournament_id` (PK, Integer) — from PDGA URL (e.g. pdga.com/tour/event/**88276**)
- `season` — calendar year
- `name`, `long_name` — short and full event names
- `start_date` (Date)
- `classification` — `Elite Series`, `Elite Series Plus`, `Elite Series Playoffs`, `Major`, `Tour Championship`
- `is_worlds` (Boolean)
- `has_finals` (Boolean)
- `total_rounds` (Integer)
- `director` (nullable)

**`course`** — One row per course layout per round (synthetic PK)
- `course_id` — synthetic: `LayoutID + year + round_num`
- `course_name` — venue name (e.g. "Olympus")
- `name` — full layout name (e.g. "DGPT - Supreme Flight Open MPO 2025")
- `holes`, `units` (Feet or Meters)

**`player`** — One row per PDGA member
- `player_id` — PDGA member number
- `first_name`, `last_name`, `city`, `state`, `country`, `division`

**`round`** — One row per player per round
- `round_id` (PK), FKs to `course`, `player`, `tournament`
- `layout_id`, `tournament_round_num`, `won_playoff`
- `prize` (Integer, USD), `round_rating`, `round_score`, `round_status`
- `hole_count`, `card_number`, `tee_time`, `round_date`

**`hole`** — One row per hole per player per round
- `hole_id` (PK, Text), FKs to `round`, `player`
- `hole_number`, `par`, `score`, `length` (Float, always stored in Feet)

### Views

**`vw_tournament_summary`** — Primary dashboard view. One row per tournament showing:
champion (rank 1 by score), prize_usd, course name, start/end dates, season, classification, is_worlds.

**`vw_classifications_per_season`** — Tournament count by classification per season.

**`vw_player_season`** — Player activity by season (tournaments_played, rounds_played).

**`vw_anomaly`** — Data quality checks (6 checks): hole count mismatches, duplicate rounds,
missing fields, unusual player count drops (cuts), non-standard hole counts.

### Key Data Notes
- **MPO only** — FPO and amateur divisions are excluded from all current data and views
- Hole lengths are always stored in **Feet** (Meters converted on ingest: × 3.280833)
- `end_date` is derived: `start_date + (total_rounds - 1)` days
- Finals are stored as round number 12 regardless of actual round number
- Prize money extracted from strings like `"$12,000"` → integer 12000

---

## Data Pipeline (Current State)

### Step 1: Register a tournament
Edit `data/seed/tournament_data.csv` manually. Find the tournament ID from the PDGA URL:
`https://www.pdga.com/tour/event/{tournament_id}`

CSV columns: `tournament_id, season, name, long_name, start_date, classification, director, is_worlds, has_finals, total_rounds`

### Step 2: Fetch round data
```bash
python get_pdga_round.py
```
Hits pdga.com at this URL pattern:
`https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round?TournID={id}&Division=MPO&Round={n}`

This is **not an official API** — it's an undocumented endpoint observed from the PDGA live results page.
No API key required. Use polite request pacing (add `time.sleep()` between requests).

Writes JSON to `data/temp/`. User manually moves to `data/pdga/`.

### Step 3: Load into DB (current — being replaced)
```bash
alembic upgrade head
```
The migration `b90ec0cb8a47_load_data.py` reads all JSONs from `data/pdga/` and upserts.
`ON CONFLICT DO NOTHING` makes this idempotent.

### Target State (ETL refactor — Phase 2)
- Replace the data-loading migration with a standalone `etl/` module
- Runnable daily without Alembic: `python etl/run.py`
- Alembic stays for schema changes only
- Support incremental loads (new rounds only) without full re-processing

---

## Dashboard (Streamlit)

### Running locally
```bash
docker compose up -d       # start PostgreSQL
streamlit run dashboard/app.py
```
Hot-reloads on file save. Hit R in browser to force reload.

### Architecture rules
- **Never use `st.dataframe()`** for user-facing tables — always build custom HTML tables
  via `st.markdown(..., unsafe_allow_html=True)`
- HTML cards must be **complete self-contained blocks** in a single `st.markdown()` call.
  Never split opening and closing tags across multiple `st.markdown()` calls — Streamlit
  renders each call as an isolated DOM element.
- Plotly charts: always `config={"displayModeBar": False}`, white background, no gridlines
- All query functions in `queries.py` must use `@st.cache_data`
- Tab navigation uses `st.tabs()` styled with CSS — do not revert to per-year tabs

### Color palette
```python
GREEN       = "#1D6B44"   # primary accent, bar charts, links, prize money
AMBER       = "#E8A838"   # highlights: #1 ranked player, world champion callout
BG          = "#F8F9FA"   # page background
WHITE       = "#FFFFFF"   # cards
TEXT        = "#1C1C1E"   # primary text
MUTED       = "#6B7280"   # secondary text, labels, dates
BORDER      = "#E5E7EB"   # card borders, table dividers
LIGHT_GREEN = "#EAF4EE"   # table row hover, subtle highlights
```

### Nav tabs (current)
`Season` | `Landing Page` | `Search` | `State of Disc Golf` | `About`

Season tab is implemented. All others are placeholder shells (`render_shell()`).

---

## Code Style

- **Type hints**: function signatures only — parameters and return types
- **Formatting**: Black (in requirements)
- **SQL**: never use f-string interpolation for user-supplied values — use parameterized queries
  (currently `queries.py` uses f-strings for internal season integers — acceptable for now,
  must be fixed before any user-input SQL is written)
- **Comments**: only where logic isn't self-evident
- **No docstrings** unless explicitly requested
- **No unused variables** — linter will flag them
- **Imports**: stdlib → third-party → local, separated by blank lines

---

## AWS Infrastructure (Phase 1 — to be built)

- **IaC**: AWS CDK (Python) — always CDK, never Terraform
- **Region**: `us-east-1`
- **App hosting**: ECS Fargate (containerized Streamlit)
- **Database**: RDS PostgreSQL (same engine as local Docker)
- **Domain**: `get-your-disc-golf-data.com` (placeholder)
- CDK app will live in `infra/` directory at repo root

---

## Phasing Plan

### Phase 1 — Infrastructure
Dockerize app → CDK stack (VPC + RDS + ECS + ALB) → GitHub Actions CI/CD → live at domain

### Phase 2 — ETL Refactor
Standalone `etl/` module → daily automated data import → no more manual Alembic data loads
Includes: better tournament registration flow, request pacing for pdga.com fetches

### Phase 3 — Landing Page
"This week in disc golf" — upcoming events, JomezPro video links, Tour Life Podcast,
Ezra Aderhold + Aaron Goosage content, disc golf blog links. Requires Phase 2 data flowing.

### Phase 4 — Text-to-SQL Search (deprioritized)
Claude API (`claude-sonnet-4-6`) → natural language → SQL → conversational results.
Requires stable schema + `docs/schema.md` with semantic column descriptions.
Read-only DB user required for safety.

### Phase 5 — Advanced features
Points standings, in-season tracking, player profiles, historical comparisons.

---

## Known Issues / Tech Debt

- `queries.py` uses f-string SQL interpolation — safe for now (internal integer values only),
  must be parameterized before any user-input queries are added
- `data/` is gitignored — JSON round files are not version controlled
- `requirements.txt` has no version pins — add pins before deploying to prod
- `disc-golf.session.sql` is untracked — keep it that way (ad-hoc analysis scratch file)
- `vw_classifications_per_season` is imported in `queries.py` but unused in current `app.py`
- `get_pdga_round.py` has no request pacing — add `time.sleep(0.5)` between requests

---

## Environment

```bash
# .env (local)
DATABASE_URL=postgresql://postgres:secret@localhost:5432/pdga_data
```

Local PostgreSQL runs in Docker. Schema + data loaded via Alembic migrations.
Prod will use an equivalent `DATABASE_URL` pointing to RDS.
