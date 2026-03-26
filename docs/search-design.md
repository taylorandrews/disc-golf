# Search Feature Design — Natural Language Stats Query

Phase 4 design specification. This document covers architecture, response paths,
safety controls, logging, and implementation sequence.

---

## Vision

A single text input on the Search tab that answers any disc golf stats question
in plain English. The user types a question; the system figures out what they're
asking, queries the database if it can, and responds conversationally with both
a natural language answer and a data table.

The experience should feel immediate and smart, not like a form. It should fail
gracefully and informatively when a question is out of scope.

---

## Response Paths

Every query routes to exactly one of three paths, determined by a single Claude
API call before any DB interaction:

### Path 1 — Off topic
The question has nothing to do with disc golf stats.

> *"This tool answers disc golf stats questions — try asking about players,
> scores, tournaments, or season results."*

No DB query. No SQL generated. Logged as `off_topic`.

### Path 2 — In scope but out of data
A legitimate disc golf stats question, but our database can't answer it:
- FPO / amateur division data
- Hole-by-hole data before 2021
- Live scoring / in-progress rounds
- Biographical data (age, sponsors, equipment)
- PDGA ratings history

Response explains what we have and what we don't:
> *"I only have MPO data from 2020–2026, and hole-by-hole data from 2021 onward.
> I can't answer questions about FPO, ratings history, or live rounds."*

Logged as `out_of_scope`. These logs are the primary signal for what data to add next.

### Path 3 — Answerable
Claude generates a SQL SELECT, we validate and execute it against a read-only
DB user, and return a natural language response + rendered data table.

> *"Paul McBeth won 3 events in the 2022 season: the Champions Cup, the
> Ledgestone Open, and the USDGC."*
> [table with event name, date, score, prize]

Logged as `answered` with the generated SQL and row count.

---

## Architecture

### Single Claude API call

One call per query. The system prompt gives Claude everything it needs to
classify the question AND generate SQL in one shot. Response is structured JSON:

```json
{
  "path": "answered",
  "sql": "SELECT ...",
  "response": "Paul McBeth won 3 events in 2022..."
}
```

or:

```json
{
  "path": "out_of_scope",
  "response": "I only have MPO data from 2020–2026..."
}
```

No streaming. Wait for full response, then render.

### System prompt components

1. **Role** — "You are a disc golf stats assistant..."
2. **Schema** — full table/column descriptions with semantic meaning (see Data Boundaries below)
3. **Data boundaries** — what's in scope, what isn't
4. **Path instructions** — when to use each path, response format for each
5. **SQL rules** — SELECT only, no semicolons, no system tables, use views where available, always LIMIT 200

### SQL validation (before execution)

Thin Python guard between Claude's output and the DB:
- Must start with `SELECT` (case-insensitive, after stripping whitespace)
- No semicolons (blocks multi-statement injection)
- No forbidden keywords: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `ALTER`, `COPY`, `pg_`, `information_schema`
- Max query length: 2000 chars

If validation fails, treat as an error (path `error`), log it, show a generic
"couldn't run that query" message. Do not expose the raw SQL or error to the user.

### Read-only database user

Claude-generated queries run as `dg_reader` — a PostgreSQL user with SELECT-only
grants on the five base tables and the three views. Created via a one-time SQL
script (not an Alembic migration — it's a DB-level permission, not a schema change).

```sql
CREATE USER dg_reader WITH PASSWORD '...';
GRANT CONNECT ON DATABASE pdga_data TO dg_reader;
GRANT USAGE ON SCHEMA public TO dg_reader;
GRANT SELECT ON tournament, course, player, round, hole TO dg_reader;
GRANT SELECT ON vw_tournament_summary, vw_player_season, vw_classifications_per_season TO dg_reader;
```

`dg_reader` credentials stored as a separate environment variable (`DG_READER_URL`)
so they're never shared with the write path.

---

## Rate Limiting

Session-based for now. No additional infrastructure required.

```python
MAX_QUERIES_PER_SESSION = 10
COOLDOWN_SECS = 3
```

`st.session_state` tracks query count and last query timestamp. When the limit
is hit, show a friendly message: *"You've reached the limit for this session.
Refresh the page to ask more questions."*

When the domain is connected and real traffic exists, upgrade to IP-based
rate limiting backed by DynamoDB or ElastiCache.

---

## Logging

Every query attempt is logged to a `search_log` table in RDS — including
off-topic and error cases. This is the primary feedback loop for understanding
what questions users are asking that we can't yet answer.

### Table: `search_log`

```sql
CREATE TABLE search_log (
    id          SERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    asked_at    TIMESTAMPTZ DEFAULT NOW(),
    question    TEXT NOT NULL,
    path        TEXT NOT NULL,   -- 'off_topic', 'out_of_scope', 'answered', 'error'
    generated_sql TEXT,          -- NULL for off_topic / out_of_scope
    row_count   INTEGER,         -- NULL unless answered
    error_msg   TEXT,            -- NULL unless error
    latency_ms  INTEGER          -- total time from question to response
);
```

### Querying the log

To see what people are asking that we don't have:

```sql
-- Out-of-scope questions (highest signal for what data to add)
SELECT question, asked_at FROM search_log
WHERE path = 'out_of_scope'
ORDER BY asked_at DESC;

-- Most common question patterns
SELECT question, COUNT(*) FROM search_log
WHERE path IN ('out_of_scope', 'off_topic')
GROUP BY question ORDER BY COUNT(*) DESC;

-- Error rate (SQL validation or execution failures)
SELECT DATE(asked_at), COUNT(*) FILTER (WHERE path='error'), COUNT(*)
FROM search_log GROUP BY 1 ORDER BY 1 DESC;
```

No dashboard for this yet — raw SQL queries against RDS are sufficient.

---

## Data Boundaries (system prompt context)

Claude needs to know exactly what's in scope to correctly classify questions.
This gets embedded in the system prompt:

**In scope (MPO only, 2020–2026):**
- Tournament results: winner, score, prize, dates, classification
- Player round scores and ratings
- Hole-by-hole scores (2021+ only — 2020 predates UDisc Live integration)
- Season standings (DGPT points — 2026 only, scraped weekly)
- Schedule and tournament metadata

**Out of scope:**
- FPO, amateur, or junior divisions
- PDGA player ratings (career rating, rating history)
- Live/in-progress rounds
- Player biography (age, hometown, sponsors, equipment)
- Hole-by-hole data for 2020 season
- Pre-2020 results

**Schema made available to Claude:**
A condensed version of the schema with semantic column descriptions —
not just column names, but what they mean. Example:
- `round.round_score` — score relative to par for the round (negative = under par)
- `round.round_rating` — PDGA-calculated round rating (1000 = scratch, >1000 = above scratch)
- `tournament.classification` — event tier: "Elite Series", "Elite Series Plus", "Major", "Tour Championship"
- `tournament.is_worlds` — boolean; TRUE for the PDGA Pro World Championships specifically

---

## UI

On the Search tab:

```
┌─────────────────────────────────────────────────────────────┐
│  Ask anything about DGPT MPO stats (2020–2026)              │
│                                                    [Ask →]  │
└─────────────────────────────────────────────────────────────┘

  Who has the most wins in Elite Series Plus events?

  ┌──────────────────────────────────────────────────────────┐
  │ Calvin Heimburg leads with 4 Elite Series Plus wins,     │
  │ followed by Ricky Wysocki (3) and Eagle McMahon (3).     │
  └──────────────────────────────────────────────────────────┘
  [table: player | wins | prize_total]

  ─────────────────────────────────────────────────────────
  Ask another question (7 remaining this session)
```

- Single `st.text_input` or `st.chat_input` — no form submission, Enter to submit
- Response appears below input in a card, same styling as triptych cards
- "N remaining this session" counter below input
- Spinner while waiting for Claude response
- Error / off-topic / out-of-scope messages use the same card, different tone

---

## API Key & Infrastructure

### Anthropic API key setup (one-time, manual)

1. Create key at console.anthropic.com → API Keys
2. Store in Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
     --name disc-golf-anthropic-key \
     --secret-string '{"api_key":"sk-ant-..."}' \
     --region us-east-1
   ```
3. Add `ANTHROPIC_API_KEY=sk-ant-...` to local `.env`

### CDK changes needed

- Add Secrets Manager secret reference to ECS task definition environment
- Add IAM permission for ECS task role to read the new secret
- Add `DG_READER_URL` environment variable (read-only DB user credentials)

### New Python dependency

`anthropic` package added to `requirements.txt` (app dependency, not Lambda).

---

## Implementation Sequence

### Step 1 — Infrastructure + logging table ✓
- Alembic migration: `search_log` table
- Read-only `dg_reader` PostgreSQL user (`scripts/create_dg_reader.sql`)
- CDK: `ANTHROPIC_API_KEY` secret wired into ECS task environment
- `dashboard/helpers/db_config.py`: `reader_engine` via `DG_READER_URL`

### Step 2 — Claude integration + query engine ✓
- `dashboard/search.py`: Claude Haiku API call, SQL validation, query execution, logging
- System prompt with full schema context and data scope boundaries
- Rate limiting via `st.session_state` (10 queries/session, 3s cooldown)

### Step 3 — Search tab UI ✓
- `render_search()` replaces shell placeholder
- Chat input, spinner, response card (green border on answered), session counter
- Explicit `color:#1C1C1E` on all rendered HTML to avoid Streamlit CSS inheritance issues

### Step 4 — Log review tooling ✓
- `make query-log`: dumps recent `search_log` rows from RDS (path, question, asked_at)

---

## Ongoing — Prompt Tuning

With the feature live, improvements are driven by real query logs. Run `make query-log`
to review what users are asking and where the system is failing. Common failure modes:
- `error` path: SQL generated but failed validation or execution → refine schema description or add SQL examples
- `out_of_scope` on questions we should be able to answer → expand system prompt scope
- `answered` with wrong/confusing results → tighten SQL rules or add guardrails
