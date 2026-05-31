# Exploratory Tests — API Logging and Log Browser

Spec: specs/session-logging.feature

**What automated tests cover:** `api_logger.py` write path, file rotation, section_format_ok flag,
latency fields, listing endpoint, file-detail endpoint — with temp directories.

**Pre-requisites:** `python dev.py --skip-tests` — stack running. Run at least 4 turns in a
session before executing these chains.

---

## Chain A — Log structure and latency fields  <!-- AC-004, AC-007, AC-008 -->

After a session with at least 4 turns:

1. Open `http://localhost:8000/api/log/api` — you'll see a JSON object with a `files` array.
2. Copy the most recent filename and navigate to `http://localhost:8000/api/log/api/<filename>`.
3. ✔ `duration_ms` values are plausible: 800–20 000 ms for normal Groq turns.
4. ✔ `first_token_ms` is a positive integer and less than `duration_ms` (e.g. 200–3 000 ms).
5. ✔ `section_format_ok` is `true` or `false` — never `null` on a successful turn.
6. ✔ `usage.total_tokens` is present and non-zero (may be `null` for older Groq models).
7. ✔ `messages[0].role` is `"system"` and `messages[0].content` is non-empty.
8. ✔ `preview` field contains the first ~200 characters of the GM response with no garbled
   escaping.

---

## Chain B — Error-path null fields  <!-- AC-004 -->

1. Kill the API mid-request (or deliberately use an invalid API key).
2. Open the resulting API log JSON.
3. ✔ `duration_ms` is set (wall time).
4. ✔ `first_token_ms` is `null` (no tokens arrived).
5. ✔ `section_format_ok` is `null` (can't be determined from an errored request).
6. ✔ `usage` is `null`.

---

## Chain C — Session log content  <!-- AC-001, AC-002, AC-003, AC-005 -->

1. After a session with 3+ turns (including one with a dice roll):
2. Open `http://localhost:8000/api/sessions/1/log`.
3. ✔ File contains the boot system prompt in a `<details>` block.
4. ✔ Each turn has a timestamped `### PLAYER` section and `### GM` section.
5. ✔ Dice rolls appear in the log with their numeric result.
6. ✔ Content is readable markdown (not raw JSON escapes).

---

## Chain D — API log browser panel  <!-- AC-009, AC-010 -->

1. Boot a session, send 3+ turns.
2. Click **API Logs** in the header.
3. ✔ Panel opens with a list of recent log files.
4. ✔ Each row shows filename, model, status, duration.
5. ✔ Clicking a row shows the detail view with: status badge, format badge, latency badge,
   token counts, raw JSON block, back button.
6. ✔ Clicking the back button returns to the list.

---

## Chain E — Listing order  <!-- AC-006 -->

1. Run 3 turns (creating 3 log files).
2. Open `http://localhost:8000/api/log/api`.
3. ✔ Files are listed newest-first (most recent timestamp at the top of the `files` array).
