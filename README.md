# RotRL: Agentic Roleplaying Game GM System

An agentic AI system that uses a local Ollama LLM to run Pathfinder 1st Edition adventures. A Game Master agent manages the world, encounters, NPCs, and narrative. A browser-based chat UI provides the player interface; a FastAPI backend handles all LLM communication.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Python](https://python.org/) | 3.9+ | Add to PATH during install |
| [Node.js](https://nodejs.org/) | 18+ | Includes npm |
| [Ollama](https://ollama.com/) | latest | Runs LLM locally |
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
cd ui
npm install
cd ..
```

### 4. Pull an Ollama model

```bash
# Recommended for testing — fast, small (986 MB)
ollama pull qwen2.5:1.5b

# Full-featured model (~2.5 GB) — better quality, slower
ollama pull qwen3:4b
```

---

## Running the system

Three services must run simultaneously. Open **three terminals** in the project root.

### Terminal 1 — Ollama

```bash
ollama serve
```

### Terminal 2 — FastAPI backend

**Windows (PowerShell):**
```powershell
.\start_backend.ps1
```

**Mac / Linux:**
```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

> **Important (Windows):** Always use `python -m uvicorn`, not bare `uvicorn`. And always pass `--host 127.0.0.1` — Vite's proxy requires explicit IPv4.  
> **Do NOT use `--reload`** — uvicorn's file-watcher (`watchfiles`) crashes silently in new PowerShell windows on Windows.

### Terminal 3 — Vite dev server

**Windows (PowerShell):**
```powershell
.\start_ui.ps1
```

**Mac / Linux:**
```bash
cd ui && npm run dev
```

### Open the UI

Navigate to **http://localhost:5173** in your browser.

---

## Playing a session

1. **Configure** — set session number, model name (e.g. `qwen2.5:1.5b`), and check **Dev** for fast mode
2. **Boot Session** — the GM streams the opening narration (expect 10–60 sec depending on model)
3. **Type player actions** in the input bar; press **Enter** to send
4. **End Session** — saves the full transcript to `outputs/session_NNN_notes.json`

### Dev mode vs full mode

| | Dev mode ✅ | Full mode |
|-|------------|----------|
| System prompt | ~60 tokens (3 sentences) | ~9,500 tokens (38K chars of rules) |
| Boot time | 3–10 sec | 30–120 sec |
| Context sent per turn | last 6 messages | last 30 messages |
| Max tokens generated | 180 | unlimited |
| Rules enforcement | none | full PF1e authority hierarchy |

Use **Dev** while testing. Uncheck it for real sessions.

---

## Project Structure

```
rotrl/
├── api/                           # FastAPI backend
│   ├── main.py                    # Routes: boot, turn, end session
│   └── session_manager.py        # GMAgent wrapper, SSE streaming, sessions
│
├── ui/                            # Vite + React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx                # Root component, session state
│   │   ├── api.ts                 # SSE fetch helpers
│   │   ├── types.ts               # Message, SessionInfo types
│   │   └── components/
│   │       ├── Header.tsx         # Session controls, model/dev toggles
│   │       ├── ChatWindow.tsx     # Message list + thinking indicator
│   │       ├── InputBar.tsx       # Player input
│   │       ├── CharacterSidebar.tsx
│   │       ├── CharacterSheet.tsx
│   │       └── DicePanel.tsx
│   ├── vite.config.ts             # Proxies /api → 127.0.0.1:8000
│   └── package.json
│
├── src/agents/
│   ├── gm_boot_agent.py           # GMAgent, GMConfig, boot verification
│   └── gm_session_start.py        # SessionStartLoader (world/campaign context)
│
├── adventure_path/                # Campaign rules & lore (authority hierarchy)
│   ├── 00_system_authority/       # Non-negotiable GM rules (~900 lines)
│   ├── 01_world_setting/          # Golarion/Varisia world lore (~1,300 lines)
│   ├── 02_campaign_setting/       # RotRL structure, factions, tone (~730 lines)
│   ├── 03_books/                  # Adventure modules
│   │   └── BOOK_01_BURNT_OFFERINGS/
│   │       └── act_01/encounters/ # Goblin raid, social, event encounters
│   └── 04_persistence/            # Session ledger
│
├── .agents/GM/                    # Canonical GM prompt templates
│   ├── SESSION_BOOT_PROMPT.md     # Boot protocol with {{PLACEHOLDER}} injection
│   ├── SESSION_PLAY_LOOP_PROMPT.md
│   └── SESSION_START_PROMPT.md
│
├── players/                       # Player character files
│   └── player_01/character_sheet.md  # Yanyeeku, Kitsune Sorcerer L1
│
├── facets/                        # GM behavior facet modules (13 facets)
├── outputs/                       # Session transcripts (auto-created)
│
├── start_backend.ps1              # Windows: start FastAPI backend
├── start_ui.ps1                   # Windows: start Vite dev server
├── requirements.txt               # Python dependencies
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sessions` | Boot session; streams opening narration via SSE |
| `POST` | `/api/sessions/{id}/turn` | Send player input; streams GM response via SSE |
| `DELETE` | `/api/sessions/{id}` | End session, save transcript to `outputs/` |

The frontend talks to the backend over Server-Sent Events (SSE). Tokens stream token-by-token from Ollama → FastAPI → browser.

---

## Architecture

### Boot-First Design

Every session starts with a mandatory boot protocol:

1. `GMAgent` loads `.agents/GM/SESSION_BOOT_PROMPT.md`
2. Three `{{PLACEHOLDER}}`s are injected: System Authority (~900 lines), Player Identity, Continuity Anchor (last session notes)
3. The rendered prompt becomes the Ollama system message (held for the entire session)
4. The GM streams the opening narration
5. Boot fails fast (`RuntimeError`) if narration violates boot constraints

In **Dev mode** steps 1–2 are skipped; a 3-sentence system prompt is used instead.

### Authority Hierarchy

Rules files are organized in strict precedence — higher always overrides lower:

```
00_system_authority/   ← GM behavior, adjudication  (loaded at every boot)
01_world_setting/      ← Golarion/Varisia lore
02_campaign_setting/   ← RotRL structure, factions, tone
03_books/              ← Individual adventure modules
session state          ← Live session notes
```

### Context Management

To keep turn latency predictable:
- Dev mode: last **6 messages** sent to Ollama, generation capped at **180 tokens**
- Full mode: last **30 messages** sent (never the full history)
- The system prompt is prepended to every Ollama call but built only once at boot

---

## Troubleshooting

### "Boot failed (500): " immediately on click
The backend is not reachable. Check:
- Is `start_backend.ps1` running in a separate terminal?
- Did it error on start? (watchfiles crash looks like instant exit)
- Backend must bind to `127.0.0.1:8000` — the Vite proxy requires this exact address

### Boot shows "Booting…" but nothing streams for 2+ minutes
Normal for full mode with a large model. Switch to **Dev mode** and a smaller model (`qwen2.5:1.5b`) for testing.

### Subsequent turns get progressively slower
The model is accumulating context. Dev mode caps history automatically. For full-mode sessions, reduce the model size or increase your machine's RAM.

### `uvicorn: command not found` / `uvicorn` not recognized
Use `python -m uvicorn ...` — uvicorn installs as a user package on Windows and may not be on PATH.

### Ollama not responding
```bash
ollama serve          # start if not running
curl http://localhost:11434/api/tags   # verify it's up
ollama list           # confirm model is pulled
```

---

## Terminal-Only Mode (no UI)

The original CLI launcher still works for boot + verification:

```bash
python gm_launcher.py
python gm_launcher.py --session 2 --model qwen3:4b --temp 0.3
```

There is no interactive play loop in CLI mode.

---

## Current Status

| Area | Status |
|------|--------|
| Browser UI (Vite + React + TypeScript) | ✅ Complete |
| FastAPI backend + SSE streaming | ✅ Complete |
| Dev mode (minimal prompt, fast testing) | ✅ Complete |
| Context window limiting per turn | ✅ Complete |
| GM Agent boot protocol + verification | ✅ Complete |
| System Authority docs (~900 lines) | ✅ Complete |
| World Setting docs (~1,300 lines) | ✅ Complete |
| Campaign Setting docs (~730 lines) | ✅ Complete |
| Book I Act I encounters | ✅ Complete |
| Player character — Yanyeeku (Kitsune Sorcerer L1) | ✅ Complete |
| Player identity wired into boot prompt | 🟨 Path mismatch (`adventure_path/PLAYER_CHARACTERS.md` is a stub) |
| Player agent (autonomous PC AI) | 🔴 Not started |
| Acts II–III of Burnt Offerings | 🔴 Placeholder |
| Shared reference tables | 🔴 Not started |

---

## Technologies

| Layer | Technology |
|-------|------------|
| LLM runtime | Ollama (local) |
| Recommended models | `qwen2.5:1.5b` (fast) · `qwen3:4b` (quality) |
| Backend | Python 3.9+, FastAPI, uvicorn |
| Frontend | Vite 5, React 18, TypeScript |
| Streaming | Server-Sent Events (SSE) |
| Rules system | Pathfinder 1st Edition RAW |

---

## Design Principles

- **Rule-First**: Pathfinder 1e RAW always; narrative never overrides mechanics
- **Authority-Governed**: Rules follow an explicit hierarchy; no negotiation
- **Fail-Fast**: Boot verification raises immediately if the GM narration violates constraints
- **Transparent**: All decisions, rolls, and reasoning are logged
- **Local**: Runs entirely on your machine — no external API calls
