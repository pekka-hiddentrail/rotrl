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

**Location**: `src/agents/gm_agent.py` | Boot Prompt: `.agents/GM/SESSION_BOOT_PROMPT.md`

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

### Boot-First Architecture

**The GM Agent follows a boot-prompt-first design:**

1. **Canonical Boot Prompt** (`.agents/GM/SESSION_BOOT_PROMPT.md`)
   - Defines the mandatory boot protocol (role, constraints, narration rules)
   - Contains three placeholder injection points: `{{SYSTEM_AUTHORITY}}`, `{{PLAYER_IDENTITY}}`, `{{CONTINUITY_ANCHOR}}`
   - Served as system prompt to Ollama /api/chat endpoint
   - Version-controlled and independently maintainable

2. **Context Injection** (Python code loads and injects)
   - System Authority files (~900 lines) injected into `{{SYSTEM_AUTHORITY}}`
   - Player characters file (if present) injected into `{{PLAYER_IDENTITY}}`
   - Previous session notes (if present) injected into `{{CONTINUITY_ANCHOR}}`
   - Rendered prompt sent to LLM with full context binding

### File Loading Sequence

The GM Agent loads and injects files in strict precedence order:

1. **System Authority** (adventure_path/00_system_authority/*)
   - `GM_OPERATING_RULES.md` - Core GM behavioral rules
   - `ADJUDICATION_PRINCIPLES.md` - Conflict resolution and fairness rules
   - `COMBAT_AND_POSITIONING.md` - Combat mechanics and grid rules
   - `PF1E_RULES_SCOPE.md` - What rules are in/out of scope
   - `SESSION_NOTES_PROTOCOL.md` - Fact recording and state tracking
   - **Injected into**: `{{SYSTEM_AUTHORITY}}` placeholder in boot prompt

2. **Player Identity** (adventure_path/PLAYER_CHARACTERS.md, if present)
   - PC names, classes, levels, backgrounds
   - **Injected into**: `{{PLAYER_IDENTITY}}` placeholder in boot prompt

3. **Continuity Anchor** (adventure_path/SESSION_NOTES_LAST.md, if present)
   - Previous session facts and NPC memory updates
   - **Injected into**: `{{CONTINUITY_ANCHOR}}` placeholder in boot prompt

### Boot Sequence

```
gm.boot_session()
  ├─ Load canonical boot prompt from .agents/GM/SESSION_BOOT_PROMPT.md
  ├─ Load System Authority files (5 files) → system_context
  ├─ Check for PLAYER_CHARACTERS.md (optional) → player_context
  ├─ Check for SESSION_NOTES_LAST.md (optional) → continuity_context
  ├─ Inject all contexts into boot prompt placeholders
  ├─ Query Ollama /api/chat with system prompt binding
  ├─ Extract "# Session Boot Output" section from boot prompt file
  └─ Display opening narration + boot output
```

### Ollama Integration

The GM Agent uses Ollama's `/api/chat` endpoint for proper system prompt binding:

```python
response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "qwen3:4b",
        "messages": [
            {"role": "system", "content": rendered_system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "temperature": 0.3,
    },
    timeout=180
)
```

The system prompt (rendered boot prompt with injected contexts) ensures the LLM respects all constraints before seeing user input.

### Boot Output

After generating the opening narration, the agent automatically extracts and displays the `# Session Boot Output` section from SESSION_BOOT_PROMPT.md. This section contains:
- Self-check verification that boot protocol was followed
- Confirmation of loaded contexts
- Ready state indicator

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
    ollama_host="http://localhost:11434",           # Ollama LLM server
    ollama_model="qwen3:4b",                        # Model name (default: qwen3:4b)
    temperature=0.3,                                # Lower = more deterministic (for rules)
    repo_root=None,                                 # Auto-detected; access .agents/
    adventure_path_root=None,                       # Defaults to rotrl/adventure_path/
    boot_prompt_path=None                           # Defaults to .agents/GM/SESSION_BOOT_PROMPT.md
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

## FileLoader Pattern

The GM Agent uses dual FileLoader instances for clean separation of concerns:

```python
# In GMAgent.__init__()
self.loader = FileLoader(config.repo_root)              # Loads from repo root (.agents/)
self.adventure_loader = FileLoader(config.adventure_path_root)  # Loads from adventure_path/
```

This allows:
- Canonical boot prompt to be independently versioned in repo root
- Adventure rules to be dynamically loaded from adventure_path/
- Clean separation between system infrastructure and campaign content

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
python gm_launcher.py
```

Expected output:
```
================================================================================
GM AGENT BOOT SEQUENCE
================================================================================

[GM-AGENT] Loading boot contexts...
[GM-AGENT] Building system prompt from canonical boot file...
[GM-AGENT] Querying Ollama for opening narration...

================================================================================
OPENING NARRATION
================================================================================

[Sensory-grounded opening scene]
**What do you do?**

--------------------------------------------------------------------------------

# Session Boot Output

[Boot protocol verification and confirmation]
```

The boot output section confirms that the Session Boot Protocol was followed.

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
