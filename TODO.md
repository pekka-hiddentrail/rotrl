# Project Todo

This file is a working backlog for the RotRL automation project. Items are grouped by area and ordered roughly by impact.

**Every time this file is updated, sections with the most open items should be at the top; sections that are fully checked off should be at the bottom. Within each section, open items come first, done items in the middle, and "obsolete" items at the bottom.**

## Markup rules (follow these exactly when adding items)

- `- [ ] Item text` — open task
- `- [x] Item text` — completed task
- `- ~~[ ] Item text~~` — obsolete / cancelled task
- Sub-bullets under a task use the same `- [ ]` format, indented two spaces
- **Never** use plain `-` bullets for tasks — everything actionable must have a checkbox
- Bold the item title when it has a longer description below it

---

## Bugs

> All known bugs live in **[BUGS.md](BUGS.md)**. Open items: B-C02, B-C03b, B-C04, B-C05, B-Q01.

---

## Quality and Testing

- [ ] **Write `specs/action-economy.feature`** — the action type picker (Standard/Move/Full-Round buttons in InputBar, `action_type_hint` POST field, `_HINT_TO_ACTION_TYPE` backend map) shipped without a spec file. Add ACs covering: (1) buttons only visible on PC combat turn; (2) selecting a type sends correct `action_type_hint` in POST body; (3) hint overrides keyword inference; (4) toggle-off by re-clicking; (5) reset on turn advance and on send. Until the spec exists the feature has zero AC coverage in the coverage matrix.
- [ ] Rewrite the token test. The combat is more complex now and the current implementation is very different from the test.
- [ ] **Update `specs/INDEX.md` and `README.md` test table for `feat/initiative-roller`** — AC count in `specs/INDEX.md` and the test-count table in `README.md` need updating after the roll-initiatives spec (9 ACs) and test files (18 pytest + 8 Vitest) landed.
- [ ] **Add AC-009 App wiring test** — `handleRollInitiatives` in `App.tsx` has no Vitest test; mock `rollInitiatives` from `api.ts` and assert `setCombatState` and `setCurrentCombatantName` are called with the response values. *(spec: roll-initiatives.feature AC-009)*
- [ ] **Remove dead `or True` assertion in `test_roll_initiatives.py`** — `assert session.combat_state.combatants[0].initiative != 99 or True` always passes; the actual coverage is in the loop below it. *(tests/test_roll_initiatives.py `TestInactiveCombatantsRolled`)*
- [ ] **Clarify `attackPhase` disable for Roll Initiatives button** — spec AC-008 does not list `attackPhase` as a disable condition; rerolling mid-attack would be disruptive. Decide and update spec or add to `controlsDisabled`. *(spec: roll-initiatives.feature AC-008)*
- [ ] **Generate HTML coverage heatmap** — combine code line coverage and feature AC coverage into one visual; dark = no tests, red = code covered but no AC, green = both
- [ ] **Define risk register** — identify high-risk areas (LLM compliance, session state loss, data corruption); map each risk to covering tests or flag as gap
- [ ] **Spike: agent-driven exploratory test harness** — one LLM plays as player (sends PF1e actions via the live SSE API), a second evaluates each GM response against a rubric (no leaked markers, narrative length, no invented lore)
- [ ] Test the full end-session SSE stream with mocked Groq — verify status events arrive in order, recap and boot files are written, and the session is removed from memory. *(critical — error paths covered in `test_end_session.py`; success path not tested)*
- [ ] Test turn input validation at the API boundary — confirm the error event is returned and no message is appended to session history when input is rejected. *(high — `validate_turn_input()` tested in isolation in `test_boot_prompt.py`; HTTP boundary + history-not-appended not tested)*
- [ ] Test `_enforce_recap_header` against real LLM output samples collected from past sessions to catch title/date extraction edge cases. *(low — synthetic coverage in `test_recap_header.py` is solid; real-sample gap is narrow)*
- [ ] Test the roll endpoint writes the correct expression and total to the log, including multi-die breakdowns (e.g. 3d6 showing individual rolls). *(low — single-die case covered in `test_roll_logged`; multi-die breakdown not tested)*
- [ ] **Live Playwright — dice roller scenario coverage** — extend `ui/e2e/live-flows.spec.ts` with dedicated dice scenarios against a real booted session: (1) basic multi-die queue (2d6+1d20) rolls and result appears in history; (2) auto-bonus applies when active character has a matching skill modifier; (3) auto-bonus absent when toggle is OFF; (4) pending roll banner clears after resolve and PASSED/FAILED badge appears; (5) history cap at 10 rolls — 12th roll evicts the oldest entry; (6) roll-while-streaming is blocked — send button disabled during GM response.
- [ ] **Skill-use rules for trained-only skills** — define and enforce when a PC can attempt skill checks they do not have trained. Knowledge skills should follow PF1e trained-only behavior where appropriate; if a character lacks the relevant Knowledge skill, fall back to an untrained general ability check only for common information, likely INT-based with a higher DC (for example +10), and make the GM state the limitation instead of silently granting full expert knowledge.
- [x] **Fix DiceTrayAttack V8 test — modifier extraction added after test was written** — `handleDamageRollClick` now extracts the `+N` modifier from `damage_expr` (e.g. `1d8+3` → mod=3) and adds it to the raw roll total before calling `onDamageRoll`. Test `V8` was asserting `([5], 5)` (no modifier); corrected to `([5], 8)` to match `roll=5 + mod=3`. *(ui/src/components/__tests__/DiceTrayAttack.test.tsx)*
- [x] **Add pytest-cov to backend** — generate per-file line coverage report; identify untested paths in streaming and fallback parsers. **Done:** `pytest-cov>=4.0.0` in requirements; `.coveragerc` (source=api, show_missing, json→outputs/code_coverage.json); `GET /api/code-coverage` endpoint; "Code Lines" tab added to the Coverage modal showing per-file bars, %, and missing line numbers.
- [x] **Build feature coverage matrix** — map each of the 178 spec ACs to the test(s) that cover it; flag ACs with zero test coverage. **Done:** `scripts/build_coverage.py` reads all `specs/*.feature` files and all test suites (pytest / Vitest / Playwright), writes `outputs/coverage.json` (45/178 covered, 133 gaps as of first run). `GET /api/coverage` serves the data. `CoverageMatrix.tsx` modal opens from a "Coverage" button in the header — filterable by feature and by gap status. Spec: `specs/coverage-matrix.feature` (6 ACs).
- [x] Add a test fixture representing a corrupt or partially-written log file and assert the parser either recovers gracefully or raises a clear error. *(low)*
- [x] Add contract tests for the SSE event shape — assert that every event emitted by boot, turn, and end-session has a `type` field and matches the known union of types. *(low)*
- [x] **E2E — Playwright UI test suite** — add Playwright to `ui/` (`npm install -D @playwright/test`). Cover the seven key flows with a mocked backend (MSW or a lightweight FastAPI fixture): (1) boot → session badge appears; (2) send turn → GM message streams in; (3) `roll_request` event → Dice Tray activates; (4) end session → chat clears; (5) Kill button on stuck ending → inline confirm → UI resets to pre-boot; (6) Purge NPCs button → inline confirm → toast notification; (7) character sidebar → sheet modal opens. These are the regression cases that break silently on UI refactors and are invisible to pytest. *(`ui/e2e/app-flows.spec.ts`; `ui/playwright.config.ts`; `npm run test:e2e` — 7 Playwright tests passing.)*
- [x] **Vitest — Character data and sheet AC coverage** — add tests for `character-system.feature` AC-001 through AC-006 and remaining AC-010/AC-011 integration: static JSON loading/failure, HP bar colors, sheet modal close behavior, stat/spell tooltips, spell grouping, active speaker persistence, and backend payload prefixing in `App` (bubble content display is covered by `player-bubble-speaker.feature` tests). *(`characters.test.tsx`; `CharacterSidebarHealth.test.tsx`; `CharacterSheet.test.tsx`; `App.test.tsx` speaker integration.)*
- [x] **Vitest — Header/session controls AC coverage** — add tests for `session-controls.feature` AC-001 through AC-008 plus `llm-providers.feature` AC-001/AC-005: provider/model switching, pre/post-boot control visibility, boot disabled state, View Log target, purge inline confirm/toast, rate-limit badge, and Kill inline confirm/abort reset. *(`Header.test.tsx`; App-level View Log/Purge/Kill/provider tests.)*
- [x] **Vitest — Chat and turn UI AC coverage** — add tests for `chat-display.feature` AC-001 through AC-006 and `player-turn.feature` AC-001/AC-005: immediate player bubble, thinking indicator, token append/cursor, intro markdown rendering, autoscroll, streaming disabled state, and end-session status bubble updates. *(`ChatWindow.test.tsx`; expanded `App.test.tsx` streaming tests.)*
- [x] **Vitest — IntentBar AC coverage** — add component tests for `intent-bar.feature` AC-001 through AC-005: 52-character truncation, NPC/skill/location tags, null tags, detecting state, and no-context-event diagnostic. *(`IntentBar.test.tsx`.)*
- [x] **Vitest — App SSE integration smoke tests** — 19 tests across 3 describe blocks in `ui/src/__tests__/App.test.tsx`. Covers: boot intro/session setup (6), send-turn event order — `context`, `token`, `patch_last`, `roll_request`, `rate_limits`, error bar, second-send clears error (8), and session end cleanup — ending bubble, status event, done→"Session saved."→cleanup, error path (4+1). Key patterns: `makeStalledGen` for intermediate-state observation; `vi.spyOn(setTimeout)` to shorten the 1800 ms hold without fake-timer/`act` conflicts; `useCharacters` + `fetch` stubbed in every test.
- [x] **pytest — session state `combatants` coverage** — `test_session_state.py` extended to cover the `combatants` field introduced in the session-state schema: `TestTemplate` checks all 5 required keys and defaults (including `active_character` and `combatants`); `TestBootInit` asserts `combatants: []` on fresh write; `TestCombatantsSerialization` (5 new tests) covers all fields present, HP-after-damage, multiple combatants, and clear-to-empty; `TestOutputValidity` and `TestBootOverwrite` updated to assert `combatants` key is always present. 42 tests total. Template (`sessions/state.template.json`) and spec (`specs/session-state.feature`) updated to match. *(spec: session-state.feature AC-001, AC-004, AC-006, AC-011, AC-012)*
- [x] **Vitest — DiceTray AC coverage** — add component tests for `dice-tray.feature` AC-001 through AC-011: queue accumulation, roll history limit/latest highlight, `/roll` payload, pending roll banner, `/resolve_roll` pass/fail handling, auto skill bonus, raw-roll fallbacks, toggle persistence, and normalized skill lookup.
- [x] Document Vitest setup, commands, and current UI component tests. *(`README.md`; `ui/vitest.config.ts`; `ui/src/test/setup.ts`; `ui/src/components/__tests__/InputBar.test.tsx` and `CharacterSidebar.test.tsx` — 30 tests)*
- [x] Add validation for prompt inputs and generated outputs before they are written to session artifacts.
- [x] Add focused tests for boot prompt assembly, file loading, and checklist verification.
- [x] Add regression tests for session-start context resolution and previous-session note discovery.
- [x] Add smoke tests for loading character JSON in the UI.
- [x] Test `_parse_response_sections` and `_parse_bracket_blocks` against representative LLM output shapes, including fallback-to-no-markers and multi-knowledge-line cases. *(`tests/test_response_sections.py` — 27 tests)*
- [x] Test `_stream_with_narrative_filter` — dev passthrough, narrative extraction, all three stop markers, holdback buffer, old-format fallback, split-token marker detection, and non-token event passthrough.
- [x] Test Layer 2 NPC auto-stub creation and index re-validation after stub write.
- [x] Test `_detect_narrative_npcs` — unknown name added to `scene_npcs`, no stub created, exclude-word filtering, already-tracked and already-indexed names skipped, short sentence-starters skipped.
- [x] `api/api_logger.py` — zero coverage. *(`tests/test_api_logger.py` — 12 tests: file creation, filename format, JSON structure, usage field, message summary, preview truncation)*
- [x] Groq provider `_groq_post` and `_stream_groq` — minimal coverage. *(`tests/test_groq_provider.py` — 15 tests: 429 retry, header parsing, backoff, max-history, streaming, rate-limit SSE event, stream_options 400 fallback)*
- [x] Skill lookup `detect()` and `lookup()` — minimal coverage. *(`tests/test_skill_lookup.py` — 21 tests)*
- [x] NPC lookup `detect_all()`, `npc_dir_for()`, `lookup()` — minimal coverage. *(`tests/test_npc_lookup_extended.py` — 26 tests)*
- [x] `GET /api/log/api` and `GET /api/log/api/{filename}` endpoints — no tests. *(`tests/test_api_logs.py` — 10 tests including path traversal case)*
- [x] `_parse_turns_from_log()` edge cases and `stream_end_session()` error paths — no tests. *(`tests/test_end_session.py` — 18 tests)*
- ~~[ ] Test deferred context injection timing — verify each chunk lands on the correct turn and that the system prompt grows in the expected order.~~ *(obsolete — `context_queue` and deferred injection removed)*
- ~~[ ] Test that dev mode uses the short system prompt and ignores all deferred context files regardless of what exists on disk.~~ *(obsolete — deferred context files no longer exist; dev mode is now about the stream filter, which is tested)*

---

## Adventure Content

The adventure is ~80% narrative infrastructure and ~20% mechanical execution. The items below are what's missing before a real session can run without the GM improvising from nothing. Priority order: things that block the first session come first; things that enrich later sessions come last.

### Act I — Swallowtail Festival (levels 1–2)

- [x] **Act I event chain — full rewrite** — `adventure_path/02_events/` now contains the complete Act I chain (9 events) replacing the old flat EC-* encounter stubs. Pre-combat social phase: `welcoming_speeches` (four speakers with full scripted speeches), `festival_social_phase` (games, swallowtail release with Desna parable, lunch with Ameiko, Aldern first meeting), `cathedral_alarm` (thunderstone moment, transition to CRISIS). Goblin raid: `goblin_attack_starts` (3 warriors, 5 named zones, civilian family, AI tactics, appearance, taunts), `first_wave_repelled` / `second_wave_repelled` (social breathers), `fire_phase_begins` (warchanter + arsonists, surprise check, arson countdown, morale), `goblin_cavalry_attack_begins` (single commando + goblin dog, Aldern at well), `attack_repelled` (full aftermath — Zantus, Hemlock, Aldern, Ameiko, deltas, level 2 milestone). Templates: `_EVENT_TEMPLATE.md` (combat) and `_SOCIAL_TEMPLATE.md`; `INDEX.md` with full chain map. `ACT_01_OVERVIEW.md` updated to reference event files.
- [x] **Goblin dog bestiary entry** — `adventure_path/09_bestiary/goblin_dog.md` created with correct PF1e stats: HP 9, AC 13, bite +2 (1d6+3 plus Allergic Reaction — Fort DC 12 or –2 Dex/Cha for 1 day, disease effect, non-stacking), immune to disease, Speed 50 ft. Corrects the old EC-COMBAT-03 stats which had wrong HP (14) and wrong effect (Goblin Pox).
- [x] **Festival encounter sequence** — superseded by the event chain rewrite above. Old EC-COM-01 through EC-SUP-01 stubs deleted; content absorbed and expanded into the 02_events/ chain.
- [x] **Aldern Foxglove introduction** — `base.md` verified complete (rescue hook, hunting trip, estate reference present); `knowledge.md` exists as session tracking log (correct format); backstory seed content lives in `base.md`.

### Act II — Shadows in Sandpoint (levels 2–3)

- [ ] **Catacombs of Wrath — dungeon document** — `CATACOMBS.md` created: 7-room prose layout, 5 sinspawn encounters, Runewell chamber with cross-reference to LOCATIONS.md, full treasure and XP tables, Karzoug name drop in Room 2, Sihedron Rune callback in Room 7.
- [ ] **Glassworks investigation sequence** — `GLASSWORKS.md` created: three entry hooks, room-by-room layout (main floor/office/upper floor), Tsuto encounter, Ameiko rescue, journal content, Catacombs entrance discovery, full aftermath.

### Act III — Thistletop (levels 3–4)

- [ ] **Thistletop — dungeon document** — `THISTLETOP.md` created: Nettlewood approach, rope bridge mechanics, full surface level (throne room, barracks, guard post, stables, trapdoor), Thassilonian level (entry passage sinspawn, Lyrie's library, yeth hound corridor, Nualia's sanctum, Runewell chamber), clearing conditions, Ameiko aftermath beat.



### Secondary NPCs

The existing "Sandpoint NPC skeletons" backlog item is correct but needs priority ordering. The 70+ secondary NPCs referenced in SANDPOINT_LOCATIONS.md have no `01_npcs/` files. Do these in tiers:

- [ ] **Tier A — encounter anchors** (players will meet these in Act I regardless of what they do): Naffer Vosk (boneyard groundskeeper — relevant when PCs investigate the Tobyn crypt), Brodert Quink (town sage — the only person who can explain Thassilonian runes), Savah Bevaniky (armory — equipment, Act I context), Risa Magravi (Hagfish tavern — rumours, Sczarni colour), Shayliss Vinder (General Store — Ven Vinder subplot). Write `base.md` for each: name, role, one-sentence personality, location anchor, and what they know that's plot-relevant.
- [ ] **Tier B — district colour** (players will encounter if they explore): Hannah Velerin (healer, White Deer district), Das Korvut (blacksmith, grief subplot), Ven Vinder (General Store owner, protective father), Banny Harker (lumber mill, Act II body discovery), Ibor Thorn (lumber mill partner). Same format as Tier A.
- [ ] **Tier C — background presence** (can be invented on demand but benefit from anchors): remaining shop owners, militia deputies, festival vendors. Batch these as a single lightweight file `adventure_path/01_npcs/_SANDPOINT_SECONDARY.md` listing name/role/location for each — not full base.md files, just enough to prevent contradiction.

### Location Coverage

- [ ] **Brodert Quink's home/study** — add `adventure_path/03_locations/quinks_house/base.md`. Players will go here to research Thassilonian runes in Act II. Needs: description (crowded with maps and artifacts), what he can tell them (Sihedron Rune meaning, Thassilon's sin-magic system), and what he doesn't know (the Runewell's current state). The knowledge injection makes this a much richer scene than the LLM improvising a generic scholar.
- [ ] **The Hagfish** — add `adventure_path/03_locations/hagfish/base.md`. Risa's tavern is the rough-end counterpart to the Rusty Dragon — different social class, Sczarni presence, rumour economy. Players will contrast the two inns early. Aliases: hagfish, risa's, the fish.
- [ ] **Sandpoint Mercantile League / Valdemar Building** — add `adventure_path/03_locations/sandpoint_mercantile/base.md`. Economic power centre; the Valdemars and Scarnettis matter for faction pressure in Act II.
- [ ] **Remaining high-traffic locations** — audit SANDPOINT_LOCATIONS.md and create `base.md` files for the next 5–8 buildings players are most likely to enter: General Store (Vinder's), Cathedral Rectory, Fatman's Feedbag, Town Hall interior, and the Jail. Each follows the existing template.
- [ ] **Magnimar — Act II arrival districts** — three location files for when the party travels to the city: (1) `magnimar_dockway/base.md` (arrival point, rough district, Sczarni presence); (2) `arvensoar/base.md` (city watch HQ, where to report the Tsuto situation); (3) `irespan_pilings/base.md` (undercity access relevant to the Shadow Clock investigation). Aliases, descriptions, and current-state following the existing seed-location format.

### Skill Files

- [x] **Expand skill coverage beyond the current five** — Added 17 skill files total: original 5 (Bluff, Diplomacy, Intimidate, Perception, Sense Motive) + 8 Knowledge/Stealth (Knowledge (Local), (Religion), (History), (Planes), (Arcana), (Nature), (Nobility), Stealth) + 4 Act I utility skills (Heal, Survival, Acrobatics, Disable Device). All RAW-complemented with `<!-- REFERENCE -->` separator. `_SKILL_TEMPLATE.md` updated with multi-table, condition modifier, fail-by-X, and Restriction section patterns. `SkillIndex` auto-discovers all files; no code changes needed.
- [x] **Knowledge (history) and Knowledge (planes)** — Both added. Knowledge (Planes) covers outsiders (removed from Religion); Knowledge (History) covers Thassilonian lore. Both include 10+CR creature identification tables and library exception for untrained use.

### Session Pacing

- [ ] **XP award table for Act I** — `adventure_path/06_books/BOOK_01_BURNT_OFFERINGS/XP_AWARDS.md`: each encounter's CR, base XP, party-size adjustment (3 PCs), and bonus XP conditions (Aldern rescue = 400 bonus XP, Tsuto non-lethal = +100 XP). The LLM uses this table when deciding what to emit in `%%XP%%` blocks. Include running totals so it's clear when the party should hit level 2 (after the Glassworks) and level 3 (after Thistletop ground floor).
- [ ] **Level 2 and 3 PC advancement** — for each PC: HP gain (die + CON modifier), new class features (fighter bonus feat, cleric channel energy increase, ranger combat style), skill point allocation, updated saves. Store in `adventure_path/00_system_authority/ADVANCEMENT.md`. Needed before Act II runs so the GM can narrate leveling accurately. The LLM should prompt the player to level up when XP threshold is crossed.
- [ ] **Encounter budget per session** — document in ACT_STRUCTURE.md: Act I is approximately 2–3 sessions (festival attack + aftermath + investigation hook). Act II is 3–5 sessions depending on Catacombs depth. Act III is 2–4 sessions for Thistletop. Knowing this prevents the LLM from burning through an act in a single exchange or dragging it over ten.
- ~~[ ] **Session zero checklist** — create `adventure_path/06_books/BOOK_01_BURNT_OFFERINGS/SESSION_ZERO.md`. What the GM needs before session 1: player character files loaded, session 1 boot file prepared, leveling milestones known, faction pressures initialised at 0. This is a pre-flight checklist, not rules content.~~

---

## GM and Session Flow

- [ ] **Session pacing controls** — a GM-only text field (hidden from players) that injects a private directive into the next turn's system prompt: "Wrap up this scene in one response", "Skip ahead to next morning", "Something urgent interrupts". Injected as `[GM DIRECTIVE — PRIVATE]` above the normal per-turn directive, stripped from the player token stream. Essential for keeping sessions on schedule when a scene runs long.
- [ ] **Player handouts** — `%%HANDOUT%%` block for the LLM to emit important in-world documents: Tsuto's journal, the Sihedron Rune diagram, letters, crude maps. Saved to `outputs/handouts/{slug}.md`. A "Handouts" button in the Tools dropdown opens a panel listing all collected documents, clickable to read in full. Key RotRL handouts: Tsuto's journal (Act II entry point), the ritual notes in the Catacombs, Nualia's letter to Tsuto.
- [ ] **Second-pass prompt token reduction** — turn 1 currently lands at ~1609 tokens (target was ~1235). Three levers identified: (1) boot.md "Who Is Present" NPC blurbs (~80 tokens) — redundant once NPC context injection fires on first mention; trim to name + location only. (2) EVENT MAP descriptions (~120 tokens) — shorten per-event trigger phrases to one clause each. (3) `_FORMAT_EXAMPLE` (~400 tokens) — drop one of the two `%%DELTAS%%` blocks in the example; single block is sufficient to teach the format. Do after session 1 is stable in production.
- [ ] **DC sourcing in the GM directive** — when both an NPC and a skill are detected on the same turn, `_build_turn_directive` should explicitly instruct the model to derive the DC from the NPC's stats and disposition (injected profile) and use the skill file only as a baseline range. Currently the model has both in context but receives no instruction to combine them, so it often falls back to generic skill-file DCs regardless of who the player is dealing with.

- [ ] **Per-character skill ability overrides** — some PC traits replace the governing ability for a specific skill. `_inject_context` skill detection currently injects the raw skill file which assumes the PF1e default ability (e.g. Knowledge (planes) → INT). When the character has an override trait, the injected briefing and any auto-roll bonus must use the character's actual governing ability, not the file default. Known overrides: **Planar Savant (Yanyeeku, Vanx)** — Knowledge (planes) uses CHA (+6) not INT (+1). Without this, any system-generated roll suggestion or DiceTray auto-bonus for Knowledge (planes) will be off by 5 for these two characters. Implementation: add an `ability_overrides: dict[str, str]` field to `pc_profiles` at boot time, populated from the character's traits list; `_inject_context` checks this map when constructing the skill briefing for a detected skill.
- [x] Make player identity loading consistent across code paths; current boot logic still expects some optional files in different locations than the repo uses.
- [ ] **Groq: per-call-type model routing** — when provider is Groq, use `llama-3.3-70b-versatile` for the two blocking `stream_end_session()` calls (recap + boot brief) and `llama-3.1-8b-instant` for normal turns. Requires a model-override parameter threaded through `_stream_groq`; the UI model dropdown stays decoupled. Not applicable to Anthropic — model is set at session boot and applies uniformly.
- [ ] Fix prompt spec gaps — three small changes to `_build_slim_system_prompt`: (1) add `personality:` field to `%%GENERATE%%` block spec (code already reads it, model never writes it); (2) add "skip `%%GENERATE%%` for NPCs already in the scene" rule; (3) add "at most one `%%ROLL%%` block per response" constraint.
- ~~[ ] **Load `00_system_authority/` files into the system prompt** — CORE BEHAVIOR and GM STYLE are hardcoded strings in `_build_slim_system_prompt()`; tuning them requires editing Python. Replace with file loading: `ADJUDICATION_PRINCIPLES.md` → CORE BEHAVIOR block at boot; `PF1E_RULES_SCOPE.md` (payload section only, above `<!-- REFERENCE -->`) → GM STYLE block at boot. `COMBAT_AND_POSITIONING.md` → inject per-turn via `_inject_context` alongside `_COMBAT_FULL_SPEC` when combat is active. Caution: files must stay at or below current token budgets — don't let file loading silently bloat the static prompt. `PERSISTENCE_HANDLING_RULES.md` and `SESSION_NOTES_PROTOCOL.md` are reference-only (no action needed).~~
- [x] Move the format example below a `<!-- REFERENCE -->` marker in the system prompt — extracted to `_FORMAT_EXAMPLE` constant; injected dynamically on the first player turn only (`len(session.messages) == 1`). Absent from all subsequent turns. *(done — different approach than <!-- REFERENCE --> but same effect)*
- [x] **Audit and trim system prompt — target sub-1500 tokens** — static base prompt trimmed to ~900 tokens; dynamic fragments injected only when needed. GM STYLE compressed (7→4 lines), SCENE EVENT rules compressed, COMBAT TRACKER reduced to a compact one-liner in the static prompt. Format example (`_FORMAT_EXAMPLE`) extracted as a constant and injected on the first player turn only. Full combat spec (`_COMBAT_FULL_SPEC`) extracted and injected per-turn only when `combat_state.round > 0`. Section specs (`_NARRATIVE_SPEC`, `_ROLL_SPEC`, `_GENERATE_SPEC`, `_DELTAS_SPEC`) moved from static to per-turn injection gated on detection (ROLL only when skill detected; DELTAS only when NPCs present). PC profile injection: two-tier profiles built at boot from `ui/public/data/player_*.json`; narrative tier injected when PC named, mechanical tier added when skill also detected. 37 new tests across `test_boot_prompt.py` and `test_inject_context.py`. *(specs: `system-prompt.feature` AC-007 through AC-010)*
- [x] Move example response block (Gerhard Pickle / Bottled Solutions) — extracted to `_FORMAT_EXAMPLE` constant; injected only on first player turn (`len(session.messages) == 1`)
- [x] Collapse `%%GENERATE%%` / `%%DELTAS%%` field descriptions — `← omit if unsure` comments removed; field specs tightened to one-liner format
- [x] Compress `%%ROLL%%` and `%%COMBAT%%` block specs — `%%ROLL%%` reduced to one bracket block; `%%COMBAT%%` reduced to a two-line reference in the static prompt; full spec injected via `_COMBAT_FULL_SPEC` when active
- [x] Move GM STYLE bullet list — compressed from 7 bullets to 4 concise lines in the static prompt
- [x] Move knowledge tag list — inlined into the `%%DELTAS%%` one-liner spec
- [x] Refine LLM output so GM responses are shorter, cleaner, and more mechanically grounded under pressure.
- [x] Split skill files into GM payload and reader reference sections. *(`<!-- REFERENCE -->` separator added to all five skill files; `_parse_skill_file` stops at the marker — payload ~26–39% smaller per injection, reader docs preserved below the line.)*
- [x] Set Groq as the default provider in the GUI; default model `llama-3.1-8b-instant`; dev mode off by default. *(dev mode with Groq only shows `%%` markers — the dev system prompt strips the full structured format, so leaving it on breaks `%%DELTAS%%` etc.)*
- [x] Split boot-time context from active-play context so the first prompt loads only critical rules and immediate continuity. *(`context_queue` removed; per-turn keyword RAG injection replaces it)*
- [x] Wire a true normal-session path instead of routing every start through the full boot pipeline. *(boot makes no LLM call; first GM response fires on the player's first turn)*
- [x] Reduce duplicate verification work in boot, especially where a second LLM call can be replaced with deterministic checks. *(boot LLM call eliminated entirely; delta extraction moved from second Groq call to parsed `%%DELTA%%` block)*
- [x] Define a post-session pipeline that writes recap, continuity, PC knowledge, and NPC state in one consistent pass. *(`stream_end_session` writes recap + next-session boot file; NPC deltas written per-turn; PC knowledge update still pending)*
- [x] Enforce a structured response template so the LLM writes `%%NARRATIVE%%`, `%%ROLL%%`, `%%DELTAS%%`, and `%%GENERATE%%` sections consistently. *(`_build_slim_system_prompt` now includes a `RESPONSE STRUCTURE` block with the full template; `_parse_response_sections` + `_parse_bracket_blocks` handle parsing)*
- [x] Hide internal `%%`-section markers from the player in non-dev mode. *(`_stream_with_narrative_filter` wraps the raw SSE token stream; dev mode passes all tokens, non-dev streams only `%%NARRATIVE%%` content and stops at the next section marker)*

---

## Knowledge and State Management

- [ ] **XP tracking** — `%%XP%%` block emitted by the LLM after encounters or awarded manually. Backend appends to `outputs/xp_log.md` and updates `session.xp_total`. Display as a progress bar per PC in the character sidebar showing current XP vs next-level threshold (PF1e medium track: 0 → 2000 → 5000 → 9000 → 15000). Party XP is shared; all PCs level at the same time.
- [ ] **Campaign world state** — `outputs/world_state.json` tracking binary flags: enemy status, location visited, key event fired. Updated via `%%STATE%%` blocks. Injected as a compact `[WORLD STATE]` block when relevant. Prevents the LLM from resurrecting killed enemies or revisiting un-entered locations. Key flags for Book I: `nualia_dead`, `tsuto_captured`, `catacombs_cleared`, `glassworks_secured`, `sinspawn_dormant`.
- [ ] **In-world time tracking** — `current_date` field in `world_state.json` starting at Rova 23, 4707 AR (Swallowtail Festival). Incremented by `%%TIME%%` blocks (e.g. `%%TIME%% +1d`) or automatically at session end. Injected into the system prompt so the LLM can reference "two days after the festival" or the current month. Required for: Hemlock's departure to Magnimar timing, Nualia's schedule at Thistletop, seasonal weather, and dating session logs.
- [ ] **Loot and treasure log** — `%%LOOT%%` block emitted after encounters and discoveries. Backend appends to `outputs/loot_log.md`: session number, turn, item description, finder. No inventory management — just an append-only record the players can reference. Key RotRL items to track: Tsuto's masterwork equipment, the +1 shortbow from Ripnugget, Nualia's ranseur, Runewell fragment.
- [ ] **PC session delta / recent activity** — PCs currently have no equivalent of the NPC delta system. The LLM has no machine-readable record of what each PC was doing moments before the current turn (who they were talking to, what skill they just used, where they moved). Add a `pc_delta` field per PC in session state — a short structured summary of recent activity (last action, current goal, last interacted NPC, last location). Updated each turn by a `%%PC_DELTA%%` block or derived from the existing `%%DELTAS%%` + scene_npcs state. Injected into the system prompt alongside NPC profiles so the LLM can reason about character continuity across turns (e.g. "Ameiko just asked Ani a question" stays live context, not something that silently falls out of history).
- [ ] Update player character knowledge files after each session so each PC only retains facts they actually learned in play.
- [ ] Smart context pruning instead of hard char cutoff — when `len(system_content) > _GROQ_MAX_SYSTEM_CHARS`, the prompt is currently truncated at character 30,000 which can split mid-block. *(superseded by M4 — context becomes discrete blocks; pruning drops whole blocks tail-first instead of truncating a string)*
- [ ] NPC context injection ordering — when multiple NPCs are in scene, inject in recency order (most recently mentioned first) so the char-limit cutoff drops least-recently-seen NPCs. *(implement in M4 when context blocks are discrete)*
- [ ] `knowledge.md` age-out across long campaigns — knowledge items grow unboundedly. When injecting, only include entries from the last N sessions; archive older entries to `knowledge_archive.md`. Prevents prompt bloat over a multi-session campaign.
- [ ] Plan message history summarization to prevent the API payload from growing unbounded across long sessions. *(closed by M6)*
- [ ] Standardize the schema for character knowledge, NPC memory, session recap, and emergent canon so state can be updated automatically. *(blocked on M1 — the `ChatTurn`/`ContextBlock` model is the first step toward a canonical schema)*
- [ ] Create a clear source-of-truth rule for contradictions between session notes, recap files, NPC logs, and JSON outputs.
- [ ] Add validation checks for continuity drift such as wrong deity, alignment, class, or duplicated features across player records.
- [ ] Decide which state should live in markdown and which should live in structured JSON for UI and automation.

---

## Movement & Zone System

> All zone-based combat movement work lives in **[MOVEMENT-TODO.md](MOVEMENT-TODO.md)**.
> Named in-world zones, adjacency-based range, AoE by target count. No grid, no compass.
> Current status: PoC complete (M1-PoC-1/2/3 done) — `Combatant.zone` field, Zone column parsed from event files, badge shown in CombatPanel. Next: location file as zone source (M1-6/7/8), then adjacency helpers (M2).

- [ ] **Zone terrain and features** — zones can carry properties (difficult terrain, cover, higher ground, darkness) that create mechanical effects for occupants. Defined in the event file `## Zones` table under a `Properties` column. Effects tracked on `Combatant.conditions` and enforced during attack resolution. Examples: `higher_ground` grants +1 ranged attack, `cover` adds +4 AC vs ranged from other zones, `difficult_terrain` costs an extra move action to enter. See M5 in MOVEMENT-TODO for the full tier breakdown.

---

## Magic System

> All spell and magic work lives in **[MAGIC-TODO.md](MAGIC-TODO.md)**.
> Tiers S1–S6: spell recognition, auto-hit damage, slot tracking, saves, buffs, spell resistance.
> Current status: not yet started. Tier S1 next (spell recognition + intent extraction).

---

## Event System

> All event triggering and event-chain work lives in **[EVENT-TODO.md](EVENT-TODO.md)**.
> Tiers E1-E4: MVP soft-trigger scheduler + hard-chain progression first, then stability, authoring scale, and optional UX.
> Current status: planned. Tier E1 MVP next.

---

## Music System

> All procedural adaptive music work lives in **[MUSIC_TODO.md](MUSIC_TODO.md)**.
> Tiers M0-M2+: calm monophonic chiptune first, then smooth looping, then multi-track arrangement.
> Current status: specs written, implementation not started. Tier M0 backend next.

---

## Combat System

> All combat work lives in **[COMBAT-TODO.md](COMBAT-TODO.md)**.
> Tiers 1-4 (tracker, HP authority, attack flow, system prompt, enemy turn, conditions,
> initiative, state authority, spells) plus cross-cutting quality items are tracked there.
> Current status: Tiers 1, 1.1, 1.5, 1.6, 1.7, 1.8, and 1.10 (partial) complete. Tiers 1.9 and 1.10.5 complete. Tier 1.11 next (death/dying/healing).
> Tier 2.5 (action economy) in progress: action type picker (Standard/Move/Full-Round buttons) shipped on `feat/action-economy`. Swift/Free deferred.
> Tier 2 (server-authoritative state) follows Tier 1.11.
> See `specs/roll-initiatives.feature` (9 ACs, 18 pytest + 8 Vitest tests).

---

## Nice-to-Have

- [ ] **Action trigger-phrase reference** — build a lookup table (or inline reference in the input bar tooltip) that maps natural-language phrases to their Pathfinder action type, so the player knows what they're spending before they type. Examples:
  - *"I grab my X"* / *"I draw my sword"* → **Move action** (draw/retrieve item not in hand)
  - *"I retreat"* / *"I back away"* / *"I disengage"* → **Full-round action — Disengage** (avoids AoO)
  - *"I shoot at"* / *"I fire my"* → **Standard action — Ranged attack** (equipped ranged weapon)
  - *"I swing at"* / *"I hit"* / *"I strike"* → **Standard action — Melee attack**
  - *"I run"* / *"I sprint"* → **Full-round action — Run** (×4 speed, loses DEX to AC)
  - *"I charge"* → **Full-round action — Charge** (+2 attack, −2 AC until next turn)
  - *"I cast"* → **Standard action — Cast spell** (possibly full-round for some spells)
  - *"I shout"* / *"I call out"* → **Free action** (brief communication)
  - *"I reload"* → **Move action** (most crossbows/firearms)
  - The reference could appear as a small collapsible cheat-sheet near the input bar, or as a tooltip on a "?" icon. Backend-side, detected phrases could also pre-fill the `%%ROLL%%` type or add a hint to the per-turn prompt so the GM narrates the correct action economy.
- [ ] **Combat appearance injection** — inject a short visual description of each combatant into `_inject_context` so the LLM can write richer `%%NARRATIVE%%` (hit reactions, wounds, stances). Two sources:
  - *Enemies*: `appearance` field from the event file `## Combatants` table (e.g. "wiry goblin with a jagged dogslicer and burn-scarred arms"). Appended to the `[INITIATIVE ORDER]` block or a new `[COMBATANT APPEARANCES]` section.
  - *PCs*: `appearance` field from `player_XX.json` combat stats (already in the profile; just not forwarded to the combat prompt). Currently `[PC COMBAT STATS]` injects only mechanics — add a one-line appearance sentence per PC.
  - Keep the injection brief (one sentence per combatant, skipped if the field is absent) to avoid token bloat.
- [ ] Dice Tray should always show why the roll is made. As in "X tries to spot..."
- [ ] Dice Tray option A — always visible but collapsed to a thin strip, expands on click
- [ ] Dice Tray option B — show only when a `roll_request` event is active, hide otherwise
- [ ] **Add clear-history button to Dice Tray** — small button to wipe the local roll log; no backend call needed (history is UI state only)
- [ ] Build a small admin view for inspecting session state, NPC memory, and pending continuity updates.
- [ ] Add diff-friendly generated outputs so session-to-session changes are easier to review.
- [ ] Stream the recap text to the chat window during End Session — `stream_end_session` already emits status events but the recap prose is written silently to disk. Yielding it as tokens would let the player read it as it generates, the same way turns stream.
- [ ] Show active scene NPCs in the UI — `scene_npcs` accumulates across turns but is invisible to the player. A small chip list below the IntentBar (or inside it) showing which NPCs are currently in scene would help the player track who the GM is "watching."
- [ ] **Session timer** — elapsed time display (HH:MM) in the header that starts when Boot Session fires. Optional visual warning at a configurable threshold (e.g. amber at 2h30m, red at 3h) so the GM knows to wrap up. Pure frontend — no backend needed. Resets on End Session.
- [ ] **Session export** — "Export Session" button in the Tools dropdown that downloads the current session log as rendered HTML: markdown processed, `%%` markers stripped, styled with print-friendly CSS. One-click artifact at the end of each session. Reads from `GET /api/sessions/{id}/log` and renders client-side.
- [ ] **Campaign statistics** — a tab in the Coverage panel (or separate Tools entry) showing aggregate metrics across all sessions: sessions played, total turns, total XP earned, unique NPCs encountered, combats run. Built by scanning `outputs/` logs. Fun end-of-campaign data, and useful for spotting unusual session lengths.
- [x] **Session auto-increment after End Session** — `setSessionNumber(n => n + 1)` added to the `done` branch of `handleEnd` in `App.tsx`. Session number increments automatically after a successful end so the next boot is pre-configured. 1 Vitest test added to `App.test.tsx`.

---

## Code Quality / Refactoring

- [ ] **Split `session_manager.py` — 4 300+ lines is unworkable** — the file has grown to cover six distinct concerns that should live in separate modules. Suggested split:

  | New module | Responsibility | Approx lines today |
  |---|---|---|
  | `api/session_manager.py` | `GameSession` dataclass, `create_session`, `get_session`, `save_session`; thin public API only | ~200 |
  | `api/combat/state.py` | `CombatState`, `Combatant`, `PendingAttack`, `ActiveEvent`; `_parse_combat_block`, `_serialize_combat_state`, `_seed_round1_combatants`, `advance_combat_turn`, `roll_combat_initiatives` | ~500 |
  | `api/combat/attack.py` | `_resolve_npc_attack`, `resolve_attack_roll`, `resolve_damage_roll`, `_roll_dice`, `_parse_attack_line/block`, `_parse_action_block`, `_apply_hp_deltas` | ~300 |
  | `api/context/injector.py` | `_inject_context`, `_build_combat_system_prompt`, `_build_slim_system_prompt`, all `_COMBAT_SPEC_*` constants, `_inject_npc_context`, `_inject_skill_context`, `_inject_location_context` | ~700 |
  | `api/streaming.py` | `_stream_chat`, `stream_turn`, `stream_boot`, `stream_enemy_turn`, `stream_close_combat`, `stream_end_session`, `stream_resume_combat`; all SSE yielding and response-section parsing | ~1 200 |
  | `api/persistence.py` | `_write_session_state`, `_log`, `_write_npc_delta`, NPC boot cleanup, `_build_pc_profiles` | ~300 |

  **Migration strategy**: move modules one at a time with a re-export shim in the old location so `api/main.py` and all tests keep working without mass-changes. Start with `api/combat/attack.py` (most self-contained; already well-tested). Each move is its own PR.

  **Do not attempt this mid-feature** — pick a clean point between tiers (e.g. after Tier 2 SA-1 ships).

- [x] **Remove dead `%%HP%%` code and tests (CB1.9-4 housekeeping)** — now that `%%HP%%` is stripped from all prompts and both stream paths discard it, the following are dead code: `_HP_BLOCK_RE`, `_HP_DELTA_LINE_RE`, `_parse_hp_deltas()` (only callers were the two stream processors), plus the `TestHpDeltaIntegration` class in `test_combat_hp.py` and the two `test_no_hp_marker` tests in `test_combat_prompt.py` (they now test absence, which will stay true forever but add no value). `_apply_hp_deltas()` and its callers in `_resolve_npc_attack` / `resolve_damage_roll` are still live — keep those. Safe to do in one commit; no behavioral change.
- [ ] **Add comment at `_is_pc_attacker` call in `roll_combat_initiatives`** — function is named for attack resolution but reused for PC detection during initiative; a one-line comment prevents future confusion. *(api/session_manager.py)*
- ~~[ ] **Fix inline `import('./types')` in `api.ts` `rollInitiatives` return type** — see **[BUGS.md](BUGS.md) B-Q01**.~~
- ~~[ ] **Document `round < 1` sentinel in `CombatPanel.tsx`** — `showRound = combatState.round >= 1` hides the round badge when round is -1 (initiative not yet rolled); add an inline comment explaining the convention.~~
- ~~[ ] **Document initiative tie-breaking behaviour** — `sorted()` breaks ties by original insertion order; add a comment on the sort in `roll_combat_initiatives` noting this is intentional (modifier-based tie rules deferred to SA-2). *(api/session_manager.py)*~~
- [x] **Include rolled totals in initiative log entry** — current format is `new order: Name1, Name2`; change to `new order: Name1 18, Name2 11` so session logs show what was rolled. *(api/session_manager.py `roll_combat_initiatives`)*
- [x] **R1c — Extract `_process_response(response_text, session) -> tuple[str, Optional[dict]]`** — pulls out steps 9–10: section-based parsing (`%%NARRATIVE%%` / `%%ROLL%%` / `%%GENERATE%%` / `%%DELTAS%%`) and the flat fallback path (`%%DELTA%%` / `%%GENERATE%%`). All NPC file writes happen here. Sets `session.pending_roll`. Returns `(display_text, roll_data)` — no SSE yielding inside. Prerequisite: R1a shipped and stable.
- [x] **R1d — Tests for `_process_response`** *(ship with R1c)* — three cases: (1) section format happy path — correct display_text and roll_data returned; (2) flat fallback — roll block stripped from display_text; (3) no markers — raw text returned unchanged. Plus extend `test_turns.py` golden-path test: mock Groq, assert SSE event order is `context → token(s) → patch_last → roll_request`.
- [ ] **R1e — Complete orchestrator: `_stream_chat` → ~40 lines** *(ship after R1c is stable in play)* — `_inject_context` is already wired; replace the remaining inline response-parsing block with a call to `_process_response`. Validate with R1d integration test.
- [ ] **R3 — Provider dispatch is duplicated** — Groq/Ollama branching in payload building, streaming, `_call_blocking`, and token options. Adding a third provider means touching all four. Propose per-provider modules with `build_payload` / `iter_stream` functions sharing a common signature
- [ ] **R5 — Global lazy indexes** — `_npc_index` / `_skill_index` are module globals mutated by `_invalidate_npc_index()`. Encapsulate in an `IndexRegistry` with `get_npc()`, `get_skill()`, `invalidate_npc()`. Makes state explicit and tests easier to write.
- [x] **R6 — Timestamp formats scattered** — `%H:%M:%S`, `%Y%m%d_%H%M%S`, `%Y-%m-%d %H:%M:%S` appear in six-plus places. Add `_ts_file()` and `_ts_human()` helpers alongside the existing `_ts()`.
- [ ] **R7 — `_write_npc_delta` mixes concerns** — does Layer 2 stub creation, status block append, knowledge append, scene_npcs update, and three log calls. Extract `_append_status_block()` and `_append_knowledge_items()`; keep `_write_npc_delta` as orchestrator.
- [x] **R8 — Duplicate `%%ROLL%%` parsing** — roll logic written once for the section path and once for the flat fallback path. Normalise the fallback to a section dict first, then run the same downstream parser..
- [x] **R4 — `_NAME_EXCLUDE_WORDS` maintenance burden** — words now loaded from `adventure_path/00_system_authority/name_exclude_words.txt` (one per line, `#` comments, blank lines ignored). Falls back to hardcoded set if file absent or empty. GM-tunable without touching Python. 6 tests in `tests/test_config_tunables.py`.
- [x] **F6 — Configurable tunables via env vars** — `_DEV_MAX_HISTORY`, `_FULL_MAX_HISTORY`, `_GROQ_MAX_HISTORY`, `_ANTHROPIC_MAX_HISTORY`, `_DEV_MAX_TOKENS`, `_GROQ_MAX_SYSTEM_CHARS`, `_GROQ_RETRY_BASE` now read from `ROTRL_*` env vars with original values as defaults. 8 tests in `tests/test_config_tunables.py`.
- [x] **R1a — Extract `_inject_context(session) -> tuple[str, dict]`** — steps 1–5 of `_stream_chat` extracted: history trimming, Groq truncation, NPC/skill/location detection, `scene_npcs` accumulation, delta-reminder path. Returns `(system_content, context_info)`; `context_info["history"]` carries the trimmed message list. Wired into `_stream_chat` immediately — orchestrator now calls `_inject_context` and unpacks the result. *(Note: signature changes in M4 — function will write to `session.context_blocks` instead of returning a string.)*
- [x] **R1b — Tests for `_inject_context`** — 30 tests in `tests/test_inject_context.py` covering all five pipeline steps: history trimming per provider/mode, Groq truncation, NPC/skill/location match → profile injection + scene_npcs update, dedup of location-vs-name matches, delta-reminder when scene_npcs active but no new context, and full `context_info` key structure.
- [x] **B1 — Silent exception swallows** — all `except Exception: pass` in section-processing loop replaced with `except Exception as _e: _log(session, ...)`.
- [x] **B2 — UnboundLocalError in party extraction** — `name`/`cls` initialised per-file; only appended when both non-empty; `break` removed so field order no longer matters.
- [x] **B3 — Stub creation failure silent** — covered by B1 fix; I/O errors in `_process_generate_block` now surface in session log.
- [x] **B4 — `retry-after` stale wait** — explanatory comment added to `_groq_post`.
- [x] **B5 — Path traversal in log endpoint** — `resolve()` + `is_relative_to()` guard added in `api/main.py`.
- [x] **R2 — `except Exception: pass` helper** — resolved together with B1.

---

## Character Data and UI Content

- [ ] **In-session HP editing** — sidebar ＋/－ buttons to adjust `hp.current` for any PC without leaving the session. Calls a new `PATCH /api/characters/{id}/hp` endpoint that updates in-memory player data and writes the JSON file. Needed for healing spells, potions, and damage taken outside the structured combat flow (traps, environmental hazards).
- [ ] **Long rest** — "Rest" button (or a step in the end-session flow) that resets all PC `hp.current` to `hp.max` and spell slots to full. Writes updated player JSON files. Prompts GM to confirm before overwriting. Resets should respect penalties from negative levels or other long-duration effects if those are tracked.
- [ ] **Party overview panel** — compact strip at the top of the character sidebar showing all three PCs: name, HP bar, active condition badges. Allows the GM to see the whole party state at a glance without opening individual sheets. Reads from `GET /api/characters`; refreshes when a `combat_update` or HP-edit event fires.
- [x] **Hide sidebar (left) when not in a session** — sidebar is visible on the splash screen but serves no purpose before boot. *(Dice Tray already hidden — wrapped in `{isBooted && ...}` in App.tsx.)*
- [ ] Splash portrait click opens character sheet — same behaviour as "Open Sheet" in session
- [x] Add fun rotating hints to splash screen — PF1e flavour or adventure-specific
- [ ] **Extract abilities, feats, and class features into separate reference files** — currently each PC's `player_*.json` embeds spell descriptions, feat text, and ability summaries inline. This is redundant (all three kitsune characters share the same racial spells) and hard to maintain. The pattern established by `04_rules/skills/` and the planned `04_rules/spells/` should extend to: `04_rules/feats/<feat_name>.md`, `04_rules/class_features/<class>/<feature>.md`. Character sheets become name lists only; the system looks up mechanics from these files. Applies to: Flurry of Blows (Ani), Nine Tailed Heir bloodline abilities (Yanyeeku), kitsune racial traits (all three), warpriest blessings (Ani).
- [ ] Normalize all player JSON files to one agreed UI schema and keep them synchronized with the markdown sheets.
- [ ] Audit Ani's data and other player records for internal inconsistencies before relying on them in UI or prompts.
- [ ] Add a small sync tool or documented workflow for copying approved sheet changes into UI JSON files.
- [ ] Review portraits, colors, runes, and labels so presentation data is consistent across all characters.
- [x] **Open the character action menu to the right of the avatar** — menu rendered via `ReactDOM.createPortal` into `document.body` with `position: fixed` and coordinates from `getBoundingClientRect()` on the wrap element. This bypasses the sidebar's `overflow-y: auto` clipping context. `z-index: 1000` ensures it floats above all other panels. Click-outside handler updated to also check the portaled menu ref. `data-placement="right"` attribute added for testability. 2 Vitest tests added to `CharacterSidebar.test.tsx`. *(spec: `character-system.feature` AC-012)*
- [x] **Quick d20 from pending-roll banner** — clicking the skill/DC box above the dice grid (the `roll-request-prompt` area) immediately fires a single d20 roll, applying the auto-bonus if enabled. Does not affect the manual dice queue. The hint text reads "click to roll d20".
- [x] **Active character UX — sidebar split** — split the avatar click action into two: "Set Active" and "Open Sheet" (character-system.feature AC-007). Rename existing `activeCharacter` state in `App.tsx` to avoid collision with sheet-open state.
- [x] **Active character UX — halo and input badge** — show halo/ring on the active avatar in the sidebar (AC-008). Show small portrait badge and "Speaking as \<Name\>" label near the input bar (AC-009).
- [x] **Active character UX — speaker tag in chat** — prefix sent input with `@<Name>:` when an active character is set; render without prefix when no character is active (AC-010).
- [x] **Dice skill bonus — auto-apply modifier** — when a pending skill roll is active and an active character is set, auto-compute `finalTotal = d20 + skillModifier` and submit that to `/resolve_roll`. Show breakdown in roll history, e.g. `1d20(13) + Perception +7 = 20 vs DC 18` (dice-tray.feature AC-007).
- [x] **Dice skill bonus — toggle and fallback** — add "Auto-apply skill bonus" toggle (default ON) in the Dice Tray. When unmapped skill or no active character, fall back to raw roll and show a visible indicator (AC-008, AC-009, AC-010, AC-011).
- [x] Remove the functionality where the diceroll goes to the input field. *(Removed `rollInjection` state and InputBar injection props; roll now appears as a local player speech bubble in the chat showing raw roll, bonus, and final total. Not sent to backend as a turn.)*

---

## GUI Improvements

Visual and interaction improvements to the UI. These are not blocked by backend work unless noted.

- [x] **Rename "Dice Tray" → "dice tray" everywhere** — the component is currently called `DiceTray` / `dice-tray` throughout the codebase but "dice tray" is a better name and matches tabletop convention. Scope: `DiceTray.tsx` → `DiceTray.tsx`; CSS class `dice-tray` → `dice-tray`; all props (`DiceTray.test.tsx`, `App.tsx` import, `api.ts` mentions, README, TESTING.md, specs, COMBAT-TODO.md, exploratory docs, Playwright selectors in `live-flows.spec.ts`). **Do this in a single dedicated commit so grep/search stays consistent.** Everything going forward should use "dice tray" in code, docs, and conversation.

- [ ] **Dice tray — always show context for the current roll** — when a `roll_request` is active the banner shows skill and DC, but when rolling outside a pending request (e.g. manual queue) there is no label. Always show a one-liner explaining what the roll is for: skill-check prompt text from `pendingRoll.success/failure` preview, or "Free roll" when no pending roll.

- [ ] **Dice tray — condensed layout when combat is active** — in combat the dice tray moves to the left column and competes for vertical space with the character sidebar. Consider a compact "collapsed" mode: only the die buttons and the pending-roll banner visible; roll history hidden behind a toggle. Expands on click.

- [ ] **Combat panel — show initiative numbers in each row** — currently the row shows name, HP bar, AC, and status badge. The initiative value (e.g. `⚡ 18`) is sorted by but not displayed. Add it as a small badge so the GM can see at a glance why the order is what it is.

- [ ] **Combat panel — highlight when it is a PC's turn vs. enemy's turn** — the current-actor gold glow exists, but a stronger visual difference (e.g. green row tint for PC turns, red tint for enemy turns) would make the flow clearer, especially on a busy screen.

- [ ] **Input bar — show current combatant's name/portrait during combat** — already partially done via `inputActiveSpeaker`, but B-C02 means the `handleSend` prefix still uses `activeCharacter` instead of the initiative actor. Fixing B-C02 is the prerequisite; the visual is already present.

- [ ] **Action card — richer content and polish** — the initial action card layout (CB1.9-3) uses a minimal mock. Follow-up: decide final information hierarchy (weapon flavour name vs. mechanical name, condition effects applied, death/KO indicator when HP hits 0), typography, colour coding (red for hits, grey for misses), and animation (brief slide-in). Requires CB1.9-3 to land first. *(Blocked on: CB1.9-3)*

- [ ] **Combat action overlay toast** — after a resolved enemy attack, flash a brief ephemeral overlay (auto-dismiss ~2 s) like *"Goblin Warchanter hits Yanyeeku with an arrow!"* on top of the chat area. Pure UI — reads from the same `action_card` SSE payload. Gives the combat kinetic feedback before the player reads the narrative. *(Blocked on: CB1.9-3)*

- [ ] **Intent bar — combat mode** — during combat the intent bar shows NPC/skill/location detection tags that are meaningless (the backend doesn't emit a `context` SSE on combat turns, so it falls through to "no npc / no skill" noise or the misleading "no event — restart backend?" message). In combat mode the intent bar should instead surface combat-relevant state: current actor, detected action type (`attack` / `cast` / `move`), resolved weapon or spell name, and target. The `context` SSE is the social-turn signal; a new `combat_intent` SSE (or reuse `action_card` payload) should feed the bar during PC turns. Enemy turns could show the parsed `%%ACTION%%` fields (action, weapon, target) after they resolve. Requires a new SSE type or a mode flag passed from `App.tsx` (`combatState !== null`) to switch the bar's rendering branch entirely.

- [ ] **Enemy turn — goblinesque taunts and battle cries in the InputBar placeholder** *(nice to have)* — the input bar already shows `enemyTaunt()` placeholder text during enemy turns. Replace the generic five-phrase list (`ENEMY_TAUNTS` in `InputBar.tsx`) with a richer, creature-specific pool. For goblins: war shrieks, broken Common insults, fire-obsessed boasts ("BURN BURN BURN!"), dog-eating taunts, and panicked retreats. For other creature types (undead, humanoids, beasts) add their own flavour lists keyed by a creature-type tag on the combatant. Chosen deterministically by name so re-renders don't flicker. Pure UI change — no backend required.

---

## Message Pipeline

Separates the internal session model from the API payload. Currently `session.messages` IS the payload — context is string-concatenated into the system message each turn, which prevents Groq caching and makes adding new context types invasive. The goal: `GameSession` holds a typed internal model; `serialize_messages()` produces the API payload on demand.

Do these in order — each step is independently shippable and leaves the system working.

- [ ] **M1 — `ChatTurn` + `ContextBlock` types; extend `GameSession`** — add two dataclasses: `ChatTurn(role, content, turn_number, *, roll_fields?)` and `ContextBlock(kind, label, content)`. Add `session.chat: list[ChatTurn]` and `session.context_blocks: list[ContextBlock]` to `GameSession`. Keep `session.messages` untouched — no behavior change yet. Tests: instantiate session, verify defaults.

- [ ] **M2 — Write `serialize_messages(session) -> list[dict]`** — produces the API payload from the new model. Layout: `[system: static_base_prompt]` → `[user: assembled context blocks]` → `[user: summary turn if present]` → `[user/assistant: chat turns in order, rolls serialized as user turns]`. Falls back to `session.messages` if `session.chat` is empty (backward compat during migration). Tests: empty context, full context with NPC+skill+delta, chat with a roll turn, chat long enough to have a summary.

- [ ] **M3 — Wire `serialize_messages()` into `_stream_chat`; dual-write** — replace the `messages = [{"role": "system", ...}] + history` line with `serialize_messages(session)`. Context injection still appends to `system_content` (old path) AND appends to `session.context_blocks` (new path). `session.chat` mirrors `session.messages` (dual-write). Both paths produce the same payload — log a warning if they diverge. No behavior change. All existing tests pass.

- [ ] **M4 — Migrate context injection to `session.context_blocks`; static system message** — `_inject_context` (R1a, updated) now writes NPC profiles to `session.context_blocks` (`kind="npc"`), NPC deltas to `kind="npc_delta"`, skill rules to `kind="skill"`. `session.system_prompt` becomes truly static — never mutated after boot. `serialize_messages()` is the only place that assembles the payload. Remove old string-concat injection. Delete dual-write. **This is the step that enables Groq prompt caching** — system message is now byte-for-byte identical across all turns. Context pruning changes from string truncation to dropping whole `ContextBlock` entries tail-first. Tests: assert system message is identical on two consecutive turns; assert NPC block appears in the correct user message.

- [ ] **M5 — First-class roll turns in `session.chat`** — `log_roll()` appends `ChatTurn(role="roll", ...)` to `session.chat` with character, expression, individual rolls, and total. `resolve_roll()` updates that turn with `dc`, `passed`, and outcome text. `serialize_messages()` renders roll turns as `{"role": "user", "content": "[ROLL RESULT] Ani — Diplomacy — rolled 14+4=18 vs DC 12 — passed"}`. The GM now sees roll outcomes in history on the next turn automatically. **Closes "Feed resolved roll outcome into next GM turn directive"** and **"Update player character knowledge."** Tests: roll turn appears in serialized messages; outcome text correct for pass and fail.

- [ ] **M6 — Chat history summarization** — when the number of `user`/`gm` turns in `session.chat` exceeds a threshold (default 20), compress the oldest N turns into a `ChatTurn(role="summary", content="...", turns="1-11")`. Initial implementation: deterministic concatenation with truncation, no LLM call. `serialize_messages()` injects the summary as a single user turn (`"[SESSION SUMMARY — turns 1–11]\n..."`) before the active window. Threshold and window size configurable via env vars (see F6). **Closes "Plan message history summarization"**. Tests: 25-turn chat serializes to summary + last 10 turns; summary is stable (same input = same output).

---

## Runtime and Tooling

- [ ] Document the exact local startup and recovery workflow for Windows, including port cleanup and Ollama checks.
- [ ] Session crash recovery — sessions are purely in-memory; a server restart during play loses `session.messages`, `scene_npcs`, `pending_roll`. After each turn, write a recovery snapshot to `outputs/sessions/{session_id}_snapshot.json`. On startup, detect orphaned snapshots and offer recovery.
- [ ] **Rate limit badge warning state** — turn the badge amber when headroom is low (e.g. `rpm_remaining < 5` or `tpm_remaining < 20%` of limit). Currently the badge is informational only; a colour change gives an at-a-glance signal before the next call hits the cap. No live ticking needed — evaluate on each `rate_limits` SSE event. Thresholds can be constants in `Header.tsx`.
- [x] **View Log — surface API call logs in the UI** — "API Logs" button added to post-boot header; opens `ApiLogPanel.tsx` overlay (right-side slide-in, Escape/backdrop to close). List view shows timestamp, provider, session, and turn parsed from filename. Detail view has a summary bar (status · section_format_ok · first_token_ms · duration_ms · total_tokens) plus full JSON in a scrollable code block. 22 Vitest tests in `ApiLogPanel.test.tsx`. *(spec: `specs/session-logging.feature` AC-009/AC-010)*
- [x] **Add Anthropic (Claude) as a provider** — `anthropic>=0.34.0` in `requirements.txt`; `_stream_anthropic` + `_call_blocking` Anthropic path in `session_manager.py`; `ANTHROPIC_API_KEY` from env; `_ANTHROPIC_MAX_HISTORY=60` (30 exchanges); `anthropic` branch in provider dispatch and history-trim; UI: "🤖 Claude" button + `claude-sonnet-4-6` / `claude-opus-4-7` / `claude-haiku-4-5-20251001` dropdown in `Header.tsx`; `provider` state union widened in `App.tsx`.
- [x] Add `first_token_ms` to the API log so first-token latency is captured alongside total response time. *(`timing_out` dict threaded through `_stream_groq` / `_stream_ollama`; first content token records elapsed ms since request dispatch; `null` on error. 4 unit tests + 2 integration tests in `test_groq_provider.py`. Spec: `specs/session-logging.feature` AC-007.)*
- [x] Add `section_format_ok` boolean to the API log (true if `_HAS_SECTION_MARKERS_RE` matched) to track structured-output adherence passively across real sessions. *(`_HAS_SECTION_MARKERS_RE.search` applied to assembled response in the `finally` block; `null` on error, `true`/`false` on success. 4 unit tests + 2 integration tests. Spec: `specs/session-logging.feature` AC-008.)*
- [x] Add `GET /api/health` endpoint — returns `{"status": "ok"}`. The UI can hit this before attempting boot and surface a clear "backend not running" message instead of a generic network error.
- [x] Track Groq token usage per turn — `stream_options: {include_usage: true}` added to Groq payload; final usage chunk captured in `_stream_groq`; written to `write_api_log()` under `"usage"` key alongside duration.
- [x] Surface Groq rate limits to the UI — per-minute `x-ratelimit-*` response headers captured in `_stream_groq` after each successful call; emitted as a `rate_limits` SSE event; `Header.tsx` shows a compact badge (e.g. `⚡ 4,500/6,000 TPM · 28/30 RPM`) with a tooltip showing reset times. 429 exhaustion now parses the error body to surface a human-readable daily-limit message instead of a bare HTTP error. 2 new tests.
- [x] `stream_options` graceful degradation — older Groq models (e.g. `llama3-8b-8192`, `mixtral-8x7b-32768`) return 400 when `stream_options: {include_usage: true}` is present. `_groq_post` now detects the 400, strips `stream_options` from a local payload copy, and retries once immediately without consuming a rate-limit retry slot. Usage tracking silently degrades to `null` for unsupported models; turns complete normally. 2 new tests.
- [x] Fix dice roll value persisting in input bar after boot — `rollInjection` state was not cleared on session boot, causing `InputBar`'s mount-time `useEffect` to re-inject the previous session's roll value. Fixed by adding `setRollInjection(null)` to `handleBoot`. (309 tests total — no new tests needed)
- [x] Harden backend startup further so orphaned Python child processes and stale listeners are detected and cleaned consistently on Windows. *(`dev.py` now calls `_free_port(8000/5173)` before launching — uses `netstat` to find the PID, `taskkill /F /T` to kill the whole process tree, polls up to 2 s, fast-fails with a clear message if the port stays held. Shutdown path also replaced `proc.terminate()` with `_kill_tree(pid)` so uvicorn's `--reload` worker child is not orphaned on Ctrl-C. `start_ui.ps1` updated to match `start_backend.ps1`'s Stop-Process + taskkill + fail-fast pattern for port 5173. See: specs/startup-hardening.feature.)*
- [x] Evaluate whether Ollama should remain the serving layer. *(Groq is now the primary provider — faster, no GPU overhead, better structured-output adherence. Ollama kept as offline fallback only; no further investment planned.)*
- [x] Fix the UI startup path and determine why `npm run dev` is currently failing. *(was a port conflict — pinned Vite to port 5173 with `strictPort: true`)*
- [x] Add one command that boots backend and UI together for local development. *(`python dev.py` — runs tests, then starts API + UI; `--skip-tests` flag to bypass)*

---

## NPC Lifecycle and Knowledge

- [ ] **Location generation should follow NPC generation rules** — session-generated locations (from `%%GENERATE%% type: location`) currently create thin stubs in `03_locations/` with just the LLM-provided fields. They should follow the same lifecycle as NPCs: dot-prefix for session stubs (`.location_name/`), `base.md` format matching the location seed files, `LocationIndex` invalidation after stub creation, and a "Purge Locations" path parallel to "Purge NPCs". Currently a session-generated location gets auto-injected as context on subsequent turns but its content is minimal and unreviewed.
  **Why:** user observed session-generated stubs (e.g. `Festival Square`) being re-injected with thin/LLM-invented content, polluting future turns. NPC lifecycle (dot-prefix → promote → purge) is the established pattern.
  **How to apply:** model the location stub writer on `_process_generate_block` for NPCs; add dot-prefix logic to `LocationIndex`; add purge endpoint.

- [ ] Write `%%GENERATE%%` summary field to NPC knowledge — the `summary:` field in `%%GENERATE%%` blocks is parsed but silently dropped. Write it as the first entry in the new NPC's `knowledge.md`: `- [world] {summary} — S{session:03d} T000`. Bootstraps the NPC's knowledge file immediately.
- [ ] **Sandpoint NPC skeletons** — populate `01_npcs/` with skeleton `base.md` files for 50–75% of named Sandpoint NPCs. A skeleton needs: name, role/occupation, one-line physical description, one-line personality, key relationships, and location (which building/district they frequent). No stat blocks, no deep backstory — just enough that the GM never has to invent a bartender from scratch. Source from `adventure_path/06_books/BOOK_01_BURNT_OFFERINGS/NPCS.md` and `SANDPOINT_LOCATIONS.md`. Priority order: (1) named NPCs already referenced in session logs or the book's Tier I/II list; (2) location anchors (innkeeper, blacksmith, sheriff's deputy, temple acolytes); (3) recurring faces (market vendors, festival organisers).
- [x] **NPC section extractor for targeted prompt assembly** — `api/context/npc_extractor.py`: `get_npc_sections(name, sections, include_below_line)` and `list_npc_sections(name)` parse any `base.md` into named sections and return only what is requested. Case-insensitive prefix matching ("location" → "Location & Availability — Act I"; longest-key wins on ambiguous prefix). Above/below `<!-- REFERENCE -->` split respected — Tier/Role/Flags/Narrative Function are opt-in only. 58 pytest tests in `tests/test_npc_extractor.py`. Foundation for the prompt builder context-spec layer.
- [x] **NPC base.md format extended** — `## GM Notes` (replaces "Reaction to PCs") and `## Secrets` sections added to the canonical format. GM Notes covers initial attitude, roleplay voice, what warms/cools the NPC, and emphasis guidance. Secrets lists plot-relevant hidden facts with unlock conditions. `abstalar_zantus/base.md` updated as the reference implementation; `specs/npc-system.feature` AC-002 updated to match.
- [x] Single-word NPC name detection — `_detect_narrative_npcs` now runs two passes: Pass 1 checks every Title Case word (≥4 chars) against `NpcIndex.canonical_for()` (the alias table, which auto-registers each word of every canonical name); Pass 2 is the original two-word heuristic for unknown NPCs. Single references like "Aldern" now resolve to "Aldern Foxglove" without an explicit alias entry. `NpcIndex.canonical_for()` added to `npc_lookup.py`. 9 tests in `test_scene_npc_tracking.py`.
- [x] Carry `scene_npcs` forward into the next session's boot file — `stream_end_session` appends `## NPCs Active at Session End` to the generated `boot.md`; `create_session` calls `_parse_scene_npcs_from_boot` and pre-populates `session.scene_npcs` on boot. The restored names are logged at session start. 3 tests in `test_scene_npc_tracking.py`.
- [x] Surface the list of detected-but-not-yet-stubbed names from `scene_npcs` — `scene_npcs` added to the `context` SSE event and shown as amber chips in the IntentBar ("scene" label, one chip per NPC). All turns now surface the full tracked scene regardless of what triggered the turn. 3 tests in `test_scene_npc_tracking.py`.
- [x] Location tracking — `%%GENERATE%%` blocks with `type: location` now create stubs in `adventure_path/03_locations/` (previously logged and skipped). `LocationIndex` singleton (`api/context/location_lookup.py`) detects location aliases and injects profiles per-turn. `scene_locations` persists location context across turns. 8 seed locations written for Act I. 43 tests in `tests/test_location_lookup.py`. *(spec: `specs/location-system.feature`, 9 ACs)*
- [x] Promote auto-created session NPCs to permanent records via a lightweight review workflow. *(session NPCs now live in dot-prefixed directories under `01_npcs/`; rename the directory to drop the dot to promote. UI "Purge NPCs" button bulk-deletes all dot-prefixed dirs via `DELETE /api/npcs/session`.)*
- [x] Update NPC knowledge and memory state after each session, including attitude shifts, known facts, suspicions, and unresolved goals. *(per-turn `%%DELTA%%` blocks written to `session_NNN.md` per NPC; delta files cleared on session boot)*
- [x] Write structured NPC deltas per turn with multi-line knowledge support. *(`%%DELTAS%%` section uses bracket blocks, one per NPC; `knowledge:` lines collected as a list; `_write_npc_delta` helper extracted)*
- [x] Auto-create NPC stub when a `%%DELTAS%%` block references an unknown NPC (Layer 2 fallback). *(if `npc_dir_for` returns `None`, `_process_generate_block` is called with stub data before writing the delta)*
- [x] Detect NPCs introduced in narrative text without any structured block (deferred Layer 3). *(`_detect_narrative_npcs` scans completed narrative for Title Case name pairs, adds to `session.scene_npcs`; stub creation is deferred until the model writes a `%%DELTAS%%` block for that name)*
- ~~[ ] Create a new location function when the LLM returns new generated locations.~~ *(superseded by "Location tracking" item above which is more complete)*

---

## Event Injection System (`%%EVENT%%`)

Event-triggered context injection. When the LLM decides a scene condition is met, it writes `%%EVENT%%` with an event ID. The code loads the corresponding content and injects it for N turns (currently N=5). Separate from `%%DELTAS%%` which is for persistent state — events are transient and time-bounded.

> **Open design question:** N=5 turns is a starting point. Needs tuning against real sessions. Also deferred: full content → compressed summary mid-window.

- [ ] **Event temperature system** — replace hard trigger conditions with a tension-building mechanic. Each event carries a list of weighted signals (e.g. `goblin_spotted: +30`, `alarm_bell: +50`, `civilian_screams: +20`). The backend tracks a `temperature` counter per pending event; each signal that appears in GM output or player input increments it. When temperature crosses a configurable threshold, a random roll (e.g. `d100 < temperature - threshold`) determines whether the event fires that turn — creating probabilistic escalation rather than binary triggers. Benefits: events feel organic rather than scripted; tension builds naturally across turns; multiple signals compound. Storage: `session.event_temperature: dict[str, int]` mapping event_id → current temperature. Event file format extension: a `## Triggers` section listing signal phrases and their weights. Fallback: events without a `## Triggers` section use the current `**Trigger:**` header as a single hard condition (backward-compatible).

- [ ] **Monitor event firing in real sessions** — verify the LLM fires events at the right narrative moments and does not double-fire or skip. N=5 turns TTL is a starting point; tune against observed sessions. Also watch whether the CORRECT/WRONG examples in the prompt fully eliminate the double-write behavior over time.
- [ ] **Rethink event TTL as dialogue milestones** — instead of a raw turn count, the `length` (or TTL) of an event should express "these are the dialogue lines/topics that must be said before event X resolves." A goblin attack event, for example, stays active until the key beats (screams heard, guards mobilised, players decide to fight/flee) have each been touched — not just after N turns have elapsed. Concrete approach: events declare a list of milestone phrases/topics; the system ticks them off as they appear in GM output, and the event expires only when all milestones are acknowledged (or a hard-cap turn limit is hit as a safety net).
- [x] **Spec — `%%EVENT%%` block format** — `specs/event-injection.feature` written: 9 ACs (AC-009 adds `event_type` metadata), inline syntax `%%EVENT%% <id>`, single event per response, TTL-only expiry.
- [x] **Event content files** — `adventure_path/02_events/` contains 9 event files covering the full Act I chain (see Adventure Content section). Format: metadata header above `<!-- INJECT -->`, injectable content below. Old flat stubs (`cavalry_arrives.md`, original `goblin_attack_starts.md`) replaced by zone-based rewrites with appearance, taunts, and binding AI tactics.
- [x] **`EventIndex`** — `api/context/event_index.py`: `EventEntry` dataclass, `EventIndex` with lazy load, `get()`, `event_map_text()`, `_parse_event_file()`. Singleton + `_get_event_index()` in `session_manager.py`.
- [x] **Session state** — `ActiveEvent` dataclass (`event_id`, `content`, `turns_remaining`) added. `active_events: list` field on `GameSession`. TTL decremented in `_inject_context`; expired entries removed.
- [x] **Parser** — `_EVENT_LINE_RE` regex; fires in both section-based and flat-block paths. Duplicate check (no TTL reset), unknown-ID guard (silent ignore).
- [x] **Injection** — active event content injected in `_inject_context` alongside NPC/skill/location blocks. `%%EVENT%%` added to streaming filter `_END_MARKERS` (hidden from player). Event map appended to system prompt via `_build_slim_system_prompt`.
- [x] **Tests** — `tests/test_event_injection.py`: 29 tests. Covers EventIndex loading, file parsing, event map text, `event_type` metadata (AC-009), firing, unknown ID, duplicate TTL, expiry, injection presence, expiry suppresses injection, SSE active_events list, player-hidden token stream, and double-write regression.
- [x] **Live-testing bugs found and fixed** — two issues discovered during manual testing:
  - *Prompt format:* `%%EVENT%%` was listed in RESPONSE STRUCTURE like other section markers, so the LLM wrote it as a section header with explanation text below, never putting the ID on the same line. Fixed: rewritten as `SCENE EVENT (optional — not a section header)` with explicit `CORRECT` / `WRONG` examples including the exact double-write pattern.
  - *Regex false match:* `_EVENT_LINE_RE = r'^%%EVENT%%\s+(\S+)'` — in multiline mode `\s+` consumes a newline, causing the second `%%EVENT%%` marker to be captured as the ID when the LLM double-writes. Fixed: `(\S+)` → `([A-Za-z]\w*)` (event IDs always start with a letter; the marker itself starts with `%`).

---

## Housekeeping

- [x] Decide what to do with `facets/FACET_*.md` — absorbed the 7 non-empty facets into a `GM STYLE` section in `_build_slim_system_prompt()`; deleted all 13 facet files and the `facets/` directory. Empty facets were superseded by the `%%ROLL%%` format block already in the prompt.
- [x] Review and clean `adventure_path/90_shared_references/temp.md` — almost certainly stale.
- [x] Delete `AGENTS.md` — documents the old `src/agents/gm_boot_agent.py` architecture that no longer exists. Only referenced once in `ADVENTURE.md` as a link. Remove the file and the link.

