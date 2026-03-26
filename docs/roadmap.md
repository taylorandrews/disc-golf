# Roadmap

Project history, current state, and future direction for disc-golf-data.com.

---

## Completed

### Phase 1 — Infrastructure
*Finished late 2025*

- Dockerized Streamlit app
- CDK stack: VPC (public-only, no NAT), RDS PostgreSQL t3.micro, ECS Fargate, ALB
- GitHub Actions CI/CD via OIDC (no stored AWS keys)
- Full 538-inspired UI redesign: custom HTML/CSS, green/amber palette, `st.tabs()` nav
- Season tab with year selector, hero stat cards, winners bar chart, events table
- Legacy data (2020-2025) seeded via Alembic migrations — 194 tournament rounds

### Phase 2 — ETL Refactor + 2026 Season
*Finished March 2026*

- S3 data lake bucket (`disc-golf-data-lake-368365885895`, RemovalPolicy.RETAIN)
- `etl/` module: parse, db, pdga, standings, youtube, podcast — Lambda-compatible
- Lambda `disc-golf-nightly-etl`: 06:00 UTC daily via EventBridge
- `make deploy-etl` / `make invoke-etl` / `make migrate-prod` for fast iteration
- 2026 tournament seed CSV + `scripts/enrich_tournaments.py`
- Driver split: psycopg2-binary (ECS) / pg8000 (Lambda)

### Phase 3 — Landing Page ("This Week" tab)
*Finished March 2026*

Full design specification: `docs/landing-page-design.md`

- **Step 1** — Static shell: triptych, schedule strip, stat callout, recent results
- **Step 2** — DGPT Points Standings: scraped from DGPT.com AJAX endpoint, `season_standings` table with `(season, pdga_id)` PK
- **Step 3** — YouTube coverage cards: JomezPro playlist scraper (bypasses 15-video RSS cap), `sort_order` for round sequence, creator preview cards
- **Step 4** — Tournament schema: `short_name` + `dgpt_url` columns, clickable schedule strip pills
- **Step 5** — Podcast episode cards: 4 shows, rss.com links, priority-ordered strip
- **Step 6** — Polish: green header/nav bar, "This Week" as default tab, About page, mobile triptych stack, Playfair Display for stat callout

---

## In Progress

### Phase 4 — Text-to-SQL Search

Natural language query interface on the Search tab. Full specification: `docs/search-design.md`.

**Completed:**
- Alembic migration: `search_log` table
- Read-only `dg_reader` PostgreSQL user (`scripts/create_dg_reader.sql`)
- `DG_READER_URL` wired into `db_config.py` + ECS task via CDK / Secrets Manager
- `ANTHROPIC_API_KEY` in Secrets Manager, injected into ECS environment
- `dashboard/search.py`: Claude Haiku API call, SQL validation, query execution, logging
- `render_search()` UI: chat input, response card, data table, session counter
- `make query-log` Makefile target for reviewing `search_log` from RDS

**In progress / tuning:**
- Prompt and response quality improvements based on real query feedback

---

## Upcoming

### Phase 5 — Player Profiles

Individual player pages with career stats.

**Planned stats per player:**
- Career wins, top-10 finishes, events played by season
- Average round rating over time (line chart)
- Head-to-head record vs. specific opponents
- Best/worst rounds by score and rating
- Tournament history table with links to event results

**Implementation:** Streamlit's URL routing (`st.query_params`) can drive player pages
without a separate routing layer. A player search box on the Search tab leads to the profile.

### Phase 6 — Advanced Analytics

These require a full season of 2026 data to be meaningful:

- **Strokes Gained** — hole-by-hole performance vs. field average (requires `hole` table, already populated)
- **Course difficulty ratings** — average score-to-par by hole, by layout, over time
- **Cut analysis** — which events have true cuts vs. field thinning; track cut lines historically
- **Comeback tracking** — largest round-over-round score improvements

---

## Site pages — current and planned

| Tab / Page | Status | Notes |
|---|---|---|
| This Week | Live | Default tab — triptych, schedule, video, podcast, standings |
| Season (2020–2026) | Live | Year selector, stat cards, bar chart, events table |
| Search | In progress (Phase 4) | Natural language stats query |
| About | Live | Project description + data source attribution |
| Player Profile | Not started | Per-player page via URL param (Phase 5) |

---

## Domain

`disc-golf-data.com` is registered but not yet connected — the site runs at the ALB URL.

**To connect:**
1. Request ACM certificate (DNS validation)
2. Add HTTPS listener (port 443) to ALB in `infra/stacks/app_stack.py`
3. Point domain A record at ALB DNS name

This also requires switching from HTTP to HTTPS in the GitHub Actions deploy URL.

---

## Recommendations

**High value, low effort:**

- **`make stop` as default end-of-session** — saves 10+ min rebuild time vs `make destroy`, data preserved, only $16/month while stopped
- **Version pin `requirements.txt`** — currently unpinned, will break silently on a new psycopg or SQLAlchemy release
- **Parameterize `queries.py` f-strings** — currently safe (integer-only values) but must be fixed before any user-supplied SQL input exists
- **Connect the domain** — `disc-golf-data.com` is registered; just needs ACM cert + ALB listener + DNS A record

**Medium effort, high value:**

- **Data completeness audit** — 2020 season has no shot-by-shot data (pre-UDisc era); document this clearly in the UI so users understand the hole table is empty for those years
- **Round completion detection** — currently the ETL retries rounds that may never complete (e.g., cancelled events). Add a `round_complete` flag or smarter detection.

**Future considerations:**

- **FPO division** — the PDGA API supports `Division=FPO`. Adding FPO data would require schema changes (remove MPO assumption from views) and roughly double the data volume.
- **Historical data pre-2021** — 2016-2020 PDGA data has no shot-by-shot scores. The hole table can't be populated for those years.
- **Shot data** — UDisc Live has shot-by-shot tracking for some events. Separate API, much larger data model change, but would unlock strokes-gained analysis.
