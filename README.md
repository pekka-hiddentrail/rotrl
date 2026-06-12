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
3. **Music controls (optional)** — use **Start Music** to begin calm procedural playback. Use **Stop Music** to halt playback. In Dev mode, **Generate Phrase (Debug)** fetches and displays phrase details without starting playback
4. **Type your first action** in the input bar and press **Enter** — this triggers the first GM response
5. **Roll dice** when prompted; the UI shows a Dice Tray. Rolling produces a player speech bubble in chat (e.g. *"Yanyeeku rolled a 13. With bonus of +7 it is a total of 20."*) and automatically submits the result to the backend. If a character is active and the skill is mapped, the modifier is added automatically (toggle in the panel to override)
6. **Combat** — when the LLM writes a `%%COMBAT%%` block, a live initiative tracker appears in the right column (DiceTray shifts left). It shows HP bars, AC, initiative order, status badges, and a phase badge for PC attacks or enemy turns. When a PC attacks, an attack banner appears in the DiceTray — click to roll d20 (to-hit), then pick dice and click **Roll Damage** on a hit. For enemies, click **Enemy Turn** to run a focused backend-mediated enemy action; the backend resolves AC, attack rolls, damage, and HP. Click **End Combat** to stream a short closure narration and clear the panel; the LLM can also signal end-of-combat by writing `round: 0`
7. **View Log** — opens the live session markdown log in a new browser tab (shown during an active session)
8. **API Logs** — opens an in-app overlay listing recent LLM call log files. Click any entry to see a summary bar (`status` · `section_format_ok` · `first_token_ms` · `duration_ms` · `total_tokens`) plus the full JSON payload. Escape or click outside to close
9. **End Session** — generates a recap and next-session boot file; all NPC state is already written per-turn. If it gets stuck (LLM hangs), click **Kill** next to the "Ending…" button — inline confirm, then state is force-reset without saving a recap
10. **Purge NPCs** — shown on the pre-boot screen; deletes all auto-created session NPC stub directories (dot-prefixed). A toast shows how many were removed

### Rate limit badge

After each Groq turn, a compact badge appears in the header showing remaining per-minute quota (e.g. `⚡ 4,500/6,000 TPM · 28/30 RPM`). Hover for reset times. When the daily limit is exhausted, the error message from Groq is surfaced directly in the UI.

### Response sections

The GM response is structured internally into sections that are stripped before you see them:

| Section | What it does |
|---------|-------------|
| `%%NARRATIVE%%` | The prose you read — streamed token-by-token |
| `%%ROLL%%` | Triggers a Dice Tray with skill, DC, success/failure text |
| `%%GENERATE%%` | Creates a new NPC stub file on disk |
| `%%DELTAS%%` | Writes updated disposition/location/knowledge to each NPC's file |
| `%%EVENT%%` | Signals a scene transition — injects event content into context for N turns |
| `%%COMBAT%%` | Updates the live initiative tracker (`round`, HP, AC, initiative, status per combatant); `round: 0` clears the panel |
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
│       ├── npc_extractor.py       # Section-level NPC parser — get_npc_sections() / list_npc_sections() for prompt builder
│       ├── skill_lookup.py        # SkillIndex — detect skill triggers, inject rules
│       ├── location_lookup.py     # LocationIndex — detect locations, inject scene profiles
│       ├── event_index.py         # EventIndex — load 02_events/, inject on %%EVENT%% tag
│       └── combat_lookup.py       # CombatRulesIndex — detect combat triggers, inject PF1e rules (active combat only)
│
├── ui/                            # Vite 5 + React 18 + TypeScript
│   └── src/
│       ├── App.tsx                # Session state, SSE event handling
│       ├── api.ts                 # SSE fetch helpers + SseEvent types
│       ├── music/
│       │   ├── synth.ts           # Tone.js synth bootstrap + AudioContext start
│       │   └── player.ts          # Calm phrase scheduling over Tone.Transport
│       ├── types.ts
│       └── components/
│           ├── Header.tsx             # Logo + controls (column layout); rate-limit badge
│           ├── MusicPlayer.tsx        # Calm music controls (Start/Stop) + debug phrase view
│           ├── ChatWindow.tsx         # Message list + thinking indicator
│           ├── InputBar.tsx           # Player input textarea
│           ├── IntentBar.tsx          # NPC/skill context + scene NPC chips (fixed bottom)
│           ├── CharacterSidebar.tsx
│           ├── CharacterSheet.tsx
│           ├── MessageBubble.tsx      # Player/GM chat bubble with speaker label and portrait
│           ├── SplashHint.tsx         # Rotating hint pool on pre-boot splash screen
│           ├── DiceTray.tsx           # Dice roller + attack banners (to-hit / damage) — feeds result back to API
│           ├── CombatPanel.tsx        # Live initiative tracker (visible during combat)
│           ├── HpBar.tsx              # HP bar with colour thresholds (green/amber/red/grey)
│           ├── LocationZonesPanel.tsx # Zone movement panel — combatant locations, queues zone moves
│           ├── TokenBenchmarks.tsx    # Token benchmark overlay (Tools dropdown)
│           ├── CoverageMatrix.tsx     # Feature AC coverage + code-line coverage modal (two tabs)
│           ├── ApiLogPanel.tsx        # In-app API call log browser (list + JSON detail view)
│           └── EventStatus.tsx        # Event scheduler status panel (overlay, Tools dropdown)
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
│   ├── 10_spells/                 # Canonical spell markdown + class indexes (SpellIndex follow-up)
│   └── 90_shared_references/      # Shared reference tables
│
├── ui/public/data/
│   └── player_NN.json             # Player identity source — name, class, race, stats (read by backend + frontend)
│
├── players/
│   ├── player_01/
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
├── tests/                         # ~1362 pytest tests
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
| `GET`  | `/api/characters` | Return lightweight player character summaries for sidebar/splash UI |
| `GET`  | `/api/characters/{id}` | Return one full character sheet on demand |
| `GET`  | `/api/intro` | Player-facing intro card for a session (intro.md → recap.md fallback) |
| `POST` | `/api/sessions` | Create session, build system prompt; streams `done` SSE event |
| `GET`  | `/api/sessions/{id}` | Session info (model, message count) |
| `POST` | `/api/sessions/{id}/turn` | Send player input; streams GM response via SSE |
| `GET`  | `/api/sessions/{id}/log` | Return live session log as plain text |
| `GET`  | `/api/sessions/{id}/event_status` | Return full event scheduler runtime state — `scheduler_enabled`, `turn_number`, `active_event_id`, `warm_events` (readiness, threshold, frozen, zones, gains), `completed_events`, `cooldowns` |
| `POST` | `/api/music/calm/next_phrase` | Generate one symbolic calm phrase (4 bars, C major pentatonic, monophonic). Tier 0 returns JSON note events only; no server-side audio files |
| `POST` | `/api/sessions/{id}/roll` | Record a dice roll expression and result into the log |
| `POST` | `/api/sessions/{id}/resolve_roll` | Resolve pending roll: compare `rolled` against DC, record outcome |
| `POST` | `/api/sessions/{id}/resolve_attack_roll` | Submit player's d20 to-hit roll; returns `{ hit, damage_expr, queue_remaining, next_attack }` |
| `POST` | `/api/sessions/{id}/resolve_damage_roll` | Submit player's damage dice; applies HP delta, returns `{ damage_total, queue_remaining, next_attack }` |
| `POST` | `/api/sessions/{id}/resume_combat` | Inject resolved attack results into history and stream LLM narration |
| `POST` | `/api/sessions/{id}/pc_turn` | Run PC combat action; extracts intent from player input, queues PC attacks, streams narrative, emits `combat_update` |
| `POST` | `/api/sessions/{id}/enemy_turn` | Run the current enemy actor through a focused LLM call; streams narrative, `attack_result`, `combat_update`, and `done` |
| `POST` | `/api/sessions/{id}/close_combat` | Stream a short combat-closing narration, then clear combat state and emit `combat_update: null` |
| `POST` | `/api/sessions/{id}/end` | Generate recap + next-session boot; streams status events via SSE |
| `DELETE` | `/api/sessions/{id}` | Discard session without recap (emergency close) |
| `DELETE` | `/api/sessions/{id}/combat` | Clear active combat state immediately (direct API fallback; UI uses `close_combat`) |
| `POST` | `/api/sessions/{id}/combat/advance_turn` | Advance initiative to next active combatant; writes state.json; returns `{ current_actor, is_pc }` |
| `POST` | `/api/sessions/{id}/combat/roll_initiatives` | Roll d20 + modifier for every combatant; re-sort initiative; returns `{ combat_state }`. Called automatically on round 1 when a combat event fires; also available as a debug endpoint |
| `PUT`  | `/api/sessions/{id}/active_character` | Set active character for the session; persists to `state.json`; drives dice bonus auto-apply and speaker badge |
| `GET`  | `/api/benchmarks` | Return token benchmark data from `outputs/token_benchmarks.csv` |
| `GET`  | `/api/benchmarks/combat` | Return combat-specific token benchmark data from `outputs/token_benchmarks_combat.csv` |
| `GET`  | `/api/coverage` | Serve `outputs/coverage.json` (feature AC coverage); used by Coverage modal's "AC Coverage" tab |
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
| `attack_request` | When a PC attack is queued — `{ attacker, target, bonus, ac, damage_expr, attack_type }`; activates DiceTray to-hit banner |
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

**Backend:** 1362 pytest tests collected across 48 test files (1304 typically passing; remainder skipped due to missing API keys):

| File | Covers |
|------|--------|
| `test_sessions.py` | Session lifecycle endpoints, boot, turn, delete |
| `test_turns.py` | Turn streaming, Ollama mock, error cases |
| `test_boot_prompt.py` | System prompt assembly, party extraction, situation loading, delta cleanup; dynamic-fragment constants (`_FORMAT_EXAMPLE`, `_COMBAT_FULL_SPEC`) absent from static prompt; section specs absent from static (moved to per-turn injection) |
| `test_groq_provider.py` | `_groq_post` retry logic, 429 handling, `stream_options` 400 fallback, streaming, max-history, rate-limit SSE event, `first_token_ms` capture |
| `test_api_logger.py` | LLM call log file format, usage field, summary truncation, `first_token_ms`, `section_format_ok` |
| `test_api_logs.py` | Log list and fetch endpoints, path traversal rejection |
| `test_response_sections.py` | `_parse_response_sections`, `_parse_bracket_blocks` (multi-line and single-line inline blocks — includes Ameiko turn-5 regression case), section marker detection |
| `test_skill_lookup.py` | Trigger detection, longest-match, word boundary, `_parse_skill_file` |
| `test_npc_lookup_extended.py` | `detect_all`, `lookup`, status/knowledge reads, `_parse_base` |
| `test_npc_extractor.py` | `get_npc_sections`, `list_npc_sections`, `_slugify`, `_find_base_md` (slug + canonical name resolution), `_parse_block`, `_parse_npc_file` (above/below-line split), `_match_key` (exact, prefix, longest-key tie-breaking) — 58 tests |
| `test_inject_context.py` | `_inject_context` per-turn system prompt assembly, NPC short-stub vs full-profile selection (skill gate), no-location-NPC-injection, skill/location/event injection, context metadata, turn-1 format example injection, full combat spec injection when active, conditional section specs (ROLL/DELTAS gated on detection), PC narrative+mechanical profile injection, PC combat roster injected on round-1 spec with `active_events`, implicit NPC injection from `scene_npcs` when player doesn't name an NPC |
| `test_end_session.py` | `_parse_turns_from_log`, `_enforce_recap_header`, `stream_end_session` errors |
| `test_stream_filter.py` | `_stream_with_narrative_filter` — dev pass-through, narrative extraction, split tokens |
| `test_narrative_guard.py` | `%%NARRATIVE%%` buffer+retry guard — valid section passes first time, missing NARRATIVE triggers retry, tokens from failed attempt not emitted, exhausted retries proceed as-is, flat-format bypasses guard, retry notice written to session log |
| `test_recap_header.py` | Recap header normalization edge cases |
| `test_log_parser.py` | Log turn parsing |
| `test_npc_generator.py` | `generate_base_md`, NPC stub creation |
| `test_character_data.py` | Character JSON field validation, summary `/api/characters` endpoint, detail `/api/characters/{id}` endpoint, index file, HP/level/abilities/saves/wealth/weapons/spells per character |
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
| `test_enemy_turn.py` | Enemy-turn Tiers 1.7–1.9: `%%ACTION%%` parser, enemy-turn system/user prompt split, `last_actor` continuity, if_hit/if_miss conditional narration, action_card SSE ordering (before narrative), weapon profile injection, attack/delay streams, endpoint guards |
| `test_pc_combat_turn.py` | PC combat action system (Tier 1.10.5): `_extract_pc_combat_intent` weapon/target extraction and fallbacks, `stream_pc_turn` attack queue from profile, `_stream_pc_turn_narration` narration with known outcome, `/pc_turn` endpoint, edge cases (no enemies, no weapons, non-attack actions) |
| `test_token_benchmark.py` | Real-API token benchmark — boots Anthropic Haiku, runs three fixed turns, appends prompt/completion/total token counts to `outputs/token_benchmarks.csv`; automatically skipped when `ANTHROPIC_API_KEY` is absent (`@pytest.mark.benchmark`) |
| `test_prompt_audit.py` | Verifies `scripts/build_coverage.py` produces `outputs/coverage.json` with the expected `summary.total`, `summary.covered`, `summary.gap` keys and correct row schema |
| `test_combat_hp.py` | `%%HP%%` non-attack HP block, `_parse_hp_deltas`, `_apply_hp_deltas`, `[CURRENT HP]` context injection, HP-status guard |
| `test_combat_prompt.py` | `_build_combat_system_prompt`, `_COMBAT_SECTION_SPECS`, `_inject_context` combat branch, `[INITIATIVE ORDER]`, `[CURRENT HP]`, `[PC COMBAT STATS]`, `[ACTIVE CONDITIONS]` — 16 tests *(spec: combat-system-prompt.feature)* |
| `test_combat_active_character.py` | `CombatState.current_actor`, `advance_combat_turn`, `POST /combat/advance_turn`, `_write_session_state` combat actor, `InputBar` hostile state + skull icon, `tests/test_combat_active_character.py`, `InputBarHostile.test.tsx` — 14 tests *(spec: combat-active-character.feature)* |
| `test_action_economy.py` | `InputBar.tsx` action-type row (Standard/Move/Full-Round), `action_type_hint` POST field, `_HINT_TO_ACTION_TYPE` map, hint override in `_extract_pc_combat_intent`, toggle/reset on turn advance *(spec: action-economy.feature)* |
| `test_click_to_target.py` | `selectedTarget` state, `combatant-targeted` CSS, target badge near InputBar, `target_hint` POST field, `_extract_pc_combat_intent` target override *(spec: click-to-target.feature)* |
| `test_enemy_action_type.py` | `_parse_action_block action_type` field, normalisation to canonical set, inference from `action` when absent, `_build_enemy_turn_system` prompt update, `action_card` SSE `action_type` *(spec: enemy-action-type.feature)* |
| `test_spell_system.py` | `_build_pc_profiles` spell parsing, `_extract_pc_combat_intent` spell detection, `stream_pc_turn` cast branch, `PendingAttack.is_spell`, `damage_request` SSE *(spec: magic-spell-system.feature)* |
| `test_healing_spells.py` | `PendingAttack.is_heal`, `stream_pc_turn` heal branch, `heal_request` SSE, `resolve_damage_roll` positive delta, DiceTray heal banner, unconscious→active restore *(spec: healing-spells.feature)* |
| `test_buff_spells.py` | `Combatant.active_effects`, `_effective_ac`, `_apply_ac_effect`, `_tick_effects` on turn advance, shield/deflection/luck/natural effect types, ✦ indicator serialisation *(spec: ac-buffs.feature)* |
| `test_multi_action_turn.py` | Multi-action turn sequencing and edge cases |
| `test_sse_contract.py` | SSE event shape and field contracts across all streaming endpoints |
| `test_active_character_api.py` | `PUT /api/sessions/{id}/active_character`, `set_active_character` state persistence, `state.json` write, speaker badge wiring |
| `test_coverage_matrix.py` | `scripts/build_coverage.py`, `outputs/coverage.json`, `GET /api/coverage`, AC coverage + code-line coverage JSON schema |
| `test_event_scheduler.py` | Full E1 MVP warm-event scheduler: readiness gain, freeze, threshold roll, pity trigger, active lockout, TTL, zone normalisation, combat TTL tick, frozen guard (BUG-001), cooldown tick (BUG-002), boot location seeding — 55 tests *(spec: event-temperature-mvp.feature)* |
| `test_event_status.py` | `GET /api/sessions/{id}/event_status` endpoint: response shape, `scheduler_enabled` flag, `warm_events` fields, `active_event_id`, `completed_events`, `turn_number`, boot location seeding — 31 tests *(spec: event-status-panel.feature AC-001–AC-010)* |
| `test_music_generation.py` | Tier 0 calm phrase generator: degree mapping, bar totals, deterministic seeds, register constraints, cadence rule, repetition/descending/eighth-ratio guards, motif carry-forward |
| `test_music_api.py` | `POST /api/music/calm/next_phrase` schema contract, API validation 422 path, and structured `generation_failed` 422 response |

**Frontend:** Vitest tests passing across 29 test files (run separately — `cd ui && npm run test`):

Recent streaming regressions are covered explicitly: `test_stream_filter.py` asserts dev mode passes raw `%%EVENT%%` tokens while full mode hides them, `test_event_injection.py` asserts event tags do not leak to player-visible non-dev chat, `ChatWindow.test.tsx` covers empty GM bubbles with three thinking dots, and `App.enemy-turn.test.tsx` covers the enemy-turn pre-token loading state.

| File | Covers |
|------|--------|
| `App.test.tsx` | App-level SSE integration — boot flow, provider/model switching, send-turn event order (`context`, `token`, `patch_last`, `roll_request`, `rate_limits`), speaker payload prefixing, purge/View Log/Kill controls, streaming lockout, error bar, session end cleanup, combat-active layout (AC-006), attack resolution wiring (`handleAttackRoll` → damage phase, `handleDamageRoll` → resume, `doResumeCombat` auto-trigger, AC-009 multi-attack banner switch, `attack_type` regression) |
| `App.enemy-turn.test.tsx` | Tier 1.7 App wiring: Enemy Turn stream state, tokens, `attack_result`, `combat_update`, 409 error handling, and close-combat stream clearing |
| `App.roll-initiatives.test.tsx` | AC-009 App wiring: `handleRollInitiatives` click → `rollInitiatives` API → `setCombatState` + `setCurrentCombatantName`; error message shown and state unchanged on API failure |
| `CombatPanel.test.tsx` | AC-007 initiative order + `combatant-current`/`combatant-inactive` CSS; AC-008 End Combat callback + disabled prop; AC-009 `HpBar` colour thresholds (green/amber/red/grey via inline style); AC-012 condition chips, title tooltips, empty conditions |
| `CombatPanelEnemyTurn.test.tsx` | Tier 1.7 CombatPanel controls: Enemy Turn button, disabled PC-attack state, PC Attacks/Enemy Turn phase badges, and Closing state |
| `DiceTrayAttack.test.tsx` | AC-002/003/004/008 attack banners — to-hit (attacker/target/AC/bonus/active-class/`onAttackRoll`), damage (HIT line/expr/Roll Damage enabled), null phase, attack log (hit/miss badges, PC/NPC labels, log-before-skill-history order), V8 `onDamageRoll` receives rolled values not die sides |
| `ChatWindow.test.tsx` | Thinking indicator, GM streaming cursor, intro markdown rendering, autoscroll |
| `Header.test.tsx` | Pre/post-boot controls, provider model options, boot disabled state, View Log handler, purge/Kill inline confirms, rate-limit badge, Benchmarks button, Coverage button |
| `IntentBar.test.tsx` | 52-char truncation, NPC/skill/location tags, null tags, detecting state, missing-context diagnostic |
| `CharacterSheet.test.tsx` | Modal close behavior, sheet sections, AC/save/spell tooltips, spell grouping |
| `CharacterSidebarHealth.test.tsx` | Portrait/title display and HP bar thresholds |
| `characters.test.tsx` | `useCharacters` summary load success, HTTP failure, fetch rejection, lazy full-sheet fetch and cache reuse |
| `DiceTray.test.tsx` | Dice roll UI, history, DC resolution, pending-roll display, quick-roll from banner (AC-012) |
| `InputBar.test.tsx` | Send/Enter behavior, disabled state, speaker badge, roll injection |
| `CharacterSidebar.test.tsx` | Character action menu, active speaker halo, loading state |
| `ApiLogPanel.test.tsx` | API log browser: list view (empty state, row rendering, filename parsing, close behaviours), detail view (status/format/latency/token badges, JSON block, back navigation, error path) |
| `MessageBubble.test.tsx` | Player speaker labels, portrait fallback, clean player content, GM bubble invariants |
| `SplashHint.test.tsx` | Hint pool integrity, initial display, timed rotation, no immediate repeats, fade class |
| `App.pc-combat-turn.test.tsx` | App wiring for PC combat turn: `pcTurn()` API call, action type routing, attack queue from `pc_turn` stream, `attackPhase` transition |
| `ActiveCharacter.test.tsx` | Active character state management, `PUT /active_character` wiring, active character reflected in session |
| `setActiveCharacterApi.test.ts` | `setActiveCharacter` API client function — request shape, response handling |
| `CombatPanelRollInit.test.tsx` | Roll Initiatives button in CombatPanel: enabled/disabled states, click handler wiring *(spec: roll-initiatives.feature AC-009)* |
| `CombatEventCard.test.tsx` | Enemy action card rendering — action/target/weapon/ability, if_hit/if_miss conditional text, `combat-event` role bubble *(spec: enemy-turn.feature)* |
| `InputBarActionEconomy.test.tsx` | Action type buttons (Standard/Move/Full-Round) — visibility gated on PC combat turn, toggle/reset on send and turn advance *(spec: action-economy.feature)* |
| `InputBarHostile.test.tsx` | InputBar hostile state: skull icon, taunting placeholder text, send button disabled *(spec: combat-active-character.feature)* |
| `ClickToTarget.test.tsx` | Click-to-target combatant row — `combatant-targeted` CSS class, target badge near InputBar, clear on non-combat *(spec: click-to-target.feature)* |
| `MultiActionBar.test.tsx` | Multi-action bar component — action sequencing UI |
| `musicApi.test.ts` | `POST /api/music/calm/next_phrase` API contract, 422 error path, `generation_failed` response shape |

**E2E:** 13 mocked Playwright tests plus 11 live Playwright tests passing in Chromium:

| File | Covers |
|------|--------|
| `e2e/app-flows.spec.ts` | Mocked-browser flows: boot badge, send turn, roll request, end session cleanup, Kill stuck ending, Purge NPCs toast, character sheet modal |
| `e2e/combat-flow.spec.ts` | CT-E2E-001a/b/c: `combat_update` SSE → CombatPanel renders in initiative order + `combat-active` layout; HP bar CSS colour shift across two rounds; End Combat fires `DELETE /combat` and panel disappears |
| `e2e/enemy-turn.spec.ts` | Mocked-browser Tier 1.7 flows: boot into combat, run Enemy Turn and update HP, block Enemy Turn during PC attack prompts, stream close-combat narrative before clearing tracker |
| `e2e/live-flows.spec.ts` | Live backend + LLM flows: boot/session format checks, log API, end-session recap, character sidebar, generated NPC directory creation, Purge NPCs directory removal, goblin event trigger, combat tracker, dice-tray roll resolution |

---

## Architecture

### Session lifecycle

```
POST /api/sessions
  └─ create_session()
       ├─ delete this session's NPC delta files (session_NNN.md per NPC)
       ├─ clear NPC knowledge files (session 1 only — full reset)
       ├─ _build_slim_system_prompt() — reads ui/public/data/player_NN.json, sessions/session_NNN/boot.md
       ├─ _parse_scene_npcs_from_boot() — restores scene_npcs from boot.md if section present
       └─ yields: done SSE event with session_id   (no LLM call)

POST /api/sessions/{id}/turn  (repeated each exchange)
  └─ stream_turn()
       ├─ validate input
       ├─ inject context into system prompt copy:
       │    NpcIndex.detect()           → inject NPC profile(s) if mentioned
       │    scene_npcs (implicit)       → inject last scene NPC profile when player doesn't name one
       │    SkillIndex.detect()         → inject skill rules if triggered
       │    scene_npcs → inject profiles of NPCs active in scene
       │    LocationIndex.detect()      → inject location profile; update scene_locations
       │    _tick_event_scheduler()     → tick readiness, roll threshold, inject [ACTIVE EVENT] block
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
8. **Event scheduler tick** — `_tick_event_scheduler` runs after zone/location detection. If `session.event_scheduler` is True: increments readiness for warm events whose zone matches the current location (base gain + action tag bonuses), freezes events in the wrong zone, then runs `_trigger_phase` (threshold roll; pity auto-trigger at N=6 failed rolls). When an event is active, its TTL is decremented. An `[ACTIVE EVENT]` context block is injected when `event_runtime.active_event_id` is set.

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
| Combat Tracker Tier 1.5 — `%%ATTACK%%` block parsing, NPC auto-resolution, PC attack queue, `resolve_attack_roll` / `resolve_damage_roll` / `resume_combat` endpoints, DiceTray to-hit + damage banners, `attack_request` / `attack_result` SSE, `attack_type` carried through to-hit → damage → log | ✅ Complete |
| Combat party roster injection — `_build_pc_combat_roster` injects all PCs with full HP/AC/init as ready-to-use `%%COMBAT%%` lines when `active_events` are present; LLM no longer lists only the active speaker | ✅ Complete |
| Combat rules lookup — `CombatRulesIndex` in `api/context/combat_lookup.py`; 12 rule files (`action_*`, `armor_class`, `attack_rolls`, `attacks_of_opportunity`, `hit_points`, `initiative`, `spellcasting`); injected on trigger-phrase match during active combat only | ✅ Complete |
| Combat Tracker Tier 1.7 — focused per-enemy `%%ACTION%%` query, `POST /enemy_turn`, backend-resolved enemy attacks, Enemy Turn/PC Attacks phase badges, and narrative `POST /close_combat` clear flow | ✅ Complete |
| Tools ▾ dropdown in header — Benchmarks, Coverage, View Session Log, API Logs, Purge NPCs consolidated into a single dropdown; outside-click + Escape dismissal | ✅ Complete |
| Code coverage tab in Coverage modal — `pytest-cov` → `outputs/code_coverage.json` → `GET /api/code-coverage` → "Code Lines" tab with per-file bar charts sorted worst-first | ✅ Complete |
| Anthropic (Claude) provider — `claude-sonnet-4-6`, `claude-opus-4-8`, `claude-haiku-4-5` | ✅ Complete |
| API call log browser UI (`ApiLogPanel`) — list + detail view, summary metrics bar | ✅ Complete |
| Env-var-configurable tunables (`ROTRL_*`) for history limits, token cap, retry base | ✅ Complete |
| `name_exclude_words.txt` — NPC name filter loaded from file, GM-editable without code changes | ✅ Complete |
| Single-word NPC detection — `_detect_narrative_npcs` Pass 1 resolves aliases (`NpcIndex.canonical_for`) | ✅ Complete |
| `scene_npcs` in `context` SSE event — chips shown in IntentBar each turn | ✅ Complete |
| `scene_npcs` persisted across sessions — written to `boot.md`, restored on `create_session` | ✅ Complete |
| Session number auto-increments after successful End Session | ✅ Complete |
| Character action menu opens to the right of the avatar (AC-012) | ✅ Complete |
| Test suites — 1362 pytest collected · Vitest · 15 Playwright mocked · 11 live Playwright tests | ✅ Complete |
| System Authority docs (`00_system_authority/` — human-reference; CORE BEHAVIOR / GM STYLE hardcoded in prompt) | ✅ Complete |
| World Setting + Campaign Setting docs | ✅ Complete |
| Book I Act I — all 12 encounter docs written (PF1e), FESTIVAL_ENCOUNTER.md, event files, NPC/location profiles | ✅ Complete |
| Player characters — Yanyeeku, Vanx, Ani | ✅ Complete |
| Combat Tracker Tier 1.8 — active character per turn: `CombatState.current_actor`, `POST /combat/advance_turn`, `InputBar` hostile state + skull icon + taunting placeholder, `set_active_character` API, speaker badge | ✅ Complete |
| Roll Initiatives — `roll_combat_initiatives`, PC/enemy modifier, `current_actor` set to highest active, auto-roll on round-1 combat event, `POST /combat/roll_initiatives` debug endpoint | ✅ Complete |
| PC combat turn — `stream_pc_turn`, `POST /pc_turn`, `_extract_pc_combat_intent` weapon/target extraction and fallbacks, attack queue from PC action | ✅ Complete |
| Magic spell system — `PendingAttack.is_spell`, `stream_pc_turn` `cast` branch, `PendingAttack` spell flow, `damage_request` SSE, `AttackPhase spell_damage`, DiceTray spell banner | ✅ Complete |
| Healing spells — `PendingAttack.is_heal`, `heal_request` SSE, `AttackPhase spell_heal`, DiceTray heal banner, `resolve_damage_roll` positive delta, unconscious→active restore | ✅ Complete |
| AC buffs — `Combatant.active_effects`, `_effective_ac`, `_apply_ac_effect`, `_tick_effects` on turn advance, shield/deflection/luck/natural effect types, ✦ indicator in CombatPanel | ✅ Complete |
| Action economy — `InputBar` action-type row (Standard/Move/Full-Round), `action_type_hint` POST field, visible only on PC combat turn, toggle/reset on send and turn advance | ✅ Complete |
| Click-to-target — `selectedTarget` state, `combatant-targeted` CSS, target badge near InputBar, `target_hint` POST field, `_extract_pc_combat_intent` target override | ✅ Complete |
| Zone combat — `Combatant.zone`, `_parse_event_combatants` Zone column, zone badge in CombatPanel below HP bar | ✅ Complete |
| Enemy action type parsing — `_parse_action_block action_type` field, normalisation to canonical set, inference from `action` when absent | ✅ Complete |
| Splash hints — rotating hint pool on pre-boot screen (`SplashHint.tsx`, `hints.ts`, timed fade) | ✅ Complete |
| Event scheduler E1 MVP — warm-event temperature system, readiness tick, zone freeze, threshold roll (d100 ≤ readiness), pity auto-trigger at N=6 failed rolls, TTL-based active event lifecycle, boot location seeding from `boot.md`, scheduler frozen guard (BUG-001), cooldown tick fix (BUG-002) | ✅ Complete |
| Event Status debug panel — `EventStatus.tsx`, `GET /api/sessions/{id}/event_status`, readiness bars, threshold markers, status badges (ACTIVE/ELIGIBLE/FROZEN/WARMING/DONE), TTL bar, opens fresh on click | ✅ Complete |
| Implicit NPC injection from `scene_npcs` — when player doesn't name an NPC the most recently tracked NPC's profile is injected; full profile when skill active, short stub otherwise | ✅ Complete |
| Single-line bracket block parsing — `_BRACKET_BLOCK_INLINE_RE` + `_parse_inline_block_fields` handle `[ key: val  key: val ]` on one line; fixes silently-dropped `%%DELTAS%%` blocks | ✅ Complete |
| NPC section extractor — `api/context/npc_extractor.py`: `get_npc_sections()` / `list_npc_sections()`; case-insensitive prefix matching, above/below `<!-- REFERENCE -->` split; 58 tests | ✅ Complete |
| NPC base.md format — canonical format extended with `## GM Notes` (replaces Reaction to PCs), `## Secrets` (with Diplomacy/Sense Motive unlock DCs), `## Social Checks`, `## State Handling`; all 20 Swallowtail Festival NPCs have complete base.md files | ✅ Complete |
| Roll outcome fed into next GM turn directive | 🔴 Not done — GM narrates blind after resolve |
| Session crash recovery (in-memory sessions lost on restart) | 🔴 Not started |
| Acts II–III of Burnt Offerings | 🔴 In progress — sinspawn, Glassworks, Catacombs, Thistletop pending |
| Player agent (autonomous PC AI) | 🔴 Not started |

---

## Technologies

| Layer | Technology |
|-------|------------|
| Primary LLM | [Groq](https://groq.com/) — `llama-3.3-70b-versatile` (quality) · `llama-3.1-8b-instant` (fast) |
| Alt LLM | [Anthropic](https://anthropic.com/) — `claude-sonnet-4-6` · `claude-opus-4-8` · `claude-haiku-4-5` |
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
