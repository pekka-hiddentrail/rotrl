# FEATURE — Session Logging

**ID:** session-logging
**Status:** Approved
**Area:** Backend
**Tags:** @logging @session-log @api-log @dice

---

## Story

> As the **GM and developer**,
> I want every session turn, dice roll, LLM call, and NPC write to be persisted incrementally,
> so that I can review what happened after the session or debug prompt issues without needing a replay.

Two log streams are maintained in parallel: a human-readable session markdown log and a machine-readable per-call JSON log.

---

## Background

- Given a session has been booted
- And the `outputs/` directory exists

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Session log is created at boot with header and system prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A new session is booted

```gherkin
Given a boot request is submitted with session_number=3, model="llama-3.3-70b-versatile", dev_mode=false
When  the session is created
Then  a file is created at outputs/session_003_YYYYMMDD_HHMMSS.log.md
And   the file starts with a session header containing model, mode, temperature, and timestamp
And   the full system prompt is written inside a collapsible <details> block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Each turn appends timestamped PLAYER and GM sections
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A player turn completes

```gherkin
Given a session is active
When  the player submits "I ask Ameiko about her brother"
And   the GM responds with narrative text
Then  the session log is appended with "### [HH:MM:SS] PLAYER" and the player input
And   the session log is appended with "### [HH:MM:SS] GM" and the clean narrative
And   the LLM payload (messages + options) is written in a collapsible <details> block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Dice rolls are logged with full breakdown
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player rolls dice during the session

```gherkin
Given a session is active
When  POST /api/sessions/{id}/roll is called with expr="2d6", rolls=[3,5], total=8
Then  the session log is appended with the expression, per-die breakdown, and total
And   the entry is timestamped
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — API call log is written per LLM request
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** An LLM call is made during a turn

```gherkin
Given a turn is submitted to Groq
When  the LLM call completes
Then  a JSON file is created at outputs/api_log/YYYYMMDD_HHMMSS_mmm_groq_s001_t003_{session[:8]}.json
And   the file contains: timestamp, provider, session_id, session_number, turn, status, duration_ms
And   the file contains raw_request with the exact API payload
And   the file contains raw_response with the full assembled response text
And   the file contains summary with model, message count, and per-message previews
And   for Groq turns: the file contains usage with prompt_tokens, completion_tokens, total_tokens
And   for Ollama turns: the file contains usage: null
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — API log records first-token latency alongside total duration
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM streams a response

```gherkin
Given a turn is submitted and the LLM streams tokens
When  the first token arrives from the stream
Then  the elapsed time from request dispatch to first token is captured as first_token_ms (integer milliseconds)
When  the full stream completes
Then  the API log JSON contains both first_token_ms and duration_ms
And   first_token_ms is less than or equal to duration_ms
And   first_token_ms is greater than 0
```

**Scenario:** LLM call errors before any token arrives

```gherkin
Given a turn is submitted and the LLM returns an error before streaming
When  the API log JSON is written
Then  first_token_ms is null
And   status is "error"
```

**Notes:**
- `first_token_ms` is measured from the moment the HTTP request is dispatched (not from when the user presses send).
- For non-streaming providers (if any are added), `first_token_ms` equals `duration_ms`.
- The field is always present in the log object; null only on error.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Session log is readable via GET /api/sessions/{id}/log
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer views the log while the session is running

```gherkin
Given a session has completed at least one turn
When  GET /api/sessions/{id}/log is called
Then  the response is PlainTextResponse with the current contents of the log file
And   the contents include all turns written so far
And   the response is the live file (not a snapshot — reflects incremental writes)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — API log listing returns files newest-first
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer browses recent API calls

```gherkin
Given outputs/api_log/ contains multiple call log files
When  GET /api/log/api is called
Then  the response lists up to 50 filenames, newest first
And   GET /api/log/api/{filename} returns the JSON contents of that file
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — `section_format_ok` boolean tracks structured-output adherence per call
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario A:** LLM response uses the section-based format

```gherkin
Given a turn completes and the LLM response contains at least one %%NARRATIVE%%, %%ROLL%%, %%DELTAS%%, or %%GENERATE%% marker
When  the API call log JSON is written
Then  the top-level field section_format_ok is true
```

**Scenario B:** LLM response omits section markers (flat / legacy format)

```gherkin
Given a turn completes and the LLM response contains no %%-section markers
When  the API call log JSON is written
Then  the top-level field section_format_ok is false
```

**Scenario C:** LLM call errors before any response is received

```gherkin
Given the LLM call fails before any content is streamed
When  the API call log JSON is written
Then  the top-level field section_format_ok is null
And   status is "error"
```

**Notes:**
- Detection uses `_HAS_SECTION_MARKERS_RE` (already module-level in `session_manager.py`); no new regex is introduced.
- The field is computed from the fully assembled response (`"".join(accumulated)`) in the same `finally:` block that calls `write_api_log`, so the log and the parse result are always consistent.
- `section_format_ok` is a passive observability field only — it does not affect session behaviour.
- Intended use: scan `outputs/api_log/*.json` after a real session to measure the rate at which the model is following the structured output template (`section_format_ok == true`) vs falling back to flat prose.

---

## Out of Scope

- Log rotation or archiving (outputs/ is git-ignored and manually managed)
- Session notes JSON (covered by SPEC-003)

---

## Notes

- See: [INDEX.md §9 — Logging](INDEX.md)
- Log file path stored on `GameSession.log_path`; written incrementally (never buffered)
- Recap LLM call strips `<details>` blocks and system prompt before feeding history to recap prompt
- `outputs/` is in `.gitignore`
