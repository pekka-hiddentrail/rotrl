# Project Todo

This file is a working backlog for the RotRL automation project. Items are grouped by area and ordered roughly by impact.

**Every time this file is updated, the open items should be at the top of the list, done should be middle and "obsolete" are at the bottom.**

---

## High Priority

- [ ] Make sure the DCs for rolls are from NPC stats AND supplemented by the skill file.
- [ ] Feed resolved roll outcome into the next GM turn directive — `resolve_roll()` returns pass/fail but this result is never injected into the next turn's `system_content`, so the GM is narrating blind. *(closed by M5 — roll turns in history)*
- [ ] Remove the functionality where the diceroll goes to the input field. Feed the roll directly to the stream as an input. *(addressed by M5)*
- [ ] Update player character knowledge files after each session so each PC only retains facts they actually learned in play.
- [x] Refine LLM output so GM responses are shorter, cleaner, and more mechanically grounded under pressure.
- [x] Update NPC knowledge and memory state after each session, including attitude shifts, known facts, suspicions, and unresolved goals. *(per-turn `%%DELTA%%` blocks written to `session_NNN.md` per NPC; delta files cleared on session boot)*
- [x] Evaluate whether Ollama should remain the serving layer. *(Groq is now the primary provider — faster, no GPU overhead, better structured-output adherence. Ollama kept as offline fallback only; no further investment planned.)*

---

## GM and Session Flow

- [ ] Make player identity loading consistent across code paths; current boot logic still expects some optional files in different locations than the repo uses.
- [ ] Route boot and recap generation to `llama-3.3-70b-versatile` and normal turns to `llama-3.1-8b-instant` — add a per-call-type model override in `_stream_groq`.
- [ ] Fix prompt spec gaps — three small changes to `_build_slim_system_prompt`: (1) add `personality:` field to `%%GENERATE%%` block spec (code already reads it, model never writes it); (2) add "skip `%%GENERATE%%` for NPCs already in the scene" rule; (3) add "at most one `%%ROLL%%` block per response" constraint.
- [ ] Move the format example below a `<!-- REFERENCE -->` marker in the system prompt — it is currently injected on every turn (~500 chars). Same mechanism used by skill files. The model has already learned the format; the example only needs to be loaded at boot.
- [x] Split skill files into GM payload and reader reference sections. *(`<!-- REFERENCE -->` separator added to all five skill files; `_parse_skill_file` stops at the marker — payload ~26–39% smaller per injection, reader docs preserved below the line.)*
- [x] Set Groq as the default provider in the GUI; default model `llama-3.1-8b-instant`; dev mode off by default. *(dev mode with Groq only shows `%%` markers — the dev system prompt strips the full structured format, so leaving it on breaks `%%DELTAS%%` etc.)*
- [x] Split boot-time context from active-play context so the first prompt loads only critical rules and immediate continuity. *(`context_queue` removed; per-turn keyword RAG injection replaces it)*
- [x] Wire a true normal-session path instead of routing every start through the full boot pipeline. *(boot makes no LLM call; first GM response fires on the player's first turn)*
- [x] Reduce duplicate verification work in boot, especially where a second LLM call can be replaced with deterministic checks. *(boot LLM call eliminated entirely; delta extraction moved from second Groq call to parsed `%%DELTA%%` block)*
- [x] Define a post-session pipeline that writes recap, continuity, PC knowledge, and NPC state in one consistent pass. *(`stream_end_session` writes recap + next-session boot file; NPC deltas written per-turn; PC knowledge update still pending)*
- [x] Enforce a structured response template so the LLM writes `%%NARRATIVE%%`, `%%ROLL%%`, `%%DELTAS%%`, and `%%GENERATE%%` sections consistently. *(`_build_slim_system_prompt` now includes a `RESPONSE STRUCTURE` block with the full template; `_parse_response_sections` + `_parse_bracket_blocks` handle parsing)*
- [x] Hide internal `%%`-section markers from the player in non-dev mode. *(`_stream_with_narrative_filter` wraps the raw SSE token stream; dev mode passes all tokens, non-dev streams only `%%NARRATIVE%%` content and stops at the next section marker)*

---

## NPC Lifecycle and Knowledge

- [x] Promote auto-created session NPCs to permanent records via a lightweight review workflow. *(session NPCs now live in dot-prefixed directories under `05_npcs/`; rename the directory to drop the dot to promote. UI "Purge NPCs" button bulk-deletes all dot-prefixed dirs via `DELETE /api/npcs/session`.)*
- [ ] Carry `scene_npcs` forward into the next session's boot file — `session.scene_npcs` is in-memory only and lost when the session ends. On `stream_end_session`, append the active NPC list to `sessions/session_NNN+1/boot.md` so the next session starts with those NPCs already in context. Without this the GM starts cold every session regardless of what was in-flight.
- [ ] Surface the list of detected-but-not-yet-stubbed names from `scene_npcs` somewhere visible (log or UI) so the GM can verify the model caught them.
- [ ] Write `%%GENERATE%%` summary field to NPC knowledge — the `summary:` field in `%%GENERATE%%` blocks is parsed but silently dropped. Write it as the first entry in the new NPC's `knowledge.md`: `- [world] {summary} — S{session:03d} T000`. Bootstraps the NPC's knowledge file immediately.
- [ ] Single-word NPC name detection — `_detect_narrative_npcs` regex requires two Title Case words (`r'\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b'`). Known NPCs with single-word canonical names (e.g., "Aldern", "Lonjiku") are never auto-tracked. Fix: add an exact-match pass against `_get_npc_index().known_npcs` canonical names; keep the two-word heuristic for unknown-NPC suspicion only.
- [ ] Location tracking — `%%GENERATE%%` blocks with `type: location` are logged and skipped. Create `adventure_path/07_locations/` with the same `base.md` stub pattern as `05_npcs`. Write location stubs and wire a `LocationIndex` to inject location profiles as scene context. *(Supersedes "Create a new location function" item below.)*
- [x] Write structured NPC deltas per turn with multi-line knowledge support. *(`%%DELTAS%%` section uses bracket blocks, one per NPC; `knowledge:` lines collected as a list; `_write_npc_delta` helper extracted)*
- [x] Auto-create NPC stub when a `%%DELTAS%%` block references an unknown NPC (Layer 2 fallback). *(if `npc_dir_for` returns `None`, `_process_generate_block` is called with stub data before writing the delta)*
- [x] Detect NPCs introduced in narrative text without any structured block (deferred Layer 3). *(`_detect_narrative_npcs` scans completed narrative for Title Case name pairs, adds to `session.scene_npcs`; stub creation is deferred until the model writes a `%%DELTAS%%` block for that name)*
- ~~[ ] Create a new location function when the LLM returns new generated locations.~~ *(superseded by "Location tracking" item above which is more complete)*

---

## Knowledge and State Management

- [ ] Smart context pruning instead of hard char cutoff — when `len(system_content) > _GROQ_MAX_SYSTEM_CHARS`, the prompt is currently truncated at character 30,000 which can split mid-block. *(superseded by M4 — context becomes discrete blocks; pruning drops whole blocks tail-first instead of truncating a string)*
- [ ] NPC context injection ordering — when multiple NPCs are in scene, inject in recency order (most recently mentioned first) so the char-limit cutoff drops least-recently-seen NPCs. *(implement in M4 when context blocks are discrete)*
- [ ] `knowledge.md` age-out across long campaigns — knowledge items grow unboundedly. When injecting, only include entries from the last N sessions; archive older entries to `knowledge_archive.md`. Prevents prompt bloat over a multi-session campaign.
- [ ] Plan message history summarization to prevent the API payload from growing unbounded across long sessions. *(closed by M6)*
- [ ] Standardize the schema for character knowledge, NPC memory, session recap, and emergent canon so state can be updated automatically. *(blocked on M1 — the `ChatTurn`/`ContextBlock` model is the first step toward a canonical schema)*
- [ ] Create a clear source-of-truth rule for contradictions between session notes, recap files, NPC logs, and JSON outputs.
- [ ] Add validation checks for continuity drift such as wrong deity, alignment, class, or duplicated features across player records.
- [ ] Decide which state should live in markdown and which should live in structured JSON for UI and automation.

---

## Character Data and UI Content

- [ ] Normalize all player JSON files to one agreed UI schema and keep them synchronized with the markdown sheets.
- [ ] Audit Ani's data and other player records for internal inconsistencies before relying on them in UI or prompts.
- [ ] Add a small sync tool or documented workflow for copying approved sheet changes into UI JSON files.
- [ ] Review portraits, colors, runes, and labels so presentation data is consistent across all characters.

---

## Code Quality / Refactoring

- [ ] **R1a — Extract `_inject_context(session) -> tuple[str, dict]`** — pulls out steps 1–5 of `_stream_chat`: history trimming, system prompt truncation, NPC/skill/location keyword lookup, `scene_npcs` accumulation, delta-reminder path. Returns `(system_content, context_info)` — orchestrator uses `context_info` to yield the SSE `context` event. Write standalone, test before wiring in. Safe to ship without touching `_stream_chat` yet. *Note: signature changes in M4 — function will write to `session.context_blocks` instead of returning a string. Implement as documented here first; M4 updates it.*
- [ ] **R1b — Tests for `_inject_context`** *(ship with R1a)* — three cases: (1) NPC alias match → profile prepended, scene_npcs updated; (2) no match → base prompt returned unchanged; (3) `scene_npcs` set but no new lookup → delta-reminder text appended.
- [ ] **R1c — Extract `_process_response(response_text, session) -> tuple[str, Optional[dict]]`** — pulls out steps 9–10: section-based parsing (`%%NARRATIVE%%` / `%%ROLL%%` / `%%GENERATE%%` / `%%DELTAS%%`) and the flat fallback path (`%%DELTA%%` / `%%GENERATE%%`). All NPC file writes happen here. Sets `session.pending_roll`. Returns `(display_text, roll_data)` — no SSE yielding inside. Prerequisite: R1a shipped and stable.
- [ ] **R1d — Tests for `_process_response`** *(ship with R1c)* — three cases: (1) section format happy path — correct display_text and roll_data returned; (2) flat fallback — roll block stripped from display_text; (3) no markers — raw text returned unchanged. Plus extend `test_turns.py` golden-path test: mock Groq, assert SSE event order is `context → token(s) → patch_last → roll_request`.
- [ ] **R1e — Wire up: `_stream_chat` becomes orchestrator** *(ship after R1c is stable in play)* — replace inline blocks with calls to `_inject_context` and `_process_response`. Validate with R1d integration test. `_stream_chat` should be ~40 lines when done.
- [ ] **R3 — Provider dispatch is duplicated** — Groq/Ollama branching in payload building, streaming, `_call_blocking`, and token options. Adding a third provider means touching all four. Propose per-provider modules with `build_payload` / `iter_stream` functions sharing a common signature.
- [ ] **R4 — `_NAME_EXCLUDE_WORDS` maintenance burden** — 40+ hardcoded words. Load from `adventure_path/00_system_authority/name_exclude_words.txt` (one per line, `#` comments). Fall back to hardcoded set if file absent. GM-tunable without touching Python.
- [ ] **R5 — Global lazy indexes** — `_npc_index` / `_skill_index` are module globals mutated by `_invalidate_npc_index()`. Encapsulate in an `IndexRegistry` with `get_npc()`, `get_skill()`, `invalidate_npc()`. Makes state explicit and tests easier to write.
- [ ] **R6 — Timestamp formats scattered** — `%H:%M:%S`, `%Y%m%d_%H%M%S`, `%Y-%m-%d %H:%M:%S` appear in six-plus places. Add `_ts_file()` and `_ts_human()` helpers alongside the existing `_ts()`.
- [ ] **R7 — `_write_npc_delta` mixes concerns** — does Layer 2 stub creation, status block append, knowledge append, scene_npcs update, and three log calls. Extract `_append_status_block()` and `_append_knowledge_items()`; keep `_write_npc_delta` as orchestrator.
- [ ] **R8 — Duplicate `%%ROLL%%` parsing** — roll logic written once for the section path and once for the flat fallback path. Normalise the fallback to a section dict first, then run the same downstream parser.
- [ ] **F6 — Configurable tunables via env vars** — `_GROQ_MAX_HISTORY`, `_GROQ_MAX_SYSTEM_CHARS`, `_GROQ_RETRY_BASE`, `_DEV_MAX_HISTORY`, `_FULL_MAX_HISTORY` are hardcoded. Read from env with fallback: `int(os.getenv("GROQ_MAX_HISTORY", "10"))` etc.
- [x] **B1 — Silent exception swallows** — all `except Exception: pass` in section-processing loop replaced with `except Exception as _e: _log(session, ...)`.
- [x] **B2 — UnboundLocalError in party extraction** — `name`/`cls` initialised per-file; only appended when both non-empty; `break` removed so field order no longer matters.
- [x] **B3 — Stub creation failure silent** — covered by B1 fix; I/O errors in `_process_generate_block` now surface in session log.
- [x] **B4 — `retry-after` stale wait** — explanatory comment added to `_groq_post`.
- [x] **B5 — Path traversal in log endpoint** — `resolve()` + `is_relative_to()` guard added in `api/main.py`.
- [x] **R2 — `except Exception: pass` helper** — resolved together with B1.

---

## Message Pipeline

Separates the internal session model from the API payload. Currently `session.messages` IS the payload — context is string-concatenated into the system message each turn, which prevents Groq caching and makes adding new context types invasive. The goal: `GameSession` holds a typed internal model; `serialize_messages()` produces the API payload on demand.

Do these in order — each step is independently shippable and leaves the system working.

- [ ] **M1 — `ChatTurn` + `ContextBlock` types; extend `GameSession`** — add two dataclasses: `ChatTurn(role, content, turn_number, *, roll_fields?)` and `ContextBlock(kind, label, content)`. Add `session.chat: list[ChatTurn]` and `session.context_blocks: list[ContextBlock]` to `GameSession`. Keep `session.messages` untouched — no behavior change yet. Tests: instantiate session, verify defaults.

- [ ] **M2 — Write `serialize_messages(session) -> list[dict]`** — produces the API payload from the new model. Layout: `[system: static_base_prompt]` → `[user: assembled context blocks]` → `[user: summary turn if present]` → `[user/assistant: chat turns in order, rolls serialized as user turns]`. Falls back to `session.messages` if `session.chat` is empty (backward compat during migration). Tests: empty context, full context with NPC+skill+delta, chat with a roll turn, chat long enough to have a summary.

- [ ] **M3 — Wire `serialize_messages()` into `_stream_chat`; dual-write** — replace the `messages = [{"role": "system", ...}] + history` line with `serialize_messages(session)`. Context injection still appends to `system_content` (old path) AND appends to `session.context_blocks` (new path). `session.chat` mirrors `session.messages` (dual-write). Both paths produce the same payload — log a warning if they diverge. No behavior change. All existing tests pass.

- [ ] **M4 — Migrate context injection to `session.context_blocks`; static system message** — `_inject_context` (R1a, updated) now writes NPC profiles to `session.context_blocks` (`kind="npc"`), NPC deltas to `kind="npc_delta"`, skill rules to `kind="skill"`. `session.system_prompt` becomes truly static — never mutated after boot. `serialize_messages()` is the only place that assembles the payload. Remove old string-concat injection. Delete dual-write. **This is the step that enables Groq prompt caching** — system message is now byte-for-byte identical across all turns. Context pruning changes from string truncation to dropping whole `ContextBlock` entries tail-first. Tests: assert system message is identical on two consecutive turns; assert NPC block appears in the correct user message.

- [ ] **M5 — First-class roll turns in `session.chat`** — `log_roll()` appends `ChatTurn(role="roll", ...)` to `session.chat` with character, expression, individual rolls, and total. `resolve_roll()` updates that turn with `dc`, `passed`, and outcome text. `serialize_messages()` renders roll turns as `{"role": "user", "content": "[ROLL RESULT] Ani — Diplomacy — rolled 14+4=18 vs DC 12 — passed"}`. The GM now sees roll outcomes in history on the next turn automatically. **Closes "Feed resolved roll outcome into next GM turn directive"** and **"Remove diceroll from input field"**. Tests: roll turn appears in serialized messages; outcome text correct for pass and fail.

- [ ] **M6 — Chat history summarization** — when the number of `user`/`gm` turns in `session.chat` exceeds a threshold (default 20), compress the oldest N turns into a `ChatTurn(role="summary", content="...", turns="1-11")`. Initial implementation: deterministic concatenation with truncation, no LLM call. `serialize_messages()` injects the summary as a single user turn (`"[SESSION SUMMARY — turns 1–11]\n..."`) before the active window. Threshold and window size configurable via env vars (see F6). **Closes "Plan message history summarization"**. Tests: 25-turn chat serializes to summary + last 10 turns; summary is stable (same input = same output).

---

## Runtime and Tooling

- [ ] Add `GET /api/health` endpoint — returns `{"status": "ok"}`. The UI can hit this before attempting boot and surface a clear "backend not running" message instead of a generic network error.
- [ ] Track Groq token usage per turn — Groq returns `usage.prompt_tokens` / `completion_tokens` in the response body. Log these in `write_api_log()` alongside duration. After a few sessions you'll know exactly how fast `session.system_prompt` is growing and when M4/M6 becomes urgent.
- [ ] Harden backend startup further so orphaned Python child processes and stale listeners are detected and cleaned consistently on Windows.
- [ ] Document the exact local startup and recovery workflow for Windows, including port cleanup and Ollama checks.
- [ ] Session crash recovery — sessions are purely in-memory; a server restart during play loses `session.messages`, `scene_npcs`, `pending_roll`. After each turn, write a recovery snapshot to `outputs/sessions/{session_id}_snapshot.json`. On startup, detect orphaned snapshots and offer recovery.
- [ ] Add `first_token_ms` to the API log so first-token latency is captured alongside total response time.
- [ ] Add `section_format_ok` boolean to the API log (true if `_HAS_SECTION_MARKERS_RE` matched) to track structured-output adherence passively across real sessions.
- [x] Fix the UI startup path and determine why `npm run dev` is currently failing. *(was a port conflict — pinned Vite to port 5173 with `strictPort: true`)*
- [x] Add one command that boots backend and UI together for local development. *(`python dev.py` — runs tests, then starts API + UI; `--skip-tests` flag to bypass)*

---

## Quality and Testing

- [ ] **E2E — Playwright UI test suite** — add Playwright to `ui/` (`npm install -D @playwright/test`). Cover the six key flows with a mocked backend (MSW or a lightweight FastAPI fixture): (1) boot → session badge appears; (2) send turn → GM message streams in; (3) `roll_request` event → dice panel activates; (4) end session → chat clears; (5) Purge NPCs button → confirm dialog → success message; (6) character sidebar → sheet modal opens. These are the regression cases that break silently on UI refactors and are invisible to pytest.
- [ ] Test the full end-session SSE stream with mocked Groq — verify status events arrive in order, recap and boot files are written, and the session is removed from memory. *(critical)*
- [ ] Test turn input validation at the API boundary — confirm the error event is returned and no message is appended to session history when input is rejected. *(high)*
- [ ] Test `_enforce_recap_header` against real LLM output samples collected from past sessions to catch title/date extraction edge cases. *(high)*
- [ ] Test the roll endpoint writes the correct expression and total to the log, including multi-die breakdowns (e.g. 3d6 showing individual rolls). *(low)*
- [ ] Add a test fixture representing a corrupt or partially-written log file and assert the parser either recovers gracefully or raises a clear error. *(low)*
- [ ] Add contract tests for the SSE event shape — assert that every event emitted by boot, turn, and end-session has a `type` field and matches the known union of types. *(low)*
- [x] Add validation for prompt inputs and generated outputs before they are written to session artifacts.
- [x] Add focused tests for boot prompt assembly, file loading, and checklist verification.
- [x] Add regression tests for session-start context resolution and previous-session note discovery.
- [x] Add smoke tests for loading character JSON in the UI.
- [x] Test `_parse_response_sections` and `_parse_bracket_blocks` against representative LLM output shapes, including fallback-to-no-markers and multi-knowledge-line cases. *(`tests/test_response_sections.py` — 27 tests)*
- [x] Test `_stream_with_narrative_filter` — dev passthrough, narrative extraction, all three stop markers, holdback buffer, old-format fallback, split-token marker detection, and non-token event passthrough.
- [x] Test Layer 2 NPC auto-stub creation and index re-validation after stub write.
- [x] Test `_detect_narrative_npcs` — unknown name added to `scene_npcs`, no stub created, exclude-word filtering, already-tracked and already-indexed names skipped, short sentence-starters skipped.
- [x] `api/api_logger.py` — zero coverage. *(`tests/test_api_logger.py` — 10 tests: file creation, filename format, JSON structure, message summary, preview truncation)*
- [x] Groq provider `_groq_post` and `_stream_groq` — minimal coverage. *(`tests/test_groq_provider.py` — 11 tests: 429 retry, header parsing, backoff, max-history, streaming)*
- [x] Skill lookup `detect()` and `lookup()` — minimal coverage. *(`tests/test_skill_lookup.py` — 21 tests)*
- [x] NPC lookup `detect_all()`, `npc_dir_for()`, `lookup()` — minimal coverage. *(`tests/test_npc_lookup_extended.py` — 26 tests)*
- [x] `GET /api/log/api` and `GET /api/log/api/{filename}` endpoints — no tests. *(`tests/test_api_logs.py` — 10 tests including path traversal case)*
- [x] `_parse_turns_from_log()` edge cases and `stream_end_session()` error paths — no tests. *(`tests/test_end_session.py` — 18 tests)*
- ~~[ ] Test deferred context injection timing — verify each chunk lands on the correct turn and that the system prompt grows in the expected order.~~ *(obsolete — `context_queue` and deferred injection removed)*
- ~~[ ] Test that dev mode uses the short system prompt and ignores all deferred context files regardless of what exists on disk.~~ *(obsolete — deferred context files no longer exist; dev mode is now about the stream filter, which is tested)*

---

## Housekeeping

- [x] Decide what to do with `facets/FACET_*.md` — absorbed the 7 non-empty facets into a `GM STYLE` section in `_build_slim_system_prompt()`; deleted all 13 facet files and the `facets/` directory. Empty facets were superseded by the `%%ROLL%%` format block already in the prompt.
- [x] Review and clean `adventure_path/90_shared_references/temp.md` — almost certainly stale.
- [x] Delete `AGENTS.md` — documents the old `src/agents/gm_boot_agent.py` architecture that no longer exists. Only referenced once in `ADVENTURE.md` as a link. Remove the file and the link.

---

## Nice-to-Have

- [ ] Build a small admin view for inspecting session state, NPC memory, and pending continuity updates.
- [ ] Add diff-friendly generated outputs so session-to-session changes are easier to review.
- [ ] Stream the recap text to the chat window during End Session — `stream_end_session` already emits status events but the recap prose is written silently to disk. Yielding it as tokens would let the player read it as it generates, the same way turns stream.
- [ ] Show active scene NPCs in the UI — `scene_npcs` accumulates across turns but is invisible to the player. A small chip list below the IntentBar (or inside it) showing which NPCs are currently in scene would help the player track who the GM is "watching."