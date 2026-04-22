# Ideas & Brainstorming

A scratchpad for product ideas, questions the site should answer, data sources to
pursue, and loose threads. Less structured than [roadmap.md](roadmap.md) — when
an idea firms up into a plan, move it to the roadmap.

---

## Mission

**Answer any question about disc golf.**

The aspirational comp is [basketball-reference.com](https://www.basketball-reference.com/):
the canonical, searchable, stats-first reference site for the sport. The working
name for that ambition is *disc-golf-reference.com* — though the current domain is
`disc-golf-data.com`.

Two design principles that fall out of this mission:
- A visitor should be able to answer a quick question without thinking ("who won
  the majors last year?") — that's the Season + This Week tabs.
- A visitor should be *prompted* to ask a harder one — that's the Search tab.

---

## Example questions the site should answer

Useful as prompt-tuning fodder for Search, and as candidate features for
purpose-built UI (e.g. a "season records" card or a player page).

- Who won the majors last year?
- What tournament had the most aces?
- When are the last few times the winner of a tournament aced on the way to
  winning?
- Has anyone gone birdie-birdie on hole 12 at New London?
- Who played all Pro Tour events in a given year?
- Who has the longest cash streak?
- Which course has the hardest average round? Easiest?
- Which players have the most top-10 finishes this season?

---

## Data sources to consider

Current scope is DGPT MPO only. Possible expansions:

- **National Tour events** — PDGA-run, typically one tier below Elite Series.
- **Historic / legacy events** — pre-DGPT-era tournaments that matter
  historically (USDGC history, early Worlds, etc.).
- **World Championships** — DGPT Worlds are already captured via `is_worlds`,
  but older Worlds predating the dataset would need a separate ingest.
- **FPO division** — PDGA API supports `Division=FPO`; see the roadmap's
  "Future considerations" for the schema work this implies.
- **UDisc Live shot data** — hole-by-hole putts/drives for strokes-gained; a
  much larger data model change, covered in the roadmap.

---

## Product ideas

### Access & rollout
- **Beta password gate** before a public launch — once the site is polished,
  put it behind a shared password for a small group of testers before
  announcing the URL publicly.

### Data quality
- **Claude-driven data validation** — feed anomalies from `vw_anomaly` (and
  new checks) to Claude and have it flag likely data errors with an explanation.

### Dashboard polish
- **Season summary card** on the Season tab: total prize pool, world champ,
  Pro Tour champion, hardest course (avg daily score + winning score), easiest
  course (same). Some of this may already be live — audit before building.
- **Event category pie chart** on the Season tab — `vw_classifications_per_season`
  is already imported but currently unused. Wire it up or drop the import.
- **Events table filters** — default or highlight the Major classification;
  keep the world champion row visually distinct (e.g. amber border).
- **PDGA deep links** — every event and player in a table should link to its
  PDGA page. Check which tables already do this and fix the gaps.
- **Winners bar chart, prize-money overlay** — the existing bar chart shows
  wins and top-10s; consider a second series (or toggle) for total season
  prize money.

### Player pages (Phase 5 in roadmap)
- Career wins, top-10s, events played by season.
- Round rating over time (line chart).
- Head-to-head vs. a chosen opponent.
- Best/worst rounds by score and rating.
- Drive this with `st.query_params` — no separate routing layer needed.

---

## Tech debt captured from the notepad

- `director` column is populated for legacy tournaments but is **not** in the
  2026 seed CSV or `enrich_tournaments.py` — new tournaments will have a NULL
  director. Decide whether to source this from PDGA or drop the column.

(Other tech debt items live in CLAUDE.md under "Known Issues / Tech Debt" and
in roadmap.md under "Recommendations".)

---

## Already covered elsewhere

These came up in the original brainstorm and are tracked in other files — no
need to duplicate here:

- **URL / domain connection** → roadmap.md "Domain" section (with cost estimate)
- **AI-answered questions** → Phase 4 Text-to-SQL Search (in progress)
- **Season dashboard, This Week landing page, events table** → Phases 1-3 (shipped)
- **Player profiles / disc-golf-reference.com vibe** → Phase 5 (planned)
- **Prize money in the dataset** → already in `round.prize`
