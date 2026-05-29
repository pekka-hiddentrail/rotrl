# RotRL: Agentic GM System

A FastAPI + React system that runs Pathfinder 1st Edition adventures with an AI Game Master. The GM agent manages narrative, NPCs, skill checks, and persistent world state. Groq is the primary LLM provider (fast, cloud-hosted); Ollama is supported as an offline fallback.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Python](https://python.org/) | 3.9+ | Add to PATH during install |
| [Node.js](https://nodejs.org/) | 18+ | Includes npm |
| [Groq API key](https://console.groq.com/) | — | Free tier is sufficient for play |
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

### 4. Set your Groq API key

Create a `.env` file in the project root (it is git-ignored):

```
GROQ_API_KEY=gsk_your_key_here
```

> Get a free key at [console.groq.com](https://console.groq.com/). The `llama-3.1-8b-instant` model is fast and free.

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

This runs the backend pytest suite, then starts the backend and UI together with colour-coded output. Press **Ctrl-C** to stop both. Run the frontend Vitest suite separately with `cd ui && npm run test`.

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
5. **View Log** — opens the live session log in a new browser tab (shown during an active session)
6. **End Session** — generates a recap and next-session boot file; all NPC state is already written per-turn. If it gets stuck (LLM hangs), click **Kill** next to the "Ending…" button — inline confirm, then state is force-reset without saving a recap
7. **Purge NPCs** — shown on the pre-boot screen; deletes all auto-created session NPC stub directories (dot-prefixed). A toast shows how many were removed

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

In **dev mode** all markers are visible in the stream so you can see the raw output.

### Output files and directories

| Path | When created | Contents |
|------|-------------|----------|
| `outputs/*.log.md` | At session boot | Timestamped markdown: system prompt, every exchange, dice rolls |
| `outputs/api_log/*.json` | Per turn | Full LLM request + response payload. Key fields: `first_token_ms` (ms to first streamed token), `section_format_ok` (true if `%%MARKER%%` sections present), `duration_ms`, `usage.total_tokens`, `status` |
| `sessions/session_NNN/recap.md` | On End Session | Player-facing recap for the next session's intro card |
| `sessions/session_NNN+1/boot.md` | On End Session | GM-facing continuity brief for the next session's system prompt |
| `adventure_path/05_npcs/<slug>/session_NNN.md` | Per turn (per NPC) | NPC disposition, location, knowledge written after each interaction |
| `adventure_path/05_npcs/.<slug>/` | On `%%GENERATE%%` | Session-NPC stub directory (dot-prefix = temporary). Rename to `<slug>/` to promote to permanent. Purge all via **Purge NPCs** or `DELETE /api/npcs/session`. |

---

## Dev mode vs full mode

| | Dev mode | Full mode |
|-|----------|-----------|
| Stream filter | All tokens visible (markers shown) | Only `%%NARRATIVE%%` streamed |
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
│       ├── npc_lookup.py          # NpcIndex — detect NPC names, inject profiles
│       ├── skill_lookup.py        # SkillIndex — detect skill triggers, inject rules
│       ├── location_lookup.py     # LocationIndex — detect locations, inject scene profiles
│       └── event_index.py         # EventIndex — load 08_events/, inject on %%EVENT%% tag
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
│           ├── IntentBar.tsx      # NPC/skill context display (fixed bottom)
│           ├── CharacterSidebar.tsx
│           ├── CharacterSheet.tsx
│           └── DicePanel.tsx      # Dice roller — feeds result back to API
│
├── adventure_path/
│   ├── 00_system_authority/       # Non-negotiable GM rules — adjudication, PF1e scope
│   ├── 01_world_setting/          # Golarion/Varisia lore
│   ├── 02_campaign_setting/       # RotRL structure, factions, tone
│   ├── 03_books/                  # Adventure modules (Book I Act I complete)
│   ├── 04_persistence/            # Session ledger
│   ├── 05_npcs/                   # NPC stubs — hand-crafted or auto-created per turn
│   ├── 06_rules/skills/           # Skill files — trigger words + rules text for RAG
│   ├── 07_locations/              # Location profiles (read by LocationIndex at runtime)
│   ├── 08_events/                 # Event files — fired by %%EVENT%% tag, injected for N turns
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
├── outputs/                       # Runtime-generated — git-ignored
│   ├── *.log.md                   # Live session logs
│   └── api_log/                   # Per-turn LLM payloads
│
├── tests/                         # 451 pytest tests
├── ui/src/components/__tests__/    # 69 Vitest component tests
├── ui/src/__tests__/               # 19 Vitest App SSE integration tests
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
| `GET`  | `/api/intro` | Player-facing intro card for a session (intro.md → recap.md fallback) |
| `POST` | `/api/sessions` | Create session, build system prompt; streams `done` SSE event |
| `GET`  | `/api/sessions/{id}` | Session info (model, message count) |
| `POST` | `/api/sessions/{id}/turn` | Send player input; streams GM response via SSE |
| `GET`  | `/api/sessions/{id}/log` | Return live session log as plain text |
| `POST` | `/api/sessions/{id}/roll` | Record a dice roll expression and result into the log |
| `POST` | `/api/sessions/{id}/resolve_roll` | Resolve pending roll: compare `rolled` against DC, record outcome |
| `POST` | `/api/sessions/{id}/end` | Generate recap + next-session boot; streams status events via SSE |
| `DELETE` | `/api/sessions/{id}` | Discard session without recap (emergency close) |
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
| `context` | Debug event for injected NPC/skill context |
| `status` | Progress messages during end-session generation |
| `error` | Any recoverable error; 429 daily-limit errors include the Groq message verbatim |
| `done` | End of stream; includes `session_id` on boot |

---

## Testing

There are two local test layers: backend `pytest` tests and frontend `Vitest` component tests.

```bash
python -m pytest -q               # run all backend tests
python -m pytest tests/test_groq_provider.py -q   # run one file
```

```bash
cd ui
npm run test                      # run all frontend Vitest tests once
npm run test:watch                # watch frontend tests during UI work
```

`python dev.py` runs the backend pytest suite before starting the API and UI. It does not run Vitest, so use `npm run test` from `ui/` before merging frontend changes.

**Backend:** 453 pytest tests passing across 20 test files:

| File | Covers |
|------|--------|
| `test_sessions.py` | Session lifecycle endpoints, boot, turn, delete |
| `test_turns.py` | Turn streaming, Ollama mock, error cases |
| `test_boot_prompt.py` | System prompt assembly, party extraction, situation loading, delta cleanup |
| `test_groq_provider.py` | `_groq_post` retry logic, 429 handling, `stream_options` 400 fallback, streaming, max-history, rate-limit SSE event, `first_token_ms` capture |
| `test_api_logger.py` | LLM call log file format, usage field, summary truncation, `first_token_ms`, `section_format_ok` |
| `test_api_logs.py` | Log list and fetch endpoints, path traversal rejection |
| `test_response_sections.py` | `_parse_response_sections`, `_parse_bracket_blocks`, section marker detection |
| `test_skill_lookup.py` | Trigger detection, longest-match, word boundary, `_parse_skill_file` |
| `test_npc_lookup_extended.py` | `detect_all`, `lookup`, status/knowledge reads, `_parse_base` |
| `test_inject_context.py` | `_inject_context` per-turn system prompt assembly, NPC/skill/location/event injection, context metadata |
| `test_end_session.py` | `_parse_turns_from_log`, `_enforce_recap_header`, `stream_end_session` errors |
| `test_stream_filter.py` | `_stream_with_narrative_filter` — dev pass-through, narrative extraction, split tokens |
| `test_recap_header.py` | Recap header normalization edge cases |
| `test_log_parser.py` | Log turn parsing |
| `test_npc_generator.py` | `generate_base_md`, NPC stub creation |
| `test_character_data.py` | Character sheet loading |
| `test_intro.py` | Intro file resolution and fallback |
| `test_event_injection.py` | `EventIndex` loading, `%%EVENT%%` parsing, TTL expiry, duplicate guard, event map, SSE `active_events`, double-write regression |
| `test_location_lookup.py` | `LocationIndex` loading, alias detection, `<!-- REFERENCE -->` boundary, profile injection, scene re-injection, session-generated location stubs |
| `test_dev_startup.py` | `dev.py` startup hardening — `_pid_on_port`, `_port_free`, `_kill_tree`, `_free_port` |

**Frontend:** 88 Vitest tests passing across 4 test files:

| File | Covers |
|------|--------|
| `App.test.tsx` | App-level SSE integration — boot flow, send-turn event order (`context`, `token`, `patch_last`, `roll_request`, `rate_limits`), error bar, session end cleanup |
| `DicePanel.test.tsx` | Dice roll UI, history, DC resolution, pending-roll display |
| `InputBar.test.tsx` | Send/Enter behavior, disabled state, speaker badge, roll injection |
| `CharacterSidebar.test.tsx` | Character action menu, active speaker halo, loading state |

---

## Architecture

### Session lifecycle

```
POST /api/sessions
  └─ create_session()
       ├─ delete this session's NPC delta files (session_NNN.md per NPC)
       ├─ clear NPC knowledge files (session 1 only — full reset)
       ├─ _build_slim_system_prompt() — reads players/, sessions/session_NNN/boot.md
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
       │    %%GENERATE%% → create new NPC stub in adventure_path/05_npcs/.<slug>/
       │    %%DELTAS%%   → write NPC status + knowledge files
       │    %%EVENT%%    → add event to active_events (TTL=5 turns); silently ignored if unknown or duplicate
       └─ yield patch_last (non-dev), append to history

POST /api/sessions/{id}/end
  └─ stream_end_session()
       ├─ _parse_turns_from_log() — extract PLAYER/GM turns from log
       ├─ blocking LLM call → player-facing recap text
       ├─ _enforce_recap_header() → canonical header
       ├─ write sessions/session_NNN/recap.md
       ├─ blocking LLM call → GM-facing boot brief for next session
       └─ write sessions/session_NNN+1/boot.md
```

### Per-turn context injection (RAG)

No vector database. Every turn, keyword lookups and active-event TTL checks run before the LLM call:

1. **NPC lookup** — `NpcIndex` scans for alias matches against `adventure_path/05_npcs/*/base.md`. Matching NPC's profile (minus `<!-- REFERENCE -->` section) is prepended to system content.
2. **Skill lookup** — `SkillIndex` scans for trigger words against `adventure_path/06_rules/skills/*.md`. Longest-match trigger wins; skill rules are prepended.
3. **Scene NPCs** — NPCs accumulated in `session.scene_npcs` (from `%%DELTAS%%` writes + `_detect_narrative_npcs` scan) have their current status injected so the GM knows their last known state.
4. **Active events** — `session.active_events` TTL is decremented; expired events are removed. Remaining events' content is injected as `## Active Event — {id}` blocks. Events are added when the LLM writes `%%EVENT%% <id>` and the corresponding `08_events/<id>.md` file exists.
5. **Event map** (system prompt, not per-turn) — `EventIndex.event_map_text()` builds a compact block listing all valid event IDs and their trigger conditions, injected once at boot. Zero-cost if `08_events/` is empty.

### Authority hierarchy

Rules files are organized in strict precedence — higher always overrides lower:

```
00_system_authority/   ← GM behavior, adjudication  (loaded at every session)
01_world_setting/      ← Golarion/Varisia lore
02_campaign_setting/   ← RotRL structure, factions, tone
03_books/              ← Individual adventure modules
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
| Test suites — 453 pytest + 88 Vitest tests | ✅ Complete |
| System Authority docs (`00_system_authority/` — human-reference; CORE BEHAVIOR / GM STYLE hardcoded in prompt) | ✅ Complete |
| World Setting + Campaign Setting docs | ✅ Complete |
| Book I Act I — all 12 encounter docs written (PF1e), FESTIVAL_ENCOUNTER.md, event files, NPC/location profiles | ✅ Complete |
| Player characters — Yanyeeku, Revemox, Ani | ✅ Complete |
| Roll outcome fed into next GM turn directive | 🔴 Not done — GM narrates blind after resolve |
| Session crash recovery (in-memory sessions lost on restart) | 🔴 Not started |
| Anthropic (Claude) provider | 🔴 Not started |
| Acts II–III of Burnt Offerings | 🔴 In progress — sinspawn, Glassworks, Catacombs, Thistletop pending |
| Player agent (autonomous PC AI) | 🔴 Not started |

---

## Technologies

| Layer | Technology |
|-------|------------|
| Primary LLM | [Groq](https://groq.com/) — `llama-3.3-70b-versatile` (quality) · `llama-3.1-8b-instant` (fast) |
| Fallback LLM | [Ollama](https://ollama.com/) — local, no internet required |
| Backend | Python 3.9+, FastAPI, uvicorn |
| Frontend | Vite 5, React 18, TypeScript |
| Streaming | Server-Sent Events (SSE) |
| Tests | pytest, FastAPI TestClient; Vitest, jsdom, React Testing Library |
| Rules system | Pathfinder 1st Edition RAW |

---

## Design Principles

- **Rule-First** — Pathfinder 1e RAW always; narrative never overrides mechanics
- **Authority-Governed** — rules follow an explicit hierarchy; no negotiation at runtime
- **Data-Driven** — NPC profiles, skill rules, and campaign lore are markdown files the GM edits, not hardcoded strings
- **Transparent** — every turn's LLM call (payload + response) is logged to `outputs/api_log/`; the session log captures every exchange timestamped
- **Fail-Loud** — exceptions in block processing are logged to the session log, never silently swallowed
