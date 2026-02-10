# Project Context: RotRL Development Assistant

## My Role

You are the primary development AI for the **RotRL** (Roleplaying Through Remote LLMs) project. Your mission is to architect and build a fully functional agentic AI system that conducts Pathfinder 1st Edition tabletop RPG campaigns autonomously using local Ollama LLMs.

## Project Overview

**What**: An autonomous Pathfinder 1st Edition DM system where AI agents play the game roles
- One DM agent orchestrates the entire session
- Multiple Player Character agents control party members
- NPC agents provide secondary interactions
- Local Ollama LLM (~5GB model) provides all reasoning

**Why**: Explore how LLMs can manage complex, rule-heavy, collaborative problem-solving tasks without human intervention. Answer questions like:
- Can an LLM fairly adjudicate rules without cheating for the party?
- How do agents negotiate and roleplay together?
- What prompting strategies maintain immersion and accuracy?

**Tech Stack**:
- Python 3.9+
- Ollama (local LLM inference)
- Pathfinder 1st Edition rules
- JSON/CSV for logging and state

## Your Responsibilities

### 1. Architecture & Design
- Design the multi-agent system (DM, Players, NPCs)
- Plan the LLM prompt strategy and token management
- Structure game state representation
- Define agent communication protocols

### 2. Core Systems (Priority Order)
1. **Ollama Client** (`src/tools/ollama_client.py`)
   - Connection management
   - Prompt templating
   - Token limit handling
   - Response parsing

2. **Game State Engine** (`src/tools/game_state.py`)
   - Maintain consistent world state
   - Track character attributes, positions, statuses
   - Manage encounter/combat rounds

3. **Dice & Mechanics** (`src/tools/dice.py`)
   - Fair, reproducible randomness
   - Pathfinder 1st Ed calculations
   - Result logging

4. **Agent Framework** (`src/agents/`)
   - Base Agent class (decision-making loop)
   - DM Agent (orchestration, rule adjudication)
   - Player Agent (character goals, actions)
   - NPC Agent (reactive, limited autonomy)

5. **Pathfinder Rules** (`src/skills/`)
   - Combat system (attacks, AC, damage)
   - Skill checks with difficulty classes
   - Spell mechanics
   - Creature stat blocks

6. **Adventure System** (`src/adventures/`)
   - Encounter definitions
   - NPC stat blocks and personalities
   - Quest frameworks
   - Treasure tables

7. **Instruction Prompts** (`.agents/`, `.skills/`, `.tools/`, `.config/`)
   - DM persona and behavioral guidelines
   - Player agent decision trees
   - Pathfinder rules reference for LLM use
   - Tool usage instructions

### 3. Key Development Principles

**Accuracy**: All rolls and mechanics must follow Pathfinder 1st Ed rules exactly.

**Transparency**: Every decision, roll, and rule invocation must be logged with explanation for auditability.

**Determinism**: Same seed → same outcome. Enable replaying sessions.

**Efficiency**: Minimize tokens used; design prompts for clarity and brevity.

**Modularity**: Adventures, rules, and agents are swappable and reusable.

**Autonomy**: System should function end-to-end without human intervention once initialized.

### 4. Implementation Patterns

**Agent Decision Loop**:
```
1. LLM observes current state (character position, surroundings, dialogue)
2. LLM generates action/decision
3. Parser validates action against rules
4. Execute action (roll dice if needed)
5. Update game state
6. Log decision and outcome
7. Back to step 1
```

**Prompt Design**:
- Provide character sheet in context (current HP, spells, equipment)
- Include recent history (last 2-3 rounds)
- Specify valid actions for scenario
- Request specific format (JSON preferred for parsing)
- Use system prompts to reinforce Pathfinder knowledge and honesty

**State Management**:
- All state is JSON-serializable for saving/loading
- Immutable state transitions for debugging
- Version state to track evolution

### 5. Success Criteria

A working RotRL system should be able to:
- ✓ Initialize a multi-character party with proper Pathfinder stat blocks
- ✓ Run an entire encounter (combat or social) autonomously
- ✓ Apply Pathfinder rules consistently (skill DCs, attack rolls, damage)
- ✓ Have agents roleplay and interact meaningfully
- ✓ Log all decisions with explanations
- ✓ Complete a 1-2 hour adventure session without human input
- ✓ Produce readable transcripts and character progression logs

## Code Organization Standards

- **Naming**: `snake_case` for functions/variables, `CamelCase` for classes
- **Docstrings**: Include purpose, parameters, returns, example usage
- **Type hints**: Use them for clarity
- **Testing**: Write unit tests for mechanics (dice, rules, parsing)
- **Logging**: Use Python `logging` module; save session logs to `outputs/`
- **Config**: All magic numbers go in `config/settings.py`

## Known Constraints & Challenges

1. **LLM Consistency**: Models may not reliably follow strict rules (e.g., always applying modifiers)
   - Solution: Validate all LLM outputs before executing; use structured prompts

2. **Token Budget**: Qwen 5B has limited context
   - Solution: Keep state compact; summarize history; focus prompts

3. **Rule Complexity**: Pathfinder has many edge cases
   - Solution: Implement rules incrementally; start with core mechanics (d20 rolls, AC, HP)

4. **Agent Communication**: Getting agents to coordinate without explicit messaging is hard
   - Solution: Give agents access to full game state; use DM to broadcast information

5. **Reproducibility**: External randomness makes replaying hard
   - Solution: Use seeded RNG; log all rolls; don't rely on external APIs

## Files to Create (Initial Phase)

```
src/
  agents/
    ├── __init__.py
    ├── agent.py          # Base class
    ├── dm.py             # Dungeon Master
    ├── player.py         # Player characters
    └── npc.py            # NPCs

  skills/
    ├── __init__.py
    ├── combat.py
    ├── skills.py
    ├── spells.py
    └── creatures.py

  tools/
    ├── __init__.py
    ├── dice.py
    ├── character_gen.py
    ├── ollama_client.py
    ├── game_state.py
    ├── parser.py
    └── logger.py

  config/
    ├── __init__.py
    └── settings.py

  adventures/
    ├── __init__.py
    └── example/ (populated later)

  └── main.py                 # Entry point

.agents/                       # Instruction prompts for DM, Players, NPCs
.skills/                       # Pathfinder 1st Ed rules reference prompts
.tools/                        # Tool integration prompts
.config/                       # System configuration prompt templates

outputs/
  └── .gitkeep

main.py                        # Root entry point
requirements.txt
```

## Project Status: IMPLEMENTATION MILESTONE

### ✅ COMPLETED (Feb 10, 2026)

**Authority Hierarchy Foundation (~2,100 lines)**
- **00_system_authority/** - GM operating rules, adjudication principles, combat positioning, PF1e rules scope
- **01_world_setting/** - Complete world canon, cosmology, magic boundaries, geography with travel mechanics
- **02_campaign_setting/** - Campaign overview, tone, player agency rules, NPC memory protocol, factions

**GM Agent System (410 lines Python)**
- `src/agents/gm_agent.py` - Full implementation with file loading, context building, Ollama integration
- `gm_launcher.py` - Command-line bootstrap with session management
- Session persistence architecture (JSON output, multi-session continuity)
- Comprehensive boot prompt that combines all authority hierarchy files

**Swallowtail Festival - Book I, Act I (~2,100 lines)**
- NPCS.md with stat blocks and persistence tiers
- LOCATIONS.md with mechanics (Runewell specifics, travel tables, encounter DCs)
- EVENTS_AND_TRIGGERS.md with pressure track (0-9 scale), escalation timers, NPC consequences
- Act I infrastructure (4 files, ~570 lines total):
  - act_overview.md: Scene structure and escalation framework
  - active_npcs.md: NPC schedules and tier-based availability
  - current_tensions.md: Background conflicts and pressure mechanics
  - encounter_01.md: Complete Goblin Cavalry encounter (stat blocks, battlefield, tactics, scaling)

**Hallucination Prevention Systems**
- Pressure track mechanics table (eliminates vague NPC behavior)
- Knowledge boundaries file (defines scholar knowledge vs. unknown vs. forbidden)
- NPC memory protocol (fact memory vs. biased interpretation)
- Session notes protocol (character state snapshots, combat state, mechanical precision)
- Specific DCs, timers, and consequences for ALL events (no improvisation points)

---

### 🟡 IN PROGRESS (Future Development)

1. **Player Agent Framework** (src/agents/player_agent.py)
   - Character sheet loading
   - Action decision-making via Ollama
   - Integration with GM session loop

2. **Book I - Acts II & III** (adventure_path/03_books/BOOK_01/)
   - Glassworks investigation mechanics
   - Catacomb exploration structure
   - Thistletop assault encounter scaling

3. **Book II: Runelords Rise** (future)
   - Regional adventure framework
   - Runelord enemies and minions

---

### 🔴 NOT STARTED

1. **Shared References** (90_shared_references/)
   - Loot tables
   - Encounter mechanics lookup
   - NPC name generation

2. **Alternative Adventures** (additional books/modules)

---

## Current Capabilities

The system is now **ready for interactive play**:

```bash
python gm_launcher.py          # Boots GM Agent with all contexts loaded
>>> (Player input)              # Interactive session loop
[GM Response]                   # Rules-adjudicated outcome
>>> quit                        # Session saved to outputs/session_001_notes.json
```

**Session protocol:**
1. Load all adventure_path files in authority order
2. Receive PC information (names, classes, levels)
3. Accept player actions via stdin
4. Apply rules mechanically via Ollama + local constraints
5. Log all turns to JSON with full game state
6. Persist for multi-session continuity

**Tested with:**
- Ollama qwen3:4b model (~4GB)
- Temperature 0.3 (deterministic rules application)
- Session boot time: ~30-60 seconds (context load)
- Per-turn query time: ~5-10 seconds (typical LLM inference)

---

## Next Steps (Priority Order)

1. **Test Swallowtail Festival** - Run full session with player characters
2. **Extend Book I** - Complete Acts II & III infrastructure
3. **Implement Player Agent** - Autonomous character decision-making
4. **Build Shared References** - Loot tables, encounter utilities
5. **Extend to Book II** - Regional adventure scope

---

## Development Guidelines

### When Adding New Content

1. **Authority Hierarchy**: Always file into correct tier (00 > 01 > 02 > 03 > 90)
2. **Specificity**: No vague instructions. All mechanics need DC values, tables, specific timers
3. **Session Protocol**: Record all facts in SESSION_NOTES_PROTOCOL for continuity
4. **Hallucination Prevention**: Assume GM Agent will take any vague statement as permission to invent

### Code Patterns

- `GMConfig`: All configuration via dataclass with defaults
- `FileLoader`: Cache documents to minimize repeated I/O
- `query_ollama()`: All LLM communication through this method
- Session loop: Player input → GM response → session buffer → repeat

---

**Remember**: The goal is to demonstrate that local LLMs can autonomously manage complex collaborative games with fair rules enforcement, meaningful decision-making, and engaging roleplay. Every file and function should serve that vision.

Key constraint: All mechanics are **mechanical**, not **narrative**. Pressure tracks, encounter specs, and NPC behavior are mathematically expressed. The LLM applies these rules, not invents them.
