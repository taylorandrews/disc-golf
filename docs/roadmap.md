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
- 6-column tournament seed CSV + `scripts/enrich_tournaments.py` for auto-filling metadata

### Phase 2D–E — 2026 season live
*Finished March 2026*

- `cdk deploy`: S3 bucket, Lambda, and EventBridge live in prod
- `make upload-legacy` archived 2020–2025 JSONs to S3
- 2026 tournament IDs seeded via `data/seed/2026_tournaments.csv`
- `make seed-and-etl`: one command to enrich tournament table + kick ETL (uses Secrets Manager, no password in config)
- ETL successfully loaded 2026 round data into RDS
- Driver split: `psycopg2-binary` for ECS app, `pg8000` (pure Python) for Lambda — avoids CDK bundling platform issues on macOS
- 2026 data flows into the existing Season tab automatically — no separate tab needed for now

---

## In Progress

*Nothing currently in progress.*

---

## Upcoming

### Phase 3 — Landing Page

Full design specification: `docs/landing-page-design.md`

A "this week in disc golf" hub replacing the current placeholder tab.
The vision: a single page that answers *who just won, what's next, who's leading the season,
and where to watch* — without any interaction from the user.

**Content sections:**
1. **Triptych hero** — Last Result / Next Event / Season Standings (top 5 points)
2. **Schedule strip** — horizontal scrollable 2026 calendar, color-coded by classification
3. **Video coverage** — JomezPro + Gatekeeper YouTube thumbnail cards (no autoplay)
4. **Podcast strip** — latest episode from The Upshot, Griplocked, Tour Life
5. **Stat callout** — one large compelling number derived from current season data
6. **Recent results table** — last 4 completed events

**New ETL jobs (additive, no existing schema changes):**
- `etl/youtube.py` — YouTube RSS feed scraper → `media_youtube` table
- `etl/podcast.py` — Podcast RSS scraper → `podcast_episodes` table
- `etl/standings.py` — DGPT points computation → `season_standings` table

**Build sequence:**
1. Static shell using existing RDS data (ships independently, no new ETL)
2. DGPT Points Standings
3. YouTube coverage cards
4. Podcast episode cards
5. Polish + mobile layout pass

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
| Season (2020–2026) | Live | Year selector, stat cards, bar chart, events table |
| 2026 | Live | Flows into Season tab automatically via nightly ETL |
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
