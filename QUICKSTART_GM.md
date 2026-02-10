# GM Agent Quick Start

## Prerequisites

1. **Ollama Running**: Start Ollama server
   ```bash
   ollama serve
   ```

2. **Qwen3:4b Model Loaded** (in another terminal):
   ```bash
   ollama pull qwen3:4b
   ```

3. **RotRL Project**: You're already here!

## Launch GM Agent

### Option 1: Simple Launch (Session 1)
```bash
python gm_launcher.py
```

### Option 2: Specific Session
```bash
python gm_launcher.py --session 3
```

### Option 3: Different Model
```bash
python gm_launcher.py --model mistral --temp 0.2
```

### Option 4: Direct Python Import
```python
from src.agents.gm_agent import GMAgent, GMConfig

config = GMConfig()
gm = GMAgent(config)
gm.boot_session(session_number=1)
gm.session_loop()
```

## What Happens on Boot

1. **Loads Canonical Boot Prompt** (`.agents/GM/SESSION_BOOT_PROMPT.md`)
   - Defines mandatory boot protocol (role, constraints, narration rules)
   - Contains three placeholder injection points for context

2. **Loads and Injects System Authority** (`adventure_path/00_system_authority/`)
   - 5 files (~900 lines total): GM rules, adjudication, combat, scope, session protocol
   - Injected into `{{SYSTEM_AUTHORITY}}` placeholder

3. **Loads Optional Player Identity** (if `adventure_path/PLAYER_CHARACTERS.md` exists)
   - PC names, classes, levels, backgrounds
   - Injected into `{{PLAYER_IDENTITY}}` placeholder

4. **Loads Optional Continuity** (if `adventure_path/SESSION_NOTES_LAST.md` exists)
   - Previous session facts and NPC memory
   - Injected into `{{CONTINUITY_ANCHOR}}` placeholder

5. **Queries Ollama** with full context
   - Uses `/api/chat` endpoint with system prompt binding
   - System prompt = rendered boot prompt with injected contexts
   - Takes ~30-60 seconds on first query (LLM context loading)
   - Returns opening narration

6. **Displays Boot Output**
   - Shows opening narration
   - Extracts and displays `# Session Boot Output` from boot prompt file
   - Confirms boot protocol was followed

## Session Notes Output

After each session, check `outputs/session_XXX_notes.json`:

```json
{
  "session_number": 1,
  "book": 1,
  "act": 1,
  "turns": [
    {
      "turn": 1,
      "player_input": "I draw my sword and rush the goblins",
      "gm_output": "[Roll initiative. AC 15, 1d20+2 for attack...] You charge..."
    },
    ...
  ]
}
```

These notes can be loaded in future sessions to maintain continuity.

## Stopping the Session

- Type `quit` or `exit` to save and exit gracefully
- Press Ctrl+C to interrupt (still saves session notes)

## Troubleshooting

### "Ollama is not responding"
- Verify `ollama serve` is running
- Check http://localhost:11434/api/tags returns model list

### "Model not found: qwen3:4b"
- Download model: `ollama pull qwen3:4b`
- List available: `ollama list`

### Slow queries (>60 sec)
- Normal on first boot (LLM context loading)
- Subsequent queries faster (~5-15 sec)
- Lower system load for speed

### Session notes not saved
- Check `outputs/` directory exists
- Verify write permissions on directory
- Session JSON saved on `quit` or Ctrl+C

## File Loading Details

**GM Agent loads files in strict hierarchy during boot injection:**

### Boot-Time Injection Points

#### 1. Canonical Boot Prompt (`.agents/GM/SESSION_BOOT_PROMPT.md`)
Defines:
- Role declaration (mandatory GM constraints)
- File loading protocol (placeholder injection points)
- Opening narration constraints (sensory detail, factual only)
- Player agency transition (ends with "What do you do?")
- Enforcement rules (protocol violation handling)

#### 2. System Authority Injection (`{{SYSTEM_AUTHORITY}}`)
Loaded from `adventure_path/00_system_authority/` (5 files):
- `GM_OPERATING_RULES.md` - How GM thinks and behaves
- `ADJUDICATION_PRINCIPLES.md` - Fair play and conflict resolution
- `COMBAT_AND_POSITIONING.md` - Combat system (grid, initiative, etc.)
- `PF1E_RULES_SCOPE.md` - Which Pathfinder 1e rules apply
- `SESSION_NOTES_PROTOCOL.md` - How to record facts

#### 3. Player Identity Injection (`{{PLAYER_IDENTITY}}`)
Optional: Loaded from `adventure_path/PLAYER_CHARACTERS.md` if present
- PC names, classes, levels, backstories
- Used only for boot-time alignment (no motivation interference)

#### 4. Continuity Injection (`{{CONTINUITY_ANCHOR}}`)
Optional: Loaded from `adventure_path/SESSION_NOTES_LAST.md` if present
- Previous session facts and NPC memory
- Prevents contradiction with established canon

### Placeholder Rendering Example

Before injection, boot prompt contains:
```markdown
### A. System Authority
{{SYSTEM_AUTHORITY}}
```

After injection:
```markdown
### A. System Authority

============================================
SYSTEM AUTHORITY
============================================

--- GM_OPERATING_RULES.md ---
[~300 lines of GM behavioral rules]

--- ADJUDICATION_PRINCIPLES.md ---
[~150 lines of fairness rules]
```

### Key Concepts: Boot-First Architecture
- **Canonical Boot Prompt**: Defined independently in `.agents/GM/SESSION_BOOT_PROMPT.md` (version-controlled, human-readable)
- **Context Injection**: Python code loads System Authority files and injects them into placeholders
- **System Prompt Binding**: Ollama `/api/chat` ensures LLM respects all constraints before user input
- **Boot Output**: Session Boot Output section automatically extracted from boot prompt and displayed

### Optional Files Pattern
Dynamic file checking at load time:
```python
player_char_path = adventure_path_root / "PLAYER_CHARACTERS.md"
if player_char_path.exists():
    player_context = load_file(player_char_path)
else:
    player_context = "[NO PLAYER FILES LOADED]"
```

## Next Steps

- **Boot a session now**: `python gm_launcher.py`
- **Review GM rules**: `adventure_path/00_system_authority/GM_OPERATING_RULES.md`
- **Check current Act**: `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/act_01/act_overview.md`
- **See encounters**: `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/act_01/encounters/`

## Full Documentation

For detailed agent architecture, see [AGENTS.md](AGENTS.md).
