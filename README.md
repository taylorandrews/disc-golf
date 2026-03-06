# Disc Golf Data Pipeline + Dashboard

A Python project for collecting PDGA Live round data, loading it into PostgreSQL, and exploring season-level insights in a Streamlit dashboard.

## What This Repo Does

- Downloads PDGA round JSON payloads for seeded tournaments (`get_pdga_round.py`)
- Builds and migrates a PostgreSQL schema with Alembic
- Loads tournament, course, player, round, and hole data from local JSON files
- Creates analytical SQL views for dashboard reporting
- Serves a Streamlit dashboard with season tabs and Plotly visualizations

## Tech Stack

- Python 3.11+
- PostgreSQL 15 (via Docker Compose)
- SQLAlchemy + Alembic
- Streamlit + Plotly

## Project Layout

- `get_pdga_round.py` - Fetches PDGA Live round JSON files
- `helpers/disc_golf_schema.py` - Canonical SQLAlchemy table definitions
- `alembic/versions/c196f70ad0b6_create_tables.py` - Creates tables
- `alembic/versions/b90ec0cb8a47_load_data.py` - Loads/upserts data from `data/pdga/`
- `alembic/versions/6ce5726d5313_create_views.py` - Creates dashboard views
- `dashboard/app.py` - Streamlit app entrypoint
- `dashboard/queries.py` - Dashboard SQL query layer
- `data/seed/tournament_data.csv` - Tournament seed metadata

## Prerequisites

- Python 3.11+ and `pip`
- Docker Desktop (or Docker Engine + Docker Compose)
- Internet access to fetch PDGA Live API data (first-time bootstrap)
- Local disk space for `data/pdga` JSON files (this folder is gitignored)

## Quick Start (Developer)

Use this full sequence when standing the project up from scratch.

1. Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start Postgres:

```bash
docker compose up -d
```

3. Confirm database connection settings:

```bash
# Streamlit / app queries read from .env
cat .env

# Alembic migrations read from alembic.ini
rg "sqlalchemy.url" alembic.ini
```

4. Fetch tournament round data (one-time initial load, or whenever you refresh source data):

```bash
python get_pdga_round.py
```

5. Move fetched files into the ingest directory used by Alembic:

```bash
mkdir -p data/pdga
mv data/temp/*.json data/pdga/
```

6. Run migrations (creates tables, loads data, then creates views):

```bash
alembic upgrade head
```

7. Start the dashboard:

```bash
streamlit run dashboard/app.py
```

### Normal Restart (after initial load)

If your DB and `data/pdga` are already populated, you usually only need:

```bash
docker compose up -d
streamlit run dashboard/app.py
```

## Data Flow

1. Seed tournament metadata lives in `data/seed/tournament_data.csv`.
2. `get_pdga_round.py` fetches PDGA round JSON and writes files to `data/temp/`.
3. JSON files to be ingested should be available under `data/pdga/`.
4. Alembic migration `b90ec0cb8a47` parses files and upserts rows into base tables.
5. Alembic migration `6ce5726d5313` creates reporting views used by Streamlit.

## Useful Commands

Run all migrations:

```bash
alembic upgrade head
```

Roll back one migration:

```bash
alembic downgrade -1
```

Fetch new PDGA round JSON files:

```bash
python get_pdga_round.py
```

Stop Postgres:

```bash
docker compose down
```

## Dashboard Views Used

The dashboard reads from these views:

- `vw_classifications_per_season`
- `vw_tournament_summary`

Additional QA/analysis views are also created:

- `vw_player_season`
- `vw_anomaly`

## Notes

- The repository currently ignores `data/`, so local PDGA JSON files are not tracked in Git.
- Alembic config uses the DB URL in `alembic.ini` (`sqlalchemy.url`) for migrations.
- Streamlit queries use `DATABASE_URL` from `.env` via `python-dotenv`.
