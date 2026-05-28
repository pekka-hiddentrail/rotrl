# Project Todo

This file is a working backlog for the RotRL automation project. Items are grouped by area and ordered roughly by impact.

## High Priority

- [ ] Update player character knowledge files after each session so each PC only retains facts they actually learned in play.
- [x] Update NPC knowledge and memory state after each session, including attitude shifts, known facts, suspicions, and unresolved goals. *(per-turn `%%DELTA%%` blocks written to `session_NNN.md` per NPC; delta files cleared on session boot)*
- [ ] Refine LLM output so GM responses are shorter, cleaner, and more mechanically grounded under pressure.
- [ ] Evaluate whether Ollama should remain the serving layer by comparing latency, determinism, prompt adherence, operational cost, and recovery behavior against alternatives. *(Groq added as a second provider; full comparison not done)*

## GM and Session Flow

- [x] Split boot-time context from active-play context so the first prompt loads only critical rules and immediate continuity. *(`context_queue` removed; per-turn keyword RAG injection replaces it)*
- [x] Wire a true normal-session path instead of routing every start through the full boot pipeline. *(boot makes no LLM call; first GM response fires on the player's first turn)*
- [x] Reduce duplicate verification work in boot, especially where a second LLM call can be replaced with deterministic checks. *(boot LLM call eliminated entirely; delta extraction moved from second Groq call to parsed `%%DELTA%%` block)*
- [ ] Make player identity loading consistent across code paths; current boot logic still expects some optional files in different locations than the repo uses.
- [x] Define a post-session pipeline that writes recap, continuity, PC knowledge, and NPC state in one consistent pass. *(`stream_end_session` writes recap + next-session boot file; NPC deltas written per-turn; PC knowledge update still pending)*
- [x] Enforce a structured response template so the LLM writes `%%NARRATIVE%%`, `%%ROLL%%`, `%%DELTAS%%`, and `%%GENERATE%%` sections consistently. *(`_build_slim_system_prompt` now includes a `RESPONSE STRUCTURE` block with the full template; `_parse_response_sections` + `_parse_bracket_blocks` handle parsing)*
- [x] Hide internal `%%`-section markers from the player in non-dev mode. *(`_stream_with_narrative_filter` wraps the raw SSE token stream; dev mode passes all tokens, non-dev streams only `%%NARRATIVE%%` content and stops at the next section marker)*

## NPC Lifecycle and Knowledge

- [x] Write structured NPC deltas per turn with multi-line knowledge support. *(`%%DELTAS%%` section uses bracket blocks, one per NPC; `knowledge:` lines collected as a list; `_write_npc_delta` helper extracted)*
- [x] Auto-create NPC stub when a `%%DELTAS%%` block references an unknown NPC (Layer 2 fallback). *(if `npc_dir_for` returns `None`, `_process_generate_block` is called with stub data before writing the delta)*
- [x] Detect NPCs introduced in narrative text without any structured block (deferred Layer 3). *(`_detect_narrative_npcs` scans completed narrative for Title Case name pairs, adds to `session.scene_npcs`; stub creation is deferred until the model writes a `%%DELTAS%%` block for that name)*
- [ ] Promote auto-created session NPCs to permanent records via a lightweight review workflow (currently requires manual file edit to remove the `session_npc:` flag).
- [ ] Surface the list of detected-but-not-yet-stubbed names from `scene_npcs` somewhere visible (log or UI) so the GM can verify the model caught them.

## Knowledge and State Management

- [ ] Plan message history summarization to prevent the API payload from growing unbounded across long sessions.
- [ ] Standardize the schema for character knowledge, NPC memory, session recap, and emergent canon so state can be updated automatically.
- [ ] Create a clear source-of-truth rule for contradictions between session notes, recap files, NPC logs, and JSON outputs.
- [ ] Add validation checks for continuity drift such as wrong deity, alignment, class, or duplicated features across player records.
- [ ] Decide which state should live in markdown and which should live in structured JSON for UI and automation.

## Character Data and UI Content

- [ ] Normalize all player JSON files to one agreed UI schema and keep them synchronized with the markdown sheets.
- [ ] Audit Ani's data and other player records for internal inconsistencies before relying on them in UI or prompts.
- [ ] Add a small sync tool or documented workflow for copying approved sheet changes into UI JSON files.
- [ ] Review portraits, colors, runes, and labels so presentation data is consistent across all characters.

## Runtime and Tooling

- [ ] Harden backend startup further so orphaned Python child processes and stale listeners are detected and cleaned consistently on Windows.
- [x] Fix the UI startup path and determine why `npm run dev` is currently failing. *(was a port conflict — pinned Vite to port 5173 with `strictPort: true`)*
- [x] Add one command that boots backend and UI together for local development. *(`python dev.py` — runs tests, then starts API + UI; `--skip-tests` flag to bypass)*
- [ ] Document the exact local startup and recovery workflow for Windows, including port cleanup and Ollama checks.

## Quality and Testing

- [x] Add validation for prompt inputs and generated outputs before they are written to session artifacts.
- [x] Add focused tests for boot prompt assembly, file loading, and checklist verification.
- [x] Add regression tests for session-start context resolution and previous-session note discovery.
- [x] Add smoke tests for loading character JSON in the UI.
- [x] Test `_parse_response_sections` and `_parse_bracket_blocks` against representative LLM output shapes, including fallback-to-no-markers and multi-knowledge-line cases.
- [x] Test `_stream_with_narrative_filter` — dev passthrough, narrative extraction, all three stop markers, holdback buffer, old-format fallback, split-token marker detection, and non-token event passthrough.
- [x] Test Layer 2 NPC auto-stub creation and index re-validation after stub write.
- [x] Test `_detect_narrative_npcs` — unknown name added to `scene_npcs`, no stub created, exclude-word filtering, already-tracked and already-indexed names skipped, short sentence-starters skipped.
- ~~[ ] Test deferred context injection timing — verify each chunk lands on the correct turn and that the system prompt grows in the expected order.~~ *(obsolete — `context_queue` and deferred injection removed)*
- [ ] Test the full end-session SSE stream with mocked Ollama — verify status events arrive in order, recap and boot files are written, and the session is removed from memory. *(critical)*
- [ ] Test turn input validation at the API boundary — confirm the error event is returned and no message is appended to session history when input is rejected. *(high)*
- ~~[ ] Test that dev mode uses the short system prompt and ignores all deferred context files regardless of what exists on disk.~~ *(obsolete — deferred context files no longer exist; dev mode is now about the stream filter, which is tested)*
- [ ] Test `_enforce_recap_header` against real LLM output samples collected from past sessions to catch title/date extraction edge cases. *(high)*
- [ ] Test the roll endpoint writes the correct expression and total to the log, including multi-die breakdowns (e.g. 3d6 showing individual rolls). *(low)*
- [ ] Add a test fixture representing a corrupt or partially-written log file and assert the parser either recovers gracefully or raises a clear error. *(low)*
- [ ] Add contract tests for the SSE event shape — assert that every event emitted by boot, turn, and end-session has a `type` field and matches the known union of types. *(low)*

## Ollama Review Questions

- [ ] Measure first-token latency and total response time for boot and normal turns.
- [ ] Measure prompt adherence across boot, rules adjudication, and recap generation.
- [ ] Compare local Ollama against at least one hosted model path for reliability and maintenance overhead.
- [ ] Decide whether different tasks should use different models rather than one model for all work.

## Nice-to-Have

- [ ] Build a small admin view for inspecting session state, NPC memory, and pending continuity updates.
- [ ] Add diff-friendly generated outputs so session-to-session changes are easier to review.
- [ ] Create a lightweight issue triage process for rules bugs, lore bugs, UI bugs, and prompt bugs.
