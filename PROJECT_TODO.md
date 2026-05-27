# Project Todo

This file is a working backlog for the RotRL automation project. Items are grouped by area and ordered roughly by impact.

## High Priority

- [ ] Update player character knowledge files after each session so each PC only retains facts they actually learned in play.
- [ ] Update NPC knowledge and memory state after each session, including attitude shifts, known facts, suspicions, and unresolved goals.
- [ ] Refine LLM answers so GM output is shorter, cleaner, and more mechanically grounded under pressure.
- [ ] Evaluate whether Ollama should remain the serving layer by comparing latency, determinism, prompt adherence, operational cost, and recovery behavior against alternatives.

## GM and Session Flow

- [ ] Split boot-time context from active-play context so the first prompt loads only critical rules and immediate continuity.
- [ ] Wire a true normal-session path instead of routing every start through the full boot pipeline.
- [ ] Reduce duplicate verification work in boot, especially where a second LLM call can be replaced with deterministic checks.
- [ ] Make player identity loading consistent across code paths; current boot logic still expects some optional files in different locations than the repo uses.
- [ ] Define a post-session pipeline that writes recap, continuity, PC knowledge, and NPC state in one consistent pass.

## Knowledge and State Management

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
- [ ] Fix the UI startup path and determine why `npm run dev` is currently failing.
- [ ] Add one command that boots backend and UI together for local development.
- [ ] Document the exact local startup and recovery workflow for Windows, including port cleanup and Ollama checks.

## Quality and Testing

- [x] Add validation for prompt inputs and generated outputs before they are written to session artifacts. *(critical)*
- [x] Add focused tests for boot prompt assembly, file loading, and checklist verification. *(critical)*
- [x] Add regression tests for session-start context resolution and previous-session note discovery. *(critical)*
- [x] Add smoke tests for loading character JSON in the UI. *(high)*
- [ ] Test deferred context injection timing — verify each chunk lands on the correct turn and that the system prompt grows in the expected order. *(critical)*
- [ ] Test the full end-session SSE stream with mocked Ollama — verify status events arrive in order, recap and boot files are written, and the session is removed from memory. *(critical)*
- [ ] Test turn input validation at the API boundary — confirm the error event is returned and no message is appended to session history when input is rejected. *(high)*
- [ ] Test that dev mode uses the short system prompt and ignores all deferred context files regardless of what exists on disk. *(high)*
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