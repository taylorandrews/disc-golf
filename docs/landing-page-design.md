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
| Worlds | `#8B1A1A` (deep red — distinct from Major despite same DB classification) |
| Tour Championship | `#1C1C1E` (TEXT / near-black) |

Worlds is identified via `is_worlds = true` on the `tournament` row, not by classification string.
The classification column will still say "Major" — `is_worlds` is the distinguishing flag.

---

### Section 3 — Video coverage

Two subsections, always both present.

#### 3A — Recent tournament coverage

Post-produced coverage from the most recently completed event.
JomezPro and GO Throw do 2 videos per 9 holes (Front 9 / Back 9), so a 5-round event
produces up to 10 videos from JomezPro alone. **No hard cap on card count.**
The row is horizontally scrollable, ordered chronologically starting with Round 1 Front 9 Jomez.

```
RECENT COVERAGE — Big Easy Open
← [R1 F9 · Jomez] [R1 B9 · Jomez] [R2 F9 · Jomez] [R2 B9 · Jomez] [R3 F9 · Jomez] ... →
```

Channels for recent coverage (in priority order):
1. JomezPro — lead card, reliable titling, primary source
2. GO Throw Disc Golf — lead card alternate angle
3. Gatekeeper Media — deprioritized; include if videos exist but don't rely on it

Video-to-event matching uses the `jomez_playlist_url` column on the `tournament` table
(see schema section). If no playlist link exists for the most recent event, omit the subsection
rather than showing unmatched videos.

#### 3B — Preview / upcoming content

Course preview and hype videos for the next upcoming event.
Source channels (all manually maintained course preview creators):

| Channel | Creator |
|---|---|
| Ezra Aderhold | `UCJ5qQfW0IPRGunN3hIrrKKA` |
| Aaron Goosage | `UCnTnv0pSDJjZRQlppkp0qUg` |
| Anthony Barela | `UC4WJMNjQdQMwuIanr1Dfy3w` |
| Ricky Wysocki | `UCsKzQ6cQfiFrq3JRUQQKxfQ` |

Match by scanning video titles for the next event's tournament name or course name.
Show up to 4 cards, ordered by published date descending.

```
PREVIEW — Waco Annual Charity Open
[Waco Course Preview · Ezra] [Waco Prep · Goosage] [Waco Walk · Barela] ...
```

If no preview videos are found for the next event, omit the subsection rather than showing
generic recent content.

---

**Card design (both subsections):**

Thumbnails link to YouTube — no embed, no autoplay. Thumbnail is a static `<img>` tag
using the YouTube thumbnail URL (`https://img.youtube.com/vi/{video_id}/mqdefault.jpg`).
A GREEN play-button overlay icon drawn with CSS on hover.
Card shows: thumbnail, title (truncated to 2 lines), channel name, published date.

---

### Section 4 — Latest podcast episodes

Horizontal card strip. Each card shows the most recent episode from one show.

```
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│ THE UPSHOT            │  │ TOUR LIFE             │  │ GRIP LOCKED           │  │ COURSE MAINTENANCE    │
│ Ultiworld             │  │ Brodie + Uli          │  │                       │  │                       │
│                       │  │                       │  │                       │  │                       │
│ Big Easy Mailbag      │  │ Waco Preview          │  │ Hot Takes + Waco      │  │ Drainage Basics Ep 12 │
│ + UDisc Growth Report │  │                       │  │ Breakdown             │  │                       │
│ Mar 20 · 64 min       │  │ Mar 19 · 72 min       │  │ Mar 18 · 48 min       │  │ Mar 15 · 38 min       │
│ [Listen ↗]            │  │ [Listen ↗]            │  │ [Listen ↗]            │  │ [Listen ↗]            │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

Podcast show name in MUTED uppercase. Episode title in TEXT bold. Date + runtime in MUTED.
Listen link opens the episode URL from the RSS feed. Horizontally scrollable on mobile.

**Confirmed RSS feeds:**

| Show | RSS Feed URL |
|---|---|
| The Upshot (Ultiworld) | `https://www.spreaker.com/show/1765686/episodes/feed` |
| Tour Life (Brodie + Uli) | `https://feeds.simplecast.com/kkFf91zi` |
| Grip Locked | `https://feeds.simplecast.com/WCZ5a8oV` |
| Course Maintenance | `https://media.rss.com/coursemaintenance/feed.xml` |

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

| Channel | Channel ID | Content type | Priority |
|---|---|---|---|
| JomezPro | `UCmGyCEbHfY91NFwHgioNLMQ` | Lead card coverage | High |
| GO Throw Disc Golf | `UC96v9uB8ZKe1TFdYzBOGnpw` | Lead card alternate angle | High |
| Ezra Aderhold | `UCJ5qQfW0IPRGunN3hIrrKKA` | Course previews / vlogs | High |
| Aaron Goosage | `UCnTnv0pSDJjZRQlppkp0qUg` | Course previews | High |
| Anthony Barela | `UC4WJMNjQdQMwuIanr1Dfy3w` | Course previews | High |
| Ricky Wysocki | `UCsKzQ6cQfiFrq3JRUQQKxfQ` | Course previews | High |
| Gatekeeper Media | `UC9a1V9evArQaHOlkqeY63Iw` | Chase card coverage | Low (deprioritized — sparse recent uploads) |

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

#### ETL Job 3: DGPT Points Standings (scraped from DGPT.com)

**Purpose:** Scrape the official DGPT standings page and store the results verbatim.
Do not attempt to recreate the DGPT points formula — scrape the authoritative source.

**Source:** `https://www.dgpt.com/full-standings/` (MPO tab)

Use a lightweight `requests.get()` + stdlib HTML parse — the same pattern as `get_pdga_round.py`.
If the page is statically rendered, `html.parser` via `xml.etree.ElementTree` or a simple
string search for the table rows will work with no extra dependencies.

If the standings table is JavaScript-rendered (empty `<tbody>` in the raw HTML response):
check the browser Network tab for a backing JSON API endpoint (common with React sports
pages). Bind to that endpoint directly with `requests.get()` — still no headless browser needed.
Resolve this at Step 2 implementation time with a quick `curl` test:
```bash
curl -s https://www.dgpt.com/full-standings/ | grep -i "wysocki\|mcbeth"
```
If names appear in the output, static parse works. If not, check Network tab for the API.

**Display labeling:** The standings widget should be labeled:
- `"Before [Next Tournament Name]"` when a next event exists in the `tournament` table
- `"Final [Season] Standings"` as fallback when no upcoming events remain

This framing is accurate (DGPT updates standings after each event concludes) and is more
precise than a scraped timestamp.

**New table: `season_standings`**

```sql
CREATE TABLE season_standings (
    season        INTEGER NOT NULL,
    rank          INTEGER NOT NULL,
    player_name   TEXT NOT NULL,            -- as displayed on DGPT site
    player_id     INTEGER REFERENCES player(player_id),  -- nullable; matched by name where possible
    total_points  NUMERIC(8, 2) NOT NULL,
    events_played INTEGER,
    fetched_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (season, rank)
);
```

**Lambda trigger:** Third job. Truncates current season rows and rebuilds from the scraped page.
Player name → `player_id` matching is best-effort (fuzzy name match against `player` table);
`player_id` can be NULL when no match is found.

---

### Tournament table — new column

Add `jomez_playlist_url TEXT` (nullable) to the `tournament` table.
This is the JomezPro YouTube playlist URL for all coverage from that event —
a good grain since one playlist covers all rounds of a tournament.

```sql
ALTER TABLE tournament ADD COLUMN jomez_playlist_url TEXT;
```

`data/seed/2026_tournaments.csv` gets a 7th column: `jomez_playlist_url`.
Populate it manually as playlists become available after each event.
The `enrich_tournaments.py` script and `ON CONFLICT DO NOTHING` behavior means
existing rows won't be overwritten — use `ON CONFLICT DO UPDATE` for this column
so new playlist links propagate to already-seeded rows.

### New Alembic migration

Create a new migration: `alembic revision -m "add_landing_page_tables"`

Tables to create: `media_youtube`, `podcast_episodes`, `season_standings`.
Column to add: `tournament.jomez_playlist_url`.

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

### ~~Step 1 — Static shell with existing data (no new ETL)~~ ✅ COMPLETE

Implemented triptych (last result, next event, standings placeholder), schedule strip,
stat callout, and recent results table using existing queries. Ships on the "This Week" tab.

### ~~Step 2 — DGPT Points Standings~~ ✅ COMPLETE

- `season_standings` table with `(season, pdga_id)` PK (supports tied-rank players)
- `etl/standings.py`: POST to DGPT.com WordPress AJAX endpoint, regex-parse HTML `<tr data-pdgaid>` rows
- Rank extracted from `class="DGPTStandings--table_rank"` span text (not `data-tied` attribute)
- Triptych standings card: top 5, AMBER for rank 1, "Before [Next Event]" sublabel, Full Standings link
- `make deploy-etl` Makefile target added for fast Lambda code updates

### ~~Step 3 — YouTube coverage cards~~ ✅ COMPLETE

- `media_youtube` table with `sort_order INTEGER` (nullable) column
- `etl/youtube.py`: RSS fetch for 5 channels + `fetch_jomez_playlist()` playlist scraper
- Playlist scraper parses `ytInitialData` from `youtube.com/playlist?list=` page — no API key
- Watch URLs (`watch?v=...&list=...`) normalized to playlist format via `_to_playlist_url()`
- `sort_order` = playlist index; RSS videos get `sort_order = NULL`; display orders by `COALESCE(sort_order, 9999) ASC, published_at ASC`
- ON CONFLICT preserves existing sort_order: `SET sort_order = COALESCE(EXCLUDED.sort_order, media_youtube.sort_order)`
- 3A: JomezPro full event coverage cards, ordered by round sequence
- 3B: creator preview cards (Aderhold, Goosage, Barela, Wysocki), 6-day pre-event window, no name matching needed
- JomezPro videos filtered to MPO only (`LOWER(title) LIKE '%mpo%'`)
- Purge scoped to `WHERE sort_order IS NULL` (RSS-only videos) to preserve playlist ordering data

### ~~Step 4 — Tournament schema additions + clickable schedule strip~~ ✅ COMPLETE

- Added `short_name TEXT` and `dgpt_url TEXT` columns to `tournament` table
- Seed CSV expanded to 11 columns (added `short_name`, `dgpt_url`)
- `enrich_tournaments.py` upserts both new columns on conflict
- Schedule strip pills wrapped in `<a>` tags linking to DGPT event pages (hover shadow effect)
- `short_name` stored for future compact display use; not yet rendered

### ~~Step 5 — Podcast episode cards~~ ✅ COMPLETE

- `podcast_episodes` table: `episode_guid` PK, `show_name` index
- `etl/podcast.py`: fetches 5 most recent episodes per show, parses `itunes:duration`
  (handles HH:MM:SS, MM:SS, and raw seconds); falls back to `<enclosure url>` if no `<link>`
- Retention: ROW_NUMBER() DELETE keeps max 5 per show after each upsert
- Card shows: show name (uppercase MUTED), episode title (3-line clamp), date + runtime, Listen ↗ link
- Subtitle line omitted for now — show name + episode info is sufficient

### ~~Step 6 — Polish, navigation, and mobile~~ ✅ COMPLETE

- "This Week" default tab; State of Disc Golf removed; About page added
- Header/nav bar: GREEN background, white tab text, AMBER underline on selected tab
- Podcast links: show-level rss.com pages for all 4 shows (consistent experience)
- Triptych: stacks vertically on mobile via `@media (max-width: 768px)`
- Playfair Display serif injected via Google Fonts `@import` for stat callout number

---

## Open Questions

1. ✅ **DGPT standings scraping approach** — Page is JS-rendered but uses a WordPress AJAX
   endpoint that returns a pre-rendered HTML fragment. POST to:
   `https://www.dgpt.com/wp-admin/admin-ajax.php`
   with form data `action=get_standings&page_id=29445&division=MPO&season=2026`.
   Response is HTML with `<tr data-pdgaid="{pdga_id}">` rows.
   **Important:** rank is the `<span>` text inside `class="DGPTStandings--table_rank"` — NOT the
   `data-tied` attribute (which is always "1" regardless of actual rank). PK is `(season, pdga_id)`
   not `(season, rank)` to handle multiple players sharing the same rank. Points from `data-sort-value`.

2. ✅ **YouTube RSS cap** — RSS feeds hard-cap at 15 most recent videos per channel. Full event weeks
   have 20+ Jomez uploads (MPO + FPO + highlights), pushing R1 off the feed. Solution: scrape the
   `jomez_playlist_url` playlist page using `ytInitialData` JSON embedded in the page HTML.
   Watch URLs must be normalized to `youtube.com/playlist?list=` format before fetching.

All other questions resolved:
- ✅ **Tab name:** "This Week" confirmed
- ✅ **Podcast RSS URLs:** confirmed and documented above
- ✅ **YouTube channel IDs:** confirmed and corrected above
- ✅ **Standings formula:** scrape DGPT.com instead of recomputing; label as "Before [Next Event]"
- ✅ **Standings fallback:** "2025 final standings — 2026 season underway" if no 2026 data
- ✅ **JomezPro playlist link:** `jomez_playlist_url` column on `tournament` table + CSV column
