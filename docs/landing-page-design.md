# Landing Page Design — "This Week in Disc Golf"

Phase 3 design specification. This document covers page architecture, component specs,
visual system, and ETL requirements for the landing page tab.

---

## Vision

The landing page is a **live snapshot of professional disc golf right now**.
A fan opens it on a Tuesday and immediately knows: who won last weekend, who plays next,
who's leading the season, and where to watch the coverage. No searching required.

The closest analogue is the PGA Tour homepage after its 2023 Haskell redesign —
leaderboard-as-hero, score relative to par as the universal shorthand, media one scroll below.
Adapted for disc golf's specific media ecosystem: JomezPro instead of PGA Tour Live,
The Upshot instead of Golf Channel analysis.

**What it is not:** A data dashboard. No query controls, no year selectors, no filter dropdowns.
Everything is automatic and current.

---

## Competitive Analysis Summary

| Site | Key Pattern | Disc Golf Lesson |
|---|---|---|
| PGA Tour (Haskell) | Leaderboard-as-hero, score relative to par, serif headline font | The template to follow for individual stroke-play tour |
| Formula 1 | Video-first hero, standings snapshot widget (top 3 + link) | Video thumbnail cards, dark brand accents for premium feel |
| ATP Tour | Persistent scores bar, rankings widget pinned above fold | Rankings snapshot belongs above the fold, not in a tab |
| StatMando | Stats-first, no editorial aggregation | Our gap: be the hub that surfaces stats + video + podcast together |
| Ultiworld | Podcast-forward editorial, no live data | Link to their content; don't try to replicate it |
| DGPT.com | Official CMS, lacks stat depth and media aggregation | Fill the depth gap; complement, don't compete |

**The gap no site currently fills:** A single page combining live standings + video links +
podcast episode + schedule in one glance. That is this page.

---

## Page Architecture

### Above the fold — the triptych

Three cards side by side (or stacked on mobile). Together they answer the three questions
every fan asks: *Who just won? What's coming up? Who's leading the season?*

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│   LAST RESULT       │   NEXT EVENT        │   SEASON STANDINGS  │
│                     │                     │                     │
│  Big Easy Open      │  Waco Annual        │  1. R. Wysocki  280 │
│  Gannon Buhr        │  Charity Open       │  2. G. Buhr     265 │
│  -22 (4 rounds)     │  Elite Series       │  3. C. Dickerson 241│
│  $10,000            │  Mar 28 · 5 days    │  4. E. Oakley   220 │
│                     │  Waco, TX           │  5. K. Jones    198 │
│  [Watch Coverage ↗] │  [View Field ↗]     │  [Full Standings →] │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

- **Last Result card:** Tournament name, winner's full name in AMBER if world champion
  or currently ranked #1, score relative to par, prize amount, link to JomezPro coverage
  for that event (if available).
- **Next Event card:** Tournament name, classification badge (color-coded), location,
  start date rendered as both ISO date and "N days away." Link to PDGA event page.
- **Standings card:** DGPT points top 5. Rank number + full name + points.
  Rank 1 rendered in AMBER. "Full Standings →" links to the Season tab.

All three cards share the same height, same border, same WHITE background.
Card header label (LAST RESULT / NEXT EVENT / SEASON STANDINGS) in MUTED uppercase small caps.

---

### Section 2 — Schedule strip

A horizontal scrollable strip of all 2026 events. Each event is a compact pill/card.
Completed events are MUTED; the current or next event is accented in GREEN; future events
are default TEXT color.

```
  [✓ Las Vegas] [✓ Big Easy] [→ Waco Apr 3] [Jonesboro Apr 17] [Preserve Champ May 1] ...
                                  ↑ current
```

Each pill shows: short name + start date. Clicking opens the PDGA event page externally.
Classification is color-coded via a small left border stripe:

| Classification | Left border color |
|---|---|
| Elite Series | `#1D6B44` (GREEN) |
| Elite Series Plus | `#2E8B57` (slightly lighter green) |
| Major | `#E8A838` (AMBER) |
| Tour Championship | `#1C1C1E` (TEXT / near-black) |

---

### Section 3 — This week's video coverage

JomezPro YouTube cards for the most recent event. One card per round.
Gatekeeper coverage cards appear below (usually releases ~1 week later).

```
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│  [thumbnail]                     │  │  [thumbnail]                     │
│  Big Easy Open · Round 4         │  │  Big Easy Open · Round 3         │
│  JomezPro                        │  │  JomezPro                        │
│  Published Mar 17                │  │  Published Mar 16                │
│  [Watch on YouTube ↗]            │  │  [Watch on YouTube ↗]            │
└──────────────────────────────────┘  └──────────────────────────────────┘
```

Thumbnails link to YouTube — no embed, no autoplay. Thumbnail is a static `<img>` tag
using the YouTube thumbnail URL (`https://img.youtube.com/vi/{video_id}/mqdefault.jpg`).
A GREEN play-button overlay icon is drawn with CSS on hover.

Max 4 cards displayed (rounds 1-4 of most recent event). If Gatekeeper has released
its chase card cut, show those cards below with a "Chase Card" label.

---

### Section 4 — Latest podcast episodes

Horizontal card strip for the top 3 podcasts. Each card shows the most recent episode.

```
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│ THE UPSHOT            │  │ GRIPLOCKED            │  │ TOUR LIFE             │
│ Ultiworld             │  │ Foundation DG         │  │ Brodie Smith + Ulibarri│
│                       │  │                       │  │                       │
│ Big Easy Mailbag      │  │ Waco Preview + Hot    │  │ Live Wed 8PM EST      │
│ + UDisc Growth Report │  │ Takes                 │  │                       │
│ Mar 20 · 64 min       │  │ Mar 19 · 48 min       │  │ Latest: Mar 18 · 55m  │
│ [Listen ↗]            │  │ [Listen ↗]            │  │ [Listen ↗]            │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

Podcast show name in MUTED uppercase. Episode title in TEXT bold. Date + runtime in MUTED.
Listen link opens the podcast's episode URL (Spotify or Apple Podcasts from the RSS feed).
Show logo displayed as a small square icon if we can cache a static asset.

---

### Section 5 — Stat callout

One large, striking stat rendered as a hero number with context text.
Rotates weekly (or pick the most interesting derived stat from current season data).

```
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │          -22                                               │
  │    Gannon Buhr's winning score at the Big Easy Open        │
  │    The lowest 72-hole winning total of the 2026 season     │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

Number in large serif font (48–64px). Context line in MUTED. Background LIGHT_GREEN.
This section requires no new data — it's derived from what's already in `vw_tournament_summary`.

Candidate stat formulas (computed dynamically, not hardcoded):
- Lowest winning score of the season so far
- Current points leader's margin over #2
- Most rounds played in the season (iron man / durable player stat)
- Highest single-round rating of the season

---

### Section 6 — Recent results table

The last 4 completed tournaments in a compact custom HTML table.
Same styling as the existing Season tab table: GREEN header row, alternating LIGHT_GREEN rows.

| Event | Champion | Score | Prize | Date |
|---|---|---|---|---|
| Big Easy Open | Gannon Buhr | -22 | $10,000 | Mar 14–17 |
| Supreme Flight Open | Ricky Wysocki | -19 | $12,000 | Mar 7–10 |
| … | | | | |

"Score" is total score relative to par for all rounds combined.
Champion name links to (future) player profile page.
Event name links to the PDGA event page externally.

---

## Visual Design

### Typography

The existing Streamlit default (Inter / system sans-serif) works for body text.
For section headings and the stat callout number, inject a serif via Google Fonts:

```html
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
```

Use `font-family: 'Playfair Display', serif` only for:
- The large stat callout number
- Section header labels (e.g., "THIS WEEK'S COVERAGE", "LATEST EPISODES")

Everything else stays in the existing sans-serif stack. Do not apply serif globally —
it will conflict with the Season tab and Streamlit's own UI elements.

### Color

No new colors. The existing palette covers everything:

| Element | Color |
|---|---|
| Triptych card borders | `BORDER` (`#E5E7EB`) |
| Card backgrounds | `WHITE` (`#FFFFFF`) |
| Page background | `BG` (`#F8F9FA`) |
| Section label text | `MUTED` (`#6B7280`) |
| Primary text | `TEXT` (`#1C1C1E`) |
| Winner name (rank 1 or world champ) | `AMBER` (`#E8A838`) |
| Classification badges, play icon, active links | `GREEN` (`#1D6B44`) |
| Stat callout background | `LIGHT_GREEN` (`#EAF4EE`) |
| Completed event pills | `MUTED` |
| Current/next event pill accent | `GREEN` |

### Layout rules

- Maximum content width: 1100px, centered. Same constraint as the Season tab.
- Cards: `border-radius: 8px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`, `padding: 20px`.
- Section spacing: 32px between major sections.
- Mobile: triptych stacks vertically (3 rows). Schedule strip becomes vertically scrollable.
  Video cards stack to single column. Podcast cards stack to single column.
- All `st.markdown()` calls must be **complete self-contained HTML blocks** per CLAUDE.md rule.
  Never split a card's opening and closing tags across multiple calls.

---

## Data Requirements

### What we already have (no new ETL needed)

| Data point | Source |
|---|---|
| Last completed tournament name | `vw_tournament_summary` WHERE `end_date < today` ORDER BY `end_date DESC` LIMIT 1 |
| Winner name + score | Same view, `champion` + `prize_usd` columns |
| Next upcoming tournament | `tournament` WHERE `start_date >= today` ORDER BY `start_date` LIMIT 1 |
| Classification, location (infer from `long_name`), dates | `tournament` table |
| Recent results table (last 4) | `vw_tournament_summary` ORDER BY `end_date DESC` LIMIT 4 |
| Stat callout — winning score | `vw_tournament_summary`, `round` table |

### What we need to add — new ETL jobs

---

#### ETL Job 1: YouTube RSS feed scraper

**Purpose:** Populate a `media_youtube` table with the latest JomezPro, Gatekeeper, and GK Pro
YouTube videos, so the landing page can render thumbnail cards without calling the YouTube API
at render time.

**Source:** YouTube RSS feeds. Each channel exposes a public Atom feed:
```
https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}
```

No API key required. Returns the 15 most recent videos per channel.

**Channels to track:**

| Channel | Channel ID | Content type |
|---|---|---|
| JomezPro | `UCGLfzfKoKa_MpnFUxFo2y-A` | Lead card, next-day post-produced |
| Gatekeeper Media | `UCQ1bU_EyEpbVrJ3HfABGJ6Q` | Chase card, ~1 week later |
| GK Pro | `UCmME4Cd3hBLMwt9UuM7P37w` | Tour Series Skins |

**New table: `media_youtube`**

```sql
CREATE TABLE media_youtube (
    video_id     TEXT PRIMARY KEY,         -- YouTube video ID (11 chars)
    channel_id   TEXT NOT NULL,
    channel_name TEXT NOT NULL,            -- "JomezPro", "Gatekeeper Media", "GK Pro"
    title        TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    thumbnail_url TEXT NOT NULL,           -- https://img.youtube.com/vi/{id}/mqdefault.jpg
    video_url    TEXT NOT NULL,            -- https://www.youtube.com/watch?v={id}
    fetched_at   TIMESTAMPTZ DEFAULT NOW()
);
```

**Lambda trigger:** Add to `etl/lambda_handler.py` as a second job. Runs after the PDGA
round fetch. Parses the Atom XML with Python's `xml.etree.ElementTree` (stdlib, no new deps).
Upserts into `media_youtube` — `ON CONFLICT (video_id) DO UPDATE SET fetched_at = NOW()`.

**Retention:** Keep last 30 days of videos per channel. A simple DELETE of older rows
prevents unbounded growth.

---

#### ETL Job 2: Podcast RSS scraper

**Purpose:** Populate a `podcast_episodes` table with the latest episode from each tracked
podcast so the landing page can render episode cards.

**Source:** Standard RSS 2.0 podcast feeds.

**Feeds to track:**

| Show | Feed URL | Notes |
|---|---|---|
| The Upshot | `https://feed.podbean.com/disc-golf-upshot/feed.xml` | Ultiworld; confirm URL from Apple Podcasts |
| Griplocked | `https://feeds.buzzsprout.com/1012108.rss` | Foundation Disc Golf |
| Tour Life | `https://feeds.buzzsprout.com/1948892.rss` | Brodie Smith + Paul Ulibarri |

> **Note:** Feed URLs must be verified against Apple Podcasts or Spotify before implementation.
> The URLs above are best-guess from known hosting platforms; confirm before coding.

**New table: `podcast_episodes`**

```sql
CREATE TABLE podcast_episodes (
    episode_guid  TEXT PRIMARY KEY,       -- RSS <guid> field, globally unique per episode
    show_name     TEXT NOT NULL,           -- "The Upshot", "Griplocked", "Tour Life"
    episode_title TEXT NOT NULL,
    published_at  TIMESTAMPTZ NOT NULL,
    duration_secs INTEGER,                -- from <itunes:duration>, normalized to seconds
    episode_url   TEXT NOT NULL,          -- direct link to episode page or audio
    fetched_at    TIMESTAMPTZ DEFAULT NOW()
);
```

**Lambda trigger:** Same lambda, third job after YouTube. Parses RSS with `xml.etree.ElementTree`.
Upserts latest 5 episodes per show. `ON CONFLICT (episode_guid) DO NOTHING`.

---

#### ETL Job 3: DGPT Points Standings (derived, no external fetch)

**Purpose:** Compute DGPT season points from existing `round` and `tournament` tables
and materialize into a `season_standings` table for fast landing page queries.

**Why a materialized table instead of a view:** The points calculation is complex
(classification multipliers, top-N scores, DNF handling) and should only run once per ETL cycle,
not on every page render.

**DGPT points system (2026):**

Points awarded by finish position within each event. Classification multiplier:

| Classification | Multiplier |
|---|---|
| Elite Series | 1.0× |
| Elite Series Plus | 1.25× |
| Major | 1.5× |
| Tour Championship | 2.0× |

Finish position → base points mapping is published by the DGPT each season.
The 2025 scale: 1st = 500, 2nd = 450, 3rd = 425, 4th = 400, 5th = 380, ... (diminishing).
**Verify the 2026 scale against official DGPT communications before implementing.**

**New table: `season_standings`**

```sql
CREATE TABLE season_standings (
    player_id    INTEGER NOT NULL REFERENCES player(player_id),
    season       INTEGER NOT NULL,
    rank         INTEGER NOT NULL,
    total_points NUMERIC(8, 2) NOT NULL,
    wins         INTEGER NOT NULL DEFAULT 0,
    top5s        INTEGER NOT NULL DEFAULT 0,
    events_played INTEGER NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, season)
);
```

**Lambda trigger:** Fourth job. Truncates and rebuilds the current season's rows from scratch.
Relatively fast (a few hundred players × a few dozen events).

---

### New Alembic migration

Create a new migration: `alembic revision -m "add_landing_page_tables"`

Tables to create: `media_youtube`, `podcast_episodes`, `season_standings`.

Do **not** modify existing tables or views. Additive only.

---

### New `queries.py` functions

All new functions follow the existing pattern: `@st.cache_data`, parameterized SQL,
return `pd.DataFrame` or a typed dict.

```python
@st.cache_data(ttl=300)  # 5-minute cache; landing page should feel live
def get_last_result() -> dict: ...

@st.cache_data(ttl=300)
def get_next_event() -> dict: ...

@st.cache_data(ttl=300)
def get_season_standings_top5(season: int) -> pd.DataFrame: ...

@st.cache_data(ttl=3600)  # 1-hour cache for media content
def get_latest_youtube_videos(limit: int = 4) -> pd.DataFrame: ...

@st.cache_data(ttl=3600)
def get_latest_podcast_episodes(limit: int = 3) -> pd.DataFrame: ...

@st.cache_data(ttl=300)
def get_recent_results(limit: int = 4) -> pd.DataFrame: ...

@st.cache_data(ttl=300)
def get_stat_callout(season: int) -> dict: ...  # returns {"number": "-22", "context": "..."}

@st.cache_data(ttl=3600)
def get_schedule_strip(season: int) -> pd.DataFrame: ...
```

Cache TTLs: short (5 min) for anything derived from tournament/round data; longer (1 hr)
for media content that changes at most daily.

---

## `dashboard/app.py` Implementation Notes

The landing page renders via the existing `Landing Page` tab stub.
Rename the tab label to `"This Week"` for clarity.

Structure of the render function (`render_landing_page()`):

```python
def render_landing_page():
    season = 2026  # hardcoded until multi-season landing page is needed
    _render_triptych(season)
    _render_schedule_strip(season)
    _render_video_section()
    _render_podcast_section()
    _render_stat_callout(season)
    _render_recent_results(season)
```

Each `_render_*` function builds a complete HTML string and calls `st.markdown(..., unsafe_allow_html=True)` once.

The Playfair Display `@import` should be injected once at the top of `render_landing_page()`
inside a `<style>` block, not globally, to avoid affecting other tabs.

---

## Implementation Sequence

Build in this order. Each step is independently deployable.

### Step 1 — Static shell with existing data (no new ETL)

Implement the triptych (last result, next event, standings using existing Season tab queries),
schedule strip, stat callout, and recent results table. No YouTube, no podcasts.
This gives the tab a real experience using only what's already in RDS.

**Queries needed:** `get_last_result`, `get_next_event`, `get_recent_results`,
`get_schedule_strip`, `get_stat_callout`.
All derivable from `vw_tournament_summary` and `tournament`.

**No schema changes. No new Lambda jobs. Ships independently.**

### Step 2 — DGPT Points Standings

Add `season_standings` table + Alembic migration.
Add standings computation to Lambda (`etl/standings.py`).
Wire `get_season_standings_top5()` into the triptych.

### Step 3 — YouTube coverage cards

Add `media_youtube` table + Alembic migration.
Add `etl/youtube.py` (channel RSS fetch + parse).
Wire `get_latest_youtube_videos()` into the video section.

### Step 4 — Podcast episode cards

Add `podcast_episodes` table + Alembic migration.
Add `etl/podcast.py` (RSS feed fetch + parse).
Wire `get_latest_podcast_episodes()` into the podcast section.

### Step 5 — Polish and mobile

Responsive layout pass. Serif font injection. Hover states on video thumbnails.
Rename tab to "This Week." Update `roadmap.md` and `CLAUDE.md`.

---

## Open Questions

1. **DGPT points scale for 2026** — verify the finish-position → base-points mapping
   from official DGPT communications before implementing `season_standings` computation.

2. **Podcast RSS feed URLs** — confirm The Upshot, Griplocked, and Tour Life feed URLs
   from Apple Podcasts source or the show hosts before coding the parser.

3. **JomezPro channel ID** — confirm `UCGLfzfKoKa_MpnFUxFo2y-A` is still the active
   JomezPro channel ID (channels sometimes create new accounts after acquisitions).

4. **"This Week" vs "Landing Page"** — tab rename only matters visually. Confirm with
   Taylor before renaming, since it changes the nav bar appearance for all users.

5. **Standings data for 2026** — the standings widget in the triptych requires at least
   one completed 2026 event. Until then, show 2025 final standings with a label noting
   "2025 final standings — 2026 season underway."

6. **Last result "Watch Coverage" link** — requires a manual mapping of `tournament_id`
   to JomezPro YouTube playlist. This could be a new column in the `tournament` table
   (`jomez_playlist_url TEXT`) or a separate lookup table. Simpler: a hardcoded dict in
   `queries.py` for known 2026 events, replaced later with a DB column.
