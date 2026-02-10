# RotRL AI Agents

This document defines all AI agents used in the Rise of the Runelords campaign automation system.

## Agent Architecture

All agents follow these principles:

1. **Authority Hierarchy**: System Authority (00_*) > World Setting (01_*) > Campaign (02_*) > Books (03_*) > Session State
2. **Determinism**: Same input + same LLM model + temperature=0.0 yields same output (for rules arbiter roles)
3. **Constraint Binding**: Each agent loads its governing rulesets before initialization
4. **State Tracking**: Session notes capture all PC-relevant facts for continuity between sessions
5. **No Retroactive Changes**: Once recorded in session notes, facts cannot be contradicted

---

## GM Agent (Game Master AI)

**Location**: `src/agents/gm_agent.py`

**Purpose**: Rules arbiter and world simulator for Pathfinder 1st Edition gameplay.

**Core Responsibilities**:
- Apply PF1e rules RAW (as written) without modification
- Maintain impartial adjudication of all mechanical outcomes
- Simulate the world state accurately (time progression, NPC behaviors, event triggers)
- Present information only to PCs that their characters could perceive
- Never fudge dice rolls, adjust DCs retroactively, or protect player characters

### Initialization

```python
from src.agents.gm_agent import GMAgent, GMConfig

config = GMConfig()
gm = GMAgent(config)
gm.boot_session(session_number=1)
```

### File Loading Sequence

The GM Agent loads files in strict precedence order:

1. **System Authority** (00_*)
   - `GM_OPERATING_RULES.md` - Core GM behavioral rules
   - `ADJUDICATION_PRINCIPLES.md` - Conflict resolution and fairness rules
   - `COMBAT_AND_POSITIONING.md` - Combat mechanics and grid rules
   - `PF1E_RULES_SCOPE.md` - What rules are in/out of scope
   - `SESSION_NOTES_PROTOCOL.md` - Fact recording and state tracking

2. **World Context** (01_*)
   - `WORLD_OPERATING_RULES.md` - Time, magic, divine interaction systems
   - `WORLD_CANON.md` - Established lore facts (immutable)
   - Geographic and cosmological constraints

3. **Campaign Rules** (02_*)
   - `CAMPAIGN_OVERVIEW.md` - Scope and bounds of campaign
   - `THEME_AND_TONE.md` - Emotional safety, humor rules, fade-to-black protocol
   - `PLAYER_AGENCY_RULES.md` - Player power/limitation boundaries
   - `NPC_MEMORY_AND_CONTINUITY.md` - NPC knowledge and bias mechanics

4. **Book-Specific Content** (03_books/BOOK_01_BURNT_OFFERINGS/)
   - `BOOK_OVERVIEW.md` - Structure and narrative arc
   - `NPCS.md` - Characters, motivations, stat blocks
   - `LOCATIONS.md` - Locations, mechanics, secrets
   - `EVENTS_AND_TRIGGERS.md` - Escalation timers, pressure mechanics
   - `ACT_STRUCTURE.md` - Current act breakdown

5. **Session State** (outputs/session_XXX_notes.json)
   - Previous session facts (may override tier 1/2 inventions with tier 3 canon)
   - PC knowledge state
   - NPC memory updates

### Boot Flow

```
gm.boot_session()
  ├─ Load all system authority files → self.system_context
  ├─ Load all campaign context files → self.campaign_context
  ├─ Load Book I files → self.book_context
  ├─ Build comprehensive GM prompt (combines all contexts)
  ├─ Query Ollama LLM → initialize GM state
  └─ Display GM ready message
```

### Session Loop

```
gm.session_loop()
  ├─ Await player/GM input
  ├─ Build context message (current state + input)
  ├─ Query Ollama LLM
  ├─ Display GM response
  ├─ Buffer turn to session notes
  └─ Repeat until quit or error
```

### Session Notes Output

Session notes are saved to `outputs/session_XXX_notes.json` with structure:

```json
{
  "session_number": 1,
  "book": 1,
  "act": 1,
  "turns": [
    {
      "turn": 1,
      "player_input": "...",
      "gm_output": "..."
    }
  ]
}
```

## Configuration

### GMConfig Parameters

```python
GMConfig(
    ollama_host="http://localhost:11434",      # Ollama LLM server
    ollama_model="qwen3:4b",                    # Model name (default: qwen3:4b)
    adventure_path_root=None,                   # Defaults to rotrl/adventure_path/
    temperature=0.3                             # Lower = more deterministic (for rules)
)
```

### Model Selection

The GM Agent works with any model available in Ollama, defaulting to **Qwen 3 4B**:

- **Qwen 3 4B** (4B): Default choice, lightweight, ~2-5s per query
- **Qwen 2** (7B): More capable but slower
- **Llama 2** (7B): General-purpose, slightly slower
- **Mistral** (7B): Good balance of speed/quality

Start Ollama with:
```bash
ollama serve
```

Then (in another terminal), pull the model:
```bash
ollama pull qwen3:4b
```

## Usage Examples

### Boot and Play Single Session

```python
#!/usr/bin/env python3
from src.agents.gm_agent import GMAgent, GMConfig

config = GMConfig(ollama_model="qwen3:4b")
gm = GMAgent(config)

# Initialize
gm.boot_session(session_number=1)

# Play
gm.session_loop()
```

### Boot Multiple Sessions

```python
for session_num in range(1, 6):
    gm = GMAgent(config)
    gm.boot_session(session_number=session_num)
    gm.session_loop()
    # Session notes auto-saved
```

### Query GM Directly (No Session Loop)

```python
gm = GMAgent(config)
gm.load_contexts(book=1, act=1)

prompt = "The wizard casts Fireball at the goblins. Roll damage results: 18, 22, 15."
response = gm.query_ollama(prompt)
print(response)
```

---

## Planned Agents

These agents are **not yet implemented** but are specified in the design:

### Player Agent (Future)

**Purpose**: Simulate NPC player characters for solo play testing.

**Design**:
- Load character sheet + personality rules
- Query Ollama for action decision
- Integrate with GM Agent for turn sequence

### Chronicler Agent (Future)

**Purpose**: Summarize sessions, maintain long-term lore, detect contradictions.

**Design**:
- Process session notes → EMERGENT_CANON entries
- Check new facts against existing canon
- Flag hallucinations for human review
- Generate session summary document

### Lore Keeper Agent (Future)

**Purpose**: Maintain world consistency, prevent knowledge leakage.

**Design**:
- Respond to queries: "What do NPCs know?"
- Cross-reference EMERGENT_CANON + NPC_MEMORY_AND_CONTINUITY
- Enforce knowledge tier boundaries
- Suggest NPC dialogue that respects knowledge constraints

---

## Ollama Integration

All agents communicate with Ollama via HTTP REST API.

### API Endpoint: `/api/generate`

```python
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3:4b",
        "prompt": "Your query here",
        "stream": False,
        "temperature": 0.3,
    },
    timeout=180
)
response_text = response.json()["response"]
```

### Error Handling

Agents catch and report:
- Connection errors → "Ollama not running"
- Timeout errors → "Query timeout (180s exceeded)"
- HTTP errors → "{status_code}: {error_text}"

---

## Testing Agents

### Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

Should return list of available models.

### Test GM Agent Boot

```bash
cd rotrl
python3 -m src.agents.gm_agent
```

Expected output:
```
================================================================================
ROTR] GM AGENT SESSION BOOT
================================================================================

[GM-AGENT] Loading system authority files...
[GM-AGENT] Loading campaign context files...
[GM-AGENT] Loading Book I files...
[GM-AGENT] Contexts loaded successfully
[GM-AGENT] Building boot prompt...
[GM-AGENT] Initializing GM Agent with Ollama...
[OLLAMA] Sending boot prompt (this may take 30-60 seconds)...

================================================================================
GM AGENT INITIALIZED
================================================================================

[GM Response greeting with context confirmation]
```

Then type player actions or 'quit' to exit.

---

## Constraints and Safety

### What Agents WILL NOT Do

- **Invent lore** beyond defined knowledge tiers
- **Contradict session facts** once recorded in notes
- **Fudge mechanics** or rules adjudication
- **Protect characters** by adjusting DCs or hiding consequences
- **Ignore environmental state** (grid positioning, weather effects, etc.)

### What Agents MUST Enforce

- **File hierarchy authority** (system rules > world > campaign > book > session)
- **Pressure mechanics** (escalation timers, NPC state tracking)
- **NPC memory binding** (facts from session notes, emotions can vary)
- **Knowledge boundaries** (scholars don't know X, can't invent Y)
- **Content safety** (fade-to-black protocol, tone consistency)
- **Mechanical resolution** (all outcomes determined by dice + rules, not narrative convenience)

---

## Future Development

### Priority 1: Multi-Session State Management
- Load campaign state from previous sessions
- Resolve conflicts between EMERGENT_CANON entries
- Track Pressure track evolution

### Priority 2: NPC Scheduling and Memory
- Automatically track NPC locations per daily schedule
- Flag memory contradictions for human review
- Generate NPC dialogue respecting knowledge constraints

### Priority 3: Encounter Scaling
- Dynamically adjust encounter difficulty based on PC level/resources
- Track combat state across multiple rounds
- Auto-generate loot based on encounter level

---

## Questions?

See parent directory files:
- `CONTEXT.md` - Campaign overview
- `ADVENTURE.md` - Adventure path status
- `adventure_path/00_system_authority/GM_OPERATING_RULES.md` - Core rules
