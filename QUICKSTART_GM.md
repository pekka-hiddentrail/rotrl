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

1. **Loads All Contexts**:
   - `adventure_path/00_system_authority/` → GM rules + procedures
   - `adventure_path/01_world_setting/` → World canon + metaphysics
   - `adventure_path/02_campaign_setting/` → Campaign rules + NPC memory + safety
   - `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/` → Current adventure

2. **Builds Comprehensive Prompt**: 
   - Combines all contexts into single GM persona
   - Specifies role (rules arbiter, NOT storyteller)
   - Establishes constraints (no fudging, RAW only, deterministic)

3. **Queries Ollama**: 
   - Sends boot prompt to LLM
   - Takes ~30-60 seconds on first query
   - Returns GM greeting + ready confirmation

4. **Enters Session Loop**:
   - Awaits player/GM input (type actions)
   - Queries LLM for GM response
   - Buffers turns to `outputs/session_XXX_notes.json`
   - Type `quit` to exit and save

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

GM Agent loads files in **precedence order** (highest → lowest):

1. **System Authority** (00_system_authority/)
   - `GM_OPERATING_RULES.md` - How GM behaves
   - `ADJUDICATION_PRINCIPLES.md` - Fair play rules
   - `COMBAT_AND_POSITIONING.md` - Combat system
   - `PF1E_RULES_SCOPE.md` - Which PF1e rules apply
   - `SESSION_NOTES_PROTOCOL.md` - How to record facts

2. **World Setting** (01_world_setting/)
   - `WORLD_OPERATING_RULES.md` - Time, magic, divinity
   - `WORLD_CANON.md` - Established facts
   - `GEOGRAPHY_AND_LOCATIONS.md` - Maps, travel, encounters
   - `MAGIC_AND_METAPHYSICS.md` - What scholars know
   - `COSMOLOGY_AND_GODS.md` - Pantheon + divine mechanics

3. **Campaign Setting** (02_campaign_setting/)
   - `CAMPAIGN_OVERVIEW.md` - Scope + boundaries
   - `THEME_AND_TONE.md` - Humor, safety, fade-to-black
   - `PLAYER_AGENCY_RULES.md` - PC power boundaries
   - `NPC_MEMORY_AND_CONTINUITY.md` - NPC knowledge rules
   - `FACTIONS_AND_POWERS.md` - Political landscape

4. **Current Book** (03_books/BOOK_01_BURNT_OFFERINGS/)
   - `BOOK_OVERVIEW.md` - Acts, themes, structure
   - `NPCS.md` - Characters, stat blocks, motivations
   - `LOCATIONS.md` - Encounters, loot, secrets
   - `EVENTS_AND_TRIGGERS.md` - Escalation timers, pressure
   - `ACT_STRUCTURE.md` - Scene breakdown

5. **Session State** (outputs/session_XXX_notes.json)
   - Facts from prior sessions override all above
   - PC knowledge state
   - NPC memory updates

## Next Steps

- **Boot a session now**: `python gm_launcher.py`
- **Review GM rules**: `adventure_path/00_system_authority/GM_OPERATING_RULES.md`
- **Check current Act**: `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/act_01/act_overview.md`
- **See encounters**: `adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/act_01/encounters/`

## Full Documentation

For detailed agent architecture, see [AGENTS.md](AGENTS.md).
