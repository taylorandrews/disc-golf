# ETL Pipeline

How PDGA round data gets from pdga.com into the dashboard.

---

## PDGA API

**URL pattern:**
```
https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round
    ?TournID={tournament_id}&Division=MPO&Round={round_num}
```

This is an **undocumented endpoint** observed from the PDGA live results page.
No API key required. The ETL uses a 0.5s delay between requests (`etl/pdga.py: REQUEST_DELAY`).

**Response structure (abbreviated):**
```json
{
  "data": [
    {
      "live_round_id": 12345,
      "layouts": [
        {
          "LayoutID": 999,
          "TournID": 88276,
          "CourseName": "Idlewild",
          "Name": "DGPT - Idlewild Open MPO 2025",
          "Holes": 18,
          "Units": "Feet",
          "Detail": [{"Hole": "H1", "HoleOrdinal": 1, "Par": 3, "Length": 285}, ...]
        }
      ],
      "scores": [
        {
          "PDGANum": 12345,
          "FirstName": "Paul",
          "LastName": "McBeth",
          "HasPDGANum": 1,
          "RoundStarted": 1,
          "Completed": 1,
          "ScoreID": 99999,
          "RoundtoPar": -11,
          "RoundRating": 1048,
          "Prize": "$3,000",
          "HoleScores": [3, 2, 3, 2, ...],
          ...
        }
      ]
    }
  ]
}
```

**Round numbering:** The PDGA API numbers rounds sequentially (1, 2, 3...) except for
finals, which always use round **12** regardless of their position in the event.
The ETL maps sequential position → API round number via `etl/pdga.py: api_round_num()`.

---

## File naming convention

All JSON files use this pattern, matching the existing `data/pdga/` legacy files:

```
tournament_{tournament_id}_MPO_round_{sequential_n}.json
```

`sequential_n` is always 1, 2, 3... — never 12, even for finals.

**S3 layout:**
```
s3://disc-golf-data-lake-368365885895/
  raw/pdga/legacy/{tourn_id}/tournament_{id}_MPO_round_{n}.json   ← 2020-2025
  raw/pdga/2026/{tourn_id}/tournament_{id}_MPO_round_{n}.json     ← 2026+
```

---

## ETL module (`etl/`)

| File | Purpose |
|---|---|
| `parse.py` | Converts PDGA JSON → Python dicts for each table. Extracted from the legacy Alembic migration so both paths share identical logic. |
| `db.py` | DB connection (from `DATABASE_URL` env var or Secrets Manager), `get_loaded_round_nums()`, `upsert_all()` |
| `pdga.py` | `fetch_round()`, `save_to_s3()`, `api_round_num()` |
| `lambda_handler.py` | Lambda entrypoint — queries 2026 tournaments, checks loaded rounds, fetches/upserts new ones |
| `run.py` | Local runner: `python -m etl.run` |
| `requirements.txt` | Lambda-only deps (`requests`, `psycopg[binary]`, `SQLAlchemy`). `boto3` is provided by the Lambda runtime. |

**DB connection logic in `etl/db.py`:**
- If `DATABASE_URL` is set → use it directly (local dev, `python -m etl.run`)
- Otherwise → fetch credentials from Secrets Manager using `DB_SECRET_ARN` + `DB_HOST` env vars (Lambda)

---

## Lambda behavior

1. Query `tournament` table for all `season = 2026` rows
2. For each tournament, query `round` for `DISTINCT tournament_round_num` already loaded
3. For each missing sequential round number (1..total_rounds):
   - Fetch from PDGA API (with 0.5s delay)
   - Skip if no data or no scores have started
   - Save raw JSON to S3
   - Parse and upsert into `course`, `player`, `round`, `hole`
4. Return `{"statusCode": 200, "body": "Loaded N new round(s)."}`
5. If RDS is unreachable → return `{"statusCode": 503, ...}` cleanly

The Lambda **does not** write to the `tournament` table — tournaments must be seeded via `scripts/enrich_2026_tournaments.py` before rounds can be loaded.

**EventBridge cron:** `06:00 UTC daily`. If the stacks are torn down, the EventBridge rule doesn't exist and the Lambda doesn't fire.

---

## Tournament registration workflow

### 1. Add to seed CSV

Edit `data/seed/2026_tournaments.csv`:

```csv
tournament_id,name,start_date,classification,is_worlds,total_rounds,has_finals
88276,Idlewild Open,2026-08-14,Elite Series,0,3,0
```

| Field | Where to find it |
|---|---|
| `tournament_id` | Integer at end of `pdga.com/tour/event/{id}` |
| `name` | Short name for dashboard display |
| `start_date` | ISO date of round 1 |
| `classification` | `Elite Series`, `Elite Series Plus`, `Major`, `Tour Championship`, etc. |
| `is_worlds` | `0` or `1` |
| `total_rounds` | Total rounds including finals |
| `has_finals` | `0` or `1` |

### 2. Enrich and seed

```bash
DATABASE_URL=postgresql+psycopg://postgres:<pw>@<host>:5432/pdga_data \
    python scripts/enrich_2026_tournaments.py
```

This fetches round 1 from PDGA to extract `long_name` from the layout `Name` field
(e.g. `"DGPT - Idlewild Open MPO 2026"`), then upserts into the `tournament` table.
Safe to re-run (`ON CONFLICT DO NOTHING`).

### 3. Load rounds

```bash
make invoke-etl   # manual
# or wait for the 06:00 UTC cron
```

---

## Legacy data (2020-2025)

Loaded once via Alembic migration `b90ec0cb8a47_load_data.py`. The migration reads all
JSON files from `data/pdga/` and upserts using the same logic now in `etl/parse.py`.

**Do not re-run this migration.** It is idempotent (`ON CONFLICT DO NOTHING`) but
would re-process all 194 files unnecessarily. The migration is frozen.

**Known data quality issues:** Some legacy JSON files were manually edited to fix
null fields that violate NOT NULL constraints. Do not overwrite them from the raw PDGA API.

Legacy JSONs are archived to S3 once via `make upload-legacy`.

---

## Local development

Run the ETL locally against your Docker PostgreSQL:

```bash
docker compose up -d
DATABASE_URL=postgresql+psycopg://postgres:secret@localhost:5432/pdga_data \
    python -m etl.run
```
