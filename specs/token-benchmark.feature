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

The benchmark runs three deterministic turns against the real Anthropic API using a fixed session-1 scenario. Token counts are appended to a persistent CSV and visualised in a panel accessible from the header. The panel shows the most-recent 12 rows at a time (merged across social and combat sources, up to 30 per source) with a paginator and six trend charts in two labelled groups covering the full history.

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
### AC-005 — Table paginates at 12 rows per page with a per-source cap
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the benchmark CSVs together have more than 12 rows
When  the panel is open
Then  the table shows exactly 12 rows on the first page (newest first, merged across sources)
And   at most 30 rows from each source (social / combat) are loaded
And   a paginator shows "1 / N  (total rows)" below the table
And   clicking Next advances to the next page
And   clicking Prev moves back
And   Prev is disabled on page 1; Next is disabled on the last page
And   if the combined total is ≤ 12 rows, no paginator is rendered
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Six trend charts in two labelled groups
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given benchmark data exists for all three social turns and at least one combat scenario
When  the panel is open
Then  a section label "Social (3-turn run)" appears above three line charts for Turn 1 / 2 / 3
And   a section label "Combat" appears above three line charts for:
        combat_init  ("Combat T2 — Initiation")
        first_strike ("Combat T3 — First Strike")
        intimidate   ("Combat T4 — Intimidate")
And   each chart plots prompt (green), completion (gold), and total (red) over run index
And   a legend identifies each series by colour and label
And   if a turn or scenario has no data, its chart shows "No data yet"
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

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Combat benchmark run appends rows to the combat CSV
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given ANTHROPIC_API_KEY is set and the backend is running
When  pytest tests/test_token_benchmark.py::test_token_counts_combat_turns is executed
Then  the test sends four turns:
        T1 pre_combat   — "We arrive at the Swallowtail festival."
        T2 combat_init  — a turn that triggers a %%COMBAT%% block (goblin attack)
        T3 first_strike — "Thaelion attacks Goblin 1."
        T4 intimidate   — a war-cry intimidation attempt
And   rows for combat_init, first_strike, and intimidate are appended to outputs/token_benchmarks_combat.csv
And   each row contains the standard token fields plus: scenario, combat_started, attack_requested, roll_requested, log_file
And   if combat_started == 0 after turn T2, the test prints a WARNING but does not fail
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — GET /api/benchmarks/combat returns all combat CSV rows as JSON
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given outputs/token_benchmarks_combat.csv contains N rows
When  GET /api/benchmarks/combat is called
Then  the response is { "rows": [ ... ] } with N objects
And   each object has the combat CSV fields (scenario, combat_started, attack_requested, roll_requested, plus standard token fields)
And   if the file does not exist, the response is { "rows": [] }
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Table rows are visually tinted by source
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the merged benchmark table contains both social (basic) and combat rows
When  the panel is open
Then  social rows have a subtle green background tint (class bm-row--basic)
And   combat rows have a subtle amber background tint (class bm-row--combat)
And   both tints intensify on row hover
And   the Turn / Scenario column shows the scenario name for combat rows and the turn number for social rows
```
