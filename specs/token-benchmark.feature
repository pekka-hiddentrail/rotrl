# FEATURE — Token Benchmark Panel

**ID:** token-benchmark
**Status:** Approved
**Area:** Backend | Frontend | Infrastructure
**Tags:** @benchmark @api-log @token @quality-of-life

---

## Story

> As a **developer**,
> I want to record LLM prompt/completion token counts for a fixed three-turn scenario after each code change,
> so that I can detect prompt bloat regressions before they accumulate into real session cost.

The benchmark runs three deterministic turns against the real Anthropic API using a fixed session-1 scenario. Token counts are appended to a persistent CSV and visualised in a panel accessible from the header. The panel shows the most-recent 9 rows at a time with a paginator and three trend charts (one per benchmark turn) covering the full history.

---

## Background

- Given the backend is running
- And `ANTHROPIC_API_KEY` is set in the environment
- And `outputs/token_benchmarks.csv` exists or can be created

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Three-turn run appends rows to the benchmark CSV
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given ANTHROPIC_API_KEY is set and the backend is running
When  pytest tests/test_token_benchmark.py is executed
Then  the test boots a session with provider=anthropic, model=claude-haiku-4-5
And   sends three turns in order:
        T1 — "We arrive to the Swallowtail festival."
        T2 — "I try to convince Belor Hemlock to join me for a pint."
        T3 — "We head inside the Rusty Dragon."
And   three new rows (turn=1, turn=2, turn=3) are appended to outputs/token_benchmarks.csv
And   each row contains: timestamp, provider, model, session (8-char id), turn,
        prompt_tokens, completion_tokens, total_tokens, system_chars, log_file
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Benchmark is skipped when API key is absent
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given ANTHROPIC_API_KEY is not set
When  pytest tests/test_token_benchmark.py is executed
Then  the test is reported as SKIPPED (not FAILED)
And   no rows are appended to the CSV
And   no real API call is made
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — GET /api/benchmarks returns all CSV rows as JSON
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given outputs/token_benchmarks.csv contains N rows
When  GET /api/benchmarks is called
Then  the response is { "rows": [ ... ] } with N objects
And   each object has the same fields as the CSV header
And   if the CSV does not exist, the response is { "rows": [] }
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Benchmarks panel opens from the header button
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session has been booted
When  the user clicks the Benchmarks button in the header
Then  the TokenBenchmarks modal opens as a full-overlay panel
And   it shows a loading state while the fetch is in flight
And   pressing Escape or clicking the backdrop closes the panel
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Table paginates at 9 rows per page
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the benchmark CSV has more than 9 rows
When  the panel is open
Then  the table shows exactly 9 rows on the first page (most recent first)
And   a paginator shows "1 / N  (total rows)" below the table
And   clicking Next advances to the next page
And   clicking Prev moves back
And   Prev is disabled on page 1; Next is disabled on the last page
And   if the CSV has ≤ 9 rows, no paginator is rendered
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Three trend charts visualise prompt/completion/total over time
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given benchmark data exists for all three turns
When  the panel is open
Then  three line charts are shown below the table: one for Turn 1, Turn 2, Turn 3
And   each chart plots prompt (green), completion (gold), and total (red) over run index
And   y-axis ticks scale to the max value across all three series
And   a legend identifies each series by colour and label
And   if a turn has no data, its chart shows "No data yet"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Each table row links to its API log file
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a benchmark row has a non-empty log_file field
When  the user clicks the "view" link in that row's Log column
Then  the browser opens GET /api/log/api/{log_file} in a new tab
And   rows with an empty log_file show "—" with no link
```
