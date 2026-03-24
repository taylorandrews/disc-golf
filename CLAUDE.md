# CLAUDE.md -- Disc Golf Pro Tour Stats

This file is read by Claude Code at the start of every session.
Keep it current as decisions are made. It is the authoritative reference for how this project works.

---

## Project Purpose

A stats and content dashboard for the Disc Golf Pro Tour (DGPT), focused on the MPO (Men's Pro Open) division.
Data comes from the PDGA website. The site surfaces season stats, event results, player performance,
and eventually a "this week in disc golf" content hub.

**Target domain**: `disc-golf-data.com` (not yet connected -- Phase 1 uses the ALB URL)
See `docs/runbook.md` for domain connection steps.

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Streamlit + Plotly | Custom HTML/CSS via `st.markdown(unsafe_allow_html=True)` |
| Database | PostgreSQL 15 | Local: Docker. Prod: RDS PostgreSQL (not Aurora) |
| ORM / schema | SQLAlchemy (core, not ORM) | Table definitions in `helpers/disc_golf_schema.py` |
| Migrations | Alembic | Schema changes only -- data loading moved to etl/ |
| ETL | `etl/` module | Lambda-compatible; also runnable locally via `python -m etl.run` |
| Data lake | S3 | Raw PDGA JSON archive -- RDS is still the query layer |
| IaC | AWS CDK (Python) | us-east-1, ECS Fargate + RDS + Lambda + S3 |
| CI/CD | GitHub Actions | OIDC, no stored AWS keys |
| Hosting | ECS Fargate | Containerized Streamlit app |

---

## Repository Structure

```
disc-golf/
+-- CLAUDE.md                        # This file
+-- README.md
+-- requirements.txt                 # App dependencies (no version pins yet)
+-- docker-compose.yml               # Local PostgreSQL (postgres:secret, port 5432, db: pdga_data)
+-- alembic.ini
+-- get_pdga_round.py                # Fetches JSON from pdga.com -- see Data Pipeline section
+-- alembic/
|   +-- env.py
|   +-- versions/
|       +-- c196f70ad0b6_create_tables.py   # Schema only -- CREATE TABLE statements
|       +-- b90ec0cb8a47_load_data.py       # Legacy data load (2020-2025) -- do not modify
|       +-- 6ce5726d5313_create_views.py    # Analytical views for dashboard
+-- etl/                             # Nightly ETL pipeline (Phase 2)
|   +-- __init__.py
|   +-- parse.py                     # JSON -> dicts (extracted from load_data migration)
|   +-- db.py                        # DB connection + upsert helpers
|   +-- pdga.py                      # PDGA API fetch + S3 save
|   +-- lambda_handler.py            # Lambda entrypoint (handler function)
|   +-- run.py                       # Local runner: python -m etl.run
|   +-- requirements.txt             # Lambda-only deps (no streamlit/black/etc)
+-- scripts/
|   +-- enrich_tournaments.py   # Seed tournament table from CSV
+-- dashboard/
|   +-- app.py                       # Streamlit entrypoint -- all UI lives here
|   +-- queries.py                   # SQL query functions, all @st.cache_data cached
|   +-- helpers/
|       +-- db_config.py             # SQLAlchemy engine from DATABASE_URL env var
+-- helpers/
|   +-- disc_golf_schema.py          # SQLAlchemy Table definitions (5 tables)
+-- infra/
|   +-- app.py                       # CDK entrypoint
|   +-- requirements.txt             # CDK Python deps
|   +-- stacks/
|       +-- network_stack.py         # VPC, subnets, security groups
|       +-- database_stack.py        # RDS PostgreSQL + Secrets Manager
|       +-- app_stack.py             # ECR, ECS, ALB, OIDC, S3, Lambda, EventBridge
+-- data/                            # GITIGNORED
    +-- seed/
    |   +-- tournament_data.csv      # Legacy registry (2020-2025, 10 columns, do not modify)
    |   +-- 2026_tournaments.csv     # 2026 registry (11 columns, manually maintained)
    +-- pdga/                        # Legacy JSON round files (2020-2025)
```

---

## Database Schema

### Tables

**`tournament`** -- One row per tournament event
- `tournament_id` (PK, Integer) -- from PDGA URL (e.g. pdga.com/tour/event/**88276**)
- `season` -- calendar year
- `name`, `long_name` -- short and full event names
- `start_date` (Date)
- `classification` -- `Elite Series`, `Elite Series Plus`, `Elite Series Playoffs`, `Major`, `Tour Championship`
- `is_worlds` (Boolean)
- `has_finals` (Boolean)
- `total_rounds` (Integer)
- `director` (nullable)
- `location` (nullable) -- "City, ST" string
- `jomez_playlist_url` (nullable) -- YouTube playlist link for event coverage
- `short_name` (nullable) -- e.g. "SFO", "BEO" -- compact display abbreviation
- `dgpt_url` (nullable) -- official DGPT event page URL

**`course`** -- One row per course layout per round (synthetic PK)
- `course_id` -- synthetic: `LayoutID + year + round_num`
- `course_name` -- venue name (e.g. "Olympus")
- `name` -- full layout name (e.g. "DGPT - Supreme Flight Open MPO 2025")
- `holes`, `units` (Feet or Meters)

**`player`** -- One row per PDGA member
- `player_id` -- PDGA member number
- `first_name`, `last_name`, `city`, `state`, `country`, `division`

**`round`** -- One row per player per round
- `round_id` (PK), FKs to `course`, `player`, `tournament`
- `layout_id`, `tournament_round_num`, `won_playoff`
- `prize` (Integer, USD), `round_rating`, `round_score`, `round_status`
- `hole_count`, `card_number`, `tee_time`, `round_date`

**`hole`** -- One row per hole per player per round
- `hole_id` (PK, Text), FKs to `round`, `player`
- `hole_number`, `par`, `score`, `length` (Float, always stored in Feet)

### Views

**`vw_tournament_summary`** -- Primary dashboard view. One row per tournament showing:
champion (rank 1 by score), prize_usd, course name, start/end dates, season, classification, is_worlds.

**`vw_classifications_per_season`** -- Tournament count by classification per season.

**`vw_player_season`** -- Player activity by season (tournaments_played, rounds_played).

**`vw_anomaly`** -- Data quality checks (6 checks): hole count mismatches, duplicate rounds,
missing fields, unusual player count drops (cuts), non-standard hole counts.

### Key Data Notes
- **MPO only** -- FPO and amateur divisions are excluded from all current data and views
- Hole lengths are always stored in **Feet** (Meters converted on ingest: x 3.280833)
- `end_date` is derived: `start_date + (total_rounds - 1)` days
- Finals are stored as round number 12 regardless of actual round number
- Prize money extracted from strings like `"$12,000"` -> integer 12000

---

## Data Pipeline

### Legacy data (2020-2025) -- frozen, do not re-run

Loaded once via `alembic upgrade head` pointing at RDS. Source JSONs live in `data/pdga/`
(gitignored locally) and are archived in S3 at `raw/pdga/legacy/` via `make upload-legacy`.
The Alembic migration `b90ec0cb8a47_load_data.py` must not be modified -- it is idempotent
(`ON CONFLICT DO NOTHING`) but re-running it would re-process all legacy files unnecessarily.

### 2026+ data -- automated nightly ETL

#### Step 1: Register a tournament (manual, ~2 min per event)

Edit `data/seed/2026_tournaments.csv`. Find the tournament ID from the PDGA URL:
`https://www.pdga.com/tour/event/{tournament_id}`

CSV columns (11): `tournament_id, name, short_name, start_date, location, classification, is_worlds, total_rounds, has_finals, jomez_playlist_url, dgpt_url`

| Field | Notes |
|---|---|
| `tournament_id` | Integer from PDGA URL |
| `name` | Display name for the dashboard |
| `short_name` | Abbreviation (e.g. "SFO", "BEO") -- for compact display |
| `start_date` | ISO format: `2026-03-07` |
| `location` | "City, ST" or "City, Country" |
| `classification` | `Elite Series`, `Elite Series Plus`, `Major`, `Tour Championship`, etc. |
| `is_worlds` | `True` or `False` |
| `total_rounds` | Total rounds including finals |
| `has_finals` | `True` or `False` -- finals use PDGA API round 12 |
| `jomez_playlist_url` | YouTube playlist URL for event coverage (add after event) |
| `dgpt_url` | Official DGPT event page URL |

#### Step 2: Enrich and seed the tournament table

```bash
DATABASE_URL=postgresql+psycopg://postgres:<pw>@<host>:5432/pdga_data \
    python scripts/enrich_tournaments.py [--year YEAR]
```

Fetches round 1 from PDGA to auto-fill `long_name`. Upserts into the `tournament` table.
Safe to re-run -- updates `location`, `jomez_playlist_url`, `short_name`, and `dgpt_url` on conflict.

#### Step 3: Load round data (nightly Lambda or manual)

**Automated:** EventBridge fires the Lambda at 06:00 UTC daily.
The Lambda checks which rounds are already in RDS, fetches only new ones from PDGA,
saves raw JSON to S3, and upserts into `course`, `player`, `round`, `hole`.

**Manual trigger** (RDS must be running):
```bash
make invoke-etl
```

**Local runner** (for dev/testing):
```bash
DATABASE_URL=postgresql+psycopg://postgres:<pw>@<host>:5432/pdga_data \
    python -m etl.run
```

**View Lambda logs:**
```bash
make logs-etl
```

### PDGA API

URL: `https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round?TournID={id}&Division=MPO&Round={n}`

This is an **undocumented endpoint** observed from the PDGA live results page. No API key required.
The ETL uses 0.5s sleep between requests (`etl/pdga.py: REQUEST_DELAY`).

Round numbering: sequential rounds 1..N map to PDGA API rounds 1..N, except for finals
which always use API round 12 regardless of their sequential position.

File naming convention: `tournament_{tourn_id}_MPO_round_{sequential_n}.json`
(matches existing `data/pdga/` files and S3 archive keys)

### S3 data lake structure

```
s3://disc-golf-data-lake-368365885895/
  raw/pdga/legacy/{tourn_id}/tournament_{id}_MPO_round_{n}.json  <- 2020-2025, uploaded once
  raw/pdga/2026/{tourn_id}/tournament_{id}_MPO_round_{n}.json    <- written by Lambda
```

Upload legacy data (one-time, after `cdk deploy`):
```bash
make upload-legacy
```

---

## Dashboard (Streamlit)

### Running locally
```bash
docker compose up -d       # start PostgreSQL
streamlit run dashboard/app.py
```
Hot-reloads on file save. Hit R in browser to force reload.

### Architecture rules
- **Never use `st.dataframe()`** for user-facing tables -- always build custom HTML tables
  via `st.markdown(..., unsafe_allow_html=True)`
- HTML cards must be **complete self-contained blocks** in a single `st.markdown()` call.
  Never split opening and closing tags across multiple `st.markdown()` calls -- Streamlit
  renders each call as an isolated DOM element.
- Plotly charts: always `config={"displayModeBar": False}`, white background, no gridlines
- All query functions in `queries.py` must use `@st.cache_data`
- Tab navigation uses `st.tabs()` styled with CSS -- do not revert to per-year tabs

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
`Season` | `This Week` | `Search` | `State of Disc Golf` | `About`

Season tab: year selector, stat cards, winners bar chart, events table.
This Week tab (Phase 3): triptych, schedule strip, video coverage, stat callout, recent results.
Search, State of Disc Golf, About: placeholder shells (`render_shell()`).

---

## Code Style

- **Type hints**: function signatures only -- parameters and return types
- **Formatting**: Black (in requirements)
- **SQL**: never use f-string interpolation for user-supplied values -- use parameterized queries
  (currently `queries.py` uses f-strings for internal season integers -- acceptable for now,
  must be fixed before any user-input SQL is written)
- **Comments**: only where logic is not self-evident
- **No docstrings** unless explicitly requested
- **No unused variables** -- linter will flag them
- **Imports**: stdlib -> third-party -> local, separated by blank lines

---

## AWS Infrastructure

- **IaC**: AWS CDK (Python) -- always CDK, never Terraform
- **Region**: `us-east-1`, **Account**: `368365885895`
- **App hosting**: ECS Fargate -- cluster `disc-golf-cluster`, service `disc-golf-service`
- **Database**: RDS PostgreSQL t3.micro -- instance ID `disc-golf-db`
- **Container registry**: ECR repo `disc-golf-app`
- **Load balancer**: ALB `disc-golf-alb` (HTTP:80 -> Streamlit:8501)
- **Task size**: 0.5 vCPU / 1 GB RAM
- **S3 data lake**: `disc-golf-data-lake-368365885895` (RemovalPolicy.RETAIN)
- **ETL Lambda**: `disc-golf-nightly-etl` (Python 3.12, 512MB, 5min timeout)
- **EventBridge rule**: `disc-golf-nightly-etl` -- cron 06:00 UTC daily
- **Domain**: `disc-golf-data.com` (not yet connected -- site runs at ALB URL for now)
- **GitHub Actions**: OIDC role `disc-golf-github-actions` -- no AWS keys stored in GitHub
- CDK stacks live in `infra/stacks/`: NetworkStack, DatabaseStack, AppStack
- Deployment: `git push main` -> GitHub Actions -> ECR -> ECS rolling deploy
- Stop/start: `make stop` / `make start` -- see `docs/runbook.md`
- Estimated cost: ~$50/month running, ~$16/month stopped (ALB base charge only)
- Lambda does not run when RDS is stopped -- exits cleanly with 503

---

## Phasing Plan

### Phase 1 -- Infrastructure (complete)

Dockerize app -> CDK stack (VPC + RDS + ECS + ALB) -> GitHub Actions CI/CD -> live at ALB URL.

### Phase 2 -- ETL Refactor + 2026 Season (complete)

Automated nightly data import for 2026 season. S3 data lake, Lambda ETL, EventBridge cron.
`etl/` module (parse, db, pdga, standings, youtube). Tournament seed CSV + enrich script.
See `docs/etl.md` for full details.

### Phase 3 -- Landing Page (steps 1-4 complete)

"This week in disc golf" hub on the "This Week" tab. Steps complete:
1. Static shell (triptych, schedule strip, stat callout, recent results)
2. DGPT Points Standings (scraped from DGPT.com AJAX endpoint)
3. YouTube coverage cards (JomezPro playlist scraper + creator preview cards)
4. Tournament schema additions + clickable schedule strip (short_name, dgpt_url)

Steps remaining:
5. Podcast episode cards (`etl/podcast.py` -> `podcast_episodes` table)
6. Polish + mobile layout pass

See `docs/landing-page-design.md` for full spec.

### Phase 4 -- Text-to-SQL Search (deprioritized)

Claude API (`claude-sonnet-4-6`) -> natural language -> SQL -> conversational results.
Requires stable schema + `docs/schema.md` with semantic column descriptions.
Read-only DB user required for safety.

### Phase 5 -- Advanced features

Points standings, in-season tracking, player profiles, historical comparisons.

---

## Known Issues / Tech Debt

- `queries.py` uses f-string SQL interpolation -- safe for now (internal integer values only),
  must be parameterized before any user-input queries are added
- `data/` is gitignored -- JSON round files are not version controlled
- `requirements.txt` has no version pins -- add pins before deploying to prod
- `vw_classifications_per_season` is imported in `queries.py` but unused in current `app.py`
- `get_pdga_round.py` has no request pacing -- add `time.sleep(0.5)` between requests
- `etl/` CDK bundling runs `docker` during `cdk synth/deploy` -- Docker Desktop must be running

---

## Environment

```bash
# .env (local)
DATABASE_URL=postgresql+psycopg://postgres:secret@localhost:5432/pdga_data
```

Local PostgreSQL runs in Docker. Schema + data loaded via Alembic migrations.
Prod uses an equivalent `DATABASE_URL` pointing to RDS.
