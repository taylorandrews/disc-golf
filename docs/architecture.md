# Architecture

Technical reference for the disc-golf stats platform.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Streamlit + Plotly | Custom HTML/CSS via `st.markdown(unsafe_allow_html=True)` |
| Database | PostgreSQL 15 | Local: Docker. Prod: RDS t3.micro |
| ORM / schema | SQLAlchemy (core, not ORM) | Table definitions in `helpers/disc_golf_schema.py` |
| Migrations | Alembic | Schema changes and legacy data load only |
| ETL | `etl/` Python module | Lambda-compatible; runnable locally via `python -m etl.run` |
| Data lake | S3 | Raw PDGA JSON archive; RDS is the query layer |
| IaC | AWS CDK (Python) | Always CDK, never Terraform |
| CI/CD | GitHub Actions | OIDC auth; no AWS keys stored in GitHub |
| Hosting | ECS Fargate | Containerized Streamlit on public subnet |

---

## AWS Infrastructure

All resources in `us-east-1`, account `368365885895`.

```
Internet
    │
    ▼
ALB (disc-golf-alb, port 80)
    │
    ▼
ECS Fargate (disc-golf-service, port 8501)
  0.5 vCPU / 1 GB RAM
  Public subnet, assign_public_ip=True (no NAT gateway)
    │
    ▼
RDS PostgreSQL 15 (disc-golf-db, t3.micro)
  Publicly accessible (developer access; 32-char generated password)
  RemovalPolicy.DESTROY

S3 (disc-golf-data-lake-368365885895)
  RemovalPolicy.RETAIN — survives make destroy

Lambda (disc-golf-nightly-etl)
  Python 3.12, 512 MB, 5 min timeout
  Triggered by EventBridge cron 06:00 UTC daily
  Reads Secrets Manager, writes S3, reads/writes RDS public endpoint

ECR (disc-golf-app)
  Docker images for ECS Fargate tasks

GitHub Actions OIDC
  Role: disc-golf-github-actions
  Scoped to main-branch pushes on taylorandrews/disc-golf
```

**CDK stacks:**
- `DiscGolfNetwork` — VPC (public subnets only, no NAT), security groups
- `DiscGolfDatabase` — RDS + Secrets Manager
- `DiscGolfApp` — ECR, ECS, ALB, OIDC role, S3, Lambda, EventBridge

**Cost:**
- Running: ~$50/month
- Stopped (`make stop`): ~$16/month (ALB base charge)
- Destroyed: $0 (S3 storage is negligible)

---

## Data Model

### Tables

**`tournament`** — one row per event
| Column | Type | Notes |
|---|---|---|
| `tournament_id` | Integer PK | From PDGA URL: `pdga.com/tour/event/{id}` |
| `season` | Integer | Calendar year |
| `name` | Text | Short display name |
| `long_name` | Text | Full event title from PDGA API layout name |
| `start_date` | Date | First round date |
| `classification` | Text | `Elite Series`, `Elite Series Plus`, `Major`, `Tour Championship`, etc. |
| `is_worlds` | Boolean | |
| `has_finals` | Boolean | Finals use PDGA API round 12 |
| `total_rounds` | Integer | Includes finals |
| `director` | Text | Nullable |

**`course`** — one row per layout per round (synthetic PK)
| Column | Type | Notes |
|---|---|---|
| `course_id` | Integer PK | `LayoutID + year + round_num` (synthetic) |
| `course_name` | Text | Venue name, e.g. "Olympus" |
| `name` | Text | Full layout name, e.g. "DGPT - Supreme Flight Open MPO 2025" |
| `holes` | Integer | |
| `units` | Text | `Feet` or `Meters` |

**`player`** — one row per PDGA member
| Column | Type | Notes |
|---|---|---|
| `player_id` | Integer PK | PDGA member number |
| `first_name`, `last_name` | Text | |
| `city`, `state`, `country` | Text | |
| `division` | Text | MPO only in current data |

**`round`** — one row per player per round
| Column | Type | Notes |
|---|---|---|
| `round_id` | Integer PK | `ScoreID` from PDGA API, or `ResultID + round_num` fallback |
| `tournament_id`, `player_id`, `course_id` | FK | |
| `tournament_round_num` | Integer | Sequential: 1, 2, 3... (not API round number) |
| `round_score` | Integer | Score relative to par |
| `round_rating` | Integer | PDGA rating for this round |
| `prize` | Integer | USD; EUR converted |
| `round_date` | Date | `start_date + (round_num - 1)` days |
| `won_playoff`, `round_status`, `hole_count`, `card_number`, `tee_time` | Various | |

**`hole`** — one row per hole per player per round
| Column | Type | Notes |
|---|---|---|
| `hole_id` | Text PK | `{round_id}_H{n}` |
| `round_id`, `player_id` | FK | |
| `hole_number`, `par`, `score` | Integer | |
| `length` | Float | Always stored in **Feet** (meters × 3.280833) |

### Views

| View | Purpose |
|---|---|
| `vw_tournament_summary` | One row per tournament: champion, prize, course, dates. Primary dashboard view. |
| `vw_classifications_per_season` | Tournament count by classification per season |
| `vw_player_season` | Player activity by season (tournaments, rounds played) |
| `vw_anomaly` | 6 data quality checks: hole count mismatches, duplicate rounds, null fields, player count drops, non-standard hole counts |

### Key data rules
- MPO only — FPO and amateur divisions are excluded
- Hole lengths always stored in Feet
- Finals always stored as `tournament_round_num = total_rounds` regardless of PDGA API round 12
- Prize money: `"$12,000"` → integer `12000`

---

## Data Flow

```
PDGA live API (undocumented)
    │
    │  GET /live_results_fetch_round?TournID=X&Division=MPO&Round=N
    │
    ▼
etl/pdga.py (fetch_round)
    │
    ├── S3: raw/pdga/2026/{tourn_id}/tournament_{id}_MPO_round_{n}.json
    │
    └── etl/parse.py (get_courses, get_players, get_holes_and_rounds)
            │
            ▼
        etl/db.py (upsert_all)
            │
            ▼
        RDS PostgreSQL
            │
            ▼
        Views (vw_tournament_summary, etc.)
            │
            ▼
        Streamlit dashboard (dashboard/queries.py → dashboard/app.py)
```

**Legacy data (2020-2025):** Loaded once via Alembic migration `b90ec0cb8a47_load_data.py`
from local `data/pdga/` JSON files. Same parse logic as `etl/parse.py`. Frozen — do not re-run.

**2026+ data:** Lambda runs nightly, checks which rounds are loaded, fetches new ones from PDGA API.

---

## Dashboard Architecture

- All user-facing tables are custom HTML via `st.markdown(unsafe_allow_html=True)` — never `st.dataframe()`
- HTML cards must be complete self-contained blocks in a single `st.markdown()` call (Streamlit renders each call as an isolated DOM element)
- Plotly charts: `config={"displayModeBar": False}`, white background, no gridlines
- All query functions in `queries.py` use `@st.cache_data`
- Navigation: `st.tabs()` styled as a nav bar via CSS overrides

### Color palette

| Name | Hex | Usage |
|---|---|---|
| `GREEN` | `#1D6B44` | Primary accent, bar charts, links, prize money |
| `AMBER` | `#E8A838` | #1 ranked player, world champion callout |
| `BG` | `#F8F9FA` | Page background |
| `WHITE` | `#FFFFFF` | Cards |
| `TEXT` | `#1C1C1E` | Primary text |
| `MUTED` | `#6B7280` | Labels, dates, secondary text |
| `BORDER` | `#E5E7EB` | Card borders, table dividers |
| `LIGHT_GREEN` | `#EAF4EE` | Table row hover, subtle highlights |
