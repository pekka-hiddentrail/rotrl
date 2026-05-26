# GM Quick Start

The primary interface is the browser UI. See [README.md](README.md) for full setup.

---

## Start a session (3 terminals)

**Terminal 1 — Ollama:**
```bash
ollama serve
```

**Terminal 2 — Backend (from project root):**
```powershell
# Windows
.\start_backend.ps1

# Mac / Linux
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

**Terminal 3 — Frontend (from project root):**
```powershell
# Windows
.\start_ui.ps1

# Mac / Linux
cd ui && npm run dev
```

Open **http://localhost:5173**.

---

## First boot

1. Leave **Dev** checked — this uses a minimal prompt and caps responses at 180 tokens, so boot takes ~5 sec instead of ~2 min
2. Set model to `qwen2.5:1.5b` for fastest testing
3. Click **Boot Session**
4. Once the GM narrates the opening scene, type your action and press **Enter**
5. Click **End Session** when done — transcript saves to `outputs/session_NNN_notes.json`

When you're ready for real play, uncheck **Dev** and use `qwen3:4b` or better.

---

## Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `qwen2.5:1.5b` | 986 MB | fastest | dev/testing |
| `qwen3:4b` | ~2.5 GB | moderate | good |

Pull a model: `ollama pull qwen2.5:1.5b`

---

## What happens at boot (full mode)

1. `GMAgent` loads `.agents/GM/SESSION_BOOT_PROMPT.md`
2. Injects System Authority (~900 lines), Player Identity, Continuity Anchor into `{{PLACEHOLDER}}` slots
3. Sends the rendered prompt as the Ollama system message
4. Streams the GM's opening narration
5. Fails fast if narration violates boot constraints

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Boot failed (500)" immediately | Backend not running, or not bound to `127.0.0.1:8000` |
| Backend exits instantly on start | Don't use `--reload` — crashes on Windows (watchfiles bug) |
| `uvicorn` not found | Use `python -m uvicorn ...` |
| Nothing streams for 2+ minutes | Switch to Dev mode + `qwen2.5:1.5b` |
| Turns getting slower over time | Dev mode caps context; for full mode use a smaller model |

---

## CLI-only mode (no UI)

Boot + verify only — no interactive loop:

```bash
python gm_launcher.py
python gm_launcher.py --session 2 --model qwen3:4b
```

---

## Key files

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI routes |
| `api/session_manager.py` | Session state, streaming, context limits |
| `.agents/GM/SESSION_BOOT_PROMPT.md` | Canonical GM boot prompt |
| `adventure_path/00_system_authority/` | Non-negotiable GM rules |
| `players/player_01/character_sheet.md` | Yanyeeku, Kitsune Sorcerer L1 |
| `outputs/` | Session transcripts (auto-created) |
