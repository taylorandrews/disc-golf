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

### Phase 2A–C — ETL Foundation
*Finished March 2026*

- S3 data lake bucket (`disc-golf-data-lake-368365885895`, RemovalPolicy.RETAIN)
- `etl/` module: parse logic extracted from Alembic into a standalone, Lambda-compatible package
- Lambda `disc-golf-nightly-etl`: checks loaded rounds nightly at 06:00 UTC, fetches new rounds from PDGA, saves to S3, upserts into RDS
- EventBridge cron + `make invoke-etl` for manual triggering
- 6-column tournament seed CSV + `scripts/enrich_2026_tournaments.py` for auto-filling metadata

---

## In Progress

### Phase 2D — Deploy 2026 infrastructure
- `cdk deploy` to create S3 + Lambda + EventBridge in prod
- `make upload-legacy` to archive 2020-2025 JSONs to S3
- Add 2026 tournament IDs to `data/seed/2026_tournaments.csv`
- Seed tournament table, kick initial ETL run

### Phase 2E — 2026 season dashboard tab
- New "2026" nav tab using existing query patterns with `WHERE season = 2026`
- Season standings card, top winners chart, events table — same design as legacy Season tab
- The tab should light up automatically once rounds are in RDS

---

## Upcoming

### Phase 3 — Landing Page

A "this week in disc golf" hub replacing the current placeholder tab.

**Planned content:**
- Upcoming DGPT events (from `tournament` table, `start_date >= today`)
- Recent results summary (last completed event champion + score)
- Embedded or linked video content: JomezPro, GK Pro, Ultiworld Disc Golf coverage
- Tour Life Podcast links (Ezra Aderhold + Aaron Goosage)
- Disc golf blog / article roundup

**Design notes:**
- Should feel like a sports media homepage, not a data dashboard
- Cards with event name, location, dates, classification badge
- Video links open externally — no embed needed for v1

### Phase 4 — Text-to-SQL Search (deprioritized)

Natural language query interface: "Show me Paul McBeth's scores at Worlds" → SQL → result table.

- Claude API (`claude-sonnet-4-6`) generates SQL from user input
- Read-only RDS user required for safety
- Needs `docs/schema.md` with semantic column descriptions as system prompt context
- Currently deprioritized — the data set isn't large enough yet to make this compelling

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

- **DGPT Points Standings** — reconstruct points table from finish positions and classification weights
- **Strokes Gained** — hole-by-hole performance vs. field average (requires `hole` table, already populated)
- **Course difficulty ratings** — average score-to-par by hole, by layout, over time
- **Cut analysis** — which events have true cuts vs. field thinning; track cut lines historically
- **Comeback tracking** — largest round-over-round score improvements

---

## Site pages — current and planned

| Tab / Page | Status | Notes |
|---|---|---|
| Season (2020-2025) | Live | Year selector, stat cards, bar chart, events table |
| 2026 | Pending (Phase 2E) | Same design, filtered to `season = 2026` |
| Landing Page | Pending (Phase 3) | "This week in disc golf" content hub |
| Search | Placeholder | Will drive player profiles in Phase 5 |
| State of Disc Golf | Placeholder | Cross-season analytics — Phase 6 territory |
| About | Placeholder | Project description, data source attribution |
| Player Profile | Not started | Per-player page via URL param |

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
- **`get_pdga_round.py` request pacing** — the legacy fetcher has no `time.sleep()` between requests; add 0.5s to match the ETL module before running it again

**Future considerations:**

- **FPO division** — the PDGA API supports `Division=FPO`. Adding FPO data would require schema changes (remove MPO assumption from views) and roughly double the data volume.
- **Historical data pre-2021** — 2016-2020 PDGA data has no shot-by-shot scores. The hole table can't be populated for those years. A separate display mode for "tournament results only" (no hole-level stats) would be needed.
- **Shot data** — UDisc Live has shot-by-shot tracking for some events. This is a separate API and a much larger data model change, but would unlock stroke-gained analysis.
