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
│   ├── 00_system_authority/       # Non-negotiable GM rules (ACTIVE)
│   │   ├── GM_OPERATING_RULES.md
│   │   ├── ADJUDICATION_PRINCIPLES.md
│   │   ├── COMBAT_AND_POSITIONING.md
│   │   └── PF1E_RULES_SCOPE.md
│   ├── 01_world_setting/          # World lore & cosmology (placeholder)
│   ├── 02_campaign_setting/       # Campaign-specific rules (placeholder)
│   ├── 03_books/                  # Adventure modules
│   └── 90_shared_references/      # Shared lookup tables
│
├── .agents/                       # Agent instruction prompts & personas
├── .skills/                       # Rules reference prompts
├── .tools/                        # Tool integration prompts
├── .config/                       # System configuration prompts
│
├── outputs/                       # Game session logs and results
├── bootstrap.py                   # Quick Ollama test & response printer
├── requirements.txt               # Python dependencies
├── ADVENTURE.md                   # Adventure path structure & status
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
- **02_campaign_setting/** - Campaign tone, factions, main threats (placeholder)
- **03_books/** - Adventure modules and encounters
- **90_shared_references/** - Shared lookup tables and utilities

See [ADVENTURE.md](ADVENTURE.md) for detailed structure and current status.

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

## Development Status

### ✅ Complete
- [x] Project structure (src/, adventure_path/, prompts)
- [x] System Authority rules (~720 lines of GM behavior)
- [x] Ollama integration (bootstrap.py, hello_world.py)
- [x] Python environment setup (Python 3.13, virtual env)
- [x] Adventure path hierarchy system

### 🟡 In Progress
- [ ] World Setting (~400 lines - RotRL canon, Varisia lore, world rules)
- [ ] Populate Campaign Setting (02_campaign_setting/)
- [ ] Base agent framework (src/agents/agent.py)
- [ ] Pathfinder 1e mechanics engine (src/skills/)

### 🔴 Not Started
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

## Project Layout

See [ADVENTURE.md](ADVENTURE.md) for a comprehensive guide to the campaign structure and authority hierarchy.

See [CONTEXT.md](CONTEXT.md) for AI development context.

## License

*To be determined*

---

**Current Status**: 
- ✅ Infrastructure: Project structure, Ollama integration, System Authority rules complete
- 🟡 Campaign Lore: World Setting (Rise of the Runelords/Varisia) emerging in progress
- 🟡 Core Systems: Agent framework and Pathfinder mechanics in progress
- 🔴 Gameplay: Adventure modules and agent autonomy pending

**Updated**: Feb 9, 2026 | **Total Lines of Code/Rules**: ~1,120
