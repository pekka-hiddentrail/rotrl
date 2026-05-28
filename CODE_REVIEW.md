# Code Review — RotRL API

Items to work through one by one. Check off as done.

---

## BUGS

### B1 — Silent exception swallows in block parsing
**File:** `api/session_manager.py` ~1129, 1138, 1168, 1181  
**Status:** ✅ Fixed

Bare `except Exception: pass` in the section-processing loop replaced with logging calls. All four sites (`%%GENERATE%%` new format, `%%DELTAS%%` new format, `%%GENERATE%%` old format, `%%DELTA%%` old format) and `_detect_narrative_npcs` now emit a GM-directive log entry on failure.

---

### B2 — UnboundLocalError in party name extraction
**File:** `api/session_manager.py` ~402  
**Status:** ✅ Fixed

`name` and `cls` were not reset between files and could be unbound if `**Class / Archetype:**` appeared before `**Name:**`. Fixed by initialising both to `""` before the inner loop and only appending when both are non-empty. Removed the `break` so the full file is scanned regardless of line order.

**Tests added:** `test_party_name_without_class_does_not_crash`, `test_party_class_before_name_does_not_crash`, `test_party_mixed_good_and_malformed_sheets` in `tests/test_boot_prompt.py`.

---

### B3 — Stub creation failure is silent
**File:** `api/session_manager.py` ~307  
**Status:** ✅ Fixed (via B1)

The stub-creation path in `_process_generate_block` runs inside the `except Exception as _e: _log(...)` block added for B1. Any I/O failure during `npc_dir.mkdir` or `base.md` write is now visible in the session log.

---

### B4 — Groq retry-after header parse leaves stale wait value
**File:** `api/session_manager.py` ~93  
**Status:** ✅ Fixed (comment added)

Added a comment explaining that a malformed header leaves `wait` at its previous exponential-backoff value, and that this is acceptable because the server already said "wait this long" on the previous attempt.

---

### B5 — Path traversal in API log endpoint
**File:** `api/main.py` ~170  
**Status:** ✅ Fixed

Added `resolve()` + `is_relative_to()` check after constructing the path. The regex filter still runs first (fast reject); the resolve check is a defence-in-depth guard against symlinks or edge cases the regex misses.

---

## MISSING TESTS

### T1 — `api/api_logger.py` — zero coverage
**Status:** ✅ Done — `tests/test_api_logger.py` (10 tests)

Covers: file creation, path return type, filename format, session-ID truncation, JSON structure, error field, message summary count, preview truncation, short-content no-truncation, char count field.

---

### T2 — Groq provider code — ~10% coverage
**Status:** ✅ Done — `tests/test_groq_provider.py` (11 tests)

Covers: `_groq_post` 200/429/413/500 paths, retry-after header variants, exponential backoff, max-retries exhaustion; integration tests for narrative streaming, missing API key, max-history truncation.

---

### T3 — Skill lookup — ~20% coverage
**File:** `api/context/skill_lookup.py`  
**Status:** ✅ Done — `tests/test_skill_lookup.py` (21 tests)

Covers: `detect()` basic/multi-word/longest-wins/case-insensitive/no-match/word-boundary/rules-text; `lookup()` by name/case/unknown; `known_skills`; edge cases (empty dir, missing dir, underscore skipped, reference separator, format_context); `_parse_skill_file` unit tests.

---

### T4 — NPC lookup gaps
**File:** `api/context/npc_lookup.py`  
**Status:** ✅ Done — `tests/test_npc_lookup_extended.py` (26 tests)

Covers: `detect_all()` multiple/empty/no-duplicates/longest-alias/three-NPCs; `npc_dir_for()` known/case-insensitive/unknown; `lookup()` canonical/case/unknown; fresh status and knowledge reads; reference separator; format_context; edge cases (no base.md, underscore dirs, missing dir); `_parse_base` unit tests.

---

### T5 — API log endpoints
**File:** `api/main.py`  
**Status:** ✅ Done — `tests/test_api_logs.py` (10 tests)

Covers: `GET /api/log/api` empty/shows-files/size_bytes/newest-first/limit; `GET /api/log/api/{filename}` returns-content/404/invalid-filename/semicolon/URL-encoded-traversal.

---

### T6 — End-of-session recap/boot generation
**File:** `api/session_manager.py`  
**Status:** ✅ Done — `tests/test_end_session.py` (18 tests)

Covers: `_parse_turns_from_log` empty/no-headers/single-player/single-GM/player-then-GM/details-blocks/h2-separator/dash-separator/multiple-turns/directive-lines; `_enforce_recap_header` canonical-form/heading-strip/place-date/default-date/trailing-sep/session-number; `stream_end_session` error paths (missing log, empty turns).

---

### T7 — `_parse_response_sections` fallback and edge cases
**File:** `api/session_manager.py`  
**Status:** ✅ Done — `tests/test_response_sections.py` (27 tests)

Covers: `_parse_response_sections` split/no-marker/deltas-without-narrative/all-four/empty/whitespace/generate-before-deltas/multiple-generate; `_parse_bracket_blocks` single/multiple/multiple-knowledge/trailing-comma/empty/no-brackets/new-fields/location-type; `_extract_knowledge_items` single/multiple/none/case-insensitive; section marker detection; `_DELTA_BLOCK_RE` fallback format.

---

## REFACTORING

### R1 — `_stream_chat` is 400 lines — split it
**File:** `api/session_manager.py`  
**Status:** Open

The function does: history trimming, context injection, logging, LLM dispatch, section parsing, block processing, and narrative scanning. Extract at minimum:

- `_process_response(response_text, session) -> (display_text, roll_data)` — owns section parsing + all block handling
- `_inject_context(session, last_user, system_content) -> (system_content, npc_match, skill_match, location_matches)` — owns lookup + scene_npcs update

---

### R2 — Silent `except Exception: pass` — add a helper
**File:** `api/session_manager.py`  
**Status:** ✅ Fixed (via B1)

All bare `except Exception: pass` sites now log with `_log()`. Further cleanup (extracting a `_log_block_error` helper) is still optional.

---

### R3 — Provider dispatch is duplicated
**File:** `api/session_manager.py`  
**Status:** Open

Groq/Ollama branching appears in: payload building, streaming, `_call_blocking`, token options. Adding a third provider means touching all of them. A simple protocol:

```python
# Not full ABC — just two private functions with a common signature
def _build_payload(session, messages, options) -> dict: ...
def _iter_stream(session, messages, options, accumulated) -> Generator: ...
```

---

### R4 — `_NAME_EXCLUDE_WORDS` is a maintenance burden
**File:** `api/session_manager.py` ~179  
**Status:** Open

40+ hardcoded words. Campaign-specific false positives (e.g., Varisian place names) get added here forever. Load from a text file in `adventure_path/` so the GM can tune it without touching Python.

---

### R5 — Global lazy indexes — make invalidation explicit
**File:** `api/session_manager.py` ~32–57  
**Status:** Open

`_npc_index` and `_skill_index` are module globals mutated by `_invalidate_npc_index()`. Works fine now (single process, single session at a time) but the pattern is fragile. Encapsulate in a simple wrapper that makes the reload explicit and testable.

---

### R6 — Timestamp format scattered
**File:** `api/session_manager.py`  
**Status:** Open

`%H:%M:%S`, `%Y%m%d_%H%M%S`, `%Y-%m-%d %H:%M:%S` appear in 6+ places. One constant or two helper functions (`_ts()` already exists for `%H:%M:%S` — use it everywhere).

---

### R7 — `_write_npc_delta` mixes concerns
**File:** `api/session_manager.py` ~275  
**Status:** Open

One function does: Layer 2 stub creation, status file append, knowledge file append, logging for each. Hard to test the file-writing in isolation. Split into `_append_status_block()` and `_append_knowledge_items()`.

---

### R8 — Duplicate bracket-block parsing in fallback vs section paths
**File:** `api/session_manager.py` ~1103–1182  
**Status:** Open

`%%ROLL%%` parsing logic is written once for the section path and once for the flat fallback path. If the roll field format changes, both need updating. Normalise the fallback to a section dict first, then run the same downstream parser.

---

## NOTES

- All 296 tests pass after bug fixes.
- B1–B5 fixed, T1–T7 tests written.
- Remaining work: R1–R8 refactoring items (R2 already resolved via B1).
- Security items B5 and T5 are both complete.
- R1 (split `_stream_chat`) is the highest-leverage refactor — it unblocks further testing by making the parsing logic independently testable.
