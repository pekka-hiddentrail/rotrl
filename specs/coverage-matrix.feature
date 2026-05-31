# FEATURE — Feature Coverage Matrix

**ID:** coverage-matrix
**Status:** Approved
**Area:** Developer Tooling
**Tags:** @developer-tools @coverage @quality-of-life @specs

---

## Story

> As a **developer**,
> I want a live view of which spec ACs have test coverage and which are gaps,
> so I can prioritise test-writing work and track progress toward full coverage.

The coverage matrix crosses the spec files (`specs/*.feature`, each with named `### AC-NNN` headings) against the test suites (pytest, Vitest, Playwright). A Python script builds the data; the UI renders a filterable table with green/red coverage dots.

---

## Background

- Given `scripts/build_coverage.py` has been run at least once
- And `outputs/coverage.json` exists
- And the backend is running

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Script parses all spec AC headings into coverage.json
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Running the script produces complete AC inventory

```gherkin
Given spec files exist in specs/*.feature
When  python scripts/build_coverage.py is run
Then  outputs/coverage.json is written
And   every AC-NNN heading found in any .feature file appears as a row
And   each row has: feature_id, feature_file, ac_id, title, pytest, vitest, playwright, status
And   summary.total equals the count of rows
And   summary.covered counts rows where at least one test list is non-empty
And   summary.gap equals summary.total minus summary.covered
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Script links test files to ACs via feature hints and AC ranges
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Test file with feature hint and range reference

```gherkin
Given a test file contains "Spec: specs/event-injection.feature"
And   the file contains the pattern "AC-001" or "AC-NNN through AC-NNN"
When  the script runs
Then  the matching AcEntry has that test filename in its pytest/vitest/playwright list
And   range references are expanded (AC-001 through AC-004 → AC-001, AC-002, AC-003, AC-004)
And   a test file with no feature hint only links to an AC when that AC ID is
      unique across all spec files
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — GET /api/coverage returns the matrix JSON
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** API endpoint serves coverage data

```gherkin
Given outputs/coverage.json exists
When  GET /api/coverage is called
Then  the response is 200 with Content-Type application/json
And   the body has keys: generated, summary, rows
And   summary has keys: total, covered, gap

Given outputs/coverage.json does not exist
When  GET /api/coverage is called
Then  the response is 200 with summary.total = 0 and rows = []
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Coverage panel opens from the header Coverage button
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Coverage button in header opens the modal

```gherkin
Given the app is loaded (booted or unbooted)
When  the user clicks the "Coverage" button in the header
Then  the CoverageMatrix modal appears
And   the modal shows a summary bar with covered / total / gaps counts
And   pressing Escape closes the modal
And   clicking the backdrop outside the panel closes the modal
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — "Gaps only" filter shows only uncovered ACs
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Filter reduces table to gap rows only

```gherkin
Given the CoverageMatrix panel is open with data loaded
When  the user clicks the "Gaps only" filter button
Then  the table shows only rows where pytest, vitest, and playwright are all empty
And   the row count label updates to reflect the filtered count
And   clicking "All" restores all rows
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Feature dropdown narrows the table to a single feature
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Feature filter is combined with gap filter

```gherkin
Given the CoverageMatrix panel is open
When  the user selects a feature from the dropdown (e.g. "event-injection")
Then  the table shows only rows where feature_id matches the selection
And   the gap filter can be applied on top: only gap rows for that feature are shown
And   selecting "All features" from the dropdown restores all rows
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Exploratory test files in tests/exploratory/ contribute coverage
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Exploratory markdown files are scanned as a fourth test suite

```gherkin
Given tests/exploratory/*.md files contain "Spec: specs/<id>.feature" and AC-NNN references
When  python scripts/build_coverage.py is run
Then  each matching AcEntry has the exploratory filename in its exploratory list
And   a row with only exploratory coverage has status = "covered"
And   the CoverageMatrix table shows an "Exploratory" column alongside pytest / Vitest / Playwright
```
