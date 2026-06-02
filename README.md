# RotRL: Agentic GM System

A FastAPI + React system that runs Pathfinder 1st Edition adventures with an AI Game Master. The GM agent manages narrative, NPCs, skill checks, combat tracking, and persistent world state. Groq is the primary LLM provider (fast, cloud-hosted); Anthropic (Claude) and Ollama are also supported.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Python](https://python.org/) | 3.9+ | Add to PATH during install |
| [Node.js](https://nodejs.org/) | 18+ | Includes npm |
| [Groq API key](https://console.groq.com/) | — | Free tier is sufficient for play |
| [Anthropic API key](https://console.anthropic.com/) | — | Optional — for Claude models |
| [Ollama](https://ollama.com/) | latest | Optional — offline fallback only |
| Git | any | To clone the repo |

---

## Setup (new machine)

### 1. Clone the repo

```bash
git clone <repo-url>
cd rotrl
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Windows note:** if `pip` isn't found, try `python -m pip install -r requirements.txt`

### 3. Install frontend dependencies

```bash
cd ui && npm install && cd ..
```

### 4. Set your API keys

Create a `.env` file in the project root (it is git-ignored):

```
GROQ_API_KEY=gsk_your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here   # optional — only needed for Claude models
```

> Get a free Groq key at [console.groq.com](https://console.groq.com/). The `llama-3.1-8b-instant` model is fast and free. Anthropic keys require a paid account.

### 5. (Optional) Pull an Ollama model

Only needed if you want to run without internet access:

```bash
ollama pull qwen3:4b
```

---

## Running the system

### Quickest way — single command

```bash
python dev.py
```

This runs the backend pytest suite, then starts the backend and UI together with colour-coded output. Press **Ctrl-C** to stop both. Run the frontend Vitest and Playwright suites separately with `cd ui && npm run test` / `npm run test:e2e`.

```bash
python dev.py --skip-tests   # skip pytest and start immediately
```

### Manual — three terminals

**Terminal 1 — FastAPI backend:**

```powershell
# Windows
.\start_backend.ps1
```
```bash
# Mac / Linux
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

> **Windows notes:** Always `python -m uvicorn`, not bare `uvicorn`. Always `--host 127.0.0.1` — Vite's proxy requires explicit IPv4. Do **not** use `--reload` in production; `start_backend.ps1` kills whatever is on port 8000 before starting.

> **Stale port cleanup:** Both `start_backend.ps1` (port 8000) and `start_ui.ps1` (port 5173) kill any existing listener and fail fast if the port stays held. `python dev.py` does the same for both ports before launching, and uses `taskkill /F /T` on exit so uvicorn's `--reload` child worker is not orphaned.

**Terminal 2 — Vite dev server:**

```powershell
# Windows
.\start_ui.ps1
```
```bash
# Mac / Linux
cd ui && npm run dev
```

**Terminal 3 — Ollama (only if using the Ollama provider):**

```bash
ollama serve
```

### Open the UI

Navigate to **http://localhost:5173** in your browser.

---

## Playing a session

1. **Configure** — pick provider (`groq` recommended), model, session number; uncheck **Dev** for real play
2. **Boot Session** — the system builds the GM's context (no LLM call at this step); click the button and wait for the ready signal
3. **Type your first action** in the input bar and press **Enter** — this triggers the first GM response
4. **Roll dice** when prompted; the UI shows a dice panel. Rolling produces a player speech bubble in chat (e.g. *"Yanyeeku rolled a 13. With bonus of +7 it is a total of 20."*) and automatically submits the result to the backend. If a character is active and the skill is mapped, the modifier is added automatically (toggle in the panel to override)
5. **Combat** — when the LLM writes a `%%COMBAT%%` block, a live initiative tracker appears in the right column (DicePanel shifts left). It shows HP bars, AC, initiative order, status badges, and a phase badge for PC attacks or enemy turns. When a PC attacks, an attack banner appears in the DicePanel — click to roll d20 (to-hit), then pick dice and click **Roll Damage** on a hit. For enemies, click **Enemy Turn** to run a focused backend-mediated enemy action; the backend resolves AC, attack rolls, damage, and HP. Click **End Combat** to stream a short closure narration and clear the panel; the LLM can also signal end-of-combat by writing `round: 0`
6. **View Log** — opens the live session markdown log in a new browser tab (shown during an active session)
7. **API Logs** — opens an in-app overlay listing recent LLM call log files. Click any entry to see a summary bar (`status` · `section_format_ok` · `first_token_ms` · `duration_ms` · `total_tokens`) plus the full JSON payload. Escape or click outside to close
8. **End Session** — generates a recap and next-session boot file; all NPC state is already written per-turn. If it gets stuck (LLM hangs), click **Kill** next to the "Ending…" button — inline confirm, then state is force-reset without saving a recap
9. **Purge NPCs** — shown on the pre-boot screen; deletes all auto-created session NPC stub directories (dot-prefixed). A toast shows how many were removed

### Rate limit badge

After each Groq turn, a compact badge appears in the header showing remaining per-minute quota (e.g. `⚡ 4,500/6,000 TPM · 28/30 RPM`). Hover for reset times. When the daily limit is exhausted, the error message from Groq is surfaced directly in the UI.

### Response sections

The GM response is structured internally into sections that are stripped before you see them:

| Section | What it does |
|---------|-------------|
| `%%NARRATIVE%%` | The prose you read — streamed token-by-token |
| `%%ROLL%%` | Triggers a dice panel with skill, DC, success/failure text |
| `%%GENERATE%%` | Creates a new NPC stub file on disk |
| `%%DELTAS%%` | Writes updated disposition/location/knowledge to each NPC's file |
| `%%EVENT%%` | Signals a scene transition — injects event content into context for N turns |
| `%%COMBAT%%` | Updates the live initiative tracker (`round`, HP, AC, initiative, status per combatant); `round: 0` clears the panel |
| `%%HP%%` | Non-attack HP changes (traps, poison, healing) — `delta: -N` per named combatant; applied by backend immediately |
| `%%ATTACK%%` | One line per attack this round — `attacker · target · bonus · damage · type`; NPC attacks auto-resolved, PC attacks queued for player dice |
| `%%ACTION%%` | Focused enemy-turn response — `action`, `target`, `weapon`/`ability`/`movement`, and `reason`; parsed by the backend and stripped from player-facing text |

In **dev mode** all markers are visible in the stream so you can see the raw output, including `%%EVENT%%` tags. In full mode the stream filter forwards only narrative text and hides control sections such as `%%EVENT%%`.

### Output files and directories

| Path | When created | Contents |
|------|-------------|----------|
| `outputs/*.log.md` | At session boot | Timestamped markdown: system prompt, every exchange, dice rolls |
| `outputs/api_log/*.json` | Per turn | Full LLM request + response payload. Key fields: `first_token_ms` (ms to first streamed token), `section_format_ok` (true if `%%MARKER%%` sections present), `duration_ms`, `usage.total_tokens`, `status` |
| `sessions/session_NNN/recap.md` | On End Session | Player-facing recap for the next session's intro card |
| `sessions/session_NNN+1/boot.md` | On End Session | GM-facing continuity brief for the next session's system prompt. Includes a `## NPCs Active at Session End` section — read by `create_session` to restore `scene_npcs` on next boot |
| `adventure_path/01_npcs/<slug>/session_NNN.md` | Per turn (per NPC) | NPC disposition, location, knowledge written after each interaction |
| `adventure_path/01_npcs/.<slug>/` | On `%%GENERATE%%` | Session-NPC stub directory (dot-prefix = temporary). Rename to `<slug>/` to promote to permanent. Purge all via **Purge NPCs** or `DELETE /api/npcs/session`. |

---

## Dev mode vs full mode

| | Dev mode | Full mode |
|-|----------|-----------|
| Stream filter | All tokens visible (markers shown, including `%%EVENT%%`) | Only `%%NARRATIVE%%` streamed; control sections such as `%%EVENT%%` are hidden |
| History sent | last **6** messages | last **10** (Groq) / **30** (Ollama) messages |
| `patch_last` event | Suppressed (raw text stays in UI) | Sent (strips markers from display) |
| System prompt | Same full prompt | Same full prompt |

> **Dev mode does not shorten the system prompt.** It only changes what the stream filter forwards to the browser and whether the raw response is replaced in the UI. Use it when you need to see the GM's structured output.

---

## Project Structure

```
rotrl/
├── api/
│   ├── main.py                    # FastAPI routes
│   ├── session_manager.py         # Sessions, LLM streaming, NPC/skill RAG,
│   │                              # section parsing, delta writes, end-session recap
│   ├── api_logger.py              # Per-turn LLM call logging to outputs/api_log/
│   └── context/
│       ├── npc_lookup.py          # NpcIndex — detect NPC names, inject full profile (skill active) or short stub
│       ├── skill_lookup.py        # SkillIndex — detect skill triggers, inject rules
│       ├── location_lookup.py     # LocationIndex — detect locations, inject scene profiles
│       ├── event_index.py         # EventIndex — load 02_events/, inject on %%EVENT%% tag
│       └── combat_lookup.py       # CombatRulesIndex — detect combat triggers, inject PF1e rules (active combat only)
│
├── ui/                            # Vite 5 + React 18 + TypeScript
│   └── src/
│       ├── App.tsx                # Session state, SSE event handling
│       ├── api.ts                 # SSE fetch helpers + SseEvent types
│       ├── types.ts
│       └── components/
│           ├── Header.tsx         # Logo + controls (column layout); rate-limit badge
│           ├── ChatWindow.tsx     # Message list + thinking indicator
│           ├── InputBar.tsx       # Player input textarea
│           ├── IntentBar.tsx      # NPC/skill context + scene NPC chips (fixed bottom)
│           ├── CharacterSidebar.tsx
│           ├── CharacterSheet.tsx
│           ├── DicePanel.tsx      # Dice roller + attack banners (to-hit / damage) — feeds result back to API
│           ├── CombatPanel.tsx    # Live initiative tracker (visible during combat)
│           ├── HpBar.tsx          # HP bar with colour thresholds (green/amber/red/grey)
│           ├── CoverageMatrix.tsx # Feature AC coverage + code-line coverage modal (two tabs)
│           └── ApiLogPanel.tsx    # In-app API call log browser (list + JSON detail view)
│
├── adventure_path/
│   ├── 00_system_authority/       # Non-negotiable GM rules — adjudication, PF1e scope
│   ├── 07_world_setting/          # Golarion/Varisia lore
│   ├── 05_campaign_setting/       # RotRL structure, factions, tone
│   ├── 06_books/                  # Adventure modules (Book I Act I complete)
│   ├── 08_persistence/            # Session ledger
│   ├── 01_npcs/                   # NPC stubs — hand-crafted or auto-created per turn
│   ├── 04_rules/skills/           # Skill files — trigger words + rules text for RAG
│   ├── 03_locations/              # Location profiles (read by LocationIndex at runtime)
│   ├── 02_events/                 # Event files — fired by %%EVENT%% tag, injected for N turns
│   ├── 09_monsters/               # Generic monster stat blocks (AC, HP, attacks, morale, XP)
│   └── 90_shared_references/      # Shared reference tables
│
├── players/
│   ├── player_01/
│   │   ├── character_sheet.md     # Name, class, stats
│   │   └── player_knowledge.md    # Facts this player's character knows
│   ├── PLAYER_CHARACTERS.md
│   └── PLAYER_LIMITS_AND_EXPECTATIONS.md
│
├── sessions/                      # Continuity files per session
│   └── session_001/
│       ├── boot.md                # GM-facing brief (loaded into system prompt)
│       ├── intro.md               # Player-facing intro card
│       └── recap.md               # Generated at end of prior session
│
├── specs/                         # Feature specs (Gherkin-style ACs)
│
├── COMBAT.md                      # How combat tracking works end-to-end
├── TESTING.md                     # Manual exploratory testing guide
├── outputs/                       # Runtime-generated — git-ignored
│   ├── *.log.md                   # Live session logs
│   └── api_log/                   # Per-turn LLM payloads
│
├── tests/                         # 944 pytest tests
├── ui/src/components/__tests__/    # Vitest component tests
├── ui/src/__tests__/               # Vitest App SSE integration tests
├── ui/e2e/                         # Playwright browser-flow tests
│
├── dev.py                         # One-command dev startup (pytest → API + UI)
├── start_backend.ps1              # Windows: start FastAPI backend
├── start_ui.ps1                   # Windows: start Vite dev server
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Liveness check — returns `{"status": "ok"}` |
| `GET`  | `/api/characters` | Return all player characters as a JSON array (reads `ui/public/data/`) |
| `GET`  | `/api/intro` | Player-facing intro card for a session (intro.md → recap.md fallback) |
| `POST` | `/api/sessions` | Create session, build system prompt; streams `done` SSE event |
| `GET`  | `/api/sessions/{id}` | Session info (model, message count) |
| `POST` | `/api/sessions/{id}/turn` | Send player input; streams GM response via SSE |
| `GET`  | `/api/sessions/{id}/log` | Return live session log as plain text |
| `POST` | `/api/sessions/{id}/roll` | Record a dice roll expression and result into the log |
| `POST` | `/api/sessions/{id}/resolve_roll` | Resolve pending roll: compare `rolled` against DC, record outcome |
| `POST` | `/api/sessions/{id}/resolve_attack_roll` | Submit player's d20 to-hit roll; returns `{ hit, damage_expr, queue_remaining, next_attack }` |
| `POST` | `/api/sessions/{id}/resolve_damage_roll` | Submit player's damage dice; applies HP delta, returns `{ damage_total, queue_remaining, next_attack }` |
| `POST` | `/api/sessions/{id}/resume_combat` | Inject resolved attack results into history and stream LLM narration |
| `POST` | `/api/sessions/{id}/enemy_turn` | Run the current enemy actor through a focused LLM call; streams narrative, `attack_result`, `combat_update`, and `done` |
| `POST` | `/api/sessions/{id}/close_combat` | Stream a short combat-closing narration, then clear combat state and emit `combat_update: null` |
| `POST` | `/api/sessions/{id}/end` | Generate recap + next-session boot; streams status events via SSE |
| `DELETE` | `/api/sessions/{id}` | Discard session without recap (emergency close) |
| `DELETE` | `/api/sessions/{id}/combat` | Clear active combat state immediately (direct API fallback; UI uses `close_combat`) |
| `POST` | `/api/sessions/{id}/combat/advance_turn` | Advance initiative to next active combatant; writes state.json; returns `{ current_actor, is_pc }` |
| `POST` | `/api/sessions/{id}/combat/roll_initiatives` | Roll d20 + modifier for every combatant; re-sort initiative; returns `{ combat_state }`. Called automatically on round 1 when a combat event fires; also available as a debug endpoint |
| `GET`  | `/api/code-coverage` | Serve `outputs/code_coverage.json` produced by `pytest --cov`; used by the Coverage modal's "Code Lines" tab |
| `GET`  | `/api/npcs/session` | List all session NPC slugs (dot-prefixed directories) |
| `DELETE` | `/api/npcs/session` | Purge all session NPC directories; invalidates the NPC index |
| `GET`  | `/api/log/api` | List recent LLM call log files (newest first, optional `?limit=N`) |
| `GET`  | `/api/log/api/{filename}` | Return a single LLM call log as JSON |

All streaming endpoints use Server-Sent Events. Each event is a JSON object with a `type` field:

| Event type | When emitted |
|-----------|-------------|
| `token` | Each streamed text chunk |
| `patch_last` | After processing — replaces last message with cleaned text (non-dev only) |
| `roll_request` | When a `%%ROLL%%` block is parsed (includes skill, dc, success, failure) |
| `rate_limits` | After each Groq turn — per-minute RPM/TPM remaining + reset times (Groq only) |
| `combat_update` | After every turn — carries serialised `CombatState` or `null`; drives CombatPanel visibility |
| `attack_request` | When a PC attack is queued — `{ attacker, target, bonus, ac, damage_expr, attack_type }`; activates DicePanel to-hit banner |
| `attack_result` | After each auto-resolved NPC attack — `{ attacker, target, roll, bonus, total, ac, hit, damage_rolls, damage_total, attack_type, is_pc }` |
| `context` | Injected NPC/skill/location context for the turn; includes `scene_npcs` list (all NPCs currently tracked in scene) |
| `status` | Progress messages during end-session generation |
| `error` | Any recoverable error; 429 daily-limit errors include the Groq message verbatim |
| `done` | End of stream; includes `session_id` on boot |

---

## Testing

There are three local test layers: backend `pytest` tests, frontend `Vitest` tests, and browser-level `Playwright` E2E tests.

```bash
python -m pytest -q               # run all backend tests
python -m pytest tests/test_groq_provider.py -q   # run one file
```

```bash
cd ui
npm run test                      # run all frontend Vitest tests once
npm run test:watch                # watch frontend tests during UI work
npm run test:e2e                  # run Playwright browser-flow tests
npm run test:e2e:ui               # run Playwright in interactive UI mode
npx playwright test --config playwright.live.config.ts  # live UI + backend + LLM flow checks
```

If Playwright reports a missing browser binary after a fresh install, run `cd ui && npx playwright install chromium`.

`python dev.py` runs the backend pytest suite before starting the API and UI. It does not run Vitest or Playwright, so use `npm run test` and `npm run test:e2e` from `ui/` before merging frontend changes.

**Backend:** 940+ pytest tests passing across 28 test files:

| File | Covers |
|------|--------|
| `test_sessions.py` | Session lifecycle endpoints, boot, turn, delete |
| `test_turns.py` | Turn streaming, Ollama mock, error cases |
| `test_boot_prompt.py` | System prompt assembly, party extraction, situation loading, delta cleanup; dynamic-fragment constants (`_FORMAT_EXAMPLE`, `_COMBAT_FULL_SPEC`) absent from static prompt; section specs absent from static (moved to per-turn injection) |
| `test_groq_provider.py` | `_groq_post` retry logic, 429 handling, `stream_options` 400 fallback, streaming, max-history, rate-limit SSE event, `first_token_ms` capture |
| `test_api_logger.py` | LLM call log file format, usage field, summary truncation, `first_token_ms`, `section_format_ok` |
| `test_api_logs.py` | Log list and fetch endpoints, path traversal rejection |
| `test_response_sections.py` | `_parse_response_sections`, `_parse_bracket_blocks`, section marker detection |
| `test_skill_lookup.py` | Trigger detection, longest-match, word boundary, `_parse_skill_file` |
| `test_npc_lookup_extended.py` | `detect_all`, `lookup`, status/knowledge reads, `_parse_base` |
| `test_inject_context.py` | `_inject_context` per-turn system prompt assembly, NPC short-stub vs full-profile selection (skill gate), no-location-NPC-injection, skill/location/event injection, context metadata, turn-1 format example injection, full combat spec injection when active, conditional section specs (ROLL/DELTAS gated on detection), PC narrative+mechanical profile injection, PC combat roster injected on round-1 spec with `active_events` |
| `test_end_session.py` | `_parse_turns_from_log`, `_enforce_recap_header`, `stream_end_session` errors |
| `test_stream_filter.py` | `_stream_with_narrative_filter` — dev pass-through, narrative extraction, split tokens |
| `test_narrative_guard.py` | `%%NARRATIVE%%` buffer+retry guard — valid section passes first time, missing NARRATIVE triggers retry, tokens from failed attempt not emitted, exhausted retries proceed as-is, flat-format bypasses guard, retry notice written to session log |
| `test_recap_header.py` | Recap header normalization edge cases |
| `test_log_parser.py` | Log turn parsing |
| `test_npc_generator.py` | `generate_base_md`, NPC stub creation |
| `test_character_data.py` | Character JSON field validation (`/api/characters` endpoint, index file, HP/level/abilities/saves/wealth/weapons/spells per character) |
| `test_intro.py` | Intro file resolution and fallback |
| `test_event_injection.py` | `EventIndex` loading, `%%EVENT%%` parsing, TTL expiry, duplicate guard, event map, SSE `active_events`, double-write regression, `EventEntry.event_type` metadata (AC-009) |
| `test_location_lookup.py` | `LocationIndex` loading, alias detection, `<!-- REFERENCE -->` boundary, profile injection, scene re-injection, session-generated location stubs |
| `test_dev_startup.py` | `dev.py` startup hardening — `_pid_on_port`, `_port_free`, `_kill_tree`, `_free_port` |
| `test_combat.py` | `Combatant`/`CombatState` dataclasses, HP clamp + status validation, `_parse_combatant_line`, `_parse_combat_block` (incl. round-0 sentinel and parse-failure semantics), `_serialize_combat_state`, `combat_update` SSE, narrative filter stripping, malformed-block-preserves-state regression, combat-only-no-leak regression, `DELETE /combat` endpoint |
| `test_config_tunables.py` | F6 env-var-configurable tunables (default values, type checks, override reads); R4 `_load_name_exclude_words` (file loading, comment/blank-line stripping, fallback on missing/empty file, case normalisation) |
| `test_scene_npc_tracking.py` | `NpcIndex.canonical_for` (explicit alias, auto-word alias, unknown word, case-insensitive); single-word `_detect_narrative_npcs` Pass 1 (known alias → scene_npcs, dedup, exclude-word skip, unknown word ignored); `scene_npcs` in `context_info` (present, empty list, copy semantics); boot persistence (`_parse_scene_npcs_from_boot`, `stream_end_session` appends section, `create_session` restores) |
| `test_session_state.py` | `sessions/state.template.json` shape and defaults; `_write_session_state` produces valid JSON with all 5 keys (mode, round, events, active_character, combatants); combat start/clear updates mode/round/combatants; combatant fields (name, hp_current, hp_max, ac, initiative, status, conditions) serialised correctly; HP-after-damage reflected; combatants cleared on combat end; `set_active_character` persists across state changes; boot overwrites stale state. 42 tests. *(spec: session-state.feature AC-001 through AC-017)* |
| `test_combat_lookup.py` | `CombatRulesIndex` loading, trigger detection, longest-match, word boundary, `_parse_combat_rule_file`, `<!-- REFERENCE -->` boundary, `format_context` |
| `test_combat_attacks.py` | All 9 attack-resolution ACs: `_roll_dice`, `_parse_attack_line/block`, `_is_pc_attacker`, `_resolve_npc_attack`, `resolve_attack_roll`, `resolve_damage_roll`, `stream_resume_combat`, multi-attack queue, `attack_result`/`attack_request` SSE, stream filter, endpoint HTTP guards (404/409) |
| `test_roll_initiatives.py` | All 9 roll-initiatives ACs: `roll_combat_initiatives`, PC/enemy modifier, `current_actor` set to highest active, `state.json` written, endpoint guards, `_parse_event_combatants` (table parsing, missing section, malformed), `pending_combatants` seeding/clearing, auto-roll detection on round-1 combat event |
| `test_enemy_turn.py` | Enemy-turn Tier 1.7: `%%ACTION%%` parser, focused enemy-turn query, short enemy system prompt, backend-resolved attack/delay streams, endpoint guards, close-combat stream and silent-clear fallback |
| `test_token_benchmark.py` | Real-API token benchmark — boots Anthropic Haiku, runs three fixed turns, appends prompt/completion/total token counts to `outputs/token_benchmarks.csv`; automatically skipped when `ANTHROPIC_API_KEY` is absent (`@pytest.mark.benchmark`) |
| `test_prompt_audit.py` | Verifies `scripts/build_coverage.py` produces `outputs/coverage.json` with the expected `summary.total`, `summary.covered`, `summary.gap` keys and correct row schema |

**Frontend:** 230+ Vitest tests passing across 15 test files (run separately — `cd ui && npm run test`):

Recent streaming regressions are covered explicitly: `test_stream_filter.py` asserts dev mode passes raw `%%EVENT%%` tokens while full mode hides them, `test_event_injection.py` asserts event tags do not leak to player-visible non-dev chat, `ChatWindow.test.tsx` covers empty GM bubbles with three thinking dots, and `App.enemy-turn.test.tsx` covers the enemy-turn pre-token loading state.

| File | Covers |
|------|--------|
| `App.test.tsx` | App-level SSE integration — boot flow, provider/model switching, send-turn event order (`context`, `token`, `patch_last`, `roll_request`, `rate_limits`), speaker payload prefixing, purge/View Log/Kill controls, streaming lockout, error bar, session end cleanup, combat-active layout (AC-006), attack resolution wiring (`handleAttackRoll` → damage phase, `handleDamageRoll` → resume, `doResumeCombat` auto-trigger, AC-009 multi-attack banner switch, `attack_type` regression) |
| `App.enemy-turn.test.tsx` | Tier 1.7 App wiring: Enemy Turn stream state, tokens, `attack_result`, `combat_update`, 409 error handling, and close-combat stream clearing |
| `App.roll-initiatives.test.tsx` | AC-009 App wiring: `handleRollInitiatives` click → `rollInitiatives` API → `setCombatState` + `setCurrentCombatantName`; error message shown and state unchanged on API failure |
| `CombatPanel.test.tsx` | AC-007 initiative order + `combatant-current`/`combatant-inactive` CSS; AC-008 End Combat callback + disabled prop; AC-009 `HpBar` colour thresholds (green/amber/red/grey via inline style); AC-012 condition chips, title tooltips, empty conditions |
| `CombatPanelEnemyTurn.test.tsx` | Tier 1.7 CombatPanel controls: Enemy Turn button, disabled PC-attack state, PC Attacks/Enemy Turn phase badges, and Closing state |
| `DicePanelAttack.test.tsx` | AC-002/003/004/008 attack banners — to-hit (attacker/target/AC/bonus/active-class/`onAttackRoll`), damage (HIT line/expr/Roll Damage enabled), null phase, attack log (hit/miss badges, PC/NPC labels, log-before-skill-history order), V8 `onDamageRoll` receives rolled values not die sides |
| `ChatWindow.test.tsx` | Thinking indicator, GM streaming cursor, intro markdown rendering, autoscroll |
| `Header.test.tsx` | Pre/post-boot controls, provider model options, boot disabled state, View Log handler, purge/Kill inline confirms, rate-limit badge, Benchmarks button, Coverage button |
| `IntentBar.test.tsx` | 52-char truncation, NPC/skill/location tags, null tags, detecting state, missing-context diagnostic |
| `CharacterSheet.test.tsx` | Modal close behavior, sheet sections, AC/save/spell tooltips, spell grouping |
| `CharacterSidebarHealth.test.tsx` | Portrait/title display and HP bar thresholds |
| `characters.test.tsx` | `useCharacters` API load success, HTTP failure, fetch rejection |
| `DicePanel.test.tsx` | Dice roll UI, history, DC resolution, pending-roll display, quick-roll from banner (AC-012) |
| `InputBar.test.tsx` | Send/Enter behavior, disabled state, speaker badge, roll injection |
| `CharacterSidebar.test.tsx` | Character action menu, active speaker halo, loading state |
| `ApiLogPanel.test.tsx` | API log browser: list view (empty state, row rendering, filename parsing, close behaviours), detail view (status/format/latency/token badges, JSON block, back navigation, error path) |
| `MessageBubble.test.tsx` | Player speaker labels, portrait fallback, clean player content, GM bubble invariants |
| `SplashHint.test.tsx` | Hint pool integrity, initial display, timed rotation, no immediate repeats, fade class |

**E2E:** 13 mocked Playwright tests plus 11 live Playwright tests passing in Chromium:

| File | Covers |
|------|--------|
| `e2e/app-flows.spec.ts` | Mocked-browser flows: boot badge, send turn, roll request, end session cleanup, Kill stuck ending, Purge NPCs toast, character sheet modal |
| `e2e/combat-flow.spec.ts` | CT-E2E-001a/b/c: `combat_update` SSE → CombatPanel renders in initiative order + `combat-active` layout; HP bar CSS colour shift across two rounds; End Combat fires `DELETE /combat` and panel disappears |
| `e2e/enemy-turn.spec.ts` | Mocked-browser Tier 1.7 flows: boot into combat, run Enemy Turn and update HP, block Enemy Turn during PC attack prompts, stream close-combat narrative before clearing tracker |
| `e2e/live-flows.spec.ts` | Live backend + LLM flows: boot/session format checks, log API, end-session recap, character sidebar, generated NPC directory creation, Purge NPCs directory removal, goblin event trigger, combat tracker, dice-panel roll resolution |

---

## Architecture

### Session lifecycle

```
POST /api/sessions
  └─ create_session()
       ├─ delete this session's NPC delta files (session_NNN.md per NPC)
       ├─ clear NPC knowledge files (session 1 only — full reset)
       ├─ _build_slim_system_prompt() — reads players/, sessions/session_NNN/boot.md
       ├─ _parse_scene_npcs_from_boot() — restores scene_npcs from boot.md if section present
       └─ yields: done SSE event with session_id   (no LLM call)

POST /api/sessions/{id}/turn  (repeated each exchange)
  └─ stream_turn()
       ├─ validate input
       ├─ inject context into system prompt copy:
       │    NpcIndex.detect()      → inject NPC profile(s) if mentioned
       │    SkillIndex.detect()    → inject skill rules if triggered
       │    scene_npcs → inject profiles of NPCs active in scene
       ├─ trim message history to provider limit
       ├─ stream LLM response token-by-token
       │    _stream_with_narrative_filter() → only %%NARRATIVE%% reaches player
       │    Groq: capture x-ratelimit-* headers → emit rate_limits SSE event
       ├─ parse complete response:
       │    %%ROLL%%     → set pending_roll, yield roll_request event
       │    %%GENERATE%% → create new NPC stub in adventure_path/01_npcs/.<slug>/
       │    %%DELTAS%%   → write NPC status + knowledge files
       │    %%EVENT%%    → add event to active_events (TTL=5 turns); silently ignored if unknown or duplicate
       │    %%COMBAT%%   → update session.combat_state (round=0 clears; malformed block preserves existing state)
       │    %%HP%%       → non-attack HP deltas (traps, poison, healing) applied via _apply_hp_deltas
       │    %%ATTACK%%   → NPC attacks auto-resolved (_resolve_npc_attack → HP delta + attack_result SSE);
       │                   PC attacks queued (PendingAttack) → attack_request SSE emitted per PC attack
       ├─ yield combat_update SSE event (serialised CombatState dict or null)
       └─ yield patch_last (non-dev), append to history

POST /api/sessions/{id}/resolve_attack_roll
  └─ resolve_attack_roll(session, rolled) → { hit, damage_expr, queue_remaining, next_attack }
       ├─ hit=True  → attack stays in queue (damage pending); attackPhase → 'damage' in UI
       └─ hit=False → attack removed from queue; result appended to attack_results

POST /api/sessions/{id}/resolve_damage_roll
  └─ resolve_damage_roll(session, rolls, total)
       ├─ applies HP delta to target via _apply_hp_deltas
       ├─ removes attack from queue; appends to attack_results
       └─ returns { damage_total, queue_remaining, next_attack }

POST /api/sessions/{id}/resume_combat
  └─ stream_resume_combat(session)
       ├─ _build_attack_history_message(attack_results, round) → [ATTACK RESULTS — round N] injected
       ├─ attack_results cleared
       └─ LLM called; streams combat_update + token SSE events

POST /api/sessions/{id}/enemy_turn
  └─ stream_enemy_turn(session)
       ├─ _build_enemy_turn_query(session, current_actor) → focused one-enemy briefing
       ├─ LLM writes %%NARRATIVE%% + %%ACTION%% only
       ├─ backend parses action and resolves attack/damage/HP with authoritative AC
       └─ streams token, attack_result, combat_update, done

POST /api/sessions/{id}/close_combat
  └─ stream_close_combat(session)
       ├─ injects current combat snapshot into a short closure prompt
       ├─ streams player-facing closure narrative
       └─ clears combat_state, attack queue/results, writes state.json, emits combat_update null

POST /api/sessions/{id}/end
  └─ stream_end_session()
       ├─ _parse_turns_from_log() — extract PLAYER/GM turns from log
       ├─ blocking LLM call → player-facing recap text
       ├─ _enforce_recap_header() → canonical header
       ├─ write sessions/session_NNN/recap.md
       ├─ blocking LLM call → GM-facing boot brief for next session
       ├─ append ## NPCs Active at Session End to boot text (if scene_npcs non-empty)
       └─ write sessions/session_NNN+1/boot.md
```

### Per-turn context injection (RAG)

No vector database. Every turn, keyword lookups and active-event TTL checks run before the LLM call:

1. **NPC lookup** — `NpcIndex` scans for alias matches against `adventure_path/01_npcs/*/base.md`. Matching NPC's profile (minus `<!-- REFERENCE -->` section) is prepended to system content.
2. **Skill lookup** — `SkillIndex` scans for trigger words against `adventure_path/04_rules/skills/*.md`. Longest-match trigger wins; skill rules are prepended.
3. **Scene NPCs** — NPCs accumulated in `session.scene_npcs` (from `%%DELTAS%%` writes + `_detect_narrative_npcs` scan) have their current status injected so the GM knows their last known state. `_detect_narrative_npcs` runs two passes: Pass 1 matches single Title Case words (≥4 chars) against the NPC alias table (`NpcIndex.canonical_for`) so first-name-only references like "Aldern" resolve correctly; Pass 2 is the two-word heuristic for unknown NPCs. The full `scene_npcs` list is included in every `context` SSE event and shown as chips in the IntentBar.
4. **Active events** — `session.active_events` TTL is decremented; expired events are removed. Remaining events' content is injected as `## Active Event — {id}` blocks. Events are added when the LLM writes `%%EVENT%% <id>` and the corresponding `02_events/<id>.md` file exists.
5. **Event map** (system prompt, not per-turn) — `EventIndex.event_map_text()` builds a compact block listing all valid event IDs and their trigger conditions, injected once at boot. Zero-cost if `02_events/` is empty.
6. **Combat rules** — `CombatRulesIndex` scans for trigger phrases against `adventure_path/04_rules/combat/*.md`. Only fires when `session.combat_state.round > 0`. Longest-match trigger wins; rules body injected as `## Combat Reference — {rule_name}`. Twelve rule files cover actions, AC, attack rolls, AoOs, HP, initiative, and spellcasting.
7. **Combat start roster** — when `active_events` are present and no combat yet, `_build_pc_combat_roster` injects a `[PARTY ROSTER]` block listing every PC in the exact `%%COMBAT%%` combatant line format (name · hp_max/hp_max · ac · init). Ensures all party members appear in the tracker from round 1, not just the active speaker.

### Authority hierarchy

Rules files are organized in strict precedence — higher always overrides lower:

```
00_system_authority/   ← GM behavior, adjudication  (loaded at every session)
07_world_setting/      ← Golarion/Varisia lore
05_campaign_setting/   ← RotRL structure, factions, tone
06_books/              ← Individual adventure modules
session state          ← Live NPC files, knowledge, recap
```

---

## Troubleshooting

### "Boot failed" or session fails to create
- Check the backend is running on port 8000
- On Windows: use `start_backend.ps1` — it kills stale processes before starting
- Check `.env` contains a valid `GROQ_API_KEY` if using the Groq provider

### First turn takes a long time
- Groq: normal first-turn latency is 2–8 seconds. If it times out, check your API key and rate limits.
- Ollama: depends on model size and GPU. Switch to `qwen3:4b` or smaller for testing.

### Subsequent turns get progressively slower (Ollama)
- The model is accumulating context. Dev mode caps history automatically. Reduce model size or increase RAM.

### End Session is stuck on "Ending…"
- The recap/boot LLM calls can hang if Groq is overloaded or the request times out. Click **Kill** next to the "Ending…" button — it aborts the HTTP request and force-resets the UI. All per-turn NPC deltas are already on disk; only the recap and next-session boot file will be missing.

### `uvicorn: command not found`
- Use `python -m uvicorn ...` — uvicorn may not be on PATH after install.

### Vite fails to start
- Port 5173 in use? Kill the old process or use `start_ui.ps1` which handles this.
- Run `npm install` in the `ui/` directory if `node_modules` is missing.

### Ollama not responding (if using Ollama provider)
```bash
ollama serve
curl http://localhost:11434/api/tags   # verify it's up
ollama list                            # confirm model is pulled
```

---

## Current Status

| Area | Status |
|------|--------|
| FastAPI backend + SSE streaming | ✅ Complete |
| Groq provider (primary) | ✅ Complete |
| Ollama provider (fallback) | ✅ Complete |
| Browser UI — Vite + React + TypeScript | ✅ Complete |
| Structured response format (`%%NARRATIVE%%` / `%%ROLL%%` / `%%GENERATE%%` / `%%DELTAS%%`) | ✅ Complete |
| Per-turn NPC RAG (keyword lookup + profile injection) | ✅ Complete |
| Per-turn skill RAG (trigger detection + rules injection) | ✅ Complete |
| NPC stub auto-creation from `%%GENERATE%%` blocks | ✅ Complete |
| Session NPC lifecycle (dot-prefix dirs, UI purge button + toast) | ✅ Complete |
| NPC state persistence (session_NNN.md per NPC per session) | ✅ Complete |
| End-session recap + next-session boot generation | ✅ Complete |
| Kill button to abort stuck End Session | ✅ Complete |
| Dice roll request + resolution (UI panel + API) | ✅ Complete |
| Dev mode (raw marker visibility, full pass-through) | ✅ Complete |
| Session log (timestamped markdown, live view) | ✅ Complete |
| API call logging — `first_token_ms`, `section_format_ok`, token usage, rate limits | ✅ Complete |
| Groq rate limit display in header (RPM/TPM remaining) | ✅ Complete |
| `stream_options` graceful degradation for older Groq models | ✅ Complete |
| Event injection system (`%%EVENT%%` tag, TTL-based active events, event map) | ✅ Complete |
| Per-turn location RAG (`LocationIndex`, alias detection, profile injection, scene persistence) | ✅ Complete |
| Combat Tracker Tier 1 — `%%COMBAT%%` block parsing, `CombatState`/`Combatant` dataclasses, `CombatPanel` + `HpBar`, layout shift, `combat_update` SSE, `DELETE /combat` endpoint, per-turn GM directive reminder, event-file combat requirements | ✅ Complete |
| Combat Tracker Tier 1.1 — backend HP authority from round 2, `%%HP%%` delta block, `[CURRENT HP]` context injection | ✅ Complete |
| Combat Tracker Tier 1.5 — `%%ATTACK%%` block parsing, NPC auto-resolution, PC attack queue, `resolve_attack_roll` / `resolve_damage_roll` / `resume_combat` endpoints, DicePanel to-hit + damage banners, `attack_request` / `attack_result` SSE, `attack_type` carried through to-hit → damage → log | ✅ Complete |
| Combat party roster injection — `_build_pc_combat_roster` injects all PCs with full HP/AC/init as ready-to-use `%%COMBAT%%` lines when `active_events` are present; LLM no longer lists only the active speaker | ✅ Complete |
| Combat rules lookup — `CombatRulesIndex` in `api/context/combat_lookup.py`; 12 rule files (`action_*`, `armor_class`, `attack_rolls`, `attacks_of_opportunity`, `hit_points`, `initiative`, `spellcasting`); injected on trigger-phrase match during active combat only | ✅ Complete |
| Combat Tracker Tier 1.7 — focused per-enemy `%%ACTION%%` query, `POST /enemy_turn`, backend-resolved enemy attacks, Enemy Turn/PC Attacks phase badges, and narrative `POST /close_combat` clear flow | ✅ Complete |
| Tools ▾ dropdown in header — Benchmarks, Coverage, View Session Log, API Logs, Purge NPCs consolidated into a single dropdown; outside-click + Escape dismissal | ✅ Complete |
| Code coverage tab in Coverage modal — `pytest-cov` → `outputs/code_coverage.json` → `GET /api/code-coverage` → "Code Lines" tab with per-file bar charts sorted worst-first | ✅ Complete |
| Anthropic (Claude) provider — `claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5` | ✅ Complete |
| API call log browser UI (`ApiLogPanel`) — list + detail view, summary metrics bar | ✅ Complete |
| Env-var-configurable tunables (`ROTRL_*`) for history limits, token cap, retry base | ✅ Complete |
| `name_exclude_words.txt` — NPC name filter loaded from file, GM-editable without code changes | ✅ Complete |
| Single-word NPC detection — `_detect_narrative_npcs` Pass 1 resolves aliases (`NpcIndex.canonical_for`) | ✅ Complete |
| `scene_npcs` in `context` SSE event — chips shown in IntentBar each turn | ✅ Complete |
| `scene_npcs` persisted across sessions — written to `boot.md`, restored on `create_session` | ✅ Complete |
| Session number auto-increments after successful End Session | ✅ Complete |
| Character action menu opens to the right of the avatar (AC-012) | ✅ Complete |
| Test suites — 940+ pytest · 230+ Vitest · 13 Playwright mocked · 11 live Playwright tests | ✅ Complete |
| System Authority docs (`00_system_authority/` — human-reference; CORE BEHAVIOR / GM STYLE hardcoded in prompt) | ✅ Complete |
| World Setting + Campaign Setting docs | ✅ Complete |
| Book I Act I — all 12 encounter docs written (PF1e), FESTIVAL_ENCOUNTER.md, event files, NPC/location profiles | ✅ Complete |
| Player characters — Yanyeeku, Vanx, Ani | ✅ Complete |
| Roll outcome fed into next GM turn directive | 🔴 Not done — GM narrates blind after resolve |
| Session crash recovery (in-memory sessions lost on restart) | 🔴 Not started |
| Acts II–III of Burnt Offerings | 🔴 In progress — sinspawn, Glassworks, Catacombs, Thistletop pending |
| Player agent (autonomous PC AI) | 🔴 Not started |

---

## Technologies

| Layer | Technology |
|-------|------------|
| Primary LLM | [Groq](https://groq.com/) — `llama-3.3-70b-versatile` (quality) · `llama-3.1-8b-instant` (fast) |
| Alt LLM | [Anthropic](https://anthropic.com/) — `claude-sonnet-4-6` · `claude-opus-4-7` · `claude-haiku-4-5` |
| Fallback LLM | [Ollama](https://ollama.com/) — local, no internet required |
| Backend | Python 3.9+, FastAPI, uvicorn |
| Frontend | Vite 5, React 18, TypeScript |
| Streaming | Server-Sent Events (SSE) |
| Tests | pytest, FastAPI TestClient; Vitest, jsdom, React Testing Library; Playwright |
| Rules system | Pathfinder 1st Edition RAW |

---

## Design Principles

- **Rule-First** — Pathfinder 1e RAW always; narrative never overrides mechanics
- **Authority-Governed** — rules follow an explicit hierarchy; no negotiation at runtime
- **Data-Driven** — NPC profiles, skill rules, and campaign lore are markdown files the GM edits, not hardcoded strings
- **Transparent** — every turn's LLM call (payload + response) is logged to `outputs/api_log/`; the session log captures every exchange timestamped
- **Fail-Loud** — exceptions in block processing are logged to the session log, never silently swallowed
