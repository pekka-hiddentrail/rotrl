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

## Quality and Testing

- [ ] **Playwright — attack resolution E2E** — one live flow `attack-resolution-flow` in `live-flows.spec.ts`: boot → trigger combat with mixed NPC+PC attack block → assert `attack_result` SSE updates CombatPanel HP → assert `attack_request` fires and DicePanel shows to-hit banner → roll d20 → hit path: damage banner appears, roll damage, assert `combat_update` reduces HP → assert `POST /resume_combat` called and GM resumes streaming. *(spec: `attack-resolution.feature` AC-002 through AC-005)*
- [ ] **Generate HTML coverage heatmap** — combine code line coverage and feature AC coverage into one visual; dark = no tests, red = code covered but no AC, green = both
- [ ] **Define risk register** — identify high-risk areas (LLM compliance, session state loss, data corruption); map each risk to covering tests or flag as gap
- [ ] **Spike: agent-driven exploratory test harness** — one LLM plays as player (sends PF1e actions via the live SSE API), a second evaluates each GM response against a rubric (no leaked markers, narrative length, no invented lore)
- [ ] Test the full end-session SSE stream with mocked Groq — verify status events arrive in order, recap and boot files are written, and the session is removed from memory. *(critical — error paths covered in `test_end_session.py`; success path not tested)*
- [ ] Test turn input validation at the API boundary — confirm the error event is returned and no message is appended to session history when input is rejected. *(high — `validate_turn_input()` tested in isolation in `test_boot_prompt.py`; HTTP boundary + history-not-appended not tested)*
- [ ] Test `_enforce_recap_header` against real LLM output samples collected from past sessions to catch title/date extraction edge cases. *(low — synthetic coverage in `test_recap_header.py` is solid; real-sample gap is narrow)*
- [ ] Test the roll endpoint writes the correct expression and total to the log, including multi-die breakdowns (e.g. 3d6 showing individual rolls). *(low — single-die case covered in `test_roll_logged`; multi-die breakdown not tested)*
- [ ] **Live Playwright — dice roller scenario coverage** — extend `ui/e2e/live-flows.spec.ts` with dedicated dice scenarios against a real booted session: (1) basic multi-die queue (2d6+1d20) rolls and result appears in history; (2) auto-bonus applies when active character has a matching skill modifier; (3) auto-bonus absent when toggle is OFF; (4) pending roll banner clears after resolve and PASSED/FAILED badge appears; (5) history cap at 10 rolls — 12th roll evicts the oldest entry; (6) roll-while-streaming is blocked — send button disabled during GM response.
- [ ] **Combat initiative active character state** — when combat is active, the current combatant in initiative order should drive `active_character`. Add an API/update path that writes the current initiative actor into the UI and `sessions/session_NNN/state.json`, including enemy turns. When the active actor is an enemy, the input field should switch to a red-ish hostile state with taunting prompt text, show a skull-style icon instead of the character rune, and label the enemy by name (for example `Goblin Warrior 1`).
- [ ] **Combat turn ownership model** — make the backend, not the LLM, the source of truth for the current combatant and initiative advancement. Store current actor, round, and acted/remaining turn state; emit it to the UI; inject it into the combat prompt as authoritative. The LLM may describe outcomes, but should not be able to drift initiative order or choose whose turn is next.
- [ ] **Backend-hydrated combat encounter start** — when a combat event starts, resolve the encounter from backend-owned event/encounter descriptions plus canonical bestiary data instead of trusting the LLM to invent monster stats. Determine the minimum LLM responsibility: likely narrative framing, enemy intent, and choosing among valid tactics; backend should supply combatants, HP, AC, initiative modifiers, attacks, saves, XP, and encounter metadata wherever the data exists.
- [ ] **Combat prompt: PC vs enemy turn behavior** — clarify and test the combat prompt contract: on a PC turn, the GM should present the immediate situation and wait for/resolve the player's declared action; on an enemy turn, the GM may choose and narrate the enemy action using `%%ATTACK%%`/`%%HP%%` as needed. This should align with the active-character/enemy input-state UI.
- [ ] **Combat action economy rules** — add prompt guidance and backend/test support for PF1e action economy: standard/move/swift/immediate/full-round actions, attacks of opportunity, readied/delayed actions, and limits on how much one combatant can do per turn.
- [ ] **Enemy stat authority for combat** — stop relying on model-invented enemy stats after initial setup. Load enemies from canonical NPC/monster stat blocks where possible, persist generated combatants into session state, and validate AC/HP/initiative/attack bonuses against those sources.
- [ ] **Combat end conditions** — define when combat should emit `round: 0` and clear the tracker: all enemies dead/fled/surrendered, encounter defused, or GM/player explicitly ends combat. Add tests so victory, surrender, fleeing enemies, and manual End Combat behave consistently.
- [ ] **Condition duration tracking** — extend combat state to track condition durations and expiry rules, not just condition labels. Include prompt/backend behavior for one-round effects, save-ends effects, prone/standing, bleed, poison, fear states, and other common PF1e combat conditions.
- [ ] **Skill-use rules for trained-only skills** — define and enforce when a PC can attempt skill checks they do not have trained. Knowledge skills should follow PF1e trained-only behavior where appropriate; if a character lacks the relevant Knowledge skill, fall back to an untrained general ability check only for common information, likely INT-based with a higher DC (for example +10), and make the GM state the limitation instead of silently granting full expert knowledge.
- [x] **Vitest — attack resolution UI** — 15 tests in `DicePanelAttack.test.tsx`: to-hit banner (attacker/target/AC/bonus/active-class/onAttackRoll callback); damage banner (HIT line/damage-expr/Roll Damage disabled+enabled); null phase (no banner, no active class); attack log (hit badge+damage, miss badge+no-damage, NPC label, log-before-skill-history DOM order). *(spec: `attack-resolution.feature` AC-002/AC-003/AC-004/AC-008)*
- [x] **Bug: `handleDamageRollClick` passes die sides as roll values** — `pending` stores die *sides* (e.g. `[8]` for a d8), not rolled values. `handleDamageRollClick` passes `pending` directly as `rolls`, so `onDamageRoll([8], 8)` is called instead of the actual d8 result. **Fixed:** `pending.map(rollDie)` replaces `[...pending]`. V8 Vitest test added to cover the fix. *(DicePanel.tsx `handleDamageRollClick`)*
- [x] **Add pytest-cov to backend** — generate per-file line coverage report; identify untested paths in streaming and fallback parsers. **Done:** `pytest-cov>=4.0.0` in requirements; `.coveragerc` (source=api, show_missing, json→outputs/code_coverage.json); `GET /api/code-coverage` endpoint; "Code Lines" tab added to the Coverage modal showing per-file bars, %, and missing line numbers.
- [x] **Build feature coverage matrix** — map each of the 178 spec ACs to the test(s) that cover it; flag ACs with zero test coverage. **Done:** `scripts/build_coverage.py` reads all `specs/*.feature` files and all test suites (pytest / Vitest / Playwright), writes `outputs/coverage.json` (45/178 covered, 133 gaps as of first run). `GET /api/coverage` serves the data. `CoverageMatrix.tsx` modal opens from a "Coverage" button in the header — filterable by feature and by gap status. Spec: `specs/coverage-matrix.feature` (6 ACs).
- [x] Add a test fixture representing a corrupt or partially-written log file and assert the parser either recovers gracefully or raises a clear error. *(low)*
- [x] Add contract tests for the SSE event shape — assert that every event emitted by boot, turn, and end-session has a `type` field and matches the known union of types. *(low)*
- [x] **E2E — Playwright UI test suite** — add Playwright to `ui/` (`npm install -D @playwright/test`). Cover the seven key flows with a mocked backend (MSW or a lightweight FastAPI fixture): (1) boot → session badge appears; (2) send turn → GM message streams in; (3) `roll_request` event → dice panel activates; (4) end session → chat clears; (5) Kill button on stuck ending → inline confirm → UI resets to pre-boot; (6) Purge NPCs button → inline confirm → toast notification; (7) character sidebar → sheet modal opens. These are the regression cases that break silently on UI refactors and are invisible to pytest. *(`ui/e2e/app-flows.spec.ts`; `ui/playwright.config.ts`; `npm run test:e2e` — 7 Playwright tests passing.)*
- [x] **Vitest — Character data and sheet AC coverage** — add tests for `character-system.feature` AC-001 through AC-006 and remaining AC-010/AC-011 integration: static JSON loading/failure, HP bar colors, sheet modal close behavior, stat/spell tooltips, spell grouping, active speaker persistence, and backend payload prefixing in `App` (bubble content display is covered by `player-bubble-speaker.feature` tests). *(`characters.test.tsx`; `CharacterSidebarHealth.test.tsx`; `CharacterSheet.test.tsx`; `App.test.tsx` speaker integration.)*
- [x] **Vitest — Header/session controls AC coverage** — add tests for `session-controls.feature` AC-001 through AC-008 plus `llm-providers.feature` AC-001/AC-005: provider/model switching, pre/post-boot control visibility, boot disabled state, View Log target, purge inline confirm/toast, rate-limit badge, and Kill inline confirm/abort reset. *(`Header.test.tsx`; App-level View Log/Purge/Kill/provider tests.)*
- [x] **Vitest — Chat and turn UI AC coverage** — add tests for `chat-display.feature` AC-001 through AC-006 and `player-turn.feature` AC-001/AC-005: immediate player bubble, thinking indicator, token append/cursor, intro markdown rendering, autoscroll, streaming disabled state, and end-session status bubble updates. *(`ChatWindow.test.tsx`; expanded `App.test.tsx` streaming tests.)*
- [x] **Vitest — IntentBar AC coverage** — add component tests for `intent-bar.feature` AC-001 through AC-005: 52-character truncation, NPC/skill/location tags, null tags, detecting state, and no-context-event diagnostic. *(`IntentBar.test.tsx`.)*
- [x] **Vitest — App SSE integration smoke tests** — 19 tests across 3 describe blocks in `ui/src/__tests__/App.test.tsx`. Covers: boot intro/session setup (6), send-turn event order — `context`, `token`, `patch_last`, `roll_request`, `rate_limits`, error bar, second-send clears error (8), and session end cleanup — ending bubble, status event, done→"Session saved."→cleanup, error path (4+1). Key patterns: `makeStalledGen` for intermediate-state observation; `vi.spyOn(setTimeout)` to shorten the 1800 ms hold without fake-timer/`act` conflicts; `useCharacters` + `fetch` stubbed in every test.
- [x] **Vitest — DicePanel AC coverage** — add component tests for `dice-panel.feature` AC-001 through AC-011: queue accumulation, roll history limit/latest highlight, `/roll` payload, pending roll banner, `/resolve_roll` pass/fail handling, auto skill bonus, raw-roll fallbacks, toggle persistence, and normalized skill lookup.
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

- [x] **Verify and complete bestiary files** — `goblin.md`, `goblin_commando.md`, and `goblin_warchanter.md` confirmed complete: AC, HP, attacks, combat scripts, morale thresholds, XP values all present.
- [x] **Festival encounter sequence** — `FESTIVAL_ENCOUNTER.md` created: three-wave raid script, Aldern rescue moment, Hemlock arrival timing, civilian rescue beat, aftermath state changes. All 12 encounter stubs (EC-COM-01 through EC-SUP-01) written with PF1e-correct content.
- [x] **Aldern Foxglove introduction** — `base.md` verified complete (rescue hook, hunting trip, estate reference present); `knowledge.md` exists as session tracking log (correct format); backstory seed content lives in `base.md`.

### Act II — Shadows in Sandpoint (levels 2–3)

- [ ] **Catacombs of Wrath — dungeon document** — `CATACOMBS.md` created: 7-room prose layout, 5 sinspawn encounters, Runewell chamber with cross-reference to LOCATIONS.md, full treasure and XP tables, Karzoug name drop in Room 2, Sihedron Rune callback in Room 7.
- [ ] **Sinspawn stat block** — `adventure_path/05_campaign_setting/bestiary/sinspawn.md` created: AC 14, HP 16, claws+bite, sinful bite (Will DC 12 or wrath compulsion), wrathful strike, GM narrative notes.
- [ ] **Glassworks investigation sequence** — `GLASSWORKS.md` created: three entry hooks, room-by-room layout (main floor/office/upper floor), Tsuto encounter, Ameiko rescue, journal content, Catacombs entrance discovery, full aftermath.
- [x] **Tsuto Kaijitsu combat stats** — added to `01_npcs/tsuto_kaijitsu/base.md`: monk 7, CR 6, AC 20, HP 42, full attack line, surrender condition, loot (journal).

### Act III — Thistletop (levels 3–4)

- [ ] **Thistletop — dungeon document** — `THISTLETOP.md` created: Nettlewood approach, rope bridge mechanics, full surface level (throne room, barracks, guard post, stables, trapdoor), Thassilonian level (entry passage sinspawn, Lyrie's library, yeth hound corridor, Nualia's sanctum, Runewell chamber), clearing conditions, Ameiko aftermath beat.
- [ ] **Thistletop goblin roster** — `01_npcs/thistletop_roster/base.md` created: Ripnugget (fighter 4, gecko mount, surrender), Bruthazmus (bugbear ranger 4, Ameiko connection, turning), Orik Vancaskerkin (fighter 4, mercenary, turning conditions), Lyrie Akenja (wizard 4, library intelligence, cooperation conditions), Stickfoot.
- [ ] **Additional bestiary entries** — `goblin_dog.md` (CR 1, Goblin Pox disease, morale); `yeth_hound.md` (CR 3, Bay DC 13, flight, DR 5/silver). Warchanter variant already complete.
- [x] **Nualia Tobyn — combat stats** — added to `01_npcs/nualia_tobyn/base.md`: cleric 4/barbarian 3, CR 7, AC 20, HP 62, spell list, aura of madness, demon claw, full combat script, redemption condition, loot (journal bridges to Book II).

### Monster Library

- [ ] **Create `adventure_path/09_monsters/` folder** — centralise all generic monster stat blocks here. Each file named `<slug>.md` (e.g. `goblin.md`, `sinspawn.md`, `yeth_hound.md`). Minimum fields per entry: AC, HP, speed, attacks (name / to-hit / damage), saves, special abilities, morale threshold, XP value, and short GM combat notes. The campaign-specific bestiary files currently scattered in `05_campaign_setting/bestiary/` should move here; named unique NPCs (Nualia, Tsuto) stay in `01_npcs/`. `LocationIndex`-style lazy loading and alias detection can be added later if the GM needs per-encounter monster context injected automatically.

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
- [ ] Make player identity loading consistent across code paths; current boot logic still expects some optional files in different locations than the repo uses.
- [ ] **Groq: per-call-type model routing** — when provider is Groq, use `llama-3.3-70b-versatile` for the two blocking `stream_end_session()` calls (recap + boot brief) and `llama-3.1-8b-instant` for normal turns. Requires a model-override parameter threaded through `_stream_groq`; the UI model dropdown stays decoupled. Not applicable to Anthropic — model is set at session boot and applies uniformly.
- [ ] Fix prompt spec gaps — three small changes to `_build_slim_system_prompt`: (1) add `personality:` field to `%%GENERATE%%` block spec (code already reads it, model never writes it); (2) add "skip `%%GENERATE%%` for NPCs already in the scene" rule; (3) add "at most one `%%ROLL%%` block per response" constraint.
- [ ] **Load `00_system_authority/` files into the system prompt** — CORE BEHAVIOR and GM STYLE are hardcoded strings in `_build_slim_system_prompt()`; tuning them requires editing Python. Replace with file loading: `ADJUDICATION_PRINCIPLES.md` → CORE BEHAVIOR block at boot; `PF1E_RULES_SCOPE.md` (payload section only, above `<!-- REFERENCE -->`) → GM STYLE block at boot. `COMBAT_AND_POSITIONING.md` → inject per-turn via `_inject_context` alongside `_COMBAT_FULL_SPEC` when combat is active. Caution: files must stay at or below current token budgets — don't let file loading silently bloat the static prompt. `PERSISTENCE_HANDLING_RULES.md` and `SESSION_NOTES_PROTOCOL.md` are reference-only (no action needed).
- [ ] **System prompt — strip non-combat context blocks outside active combat** — when `session.combat_state is None`, suppress from the per-turn injection: `_COMBAT_FULL_SPEC`, `_COMBAT_SPEC_ONGOING`, `[CURRENT HP]` block, `_ENEMY_TURN_DIRECTIVE`, and the attack-resolution section of `_COMBAT_SPEC_ONGOING`. Broader review: audit all per-turn injections for appropriate activity-gating; consider a leaner "exploration mode" base prompt variant separate from a "combat mode" variant that activates only when `combat_state is not None`. Potentially large token savings on every non-combat turn.

- ~~[ ] **Design a dedicated combat system prompt**~~ — **(moved to Combat System → Tier 1.6)**
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

## Combat System

Combat runs through the existing narrative loop — the LLM drives pacing, the system tracks state. Multiple tiers of fidelity, each independently shippable. Tier 1 is complete; Tiers 1.1 and 1.5 establish HP authority and the interactive attack flow. Tier 1.6 replaces the bolted-on combat injections with a purpose-built combat system prompt before Tier 2 adds mechanical depth.

> **Layout note:** when the CombatPanel is visible it occupies the right column. DicePanel moves to the left column (stacked beneath CharacterSidebar), freeing the right for initiative/HP display. Out of combat the layout reverts to current (CharSidebar left · Chat centre · DicePanel right).

---

### Combat Rules Reference

- [x] **Create `adventure_path/04_rules/combat/` folder** — six PF1e combat reference files created: `attack_rolls.md`, `armor_class.md`, `initiative.md`, `hit_points.md`, `actions.md`, `attacks_of_opportunity.md`. Each follows the skill file format with `**Triggers:**` header and `<!-- REFERENCE -->` payload/reader split. Injection wired in when a `CombatRulesIndex` is built (same pattern as `SkillIndex`).
- [x] **Wire `CombatRulesIndex` injection** — `api/context/combat_lookup.py` built (`CombatRulesIndex`, `CombatRuleMatch`, `_parse_combat_rule_file`); singleton wired in `session_manager.py`; trigger detection runs in `_inject_context` when `combat_state.round > 0`; 22 tests in `test_combat_lookup.py`.

### Tier 1 — Combat Tracker Panel (MVP)

A right-side panel that appears when `session.combat_state` is set and disappears when it is cleared. The LLM writes a `%%COMBAT%%` block each turn to update the state; the UI is read-only.

#### `%%COMBAT%%` block format

Written by the LLM after `%%DELTAS%%` whenever combat is active or just ended. Uses the same indented key-value style as other blocks:

```
%%COMBAT%%
round: 2
combatants:
  - name: Shalelu      · hp: 18/24 · ac: 17 · init: 14 · status: active
  - name: Goblin 1     · hp: 0/5   · ac: 13 · init: 12 · status: unconscious
  - name: Goblin 2     · hp: 5/5   · ac: 13 · init:  8 · status: active
  - name: Thaelion     · hp: 22/22 · ac: 16 · init:  6 · status: active
```

`round: 0` signals combat ended — backend clears `session.combat_state`. If the block is omitted entirely, existing state is preserved (LLM may omit the block between rounds without wiping the tracker). A malformed block (missing `round:` field) is also treated as a parse failure and leaves state unchanged.

#### Backend

- [x] **CB1 — `CombatState` + `Combatant` dataclasses** — `Combatant(name, hp_current, hp_max, ac, initiative, status)` where `status ∈ {active, unconscious, fled, dead}`. `CombatState(round, combatants)`. `Combatant.__post_init__` clamps HP and validates status. `combat_state: Optional[CombatState] = None` field on `GameSession`.
- [x] **CB2 — `%%COMBAT%%` parser** — `_parse_combat_block(text) -> Optional[CombatState]` + `_parse_combatant_line(line) -> Optional[Combatant]`. Return semantics: `CombatState(round=0, combatants=[])` when `round: 0` is present (intentional clear sentinel); `None` on missing block, missing `round:` field, or parse error (preserve existing state — do not wipe on bad LLM output). `_COMBAT_BLOCK_RE` regex for flat-block fallback path. Processed in both section and fallback response paths. `_HAS_SECTION_MARKERS_RE` does **not** include COMBAT (keeping it out prevents COMBAT-only responses from routing to the sections path and leaking raw markup via the NARRATIVE fallback).
- [x] **CB3 — SSE `combat_update` event** — `_serialize_combat_state()` helper; `{"type": "combat_update", "combat_state": <dict|null>}` emitted every turn after `roll_request`. `SseEvent` union in `api.ts` updated with `combat_update` variant.
- [x] **CB4 — `%%COMBAT%%` in system prompt** — COMBAT TRACKER block added to `_build_slim_system_prompt` with format spec and rules. `"\n%%COMBAT%%"` added to `_END_MARKERS` in `_stream_with_narrative_filter`. `DELETE /api/sessions/{id}/combat` endpoint clears `session.combat_state`.

#### Frontend

- [x] **CB5 — Layout: DicePanel moves left** — `combat-active` CSS class on `.main-content` when `combatState !== null`. CSS flex `order` rules: non-combat: sidebar(1)|chat(2)|dice(3); combat: sidebar(1)|dice(2)|chat(3)|combat(4). DicePanel border swaps sides in combat mode.
- [x] **CB6 — `CombatPanel` component** — `ui/src/components/CombatPanel.tsx`. Right column (220 px), shown only when `combatState !== null`. Shows: "⚔ Combat" title + "Round N" badge; initiative list sorted descending; current actor (top) highlighted with gold glow; inactive combatants dimmed; status badges (KO / fled / dead). "End Combat" button calls `DELETE /combat` + clears client state.
- [x] **CB6.1 — CombatPanel active-turn highlight advances** — `currentCombatantName: string | null` state in `App.tsx` tracks the highlighted combatant by name (not by position). Initialised to the highest-initiative active combatant on the first `combat_update` of a new combat. "Next Turn →" button in `CombatPanel` advances the highlight to the next active combatant in initiative order and wraps at the end of the round. Falls back to the first active combatant when `currentCombatantName` is unset. Resets to `null` on combat clear, end session, and kill-end.
- [x] **CB7 — HP bar component** — `ui/src/components/HpBar.tsx`. Green > 66%, amber 33–66%, red < 33%, dark-grey at 0. CSS `transition` for animated width changes on HP update.
- [x] **CB8 — `combatState` in `App.tsx`** — `useState<CombatState | null>(null)`. Updated from `combat_update` SSE events. Cleared on session end and kill-end. `endCombat()` API call in `api.ts`.

#### Tests

- [x] **CB-T1** — `tests/test_combat.py`: 29 tests. Combatant HP clamp + status validation (5); `_parse_combatant_line` happy path + edge cases (6); `_parse_combat_block` happy path + round-0-clear-sentinel + no-round-field-returns-None + empty + None/empty-string + malformed-line-skipped + HP clamp (8); `_serialize_combat_state` None + full shape (2); SSE null-when-no-block + populated + state-persists-and-clears + malformed-block-preserves-state + combat-only-no-leak + filter (6); DELETE endpoint clears state + 404 (2). 482 total passing.

---

### Tier 1.1 — HP Authority Shift

Move HP ownership from the LLM to the backend. In Tier 1 the LLM writes HP values every turn
and inevitably drifts (arithmetic errors, forgetting damage between rounds). Tier 1.1 makes the
backend the single source of truth so Tier 1.5 attack resolution can update HP reliably.

> **Authority model after Tier 1.1:**
> LLM writes: round number, initiative, status (active/unconscious/fled/dead), conditions, new combatants.
> Backend owns: HP values. LLM never writes HP after round 1 — it reads current HP from injected context.

#### Backend

- [x] **CB1.1-1 — HP stripped from `%%COMBAT%%` format after round 1** — on combat start (first turn `session.combat_state` is None), accept HP values from the LLM to initialise `combat_state`. On subsequent turns, parse and discard HP columns from `%%COMBAT%%` lines; backend retains its own HP values. `_parse_combat_block` gains an `existing_state: Optional[CombatState]` parameter — when provided, it copies HP from matching combatants by name instead of using the LLM-written values.
- [x] **CB1.1-2 — `%%COMBAT%%` format update in system prompt** — two spec constants: `_COMBAT_SPEC_ROUND1` (with `hp: cur/max` for initialisation) and `_COMBAT_SPEC_ONGOING` (no HP columns; references `%%HP%%` for deltas). `_inject_context` injects `_COMBAT_SPEC_ONGOING` when `combat_state.round > 0`.
- [x] **CB1.1-3 — HP context injection** — `[CURRENT HP]` block injected into per-turn system content alongside the combat reminder. Lists each combatant with `name: cur/max (status)` so the LLM can narrate accurately without recomputing HP.
- [x] **CB1.1-4 — `%%HP%%` delta block for non-attack HP changes** — `_HP_BLOCK_RE`, `_parse_hp_deltas`, `_apply_hp_deltas` added. Processed in both section-based and flat-block paths after `%%DELTAS%%` and before `%%COMBAT%%`. Block stripped from player token stream (`"\n%%HP%%"` added to `_END_MARKERS`). Silently ignored when `combat_state` is None.

#### Tests

- [x] **CB1.1-T** — `tests/test_combat_hp.py`: 29 tests. HP inheritance (9 cases: init from LLM, preserve from backend, new combatant, case-insensitive, round-0 unaffected, parse-failure still None, backward-compat); `_parse_hp_deltas` (8 cases); `_apply_hp_deltas` (7 cases: damage, healing-clamp, overkill-clamp, unknown-name, multiple, case-insensitive, None-state); HP context injection (2 cases); stream stripping (1 case); full-turn integration (2 cases). 584 total passing (excl. 2 pre-existing test_end_session failures unrelated to this work).

---

### Tier 1.5 — Interactive PC Attack Flow

The player rolls dice for PC attacks; backend auto-rolls for monsters. LLM writes `%%ATTACK%%`
blocks to signal which attacks happen this round (with stats). All dice are resolved before the
LLM is called again — minimising LLM calls during mechanical resolution and eliminating the
chance of the LLM inventing roll outcomes.

> **Flow:**
> 1. LLM writes `%%ATTACK%%` block (one line per attack, in initiative order)
> 2. Backend splits: NPC attacks auto-resolved immediately; PC attacks queued
> 3. NPC results emitted as `attack_result` SSE events
> 4. `attack_request` SSE emitted for first PC attack → player rolls to-hit (d20)
> 5. Hit → `damage_request` SSE → player rolls damage dice
> 6. Miss / damage resolved → advance queue
> 7. Queue empty → all results injected into history → LLM called → response streamed

#### `%%ATTACK%%` block format

```
%%ATTACK%%
- attacker: Goblin 1   · target: Shalelu   · bonus: +4 · damage: 1d4+2 · type: melee
- attacker: Thaelion   · target: Goblin 2  · bonus: +5 · damage: 1d8+3 · type: melee
```

Fields: `attacker` (name), `target` (name), `bonus` (e.g. `+4`, `-1`), `damage` (dice expr), `type` (`melee`|`ranged`|`spell`, default `melee`). Backend identifies PC vs NPC by comparing `attacker` against known PC names from the session. Multiple `-` lines = multiple attacks this round.

#### Backend

- [x] **CB1.5-1 — `_parse_attack_line` + `_parse_attack_block`** — `_ATTACK_BLOCK_RE` regex; same separator pattern as `_parse_combatant_line`; `"\n%%ATTACK%%"` added to `_END_MARKERS`; NOT added to `_HAS_SECTION_MARKERS_RE`.
- [x] **CB1.5-2 — `_roll_dice(expr: str) → tuple[list[int], int]`** — `_DICE_EXPR_RE` regex; `random.randint` per die; invalid expr → `([], 0)`.
- [x] **CB1.5-3 — `PendingAttack` dataclass + session attack queue** — `PendingAttack` dataclass with hit/damage resolution fields; `GameSession` gains `attack_queue: list[PendingAttack]` and `attack_results: list[dict]`.
- [x] **CB1.5-4 — NPC auto-resolution** — `_resolve_npc_attack` rolls d20+bonus vs target AC, applies HP delta via `_apply_hp_deltas`, emits `attack_result` SSE immediately; `_get_combatant_ac` and `_is_pc_attacker` helpers; `_build_attack_history_message` formats results for history injection.
- [x] **CB1.5-5 — `POST /sessions/{id}/resolve_attack_roll`** — `resolve_attack_roll()` function + endpoint; hit path leaves attack in queue for damage; miss path pops queue and returns `next_attack` info.
- [x] **CB1.5-6 — `POST /sessions/{id}/resolve_damage_roll`** — `resolve_damage_roll()` function + endpoint; applies HP delta, pops queue, returns `next_attack` info.
- [x] **CB1.5-7 — `POST /sessions/{id}/resume_combat`** — `stream_resume_combat()` appends attack history message, clears `attack_results`, delegates to `_stream_chat()`; endpoint streams SSE.
- [x] **CB1.5-8 — System prompt update** — ATTACK RESOLUTION section added to `_COMBAT_SPEC_ONGOING`; `conditions:` field documented in format spec.

#### New SSE events

- `attack_request` — `{ type, attacker, target, bonus, ac, damage_expr, attack_type }` — player must roll to-hit
- `attack_result` — `{ type, attacker, target, roll, bonus, total, ac, hit, damage_rolls, damage_total, attack_type, is_pc }` — one per resolved attack

`SseEvent` union in `api.ts`, `AttackResult` + `AttackPhase` in `types.ts` updated.

#### Frontend

- [x] **CB1.5-9 — DicePanel attack flow** — `attackPhase` prop drives to-hit and damage banners; `onAttackRoll`/`onDamageRoll` callbacks in App.tsx call resolve endpoints; auto-resume when `queue_remaining === 0`; stale-closure guard via refs.
- [x] **CB1.5-10 — DicePanel attack history** — `attackLog` prop rendered above skill-roll history; ⚔ prefix, hit/miss badge, damage total shown.
- [x] **CB1.5-11 — CombatPanel condition chips** — `conditions: list[str]` on `Combatant` dataclass; `_parse_combatant_line` parses `conditions: [prone, shaken]` field; `_serialize_combat_state` includes it; `CombatPanel` renders chips with `CONDITION_TOOLTIPS` map (17 PF1e conditions).

#### Tests

- [x] **CB1.5-T** — `tests/test_combat_attacks.py`: 43 tests. `_roll_dice` (6); `_parse_attack_line` (7); `_parse_attack_block` (3); `_is_pc_attacker` (2); `_resolve_npc_attack` (3); `resolve_attack_roll` hit+miss+no-queue (3); `resolve_damage_roll` damage+no-pending (2); `/resume_combat` injects+streams+404+409 (3); SSE integration: NPC+PC split, NPC HP update, stream filter (3); `_build_attack_history_message` hit/miss/negative-bonus/empty/multi (5); multi-attack queue miss-exposes-next/hit-blocks/damage-exposes-second (3); resolve_attack_roll damage-phase guard (1); NPC attack on 0-HP target (1); resume_combat empty results (1). `_get_combatant_ac` (4) and conditions (4) in `test_combat.py`/`test_combat_hp.py`.

---

### Tier 1.6 — Dedicated Combat System Prompt

`_build_slim_system_prompt` is a narrative GM prompt with combat sections bolted on. In combat the
priorities flip: mechanical accuracy trumps tone guidance, NPC knowledge is irrelevant, and the
LLM must not invent any numbers. This tier replaces the current ad-hoc combat injections with a
purpose-built prompt that is shorter in total tokens, more deterministic in its instructions, and
hardened against hallucinated dice outcomes. It is also prerequisite infrastructure for the
`_ENEMY_TURN_DIRECTIVE` used in Tier 1.7 — both are focused modes of the same combat prompt.

> **Authority model after Tier 1.6:**
> The combat prompt owns the section tag set. `_inject_context` branches on `session.combat_state
> is not None` and assembles an entirely different system content block — no NPC profiles, no skill
> profiles, no location profiles, no `%%GENERATE%%`/`%%DELTAS%%`/`%%ROLL%%` specs. Instead it
> injects `[INITIATIVE ORDER]`, `[CURRENT HP]`, `[PC COMBAT STATS]`, and `[ACTIVE CONDITIONS]`.

#### What to strip (vs normal narrative prompt)

| Stripped | Reason |
|---|---|
| `%%GENERATE%%` spec | No new NPC stubs mid-combat; combatants already in `combat_state` |
| `%%DELTAS%%` spec | Knowledge logging can wait until after the fight |
| `%%ROLL%%` spec | Dice go through `%%ATTACK%%` + backend rolls; narrative roll flow not used |
| `%%EVENT%%` | Events re-fire after combat; suppress mid-fight to avoid prompt noise |
| NPC profile injection | Personality and knowledge blocks irrelevant while goblins are swinging |
| Skill context injection | Skills resolved mechanically in combat, not via narrative skill profiles |
| Location profile injection | Tavern ambiance does not matter during a fight |
| GM STYLE block | Mechanical accuracy beats narrative tone guidance in combat |
| `_FORMAT_EXAMPLE` | Does not apply — combat sections differ entirely |
| EVENT MAP | Active event content injected directly; full map suppressed |

#### What to add (vs normal narrative prompt)

| Added | Detail |
|---|---|
| `[INITIATIVE ORDER]` | Sorted combatant list, current actor marked; always injected |
| `[CURRENT HP]` | Authoritative HP for all combatants (promoted to top-level block) |
| `[PC COMBAT STATS]` | Full mechanical stats for every PC: AC, max HP, saves, weapon attacks; backend-authoritative — LLM reads, never writes |
| `[ACTIVE CONDITIONS]` | Non-empty `conditions` per combatant with one-line mechanical effect (e.g. "Prone: −4 AC, −4 ranged") |
| Full `%%COMBAT%%` format | Always present — no hint/fallback; full ongoing-round spec inline |
| `%%ATTACK%%` format | Always present; rules on when to omit |
| `%%HP%%` format | Always present; non-attack HP deltas |
| Anti-hallucination rules | "Never write a d20 result. Never narrate HP values. Never resolve dice yourself. Write `%%ATTACK%%` and let the backend roll." |
| Tight `%%NARRATIVE%%` spec | "1–2 paragraphs max. Physical action and immediate observable result only. No exposition, no foreshadowing." |

#### Section tag set for combat turns

```
[SECTIONS ACTIVE THIS TURN — COMBAT MODE]
%%NARRATIVE%%  — 1–2 paragraphs; physical action + immediate observable result only.
%%COMBAT%%     — always required; full format spec injected above.
%%ATTACK%%     — every attack that occurs this round; omit when no attacks happen.
%%HP%%         — non-attack HP changes only (traps, poison, healing); omit otherwise.
```

- [x] **CB1.6-1 — `_build_combat_system_prompt(session)`** — new builder function alongside
  `_build_slim_system_prompt`. Reads party list and situation from the same files (boot.md /
  recap.md). Replaces GM STYLE with a compact combat-conduct block (resolve declared actions,
  no questioning, no guessing, no invented numbers). Appends anti-hallucination rules and the
  full `%%COMBAT%%` / `%%ATTACK%%` / `%%HP%%` format specs. Does NOT append the EVENT MAP.
  Token target: ≤ 60% of the equivalent narrative prompt at the same session state.

- [x] **CB1.6-2 — `_COMBAT_SECTION_SPECS` constant** — the stripped-down `[SECTIONS ACTIVE THIS
  TURN — COMBAT MODE]` block. Used in place of `_NARRATIVE_SPEC` / `_GENERATE_SPEC` /
  `_DELTAS_SPEC` / `_ROLL_SPEC` when combat is active.

- [x] **CB1.6-3 — `_inject_context` combat branch** — when `session.combat_state is not None`,
  skip all of: `_FORMAT_EXAMPLE` injection, NPC detect + profile inject, skill detect + profile
  inject, location detect + re-inject, `_GENERATE_SPEC`, `_DELTAS_SPEC`, `_ROLL_SPEC`, and
  `_build_turn_directive`. Instead build `system_content` from `_build_combat_system_prompt`
  and append: `[INITIATIVE ORDER]` (sorted descending, current actor marked with `→`),
  `[CURRENT HP]` (existing block, promoted), `[PC COMBAT STATS]` (from `pc_profiles`
  `combat_stats` tier), `[ACTIVE CONDITIONS]` (only when any combatant has non-empty
  `conditions`), and `_COMBAT_SECTION_SPECS`. Active event content still injected directly
  (not the full EVENT MAP). Combat rules lookup (`CombatRulesIndex`) still runs.

- [x] **CB1.6-4 — Token benchmark** — `_build_combat_system_prompt` verified ≤ 60% of
  `_build_slim_system_prompt` at same session state (`test_shorter_than_slim_prompt`).
  Combat branch verified not to inject narrative-only blocks (`_NARRATIVE_SPEC`,
  `_GENERATE_SPEC`) via `TestCombatPromptDoesNotAddNarrativeBlocks`.

- [x] **CB1.6-T — Tests** — `tests/test_combat_prompt.py` (75 tests, all passing):
  `TestCombatSectionSpecs` (8), `TestBuildCombatSystemPrompt` (9), `TestInjectContextCombatBranch`
  (36), `TestPreCombatBranch` (20), `TestCombatPromptDoesNotAddNarrativeBlocks` (2). Existing
  tests in `test_inject_context.py` and `test_combat.py` updated to reflect new combat branch
  behavior (6 tests updated). Total suite: 802 pytest passing.

---

### Tier 1.7 — Combat Flow Control (Enemy Turn)

The LLM currently resolves both player and enemy actions in a single response, giving it too
much authority over pacing. Tier 1.7 splits each combat round into two explicit phases: the
player acts and resolves PC dice, then clicks **Enemy Turn** to trigger enemy actions.

All dice for enemy attacks are rolled server-side — `_resolve_npc_attack` already does this
for auto-resolved NPC attacks in Tier 1.5. The constraint is that the LLM must write `%%ATTACK%%`
blocks for enemy actions rather than inventing outcomes in prose; the backend then rolls and
applies HP deltas. No LLM number invention.

- [ ] **CB1.7-1 — `_ENEMY_TURN_DIRECTIVE` constant** — tightly scoped system injection used by the
  enemy-turn endpoint: *"Enemy phase only. Write `%%NARRATIVE%%` narrating enemy actions. Write
  `%%ATTACK%%` blocks for every NPC who attacks this round. Do NOT resolve PC actions. Do NOT write
  `%%ROLL%%`."* Kept short and unambiguous; prepended to `system_content` in a dedicated helper
  (not mixed into the normal turn injection path). Builds on top of `_build_combat_system_prompt`
  so the LLM still has `[CURRENT HP]` and `[INITIATIVE ORDER]` during the enemy phase.

- [ ] **CB1.7-2 — `POST /sessions/{id}/enemy_turn` endpoint** — calls `stream_enemy_turn(session)`,
  a focused version of `_stream_chat` that injects `_ENEMY_TURN_DIRECTIVE` and processes the LLM
  response identically to a normal turn (`%%ATTACK%%` blocks → `_resolve_npc_attack` → HP delta →
  `attack_result` SSE; `%%COMBAT%%` → `combat_update` SSE; `%%NARRATIVE%%` → `token` SSE). Returns
  409 if `session.attack_queue` is non-empty (PC dice still pending). Returns 404 on unknown session.
  Returns 409 if `session.combat_state` is None (no active combat).

- [ ] **CB1.7-3 — CombatPanel "Enemy Turn" button** — rendered below "End Combat" in `CombatPanel`.
  Enabled when `attack_queue` is empty and not streaming. Disabled with tooltip `"Resolve PC attacks
  first"` while `attackPhase !== null`. App.tsx wiring: `onEnemyTurn` prop on CombatPanel → calls
  `POST /enemy_turn` → SSE stream handled identically to `doResumeCombat` (token/patch_last/
  combat_update/attack_result events; sets `streaming` true/false around the call).

- [ ] **CB1.7-4 — Turn phase label in CombatPanel header** — small badge next to "Round N" showing
  current phase. Derived from existing client state — no new backend field: `attackPhase !== null`
  → **PC Attacks** (amber); `streaming` during enemy turn → **Enemy Turn** (red); otherwise nothing
  shown. Requires a new `enemyTurnStreaming` boolean in App.tsx (separate from `streaming` so the
  normal send button stays unlocked during enemy turn resolution).

- [ ] **CB1.7-5 — End Combat narrative** — clicking "End Combat" currently clears `combat_state`
  silently via `DELETE /combat`. Instead, first stream a focused LLM closure call, then clear.
  New `POST /sessions/{id}/close_combat` endpoint: builds a `_COMBAT_CLOSE_DIRECTIVE` that
  injects the current combat snapshot — surviving enemies with HP/status, party HP — and instructs
  the LLM: *"The player ended combat. Write 1–2 paragraphs narrating how it concludes (escape,
  standoff, surrender, pursuit, or rout). Do NOT write %%COMBAT%%, %%ATTACK%%, or %%ROLL%%."*
  Response streams as normal `token` SSE events. `DELETE /combat` fires only after the stream
  completes. If the LLM call fails or times out, fall back to silent clear (graceful degradation).
  CombatPanel "End Combat" button shows a "Closing…" disabled state during the stream.
  App.tsx: `onEndCombat` calls `POST /close_combat` instead of `DELETE /combat` directly;
  handles the SSE stream (tokens appear in chat), then calls `setCombatState(null)`.

- [ ] **CB1.7-T — Tests** — pytest: `enemy_turn` 200 streams NPC `attack_result` events; 404
  on missing session; 409 while `attack_queue` non-empty; 409 when `combat_state` is None;
  `_ENEMY_TURN_DIRECTIVE` present in system content during enemy-turn call; `%%COMBAT%%` update
  processed; PC `attack_request` events NOT emitted (enemy-only block); `close_combat` streams
  tokens then clears state; `close_combat` 409 when no active combat; fallback-to-silent-clear
  on LLM error. Vitest: "Enemy Turn" button present in CombatPanel; disabled while
  `attackPhase !== null`; `onEnemyTurn` fires on click; phase badge shows/hides correctly;
  "End Combat" shows "Closing…" state during stream.

---

### Tier 1.8 — Conditions and Death

Prerequisite for Tier 2 mechanical depth. Condition chips (CB1.5-11) are display-only; these items give them teeth.

- [ ] **CB1.8-1 — Conditions with mechanical effects** — apply PF1e penalties when a combatant has active conditions. `_apply_condition_effects(combatant)` returns AC modifier and attack modifier: Prone (−4 AC, −4 ranged attack, stand = move action), Shaken (−2 attack/saves/checks), Staggered (one standard or move action per round), Entangled (−2 attack and Reflex, no run/charge), Nauseated (move actions only). Modifiers applied in `resolve_attack_roll` and `_resolve_npc_attack` when computing hit/miss.
- [ ] **CB1.8-2 — Death and dying states** — current status `unconscious` covers 0 HP. PF1e requires graduated states: 0 HP = Disabled (can act, then falls unconscious); negative HP and above −CON = Dying (loses 1 HP/round until stabilised or dead); −CON HP or below = Dead. Backend: on HP update in `_apply_hp_deltas`, derive status automatically from HP and a `constitution` field added to `Combatant`. CombatPanel shows Disabled/Dying/Dead badges distinctly. Dying combatants automatically lose 1 HP per round in `_inject_context` unless stabilised.
- [ ] **CB1.8-3 — Healing in combat** — `%%HP%%` delta blocks already apply negative deltas (damage). Add positive delta support: `(target, +N)` raises HP up to `hp_max`. LLM uses positive deltas for cure spells, channel energy, lay on hands, potion use. `_apply_hp_deltas` already clamps at 0 min; add clamp at `hp_max`.

---

### Tier 1.9 — Initiative Authority

Mirrors Tier 1.1 (HP authority): the LLM currently writes final initiative totals in the
`%%COMBAT%%` block, which means it can hallucinate values, ignore modifiers, or repeat the
same number for every combatant. Tier 1.9 moves initiative rolls to the backend on round 1
and treats the LLM's `init:` field as a **modifier** (e.g. `+3`, `−1`) rather than a total.

> **Authority model after Tier 1.9:**
> - **Round 1:** LLM writes `init: <modifier>` for each combatant. Backend rolls `1d20 +
>   modifier` for every combatant and stores the result. For PCs, the modifier is read from
>   `pc_profiles[*]["combat_stats"]["initiative"]` and the LLM's value is ignored entirely.
> - **Round 2+:** Backend retains its own initiative values; `init:` columns in subsequent
>   `%%COMBAT%%` lines are silently discarded (same pattern as HP authority from Tier 1.1).

- [ ] **CB1.9-1 — `_COMBAT_SPEC_ROUND1` format update** — change `init:` field description
  from "initiative score" to "initiative modifier (e.g. `+3`, `−1`); backend will roll
  `1d20 + modifier`". Update `_COMBAT_SPEC_ONGOING` to state "omit `init:` — backend owns
  initiative order from round 1 onward".

- [ ] **CB1.9-2 — Server-side initiative roll on round 1** — in `_parse_combat_block`, when
  `existing_state is None` (first parse): for each combatant extract the `init:` field as a
  signed integer modifier; roll `random.randint(1, 20) + modifier`; store the result as
  `combatant.initiative`. For PCs (name matches `pc_profiles` key), use the modifier from
  `pc_profiles[name]["combat_stats"]["initiative"]` instead of the LLM-written value.
  `_parse_combatant_line` updated to return the raw `init:` string; conversion and rolling
  happen in `_parse_combat_block` where `existing_state` context is available.

- [ ] **CB1.9-3 — Initiative preserved on round 2+** — in `_parse_combat_block` when
  `existing_state is not None`, copy `initiative` from the matching existing combatant by
  name (same lookup as HP authority). New combatants entering after round 1 still get
  server-rolled initiative from their `init:` modifier field.

- [ ] **CB1.9-4 — `[PARTY ROSTER]` init values updated** — `_build_pc_combat_roster` currently
  writes the raw initiative modifier string (e.g. `+2`). After CB1.9-2 the roster should
  still write the modifier (not a pre-rolled value) so the LLM can copy it into `init:` for
  the backend to roll. No change needed to the roster builder — just confirm the format
  remains a modifier, not a total.

- [ ] **CB1.9-T — Tests** — `test_combat.py`: round-1 block with `init: +3` stores a value
  in `[4, 23]` (d20 + 3); PC name in `pc_profiles` uses stored modifier and ignores
  LLM value; round-2 block preserves existing initiative; new combatant on round 2 gets
  fresh roll; `init: 0` and `init: −1` edge cases; two combatants with the same modifier
  get independent rolls (not the same value). `test_inject_context.py`: `_COMBAT_SPEC_ROUND1`
  no longer describes `init:` as a total.


---

### Tier 1.10 — Combat Turn Auto-Speaker

When the current turn advances in the combat tracker, automatically update the active chat speaker to match:

- [ ] **CB1.10-1 — PC turn → auto-activate speaker** — when the initiative tracker advances to a PC's turn, set that PC as the active character in the chat (same as clicking their portrait). The chat input placeholder and speaker badge update to reflect who is acting.

- [ ] **CB1.10-2 — Enemy turn → show enemy name** — when the turn belongs to an enemy/NPC, display the enemy's name in the speaker area instead of a PC. This is read-only / decorative (no dice rolling from an enemy perspective) but makes the tracker easier to follow at a glance.

- [ ] **CB1.10-3 — Manual override preserved** — if the player manually clicks a different character mid-turn, that selection takes precedence and is not overwritten until the *next* turn advance.

- [ ] **CB1.10-T — Tests** — Vitest: advancing turn to PC sets `activeSpeaker`; advancing to enemy shows enemy name label; manual override is not clobbered on re-render.

---

### Tier 2 — Server-Authoritative State

**The foundational shift: the backend, not the LLM, is the single source of truth for everything displayed on screen.**

Currently, every piece of data the UI shows during combat — who is in the fight, their HP, AC, conditions, whose turn it is — flows through the LLM's `%%COMBAT%%` messages. That means the UI is only as accurate as the LLM's memory. The LLM can drift initiative, forget damage, invent stats, and resurrect dead enemies. This tier ends that dependency.

After this tier:
- `sessions/session_NNN/state.json` is the authoritative record of all game state: combatants, HP, AC, conditions, round, active character, active events. It persists across restarts.
- The LLM reads state via injected `[CURRENT HP]` / `[INITIATIVE ORDER]` blocks. It never writes HP, AC, initiative, or combatant lists directly.
- The `%%COMBAT%%` block is used only on round 1 to introduce new combatants (name + initiative modifier). After that, it is stripped and ignored.
- All state mutations happen through backend endpoints with discrete, validated writes to `state.json`.
- The frontend receives `state_changed` SSE events and reads authoritative state via `GET /api/sessions/{id}/state`. It no longer derives state from LLM token content.

> **Why this overrides Tiers 1.7–1.10 and must come first:** Tiers 1.7–1.10 add features (enemy turn, conditions, initiative rolls, auto-speaker) on top of an LLM-driven state model. If built before this tier, each feature inherits the trust problem and must be rebuilt. This tier provides the stable authority model that all subsequent tiers build on correctly.

#### SA-1 — Full `state.json` schema

Extend `sessions/session_NNN/state.json` (already created in session-state feature) to hold the complete visible game state. Currently it holds `{ mode, round, events, active_character }`. After this item it holds:

```json
{
  "mode": "combat",
  "round": 2,
  "events": ["goblin_attack_starts"],
  "active_character": "Yanyeeku",
  "combatants": [
    { "name": "Yanyeeku",  "hp_current": 18, "hp_max": 22, "ac": 16, "initiative": 14, "status": "active", "conditions": [] },
    { "name": "Goblin 1",  "hp_current": 3,  "hp_max": 5,  "ac": 13, "initiative": 11, "status": "active", "conditions": ["shaken"] }
  ],
  "current_actor": "Yanyeeku"
}
```

`_write_session_state` already writes mode/round/events/active_character. Extend it to serialise `session.combat_state` combatants and `current_actor` whenever combat is active. Cleared (`combatants: []`) when `combat_state` is None.

- [ ] **CB2-SA1 — Extend `_write_session_state`** — include `combatants` array and `current_actor` string (null when no combat). Call site already fires on every `%%COMBAT%%` parse, `%%HP%%` apply, event fire/expiry, and `DELETE /combat`; no new call sites needed.
- [ ] **CB2-SA1-T — Tests** — `test_session_state.py`: combat combatants present in `state.json` after `%%COMBAT%%` parse; HP update reflected; `combatants: []` after combat clear.

#### SA-2 — Encounter pre-load from bestiary

Currently the LLM invents all combatant stats in the first `%%COMBAT%%` block. Replace this: when a new combat starts, the `%%COMBAT%%` block is parsed for combatant *names* only; actual stats (HP, AC, initiative modifier, attack bonus, damage dice, saves) are looked up in `adventure_path/09_monsters/` or `adventure_path/01_npcs/`. If a canonical stat block exists, backend values override anything the LLM wrote. If no file exists for a combatant, the LLM-written values are accepted as a fallback (same as today).

- [ ] **CB2-SA2-1 — `CombatantRegistry` loader** — `api/context/combatant_registry.py`. Reads markdown stat blocks from `adventure_path/09_monsters/` and the `base.md` combat stats from `01_npcs/`. Parses HP, AC, initiative modifier, attack bonus, damage expr. Returns a `CombatantStats` dataclass per name (case-insensitive). Cached at import time (same pattern as `SkillIndex`).
- [ ] **CB2-SA2-2 — Override LLM-written stats on round 1** — in `_parse_combat_block`, after parsing the LLM's combatant lines, look each name up in `CombatantRegistry`. Where a canonical record exists, replace HP/AC with registry values; log a `[REGISTRY OVERRIDE]` debug line. LLM-invented stats still used for combatants with no registry entry (graceful fallback).
- [ ] **CB2-SA2-T — Tests** — registry loads goblin stats from `bestiary/goblin.md`; `_parse_combat_block` uses registry HP, ignores LLM-written HP; fallback to LLM value when no registry entry exists; case-insensitive name match.

#### SA-3 — State read endpoint

- [ ] **CB2-SA3 — `GET /api/sessions/{id}/state`** — returns the full current `state.json` content as JSON. Frontend polls this or uses it to hydrate after a reconnect. Returns 404 on unknown session. Returns the on-disk file if `session.combat_state` is None (social mode). Does NOT trigger a file write — reads from the in-memory `GameSession` serialised on the fly, same structure as `state.json`.

#### SA-4 — Frontend reads state from backend

Replace the pattern where the frontend derives `combatState` from LLM-generated SSE tokens with one where the `combat_update` SSE event is emitted by the backend after its own state write (not by parsing the LLM response). The event carries the same `CombatState` payload as today — the SSE contract does not change — but the data is now authoritative.

- [ ] **CB2-SA4-1 — `combat_update` emitted after state write, not after LLM parse** — `_write_session_state` (or the call sites that call it) emit the `combat_update` SSE event. This means the UI update is driven by the backend's state transition, not by the LLM's text. Existing `combat_update` consumer in `App.tsx` is unchanged.
- [ ] **CB2-SA4-2 — Remove combatant data from LLM token stream entirely** — `%%COMBAT%%` is already stripped from the player-visible token stream in non-dev mode. After this item it is also stripped in dev mode; the dev display instead shows a `[COMBAT STATE UPDATED]` marker so testers can see when a state transition occurred without seeing raw block text.
- [ ] **CB2-SA4-T — Tests** — Playwright: CombatPanel HP values after an attack reflect `state.json`, not LLM token content; `state.json` HP matches CombatPanel display.

#### SA-5 — Deprecate `%%COMBAT%%` for ongoing rounds

After round 1 the LLM no longer needs to write `%%COMBAT%%` blocks. Backend owns round advancement, combatant list, and all numeric fields.

- [ ] **CB2-SA5-1 — System prompt update** — `_COMBAT_SPEC_ONGOING` drops all `%%COMBAT%%` instructions. LLM is told: *"Do not write `%%COMBAT%%` blocks. State is managed by the backend. Write `%%NARRATIVE%%` and `%%ATTACK%%` only."* `_COMBAT_SPEC_ROUND1` retains the combatant-introduction format (names + initiative modifiers + conditions only — no HP or AC; those come from the registry).
- [ ] **CB2-SA5-2 — Parser no longer accepts HP/AC from LLM after round 1** — already partially done via Tier 1.1. This item hardens it: `%%COMBAT%%` blocks on turns where `session.combat_state is not None` are fully ignored for stat fields; only new-combatant lines (names not yet in state) are processed.
- [ ] **CB2-SA5-T** — Tests confirm `%%COMBAT%%` on round 2+ does not mutate HP; new combatant entering round 2 IS added; session state correct after full round trip.

---

### Tier 3 — Advanced Attack Mechanics

Builds on Tier 1.5 and Tier 2. The `%%ATTACK%%` format is already established; Tier 3 adds PF1e mechanical depth.

- [ ] **CB2-1 — Critical hits** — `%%ATTACK%%` line gains optional `crit_range: 18` (default 20) and `crit_mult: 2` fields. Backend: if natural d20 roll ≥ `crit_range`, roll a confirmation attack (same bonus vs same AC); if confirmed, multiply damage by `crit_mult`. `attack_result` event gains `critical: bool`. DicePanel history shows `⚔ CRITICAL HIT (×2)`.
- [ ] **CB2-2 — Iterative attacks** — `%%ATTACK%%` line gains optional `sequence: 1/2/3` field. Parser groups lines by attacker; `sequence` is informational (bonus already accounts for the -5/-10 penalty). Backend resolves each line independently in order. No new resolve flow needed — same queue.
- [ ] **CB2-3 — Combat manoeuvres (CMB/CMD)** — `type: manoeuvre` + `manoeuvre: trip|bull_rush|grapple|disarm|sunder`. Backend: roll CMB vs target CMD (from combatant stats — requires `cmd` field added to `%%COMBAT%%` format). On success, inject corresponding condition into target's next `%%COMBAT%%` update. `attack_result` event includes `manoeuvre` and `success` fields.
- [ ] **CB2-4 — Attack of Opportunity** — `%%ATTACK%%` line gains `trigger: aoo` field. Resolved exactly like a normal attack; `attack_result` event includes `aoo: true`. DicePanel history labels it `⚔ AoO`. No separate flow needed.

---

### Tier 4 — Spells and Area Effects

Extends the combat loop with spell casting, area targeting, and saving throws. No canvas grid —
mechanical depth over visual positioning.

- [ ] **CB3-1 — `%%CAST%%` block** — `spell: Fireball · level: 3 · dc: 14 · save: Reflex · half_on_save: true · targets: [Goblin 1, Goblin 2, Shalelu]`. Backend resolves a Reflex save per target (d20 + target save bonus vs DC); full damage on fail, half on save. Damage rolled once, applied per-target. Emits `save_result` SSE per target + `combat_update`. `%%CAST%%` stripped from player stream.
- [ ] **CB3-2 — Spell slot tracking** — add `spell_slots: { [level]: { max: N, used: N } }` to PC character JSON. CharacterSidebar shows pip rows per spell level. `%%CAST%%` decrements the correct level slot; `slot_update` SSE event; CharacterSidebar updates immediately. Slot state persisted in `session.spell_slots` dict keyed by PC name.
- [ ] **CB3-3 — AoE condition effects** — `%%CAST%%` gains `on_fail_condition: prone` field. Backend applies the condition to failing targets in `combat_state`. Existing condition chip machinery (CB1.5-11) handles display.
- [ ] **CB3-4 — Concentration tracking** — `%%CAST%%` with `concentration: true` sets a `concentrating_on` field on the caster's combatant entry. If the caster takes damage while concentrating, backend automatically queues a Concentration check (DC = 10 or half damage taken, whichever is higher) as a `roll_request` event — same flow as skill checks.

---

## Nice-to-Have

- [ ] **Redesign dice panel** — panel is too large relative to its usage; decide on visibility model and condense the layout
- [ ] Dice panel should always show why the roll is made. As in "X tries to spot..."
- [ ] Dice panel option A — always visible but collapsed to a thin strip, expands on click
- [ ] Dice panel option B — show only when a `roll_request` event is active, hide otherwise
- [ ] **Add clear-history button to dice panel** — small button to wipe the local roll log; no backend call needed (history is UI state only)
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

- [ ] **R1c — Extract `_process_response(response_text, session) -> tuple[str, Optional[dict]]`** — pulls out steps 9–10: section-based parsing (`%%NARRATIVE%%` / `%%ROLL%%` / `%%GENERATE%%` / `%%DELTAS%%`) and the flat fallback path (`%%DELTA%%` / `%%GENERATE%%`). All NPC file writes happen here. Sets `session.pending_roll`. Returns `(display_text, roll_data)` — no SSE yielding inside. Prerequisite: R1a shipped and stable.
- [ ] **R1d — Tests for `_process_response`** *(ship with R1c)* — three cases: (1) section format happy path — correct display_text and roll_data returned; (2) flat fallback — roll block stripped from display_text; (3) no markers — raw text returned unchanged. Plus extend `test_turns.py` golden-path test: mock Groq, assert SSE event order is `context → token(s) → patch_last → roll_request`.
- [ ] **R1e — Complete orchestrator: `_stream_chat` → ~40 lines** *(ship after R1c is stable in play)* — `_inject_context` is already wired; replace the remaining inline response-parsing block with a call to `_process_response`. Validate with R1d integration test.
- [ ] **R3 — Provider dispatch is duplicated** — Groq/Ollama branching in payload building, streaming, `_call_blocking`, and token options. Adding a third provider means touching all four. Propose per-provider modules with `build_payload` / `iter_stream` functions sharing a common signature
- [ ] **R5 — Global lazy indexes** — `_npc_index` / `_skill_index` are module globals mutated by `_invalidate_npc_index()`. Encapsulate in an `IndexRegistry` with `get_npc()`, `get_skill()`, `invalidate_npc()`. Makes state explicit and tests easier to write.
- [ ] **R6 — Timestamp formats scattered** — `%H:%M:%S`, `%Y%m%d_%H%M%S`, `%Y-%m-%d %H:%M:%S` appear in six-plus places. Add `_ts_file()` and `_ts_human()` helpers alongside the existing `_ts()`.
- [ ] **R7 — `_write_npc_delta` mixes concerns** — does Layer 2 stub creation, status block append, knowledge append, scene_npcs update, and three log calls. Extract `_append_status_block()` and `_append_knowledge_items()`; keep `_write_npc_delta` as orchestrator.
- [ ] **R8 — Duplicate `%%ROLL%%` parsing** — roll logic written once for the section path and once for the flat fallback path. Normalise the fallback to a section dict first, then run the same downstream parser..
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
- [ ] Hide sidebar (left) and dice panel (right) when not in a session — both panels are visible on the splash screen but serve no purpose before boot
- [ ] Make sidebar character icons bigger
- [ ] Splash portrait click opens character sheet — same behaviour as "Open Sheet" in session
- [ ] Add fun rotating hints to splash screen — PF1e flavour or adventure-specific
- [ ] Normalize all player JSON files to one agreed UI schema and keep them synchronized with the markdown sheets.
- [ ] Audit Ani's data and other player records for internal inconsistencies before relying on them in UI or prompts.
- [ ] Add a small sync tool or documented workflow for copying approved sheet changes into UI JSON files.
- [ ] Review portraits, colors, runes, and labels so presentation data is consistent across all characters.
- [x] **Open the character action menu to the right of the avatar** — menu rendered via `ReactDOM.createPortal` into `document.body` with `position: fixed` and coordinates from `getBoundingClientRect()` on the wrap element. This bypasses the sidebar's `overflow-y: auto` clipping context. `z-index: 1000` ensures it floats above all other panels. Click-outside handler updated to also check the portaled menu ref. `data-placement="right"` attribute added for testability. 2 Vitest tests added to `CharacterSidebar.test.tsx`. *(spec: `character-system.feature` AC-012)*
- [x] **Quick d20 from pending-roll banner** — clicking the skill/DC box above the dice grid (the `roll-request-prompt` area) immediately fires a single d20 roll, applying the auto-bonus if enabled. Does not affect the manual dice queue. The hint text reads "click to roll d20".
- [x] **Active character UX — sidebar split** — split the avatar click action into two: "Set Active" and "Open Sheet" (character-system.feature AC-007). Rename existing `activeCharacter` state in `App.tsx` to avoid collision with sheet-open state.
- [x] **Active character UX — halo and input badge** — show halo/ring on the active avatar in the sidebar (AC-008). Show small portrait badge and "Speaking as \<Name\>" label near the input bar (AC-009).
- [x] **Active character UX — speaker tag in chat** — prefix sent input with `@<Name>:` when an active character is set; render without prefix when no character is active (AC-010).
- [x] **Dice skill bonus — auto-apply modifier** — when a pending skill roll is active and an active character is set, auto-compute `finalTotal = d20 + skillModifier` and submit that to `/resolve_roll`. Show breakdown in roll history, e.g. `1d20(13) + Perception +7 = 20 vs DC 18` (dice-panel.feature AC-007).
- [x] **Dice skill bonus — toggle and fallback** — add "Auto-apply skill bonus" toggle (default ON) in the dice panel. When unmapped skill or no active character, fall back to raw roll and show a visible indicator (AC-008, AC-009, AC-010, AC-011).
- [x] Remove the functionality where the diceroll goes to the input field. *(Removed `rollInjection` state and InputBar injection props; roll now appears as a local player speech bubble in the chat showing raw roll, bonus, and final total. Not sent to backend as a turn.)*

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

- [ ] **Monitor event firing in real sessions** — verify the LLM fires events at the right narrative moments and does not double-fire or skip. N=5 turns TTL is a starting point; tune against observed sessions. Also watch whether the CORRECT/WRONG examples in the prompt fully eliminate the double-write behavior over time.
- [x] **Spec — `%%EVENT%%` block format** — `specs/event-injection.feature` written: 8 ACs, inline syntax `%%EVENT%% <id>`, single event per response, TTL-only expiry.
- [x] **Event content files** — `adventure_path/02_events/` created with `goblin_attack_starts.md`, `fire_phase_begins.md`, `cavalry_arrives.md`, `attack_repelled.md`. Format: metadata header above `<!-- INJECT -->`, injectable content below.
- [x] **`EventIndex`** — `api/context/event_index.py`: `EventEntry` dataclass, `EventIndex` with lazy load, `get()`, `event_map_text()`, `_parse_event_file()`. Singleton + `_get_event_index()` in `session_manager.py`.
- [x] **Session state** — `ActiveEvent` dataclass (`event_id`, `content`, `turns_remaining`) added. `active_events: list` field on `GameSession`. TTL decremented in `_inject_context`; expired entries removed.
- [x] **Parser** — `_EVENT_LINE_RE` regex; fires in both section-based and flat-block paths. Duplicate check (no TTL reset), unknown-ID guard (silent ignore).
- [x] **Injection** — active event content injected in `_inject_context` alongside NPC/skill/location blocks. `%%EVENT%%` added to streaming filter `_END_MARKERS` (hidden from player). Event map appended to system prompt via `_build_slim_system_prompt`.
- [x] **Tests** — `tests/test_event_injection.py`: 24 tests. Covers EventIndex loading, file parsing, event map text, firing, unknown ID, duplicate TTL, expiry, injection presence, expiry suppresses injection, SSE active_events list, player-hidden token stream, and double-write regression (LLM writes bare `%%EVENT%%` then `%%EVENT%% <id>` — see known quirk note below).
- [x] **Live-testing bugs found and fixed** — two issues discovered during manual testing:
  - *Prompt format:* `%%EVENT%%` was listed in RESPONSE STRUCTURE like other section markers, so the LLM wrote it as a section header with explanation text below, never putting the ID on the same line. Fixed: rewritten as `SCENE EVENT (optional — not a section header)` with explicit `CORRECT` / `WRONG` examples including the exact double-write pattern.
  - *Regex false match:* `_EVENT_LINE_RE = r'^%%EVENT%%\s+(\S+)'` — in multiline mode `\s+` consumes a newline, causing the second `%%EVENT%%` marker to be captured as the ID when the LLM double-writes. Fixed: `(\S+)` → `([A-Za-z]\w*)` (event IDs always start with a letter; the marker itself starts with `%`).

---

## Housekeeping

- [x] Decide what to do with `facets/FACET_*.md` — absorbed the 7 non-empty facets into a `GM STYLE` section in `_build_slim_system_prompt()`; deleted all 13 facet files and the `facets/` directory. Empty facets were superseded by the `%%ROLL%%` format block already in the prompt.
- [x] Review and clean `adventure_path/90_shared_references/temp.md` — almost certainly stale.
- [x] Delete `AGENTS.md` — documents the old `src/agents/gm_boot_agent.py` architecture that no longer exists. Only referenced once in `ADVENTURE.md` as a link. Remove the file and the link.
