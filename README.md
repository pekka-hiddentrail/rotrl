# RotRL: Agentic Roleplaying Game DM System

An agentic AI system that uses Ollama LLM and Python to conduct Pathfinder 1st Edition roleplay adventures. Instead of requiring human players, AI agents take on character roles and play through campaigns together, with a DM agent managing the world, encounters, and narrative.

## Project Vision

**RotRL** (Roleplaying Through Remote LLMs) aims to create a fully autonomous Pathfinder 1st Edition roleplay experience where:
- Multiple AI agents control player characters
- A DM agent orchestrates the adventure, managing encounters, NPCs, and world state
- The system utilizes local Ollama LLMs for cost-effective and private inference
- Adventures are modular, reusable, and can be mixed/matched
- All interactions are logged for analysis and replay

## Project Structure

```
rotrl/
├── src/                           # All Python source code
│   ├── agents/                    # AI agent definitions
│   ├── skills/                    # Pathfinder 1st Ed mechanics
│   ├── tools/                     # Utilities (dice, LLM client, game state)
│   ├── config/                    # Configuration
│   ├── adventures/                # Adventure modules
│   └── main.py                    # Entry point
│
├── adventure_path/                # Campaign rules & lore (AUTHORITY HIERARCHY)
│   ├── 00_system_authority/       # Non-negotiable GM rules (✅ ACTIVE, ~720 lines)
│   ├── 01_world_setting/          # World lore & cosmology (🟡 IN PROGRESS, ~400 lines)
│   ├── 02_campaign_setting/       # Campaign-specific rules (✅ ACTIVE, ~700 lines)
│   ├── 03_books/                  # Adventure modules (placeholder)
│   └── 90_shared_references/      # Shared lookup tables (placeholder)
│
├── .agents/                       # Agent instruction prompts & personas
├── .skills/                       # Rules reference prompts
├── .tools/                        # Tool integration prompts
├── .config/                       # System configuration prompts
│
├── outputs/                       # Game session logs and results
├── bootstrap.py                   # Quick Ollama test & response printer
├── requirements.txt               # Python dependencies
├── ADVENTURE.md                   # Adventure path structure & hierarchy
├── CAMPAIGN.md                    # Campaign settings overview & phases
├── CONTEXT.md                     # Development context for AI
└── README.md                      # This file
```

## Key Components

### Agents (`src/agents/`)
- **DM Agent**: Manages world state, generates encounters, describes scenes, adjudicates rules
- **Player Agents**: Control party members, make decisions, cast spells, roleplay interactions
- **NPC Agents**: Secondary characters with limited autonomy (shop keepers, quest-givers, allies)

### Adventures (`src/adventures/`)
Modular adventure files defining:
- Encounters (monsters, traps, environmental hazards)
- NPCs with personality and goals
- Maps and descriptions
- Quest lines and objectives

### Tools (`src/tools/`)
- Dice rolling engine (for fair, reproducible results)
- Character generation templates
- Ollama LLM interface (prompt engineering, token limits)
- Game state tracking
- Response parsing and validation

### Config (`src/config/`)
- LLM model selection and parameters
- Difficulty modifiers
- Game rules variants

### Adventure Path (`adventure_path/`)
**Hierarchical authority system** for campaign rules - **Rise of the Runelords** in **Varisia, Golarion**:
- **00_system_authority/** (✅ ACTIVE) - Non-negotiable GM behavioral rules (~720 lines)
  - How the GM thinks, adjudicates, and maintains impartiality
  - Combat positioning model
  - Pathfinder 1e rules scope (what's allowed/banned)
- **01_world_setting/** (🟡 IN PROGRESS) - World lore, geography, canon (~400 lines)
  - Rise of the Runelords Adventure Path canon authority
  - World Operating Rules (prevents hallucination, controls improvisation)
  - Golarion/Varisia setting specifics
  - Thassilon ancient empire context
- **02_campaign_setting/** (✅ ACTIVE) - Campaign structure, tone, player agency, factions (~700 lines)
  - Six narrative phases (Lvl 1–16+) with escalating scope
  - Theme and emotional tone guidance
  - Player agency guarantees and constraints
  - Faction persistence and NPC continuity rules
- **03_books/** (🟡 IN PROGRESS) - Adventure modules and encounters
  - **BOOK_01_BURNT_OFFERINGS/** (🟨 IN PROGRESS) - Foundational adventure (Lvl 1-4)
    - BOOK_OVERVIEW.md (✅ role, themes, narrative structure)
    - LOCATIONS.md (✅ narrative-significant locations)
    - NPCS.md (✅ campaign NPCs by persistence tier)
    - ACT_STRUCTURE.md, EVENTS_AND_TRIGGERS.md (🟨 in progress)
- **90_shared_references/** - Shared lookup tables and utilities

See [ADVENTURE.md](ADVENTURE.md) for detailed structure and current status.  
See [CAMPAIGN.md](CAMPAIGN.md) for campaign settings overview.

### Instruction Prompts (`.agents/`, `.skills/`, `.tools/`, `.config/`)
These dot-prefixed folders contain instruction prompts and persona definitions:
- `.agents/` - DM persona, Player behaviors, NPC templates
- `.skills/` - Pathfinder 1st Ed rules reference for LLM use
- `.tools/` - Tool integration instructions (Ollama, dice, etc.)
- `.config/` - System configuration templates

### Outputs (`outputs/`)
- Session transcripts and logs
- Character progression records
- Battle reports
- Game state snapshots

## Technologies & Design

- **Language**: Python 3.9+ (virtual environment)
- **LLM**: Ollama (local inference - tested with qwen3:4b, ~2.5GB)
- **Rules System**: Pathfinder 1st Edition RAW (as written)
- **Architecture**: Hierarchical authority system for rules consistency
  - System Authority → World Lore → Campaign Settings → Adventures
  - Higher authority always overrides lower (no conflicts)
  - GM behavior is rule-governed, not intuitive

## Quick Start — GM Agent (✅ READY TO PLAY)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This sets up a Python 3.13 virtual environment with:
- `requests` - Ollama API communication
- `pydantic` - Data validation
- `pytest` - Testing framework

### 2. Start Ollama

```bash
ollama serve
```

Then pull the model (if not already installed):
```bash
ollama pull qwen3:4b
```

### 3. Launch GM Agent for Interactive Play

In another terminal:

```bash
python gm_launcher.py
```

Optional arguments:
```bash
python gm_launcher.py --session 1          # Boot session 1 (default)
python gm_launcher.py --session 3          # Boot specific session
python gm_launcher.py --model qwen2        # Use different model
python gm_launcher.py --temp 0.2           # Lower temperature for consistency
```

**What happens:**
1. ✅ Verifies Ollama is running
2. ✅ Loads all adventure_path files in authority hierarchy order
3. ✅ Initializes GM Agent with comprehensive context
4. ✅ Prompts for PC info (names, classes, levels)
5. ✅ Enters interactive session loop
6. ✅ Saves session notes to `outputs/session_XXX_notes.json`

See [QUICKSTART_GM.md](QUICKSTART_GM.md) for detailed guide.

### 4. Run Bootstrap Verification (Optional)

For Ollama connectivity check:

```bash
python bootstrap.py
```

This will:
- ✅ Check if Ollama is running
- ✅ Detect available models
- ✅ Send a test query
- ✅ Print the LLM response

**Example output:**
```
[BOOTSTRAP] RotRL Ollama Bootstrap
============================================================
[CHECK] Is Ollama running?
[OK] Ollama is running!
[CHECK] Available models:
  - qwen3:4b
[SELECT] Using model: qwen3:4b
[QUERY] Sending test query...
[WAITING] Calling Ollama (this may take a moment)...
[OK] Response received!
============================================================
RESPONSE:
hello world
============================================================
[SUCCESS] Got expected response!
```

### 4. Verify Strict Hello World Test

For a more rigorous test:

```bash
python src/tools/hello_world.py
```

See [.agents/hello/README.md](.agents/hello/README.md) for details.

## Example Usage

*Coming soon*

```python
from agents.dm import DungeonMaster
from agents.player import PlayerCharacter
from adventures.example import ExampleAdventure

# Initialize
dm = DungeonMaster(model="qwen")
party = [
    PlayerCharacter("Theron", race="Human", class="Fighter"),
    PlayerCharacter("Elara", race="Elf", class="Wizard"),
    PlayerCharacter("Borin", race="Dwarf", class="Cleric"),
]

# Run adventure
adventure = ExampleAdventure()
dm.conduct_session(party, adventure)
```

## Current Project Status

### 🎮 GM Agent System (✅ COMPLETE & OPERATIONAL)
- ✅ **src/agents/gm_agent.py** (370 lines) - Full GM Agent implementation
- ✅ **gm_launcher.py** (100 lines) - Command-line launcher with Ollama verification
- ✅ **Session persistence** - Saves to outputs/session_XXX_notes.json (JSON format with turn-by-turn logs)
- ✅ **Multi-session continuity** - Loads prior session facts for npc memory and world state

### Documentation & Rules (✅ ~2,100 lines complete)
- ✅ **System Authority** (00_system_authority/): GM behavior, adjudication, rules scope — **900 lines**
- ✅ **World Setting** (01_world_setting/): Golarion/Varisia canon, world operating rules — **1,300 lines**
- ✅ **Campaign Settings** (02_campaign_setting/): RotRL structure, 6 narrative phases, player agency — **730 lines**
- 🟨 **Adventure Modules** (03_books/BOOK_01_BURNT_OFFERINGS/)
  - ✅ Book Overview, NPCs, Locations
  - ✅ Act I Infrastructure (~570 lines): Scene structure, NPC schedule, tension framework, complete encounter_01
  - 🟨 Acts II-III (placeholder)
- 🔴 **Shared References** (90_shared_references/): Not yet started

### Code & Infrastructure (✅ Complete)
- ✅ Project structure (src/, adventure_path/, outputs/)
- ✅ Ollama integration (bootstrap.py, gm_launcher.py, hello_world.py)
- ✅ Python 3.13 virtual environment
- ✅ Authority hierarchy system (5-tier)
- ✅ Hallucination prevention (concrete mechanics, pressure tables, knowledge boundaries)

### Gameplay Features (✅ Ready for Testing)
- ✅ Session initialization with full context loading
- ✅ Interactive session loop (player input → GM response)
- ✅ Session notes logging and persistence
- ✅ Multi-session continuity framework
- 🟡 Player agent autonomy (future enhancement)
- 🟨 Shared reference tables (90_shared_references/)

## Design Principles

- **Rule-First**: Pathfinder 1st Ed RAW always; narrative never overrides mechanics
- **Authority-Governed**: Rules follow explicit hierarchy; no negotiation
- **Transparent**: All decisions, rolls, and reasoning are logged
- **Modular**: Campaign rules stack without conflicts (authority hierarchy)
- **Efficient**: Works on modest hardware (~2.5GB LLM model)
- **Deterministic**: Same seed → same outcome (reproducible games)

## Documentation

This project has extensive rules and configuration documentation organized by authority:

- **[ADVENTURE.md](ADVENTURE.md)** — Overview of the 5-tier authority hierarchy, links to all config files, status tracking
- **[CAMPAIGN.md](CAMPAIGN.md)** — Rise of the Runelords campaign specifics: 6 narrative phases (Lvl 1–16+), player agency rules, faction definitions
- **[CONTEXT.md](CONTEXT.md)** — Development guidance for AI assistants working on this project

**Config Folder Hierarchy:**
```
adventure_path/
├── 00_system_authority/        ← How GM thinks, decides, and adjudicates
├── 01_world_setting/           ← Golarion/Varisia lore and world rules 
├── 02_campaign_setting/        ← Rise of the Runelords structure, tone, themes
├── 03_books/                   ← Individual adventures (not yet populated)
└── 90_shared_references/       ← Shared tables and utilities (not yet populated)
```

Higher sections override lower sections — no conflicts possible by design.

## Playing a Session

### Session Setup

1. **Start Ollama** (Terminal 1):
   ```bash
   ollama serve
   ```

2. **Launch GM Agent** (Terminal 2):
   ```bash
   cd rotrl
   python gm_launcher.py
   ```

3. **Answer Setup Questions** when prompted:
   - Has Session 1 been run before? (Input prior session notes if applicable)
   - How many player characters? (Enter PC names, classes, levels)
   - Ready to begin? (Confirm to start play)

4. **Play** by typing player actions:
   ```
   >>> I draw my sword and rush the goblins
   [GM response with rules resolution]
   >>> The wizard casts Fireball
   [Spell resolution with damage rolls]
   ```

5. **End Session** by typing `quit`
   ```
   >>> quit
   [Session notes saved to outputs/session_001_notes.json]
   ```

See [QUICKSTART_GM.md](QUICKSTART_GM.md) and [outputs/README.md](outputs/README.md) for detailed session protocol.

## License

*To be determined*

---

**Current Status**: GM Agent ✅ OPERATIONAL | Foundation + Campaign Lore ✅ COMPLETE | Book I Act I ✅ COMPLETE | Core Systems (Player Agent) 🟡 FUTURE

**Updated**: Feb 10, 2026  
**Metrics**: ~2,100 lines of rules/config | GM Agent ready | 1 complete adventure book (Book I, Act I) | Session notes persistent
