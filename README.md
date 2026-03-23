# Disc Golf Pro Tour Stats — disc-golf-data.com

A stats and content dashboard for the DGPT MPO division. Surfaces season results,
event standings, player data, and a live "this week in disc golf" hub —
pulling from the PDGA API, DGPT.com, and YouTube.

---

## What's Live

| Feature | Status |
|---|---|
| Season tab (2020–2026) — stat cards, winners chart, events table | Live |
| Nightly ETL — PDGA round data → RDS, archived to S3 | Live |
| DGPT Points Standings widget (scraped from DGPT.com) | Live |
| JomezPro coverage cards — full event playlist, sorted by round | Live |
| Creator preview cards — Aderhold, Goosage, Barela, Wysocki | Live |
| Schedule strip — 2026 season calendar, color-coded by classification | Live |
| Stat callout — lowest winning score of the season | Live |
| Recent results table — last 4 completed events | Live |
| Podcast episode cards | Upcoming |
| Player profiles | Upcoming |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Streamlit + Plotly + custom HTML/CSS |
| Database | PostgreSQL 15 — Docker locally, RDS t3.micro in prod |
| ORM / schema | SQLAlchemy core + Alembic migrations |
| ETL | `etl/` module — runs in AWS Lambda nightly |
| Data lake | S3 — raw PDGA JSON archive |
| IaC | AWS CDK (Python), us-east-1 |
| CI/CD | GitHub Actions (OIDC, no stored AWS keys) |
| Hosting | ECS Fargate + ALB |

---

## Repository Layout

```
disc-golf/
├── dashboard/
│   ├── app.py              # Streamlit entrypoint — all UI
│   ├── queries.py          # SQL query functions (@st.cache_data)
│   └── helpers/
│       └── db_config.py    # SQLAlchemy engine from DATABASE_URL
├── etl/
│   ├── lambda_handler.py   # Lambda entrypoint (EventBridge cron, 06:00 UTC)
│   ├── run.py              # Local runner: python -m etl.run
│   ├── db.py               # DB connection + upsert helpers
│   ├── parse.py            # PDGA JSON → dicts
│   ├── pdga.py             # PDGA API fetch + S3 save
│   ├── standings.py        # DGPT standings scraper
│   └── youtube.py          # YouTube RSS + playlist scraper
├── helpers/
│   └── disc_golf_schema.py # SQLAlchemy table definitions
├── alembic/
│   └── versions/           # Schema migrations (additive only)
├── infra/
│   └── stacks/             # CDK: NetworkStack, DatabaseStack, AppStack
├── scripts/
│   └── enrich_tournaments.py  # Seed tournament table from CSV
├── data/seed/
│   └── 2026_tournaments.csv   # 2026 event registry (manually maintained)
└── docs/
    ├── runbook.md          # Ops procedures
    ├── architecture.md     # System design
    ├── etl.md              # ETL pipeline details
    ├── roadmap.md          # Project history + upcoming work
    └── landing-page-design.md  # Phase 3 design spec
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Docker Desktop
- AWS CLI (for `make deploy-etl`, `make invoke-etl`)

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d          # start local PostgreSQL
alembic upgrade head          # create schema + load legacy data (2020-2025)
streamlit run dashboard/app.py
```

Hot-reloads on file save. Hit `R` in the browser to force a full reload.

### Environment

```bash
# .env (local)
DATABASE_URL=postgresql+psycopg://postgres:secret@localhost:5432/pdga_data
```

---

## Data Pipeline

### Nightly ETL (automated)

EventBridge triggers the Lambda at 06:00 UTC daily. The handler:

1. **PDGA rounds** — fetches any new rounds for 2026 tournaments, saves raw JSON to S3, upserts into `course` / `player` / `round` / `hole`
2. **DGPT standings** — POSTs to DGPT.com WordPress AJAX endpoint, parses HTML, rebuilds `season_standings`
3. **YouTube RSS** — fetches 15 most-recent videos from 5 channels (JomezPro + 4 creator channels), upserts into `media_youtube`
4. **JomezPro playlist** — scrapes the current event's playlist page via `ytInitialData`, stores full video set with sort order for correct round display

### Manual triggers

```bash
make invoke-etl     # trigger Lambda manually (RDS must be running)
make logs-etl       # tail Lambda logs
make deploy-etl     # repackage + upload Lambda code without Docker/CDK
make migrate-prod   # run Alembic migrations against RDS
```

### Adding a 2026 tournament

1. Edit `data/seed/2026_tournaments.csv` — add a row with tournament ID from `pdga.com/tour/event/{id}`
2. Run `scripts/enrich_tournaments.py` to auto-fill `long_name` and upsert into RDS
3. After the event, add the `jomez_playlist_url` to the CSV and re-run enrich (uses `ON CONFLICT DO UPDATE`)
4. ETL picks up new rounds automatically on next run

---

## AWS Infrastructure

- **ECS Fargate** — cluster `disc-golf-cluster`, service `disc-golf-service` (0.5 vCPU / 1 GB)
- **RDS PostgreSQL** — `disc-golf-db`, t3.micro (~$16/month stopped, ~$50/month running)
- **Lambda** — `disc-golf-nightly-etl`, Python 3.12, 512 MB, 5-min timeout
- **S3** — `disc-golf-data-lake-368365885895` (RemovalPolicy.RETAIN)
- **ALB** — `disc-golf-alb`, HTTP:80

```bash
make stop     # stop RDS + scale ECS to 0 (saves ~$34/month)
make start    # restart both
```

See `docs/runbook.md` for full ops procedures.

---

## Docs

- `docs/roadmap.md` — project history and upcoming work
- `docs/architecture.md` — system design and data flow
- `docs/etl.md` — ETL pipeline details and PDGA API notes
- `docs/landing-page-design.md` — Phase 3 landing page spec
- `docs/runbook.md` — day-to-day ops: deploy, stop/start, migrate, seed
