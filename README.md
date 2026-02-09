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
- **03_books/** - Adventure modules and encounters
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

## Quick Start

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

Then pull a model (if not already installed):
```bash
ollama pull qwen
```

### 3. Run Bootstrap Test

In another terminal:

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

### Configuration & Rules (✅ ~1,838 lines complete)
- ✅ **System Authority** (00_system_authority/): GM behavior, adjudication, rules scope — **720 lines**
- 🟡 **World Setting** (01_world_setting/): Golarion/Varisia canon, world operating rules — **~400 lines** (in progress)
- ✅ **Campaign Settings** (02_campaign_setting/): RotRL structure, 6 narrative phases, player agency — **~700 lines**
- 🔴 **Adventure Modules** (03_books/): Not yet started
- 🔴 **Shared References** (90_shared_references/): Not yet started

### Code & Infrastructure (✅ Complete)
- ✅ Project structure (src/, adventure_path/, prompts)
- ✅ Ollama integration (bootstrap.py, hello_world.py)
- ✅ Python 3.13 virtual environment
- ✅ Authority hierarchy system (5-tier)

### Core Systems (🟡 In Progress)
- [ ] Base agent framework (src/agents/agent.py)
- [ ] Pathfinder 1e mechanics engine (src/skills/)
- [ ] World Setting detail (complementary lore)

### Gameplay Features (🔴 Not Started)
- [ ] DM orchestration logic
- [ ] Player agent autonomy
- [ ] Adventure modules (03_books/)
- [ ] Session logging and replay
- [ ] Shared reference tables (90_shared_references/)

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

## License

*To be determined*

---

**Current Status**: Foundation + Campaign Lore ✅ COMPLETE | Core Systems 🟡 IN PROGRESS | Gameplay 🔴 TODO

**Updated**: Feb 10, 2026  
**Metrics**: ~1,838 lines of rules/config | 6 campaign phases | 2 sections active | 1 in progress
