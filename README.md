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
├── src/                        # All Python source code
│   ├── agents/                 # AI agent definitions and orchestration
│   │   ├── __init__.py
│   │   ├── agent.py           # Base agent class
│   │   ├── dm.py              # Dungeon Master agent
│   │   ├── player.py          # Player character agents
│   │   └── npc.py             # Non-player character agents
│   ├── skills/                # Pathfinder 1st Ed skills and mechanics
│   │   ├── __init__.py
│   │   ├── combat.py          # Combat resolution
│   │   ├── skills.py          # Skill checks (Perception, Stealth, etc.)
│   │   ├── spells.py          # Spell mechanics
│   │   └── creatures.py       # Monster/NPC stat blocks
│   ├── tools/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── dice.py            # Dice rolling (d20, d100, etc.)
│   │   ├── character_gen.py   # Character sheet generation
│   │   ├── ollama_client.py   # LLM interface
│   │   ├── game_state.py      # Game state management
│   │   ├── parser.py          # Response parsing/validation
│   │   └── logger.py          # Session logging
│   ├── config/                # Configuration files
│   │   ├── __init__.py
│   │   └── settings.py        # LLM, game, and system settings
│   ├── adventures/            # Adventure modules
│   │   ├── __init__.py
│   │   └── example/           # Example adventure template
│   │       ├── encounters.py
│   │       ├── npcs.py
│   │       └── maps.json
│   └── main.py                # Entry point
│
├── .agents/                   # Agent instruction prompts & personas
├── .skills/                   # Rules & mechanics reference prompts
├── .tools/                    # Tool integration prompts (Ollama, dice, etc.)
├── .config/                   # System configuration prompt templates
│
├── outputs/                   # Game session logs and results
├── .gitignore
├── requirements.txt           # Python dependencies
├── CONTEXT.md                 # AI assistant context for development
└── README.md                  # This file
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

### Instruction Prompts (`.agents/`, `.skills/`, `.tools/`, `.config/`)
These dot-prefixed folders contain instruction prompts and persona definitions for each subsystem:
- `.agents/` - DM persona, Player agent behaviors, NPC templates
- `.skills/` - Pathfinder 1st Ed rules reference, mechanics checklists
- `.tools/` - Tool usage instructions, prompt templates
- `.config/` - System configuration templates

### Outputs (`outputs/`)
- Session logs (JSON/CSV)
- Character sheets (final state)
- Battle reports
- Transcript archives

## Technologies

- **Language**: Python 3.9+
- **LLM**: Ollama (local inference - ~5GB models like Qwen, Llama 2, or Mistral)
- **Rules System**: Pathfinder 1st Edition

## Installation & Setup

*Coming soon*

1. Install Ollama and pull a model (e.g., `ollama pull qwen`)
2. Install Python dependencies: `pip install -r requirements.txt`
3. Configure Ollama in `config/settings.py`
4. Run example adventure: `python main.py --adventure example`

## Quick Start: Hello World Test

To verify your Ollama setup is working:

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running
ollama serve

# In another terminal, run the hello world test
python src/tools/hello_world.py
```

This test validates:
- ✅ Ollama connectivity
- ✅ Prompt loading
- ✅ Response parsing
- ✅ Strict output validation

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

## Development Roadmap

- [ ] Core agent architecture and LLM integration
- [ ] Pathfinder 1st Ed skill/combat system
- [ ] DM orchestration logic
- [ ] Adventure module system
- [ ] Session logging and analysis
- [ ] Example adventure (Beginner's adventure)
- [ ] Character persistence
- [ ] Advanced NPC interactions
- [ ] Custom adventure creation tools

## Contribution Notes

This system aims to be:
- **Rule-accurate**: Follows Pathfinder 1st Ed rules
- **Modular**: Easy to extend with new adventures/mechanics
- **Transparent**: Logs all decisions and rolls for auditing
- **Efficient**: Works well on modest hardware

## License

*To be determined*

---

**Status**: Early development - Structure phase complete, core systems in progress.
