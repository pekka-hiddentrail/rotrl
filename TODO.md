# Project Todo

This file is a working backlog for the RotRL automation project. Items are grouped by area and ordered roughly by impact.

**Every time this file is updated, the open items should be at the top of the list, done should be middle and "obsolete" are at the bottom.**

---

## GM and Session Flow

- [ ] Make sure the DCs for rolls are from NPC stats AND supplemented by the skill file.
- [ ] Make player identity loading consistent across code paths; current boot logic still expects some optional files in different locations than the repo uses.
- [ ] Route boot and recap generation to `llama-3.3-70b-versatile` and normal turns to `llama-3.1-8b-instant` — add a per-call-type model override in `_stream_groq`.
- [ ] Fix prompt spec gaps — three small changes to `_build_slim_system_prompt`: (1) add `personality:` field to `%%GENERATE%%` block spec (code already reads it, model never writes it); (2) add "skip `%%GENERATE%%` for NPCs already in the scene" rule; (3) add "at most one `%%ROLL%%` block per response" constraint.
- [ ] Move the format example below a `<!-- REFERENCE -->` marker in the system prompt — it is currently injected on every turn (~500 chars). Same mechanism used by skill files. The model has already learned the format; the example only needs to be loaded at boot.
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

## Event Injection System (`%%EVENT%%`)

Event-triggered context injection. When the LLM decides a scene condition is met, it writes `%%EVENT%%` with an event ID. The code loads the corresponding content and injects it for N turns (currently N=5). Separate from `%%DELTAS%%` which is for persistent state — events are transient and time-bounded.

> **Open design question:** N=5 turns is a starting point. Needs tuning against real sessions. Also deferred: full content → compressed summary mid-window.

- [ ] **Spec — `%%EVENT%%` block format** — define the response block syntax the LLM writes. Decide: single-line (`%%EVENT%% goblin_attack_starts`) or block form with fields. Add to the response structure spec in `_build_slim_system_prompt`. Document in `specs/`.
- [ ] **Event content files** — create `adventure_path/08_events/` directory and write injectable content files for the four Swallowtail events: `goblin_attack_starts.md`, `fire_phase_begins.md`, `cavalry_arrives.md`, `attack_repelled.md`. Each file: compact, prompt-ready, covers what the LLM needs for that event window.
- [ ] **`EventIndex`** — new class in `api/context/event_index.py`. Loads `08_events/`, maps event ID → content. Same pattern as `LocationIndex`. Add lazy-loaded singleton `_event_index` + `_get_event_index()` to `session_manager.py`.
- [ ] **Session state** — add `active_events: list` to `GameSession` (list of `ActiveEvent` dataclass: `event_id`, `content`, `turns_remaining`). Each turn: decrement all, remove expired.
- [ ] **Parser** — extend `_parse_response_sections` (or add a sibling) to extract `%%EVENT%%` blocks from LLM responses. On detection: look up content via EventIndex, append to `active_events`.
- [ ] **Injection** — in `_inject_context`, include active event content in the system payload alongside NPC/skill/location context. Expired events are already gone; no extra cleanup needed at injection time.
- [ ] **Tests** — unit tests for EventIndex loading, parser extraction, turn countdown/expiry, injection presence, and the full round-trip (event fires → content injected → expires after N turns).

---

## Adventure Content

The adventure is ~80% narrative infrastructure and ~20% mechanical execution. The items below are what's missing before a real session can run without the GM improvising from nothing. Priority order: things that block the first session come first; things that enrich later sessions come last.

### Act I — Swallowtail Festival (levels 1–2)

- [x] **Verify and complete bestiary files** — `goblin.md`, `goblin_commando.md`, and `goblin_warchanter.md` confirmed complete: AC, HP, attacks, combat scripts, morale thresholds, XP values all present.
- [ ] **Festival encounter sequence** — `FESTIVAL_ENCOUNTER.md` created: three-wave raid script, Aldern rescue moment, Hemlock arrival timing, civilian rescue beat, aftermath state changes.
- [x] **Aldern Foxglove introduction** — `base.md` verified complete (rescue hook, hunting trip, estate reference present); `knowledge.md` exists as session tracking log (correct format); backstory seed content lives in `base.md`.

### Act II — Shadows in Sandpoint (levels 2–3)

- [ ] **Catacombs of Wrath — dungeon document** — `CATACOMBS.md` created: 7-room prose layout, 5 sinspawn encounters, Runewell chamber with cross-reference to LOCATIONS.md, full treasure and XP tables, Karzoug name drop in Room 2, Sihedron Rune callback in Room 7.
- [ ] **Sinspawn stat block** — `adventure_path/02_campaign_setting/bestiary/sinspawn.md` created: AC 14, HP 16, claws+bite, sinful bite (Will DC 12 or wrath compulsion), wrathful strike, GM narrative notes.
- [ ] **Glassworks investigation sequence** — `GLASSWORKS.md` created: three entry hooks, room-by-room layout (main floor/office/upper floor), Tsuto encounter, Ameiko rescue, journal content, Catacombs entrance discovery, full aftermath.
- [x] **Tsuto Kaijitsu combat stats** — added to `05_npcs/tsuto_kaijitsu/base.md`: monk 7, CR 6, AC 20, HP 42, full attack line, surrender condition, loot (journal).

### Act III — Thistletop (levels 3–4)

- [ ] **Thistletop — dungeon document** — `THISTLETOP.md` created: Nettlewood approach, rope bridge mechanics, full surface level (throne room, barracks, guard post, stables, trapdoor), Thassilonian level (entry passage sinspawn, Lyrie's library, yeth hound corridor, Nualia's sanctum, Runewell chamber), clearing conditions, Ameiko aftermath beat.
- [x] **Nualia Tobyn — combat stats** — added to `05_npcs/nualia_tobyn/base.md`: cleric 4/barbarian 3, CR 7, AC 20, HP 62, spell list, aura of madness, demon claw, full combat script, redemption condition, loot (journal bridges to Book II).
- [ ] **Thistletop goblin roster** — `05_npcs/thistletop_roster/base.md` created: Ripnugget (fighter 4, gecko mount, surrender), Bruthazmus (bugbear ranger 4, Ameiko connection, turning), Orik Vancaskerkin (fighter 4, mercenary, turning conditions), Lyrie Akenja (wizard 4, library intelligence, cooperation conditions), Stickfoot.
- [ ] **Additional bestiary entries** — `goblin_dog.md` (CR 1, Goblin Pox disease, morale); `yeth_hound.md` (CR 3, Bay DC 13, flight, DR 5/silver). Warchanter variant already complete.

### Secondary NPCs

The existing "Sandpoint NPC skeletons" backlog item is correct but needs priority ordering. The 70+ secondary NPCs referenced in SANDPOINT_LOCATIONS.md have no `05_npcs/` files. Do these in tiers:

- [ ] **Tier A — encounter anchors** (players will meet these in Act I regardless of what they do): Naffer Vosk (boneyard groundskeeper — relevant when PCs investigate the Tobyn crypt), Brodert Quink (town sage — the only person who can explain Thassilonian runes), Savah Bevaniky (armory — equipment, Act I context), Risa Magravi (Hagfish tavern — rumours, Sczarni colour), Shayliss Vinder (General Store — Ven Vinder subplot). Write `base.md` for each: name, role, one-sentence personality, location anchor, and what they know that's plot-relevant.
- [ ] **Tier B — district colour** (players will encounter if they explore): Hannah Velerin (healer, White Deer district), Das Korvut (blacksmith, grief subplot), Ven Vinder (General Store owner, protective father), Banny Harker (lumber mill, Act II body discovery), Ibor Thorn (lumber mill partner). Same format as Tier A.
- [ ] **Tier C — background presence** (can be invented on demand but benefit from anchors): remaining shop owners, militia deputies, festival vendors. Batch these as a single lightweight file `adventure_path/05_npcs/_SANDPOINT_SECONDARY.md` listing name/role/location for each — not full base.md files, just enough to prevent contradiction.

### Location Coverage

- [ ] **Brodert Quink's home/study** — add `adventure_path/07_locations/quinks_house/base.md`. Players will go here to research Thassilonian runes in Act II. Needs: description (crowded with maps and artifacts), what he can tell them (Sihedron Rune meaning, Thassilon's sin-magic system), and what he doesn't know (the Runewell's current state). The knowledge injection makes this a much richer scene than the LLM improvising a generic scholar.
- [ ] **The Hagfish** — add `adventure_path/07_locations/hagfish/base.md`. Risa's tavern is the rough-end counterpart to the Rusty Dragon — different social class, Sczarni presence, rumour economy. Players will contrast the two inns early. Aliases: hagfish, risa's, the fish.
- [ ] **Sandpoint Mercantile League / Valdemar Building** — add `adventure_path/07_locations/sandpoint_mercantile/base.md`. Economic power centre; the Valdemars and Scarnettis matter for faction pressure in Act II.
- [ ] **Remaining high-traffic locations** — audit SANDPOINT_LOCATIONS.md and create `base.md` files for the next 5–8 buildings players are most likely to enter: General Store (Vinder's), Cathedral Rectory, Fatman's Feedbag, Town Hall interior, and the Jail. Each follows the existing template.

### Skill Files

- [x] **Expand skill coverage beyond the current five** — Added 8 new skill files: Knowledge (Local), Knowledge (Religion), Knowledge (History), Knowledge (Planes), Knowledge (Arcana), Knowledge (Nature), Knowledge (Nobility), Stealth. All RAW-complemented with `<!-- REFERENCE -->` separator. `_SKILL_TEMPLATE.md` created for future additions. `SkillIndex` auto-discovers all files; no code changes needed.
- [x] **Knowledge (history) and Knowledge (planes)** — Both added. Knowledge (Planes) covers outsiders (removed from Religion); Knowledge (History) covers Thassilonian lore. Both include 10+CR creature identification tables and library exception for untrained use.

### Session Pacing

- [ ] **Session zero checklist** — create `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/SESSION_ZERO.md`. What the GM needs before session 1: player character files loaded, session 1 boot file prepared, leveling milestones known, faction pressures initialised at 0. This is a pre-flight checklist, not rules content.
- [ ] **Encounter budget per session** — document in ACT_STRUCTURE.md: Act I is approximately 2–3 sessions (festival attack + aftermath + investigation hook). Act II is 3–5 sessions depending on Catacombs depth. Act III is 2–4 sessions for Thistletop. Knowing this prevents the LLM from burning through an act in a single exchange or dragging it over ten.

---

## NPC Lifecycle and Knowledge

- [ ] Carry `scene_npcs` forward into the next session's boot file — `session.scene_npcs` is in-memory only and lost when the session ends. On `stream_end_session`, append the active NPC list to `sessions/session_NNN+1/boot.md` so the next session starts with those NPCs already in context. Without this the GM starts cold every session regardless of what was in-flight.
- [ ] Surface the list of detected-but-not-yet-stubbed names from `scene_npcs` somewhere visible (log or UI) so the GM can verify the model caught them.
- [ ] Write `%%GENERATE%%` summary field to NPC knowledge — the `summary:` field in `%%GENERATE%%` blocks is parsed but silently dropped. Write it as the first entry in the new NPC's `knowledge.md`: `- [world] {summary} — S{session:03d} T000`. Bootstraps the NPC's knowledge file immediately.
- [ ] Single-word NPC name detection — `_detect_narrative_npcs` regex requires two Title Case words (`r'\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b'`). Known NPCs with single-word canonical names (e.g., "Aldern", "Lonjiku") are never auto-tracked. Fix: add an exact-match pass against `_get_npc_index().known_npcs` canonical names; keep the two-word heuristic for unknown-NPC suspicion only.
- [x] Location tracking — `%%GENERATE%%` blocks with `type: location` now create stubs in `adventure_path/07_locations/` (previously logged and skipped). `LocationIndex` singleton (`api/context/location_lookup.py`) detects location aliases and injects profiles per-turn. `scene_locations` persists location context across turns. 8 seed locations written for Act I. 43 tests in `tests/test_location_lookup.py`. *(spec: `specs/location-system.feature`, 9 ACs)*
- [ ] **Sandpoint NPC skeletons** — populate `05_npcs/` with skeleton `base.md` files for 50–75% of named Sandpoint NPCs. A skeleton needs: name, role/occupation, one-line physical description, one-line personality, key relationships, and location (which building/district they frequent). No stat blocks, no deep backstory — just enough that the GM never has to invent a bartender from scratch. Source from `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/NPCS.md` and `SANDPOINT_LOCATIONS.md`. Priority order: (1) named NPCs already referenced in session logs or the book's Tier I/II list; (2) location anchors (innkeeper, blacksmith, sheriff's deputy, temple acolytes); (3) recurring faces (market vendors, festival organisers).
- [x] Promote auto-created session NPCs to permanent records via a lightweight review workflow. *(session NPCs now live in dot-prefixed directories under `05_npcs/`; rename the directory to drop the dot to promote. UI "Purge NPCs" button bulk-deletes all dot-prefixed dirs via `DELETE /api/npcs/session`.)*
- [x] Update NPC knowledge and memory state after each session, including attitude shifts, known facts, suspicions, and unresolved goals. *(per-turn `%%DELTA%%` blocks written to `session_NNN.md` per NPC; delta files cleared on session boot)*
- [x] Write structured NPC deltas per turn with multi-line knowledge support. *(`%%DELTAS%%` section uses bracket blocks, one per NPC; `knowledge:` lines collected as a list; `_write_npc_delta` helper extracted)*
- [x] Auto-create NPC stub when a `%%DELTAS%%` block references an unknown NPC (Layer 2 fallback). *(if `npc_dir_for` returns `None`, `_process_generate_block` is called with stub data before writing the delta)*
- [x] Detect NPCs introduced in narrative text without any structured block (deferred Layer 3). *(`_detect_narrative_npcs` scans completed narrative for Title Case name pairs, adds to `session.scene_npcs`; stub creation is deferred until the model writes a `%%DELTAS%%` block for that name)*
- ~~[ ] Create a new location function when the LLM returns new generated locations.~~ *(superseded by "Location tracking" item above which is more complete)*

---

## Knowledge and State Management

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

## Character Data and UI Content

- [ ] Open the "character action menu" to the right side of the character avatar.
- [ ] Normalize all player JSON files to one agreed UI schema and keep them synchronized with the markdown sheets.
- [ ] Audit Ani's data and other player records for internal inconsistencies before relying on them in UI or prompts.
- [ ] Add a small sync tool or documented workflow for copying approved sheet changes into UI JSON files.
- [ ] Review portraits, colors, runes, and labels so presentation data is consistent across all characters.
- [x] **Active character UX — sidebar split** — split the avatar click action into two: "Set Active" and "Open Sheet" (character-system.feature AC-007). Rename existing `activeCharacter` state in `App.tsx` to avoid collision with sheet-open state.
- [x] **Active character UX — halo and input badge** — show halo/ring on the active avatar in the sidebar (AC-008). Show small portrait badge and "Speaking as \<Name\>" label near the input bar (AC-009).
- [x] **Active character UX — speaker tag in chat** — prefix sent input with `@<Name>:` when an active character is set; render without prefix when no character is active (AC-010).
- [x] **Dice skill bonus — auto-apply modifier** — when a pending skill roll is active and an active character is set, auto-compute `finalTotal = d20 + skillModifier` and submit that to `/resolve_roll`. Show breakdown in roll history, e.g. `1d20(13) + Perception +7 = 20 vs DC 18` (dice-panel.feature AC-007).
- [x] **Dice skill bonus — toggle and fallback** — add "Auto-apply skill bonus" toggle (default ON) in the dice panel. When unmapped skill or no active character, fall back to raw roll and show a visible indicator (AC-008, AC-009, AC-010, AC-011).
- [x] Remove the functionality where the diceroll goes to the input field. *(Removed `rollInjection` state and InputBar injection props; roll now appears as a local player speech bubble in the chat showing raw roll, bonus, and final total. Not sent to backend as a turn.)*

---

## Code Quality / Refactoring

- [ ] **R1c — Extract `_process_response(response_text, session) -> tuple[str, Optional[dict]]`** — pulls out steps 9–10: section-based parsing (`%%NARRATIVE%%` / `%%ROLL%%` / `%%GENERATE%%` / `%%DELTAS%%`) and the flat fallback path (`%%DELTA%%` / `%%GENERATE%%`). All NPC file writes happen here. Sets `session.pending_roll`. Returns `(display_text, roll_data)` — no SSE yielding inside. Prerequisite: R1a shipped and stable.
- [ ] **R1d — Tests for `_process_response`** *(ship with R1c)* — three cases: (1) section format happy path — correct display_text and roll_data returned; (2) flat fallback — roll block stripped from display_text; (3) no markers — raw text returned unchanged. Plus extend `test_turns.py` golden-path test: mock Groq, assert SSE event order is `context → token(s) → patch_last → roll_request`.
- [ ] **R1e — Complete orchestrator: `_stream_chat` → ~40 lines** *(ship after R1c is stable in play)* — `_inject_context` is already wired; replace the remaining inline response-parsing block with a call to `_process_response`. Validate with R1d integration test.
- [ ] **R3 — Provider dispatch is duplicated** — Groq/Ollama branching in payload building, streaming, `_call_blocking`, and token options. Adding a third provider means touching all four. Propose per-provider modules with `build_payload` / `iter_stream` functions sharing a common signature.
- [ ] **R4 — `_NAME_EXCLUDE_WORDS` maintenance burden** — 40+ hardcoded words. Load from `adventure_path/00_system_authority/name_exclude_words.txt` (one per line, `#` comments). Fall back to hardcoded set if file absent. GM-tunable without touching Python.
- [ ] **R5 — Global lazy indexes** — `_npc_index` / `_skill_index` are module globals mutated by `_invalidate_npc_index()`. Encapsulate in an `IndexRegistry` with `get_npc()`, `get_skill()`, `invalidate_npc()`. Makes state explicit and tests easier to write.
- [ ] **R6 — Timestamp formats scattered** — `%H:%M:%S`, `%Y%m%d_%H%M%S`, `%Y-%m-%d %H:%M:%S` appear in six-plus places. Add `_ts_file()` and `_ts_human()` helpers alongside the existing `_ts()`.
- [ ] **R7 — `_write_npc_delta` mixes concerns** — does Layer 2 stub creation, status block append, knowledge append, scene_npcs update, and three log calls. Extract `_append_status_block()` and `_append_knowledge_items()`; keep `_write_npc_delta` as orchestrator.
- [ ] **R8 — Duplicate `%%ROLL%%` parsing** — roll logic written once for the section path and once for the flat fallback path. Normalise the fallback to a section dict first, then run the same downstream parser.
- [ ] **F6 — Configurable tunables via env vars** — `_GROQ_MAX_HISTORY`, `_GROQ_MAX_SYSTEM_CHARS`, `_GROQ_RETRY_BASE`, `_DEV_MAX_HISTORY`, `_FULL_MAX_HISTORY` are hardcoded. Read from env with fallback: `int(os.getenv("GROQ_MAX_HISTORY", "10"))` etc.
- [x] **R1a — Extract `_inject_context(session) -> tuple[str, dict]`** — steps 1–5 of `_stream_chat` extracted: history trimming, Groq truncation, NPC/skill/location detection, `scene_npcs` accumulation, delta-reminder path. Returns `(system_content, context_info)`; `context_info["history"]` carries the trimmed message list. Wired into `_stream_chat` immediately — orchestrator now calls `_inject_context` and unpacks the result. *(Note: signature changes in M4 — function will write to `session.context_blocks` instead of returning a string.)*
- [x] **R1b — Tests for `_inject_context`** — 30 tests in `tests/test_inject_context.py` covering all five pipeline steps: history trimming per provider/mode, Groq truncation, NPC/skill/location match → profile injection + scene_npcs update, dedup of location-vs-name matches, delta-reminder when scene_npcs active but no new context, and full `context_info` key structure.
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

- [ ] **M5 — First-class roll turns in `session.chat`** — `log_roll()` appends `ChatTurn(role="roll", ...)` to `session.chat` with character, expression, individual rolls, and total. `resolve_roll()` updates that turn with `dc`, `passed`, and outcome text. `serialize_messages()` renders roll turns as `{"role": "user", "content": "[ROLL RESULT] Ani — Diplomacy — rolled 14+4=18 vs DC 12 — passed"}`. The GM now sees roll outcomes in history on the next turn automatically. **Closes "Feed resolved roll outcome into next GM turn directive"** and **"Update player character knowledge."** Tests: roll turn appears in serialized messages; outcome text correct for pass and fail.

- [ ] **M6 — Chat history summarization** — when the number of `user`/`gm` turns in `session.chat` exceeds a threshold (default 20), compress the oldest N turns into a `ChatTurn(role="summary", content="...", turns="1-11")`. Initial implementation: deterministic concatenation with truncation, no LLM call. `serialize_messages()` injects the summary as a single user turn (`"[SESSION SUMMARY — turns 1–11]\n..."`) before the active window. Threshold and window size configurable via env vars (see F6). **Closes "Plan message history summarization"**. Tests: 25-turn chat serializes to summary + last 10 turns; summary is stable (same input = same output).

---

## Runtime and Tooling

- [ ] **View Log — surface API call logs in the UI** — the current "View Log" button opens the session markdown log (`GET /api/sessions/{id}/log`). Extend or add a second view so the GM can browse `outputs/api_log/` from the UI without leaving the browser: a file list (newest first) and a JSON viewer for the selected entry. Key fields to surface prominently: `first_token_ms`, `duration_ms`, `section_format_ok`, `usage.total_tokens`, and `status`. The endpoints (`GET /api/log/api` and `GET /api/log/api/{filename}`) already exist. Decide whether to replace the current log button, add a tab, or open a separate panel.
- [ ] Document the exact local startup and recovery workflow for Windows, including port cleanup and Ollama checks.
- [ ] Session crash recovery — sessions are purely in-memory; a server restart during play loses `session.messages`, `scene_npcs`, `pending_roll`. After each turn, write a recovery snapshot to `outputs/sessions/{session_id}_snapshot.json`. On startup, detect orphaned snapshots and offer recovery.
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

## Quality and Testing

- [ ] **E2E — Playwright UI test suite** — add Playwright to `ui/` (`npm install -D @playwright/test`). Cover the seven key flows with a mocked backend (MSW or a lightweight FastAPI fixture): (1) boot → session badge appears; (2) send turn → GM message streams in; (3) `roll_request` event → dice panel activates; (4) end session → chat clears; (5) Kill button on stuck ending → inline confirm → UI resets to pre-boot; (6) Purge NPCs button → inline confirm → toast notification; (7) character sidebar → sheet modal opens. These are the regression cases that break silently on UI refactors and are invisible to pytest.
- [ ] **Vitest — Character data and sheet AC coverage** — add tests for `character-system.feature` AC-001 through AC-006 and remaining AC-010/AC-011 integration: static JSON loading/failure, HP bar colors, sheet modal close behavior, stat/spell tooltips, spell grouping, active speaker persistence, and backend/chat prefixing in `App`.
- [ ] **Vitest — Header/session controls AC coverage** — add tests for `session-controls.feature` AC-001 through AC-008 plus `llm-providers.feature` AC-001/AC-005: provider/model switching, pre/post-boot control visibility, boot disabled state, View Log target, purge inline confirm/toast, rate-limit badge, and Kill inline confirm/abort reset.
- [ ] **Vitest — Chat and turn UI AC coverage** — add tests for `chat-display.feature` AC-001 through AC-006 and `player-turn.feature` AC-001/AC-005: immediate player bubble, thinking indicator, token append/cursor, intro markdown rendering, autoscroll, streaming disabled state, and end-session status bubble updates.
- [ ] **Vitest — IntentBar AC coverage** — add component tests for `intent-bar.feature` AC-001 through AC-005: 52-character truncation, NPC/skill/location tags, null tags, detecting state, and no-context-event diagnostic.
- [ ] Test the full end-session SSE stream with mocked Groq — verify status events arrive in order, recap and boot files are written, and the session is removed from memory. *(critical)*
- [ ] Test turn input validation at the API boundary — confirm the error event is returned and no message is appended to session history when input is rejected. *(high)*
- [ ] Test `_enforce_recap_header` against real LLM output samples collected from past sessions to catch title/date extraction edge cases. *(high)*
- [ ] Test the roll endpoint writes the correct expression and total to the log, including multi-die breakdowns (e.g. 3d6 showing individual rolls). *(low)*
- [ ] Add a test fixture representing a corrupt or partially-written log file and assert the parser either recovers gracefully or raises a clear error. *(low)*
- [ ] Add contract tests for the SSE event shape — assert that every event emitted by boot, turn, and end-session has a `type` field and matches the known union of types. *(low)*
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
