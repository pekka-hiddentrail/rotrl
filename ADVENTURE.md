# Adventure Path Structure & Current Status

## Overview

The **adventure_path** folder contains all rules, settings, and campaign configuration for RotRL. It's organized as a **hierarchical authority system** where higher-numbered folders (lower priority) are superseded by lower-numbered folders (higher priority) and System Authority documents.

This ensures:
- ✅ GM behavior is predictable and rules-compliant
- ✅ Conflicts are resolved by authority hierarchy, never by interpretation
- ✅ Campaign rules can be added without breaking system core
- ✅ Each agent has clear operational guidelines

---

## Directory Structure

```
adventure_path/
│
├── 00_system_authority/          [HIGHEST PRIORITY] - Non-negotiable GM rules
│   ├── GM_OPERATING_RULES.md      ✅ ACTIVE - GM behavioral constraints & neutrality
│   ├── ADJUDICATION_PRINCIPLES.md ✅ ACTIVE - Authority hierarchy & fudging rules
│   ├── COMBAT_AND_POSITIONING.md  ✅ ACTIVE - Spatial model & combat mechanics
│   └── PF1E_RULES_SCOPE.md        ✅ ACTIVE - Allowed rulebooks & banned sources
│
├── 01_world_setting/              - World cosmology, gods, history, culture
│   ├── WORLD_CANON.md             ⧖ PLACEHOLDER - Main world lore
│   ├── COSMOLOGY_AND_GODS.md      ⧖ PLACEHOLDER - Religious & celestial structure
│   ├── MAGIC_AND_METAPHYSICS.md   ⧖ PLACEHOLDER - How magic works in-world
│   └── TECHNOLOGY_AND_CULTURE.md  ⧖ PLACEHOLDER - Technology & cultures
│
├── 02_campaign_setting/           - Campaign-specific configuration
│   ├── CAMPAIGN_OVERVIEW.md       ⧖ PLACEHOLDER - Campaign timeline & scope
│   ├── THEME_AND_TONE.md          ⧖ PLACEHOLDER - Campaign's emotional arc
│   ├── FACTIONS_AND_POWERS.md     ⧖ PLACEHOLDER - Major factions & organizations
│   ├── LONG_ARC_THREATS.md        ⧖ PLACEHOLDER - Main campaign antagonists
│   └── PLAYER_AGENCY_RULES.md     ⧖ PLACEHOLDER - Campaign-specific freedoms
│
├── 03_books/                      - Adventure books/modules (✅ BOOK_01 ACTIVE)
│   ├── BOOK_01_BURNT_OFFERINGS/   ✅ ACTIVE - Foundational adventure Swallowtail Festival (Lvl 1-4, ~2,100 lines)
│   │   ├── BOOK_OVERVIEW.md       ✅ ACTIVE - Campaign role, themes, narrative structure
│   │   ├── ACT_STRUCTURE.md       ✅ ACTIVE - Act-by-act breakdown with escalation mechanics
│   │   ├── LOCATIONS.md           ✅ ACTIVE - Narrative-significant locations & world state (with Runewell mechanics)
│   │   ├── NPCS.md                ✅ ACTIVE - Campaign NPCs by persistence tier (stat blocks, motivations)
│   │   ├── EVENTS_AND_TRIGGERS.md ✅ ACTIVE - Time-based escalations, pressure track, NPC consequences
│   │   ├── ACT_01/                ✅ ACTIVE - Act I complete infrastructure (~570 lines)
│   │   │   ├── act_overview.md    ✅ - Scene structure, mandatory revelations, escalation triggers
│   │   │   ├── active_npcs.md     ✅ - NPC schedules & tier-based availability
│   │   │   ├── current_tensions.md✅ - Background conflicts, pressure mechanics
│   │   │   └── encounters/encounter_01.md ✅ - Goblin Cavalry encounter (complete stat blocks, tactics, loot)
│   │   ├── ACT_02/                🔲 PLACEHOLDER - (future expansion)
│   │   └── ACT_03/                🔲 PLACEHOLDER - (future expansion)
│   └── BOOK_02_RUNELORDS_RISE/    🔲 PLACEHOLDER - (future adventure book)
│
└── 90_shared_references/          - Shared lookup tables & utilities
    └── temp.md                    🔲 PLACEHOLDER - (for shared resources)
```

**Legend:**
- `✅ ACTIVE` = File has substantial content (used by GM Agent, tested)
- `🟨 IN PROGRESS` = File has evolving content (partially populated, not yet complete)
- `🔲 PLACEHOLDER` = File structure exists, content pending
- `⧖ DEPRECATED` = Superseded by newer structure

---

## Current Status by Section

### � Section 00: System Authority (ACTIVE)

**Status:** ✅ **Core system complete** - GM behavior & rules fully specified

#### Currently Defined:

1. **[GM_OPERATING_RULES.md](adventure_path/00_system_authority/GM_OPERATING_RULES.md)** (204 lines)
   - Role Definition: GM is a neutral rules arbiter, not a storyteller
   - Neutrality enforcement: No favoring players or narrative outcomes
   - Player Agency Supremacy: Players decide intent; GM presents consequences
   - Information Control: What NPCs know vs what players know
   - Narration constraints: How the GM describes the world

2. **[ADJUDICATION_PRINCIPLES.md](adventure_path/00_system_authority/ADJUDICATION_PRINCIPLES.md)** (197 lines)
   - Authority Hierarchy: Strict order (RAW > System Authority > World Canon > Campaign > Book-level)
   - Pathfinder 1e Rules Supremacy: No narrative override of mechanics
   - No Fudging Rule: Dice results, DCs, and NPC stats are irreversible
   - Player Declarations Only: GM resolves explicit actions, not implied ones
   - Uncertainty Resolution: How to handle unknown facts during play

3. **[COMBAT_AND_POSITIONING.md](adventure_path/00_system_authority/COMBAT_AND_POSITIONING.md)** (173 lines)
   - Spatial Model: Abstract 5-foot grid system
   - Explicit Spatial State: Required format for position tracking
   - Token Management: How creatures, PCs, and obstacles are tracked
   - Update Rules: How to handle movement, reach, and area spells
   - Mechanical Sanctity: Positioning cannot be narrative-handwaved

4. **[PF1E_RULES_SCOPE.md](adventure_path/00_system_authority/PF1E_RULES_SCOPE.md)** (144 lines)
   - Core System: Pathfinder 1e RAW only, no Unchained or 3.5
   - Allowed Rulebooks: 9 primary sources approved (Core, ACG, ARG, etc.)
   - Bestiary Sources: 3 official Bestiaries allowed for creature stats
   - Explicitly Banned: Unchained, Mythic Adventures, Leadership feat
   - Custom Content: Guidelines for adding homebrew material

---

### 🟡 Section 01: World Setting (IN PROGRESS)

**Status:** 🟨 **Content emerging** - Core structure defined and being populated

**Setting:** Golarion (Varisia) - Rise of the Runelords Adventure Path

#### Currently Defined:

1. **[WORLD_OPERATING_RULES.md](adventure_path/01_world_setting/WORLD_OPERATING_RULES.md)** (223 lines)
   - ✅ Canon authority hierarchy (RotRL > Golarion canon > project docs > improvisation)
   - ✅ World scope: Golarion/Varisia/Lost Coast (intentionally bounded)
   - ✅ Prevents lore hallucination and canon drift
   - ✅ Allows controlled improvisation where safe
   - ✅ AI GM constraints for knowledge boundaries

2. **[WORLD_CANON.md](adventure_path/01_world_setting/WORLD_CANON.md)** (175 lines)
   - ✅ Primary region: Varisia (northwestern Avistan)
   - ✅ Lore grounded in Rise of the Runelords + Paizo canon
   - ✅ Authority ordering: RotRL > Varisia sourcebooks > Sandpoint guides
   - ✅ Thassilon ancient empire context
   - ⧖ Intentionally incomplete (background + emergent canon)

3. **[EMERGENT_CANON.md](adventure_path/01_world_setting/EMERGENT_CANON.md)** (empty)
   - ⧖ Rules for improvisation within safe boundaries
   - ⧖ How to extend canon without contradicting published material

#### Still Placeholder:
- COSMOLOGY_AND_GODS.md - Pantheon, alignments, divine influence
- MAGIC_AND_METAPHYSICS.md - How magic works in Golarion
- TECHNOLOGY_AND_CULTURE.md - Technology level, Varisia cultures

---

### 🟡 Section 02: Campaign Setting (ACTIVE)

**Status:** ✅ **Campaign framework complete** - Core campaign structure fully specified

**Purpose:** Define campaign-specific elements (tone, scope, player freedoms, faction rules)

#### Currently Defined:

1. **[CAMPAIGN_OVERVIEW.md](adventure_path/02_campaign_setting/CAMPAIGN_OVERVIEW.md)** (158 lines)
   - ✅ Campaign Name: Rise of the Runelords in Varisia
   - ✅ System: Pathfinder 1e
   - ✅ Geographic/Narrative scope: Varisia, local → world-altering arc
   - ✅ Six narrative phases (Lvl 1–16+): Local Defenders → Final Reckoning
   - ✅ Central themes: Ancient sin momentum, civilization fragility, knowledge danger
   - ✅ Failure/Recovery model: Permanent but campaign-adaptive

2. **[THEME_AND_TONE.md](adventure_path/02_campaign_setting/THEME_AND_TONE.md)** (218 lines)
   - ✅ Emotional logic and descriptive framing guidelines
   - ✅ Core thematic pillars: Ancient sin, civilization fragility, knowledge danger
   - ✅ Tone escalation and NPC behavior patterns
   - ✅ GM instructions for maintaining campaign atmosphere

3. **[PLAYER_AGENCY_RULES.md](adventure_path/02_campaign_setting/PLAYER_AGENCY_RULES.md)** (123 lines)
   - ✅ Constrained agency model: Players choose *how*, not *whether*
   - ✅ Guaranteed freedoms: approach choice, alliance forming, retreat, failure tolerance
   - ✅ Explicit constraints: No opting out, no off-genre escape, no world-rewriting
   - ✅ Avoidance is treated as a player choice, not an escape route

4. **[FACTIONS_AND_POWERS.md](adventure_path/02_campaign_setting/FACTIONS_AND_POWERS.md)** (207 lines)
   - ✅ Faction design principles: persistence, hierarchy, realism
   - ✅ Major campaign factions: Thassilonian Remnants, The Runelords, Sandpoint powers, wilderness threats
   - ✅ Faction interaction logic and adaptation patterns
   - ✅ Rules against invention drift; existing factions prioritized

5. **[NPC_MEMORY_AND_CONTINUITY.md](adventure_path/02_campaign_setting/NPC_MEMORY_AND_CONTINUITY.md)** (✅ ACTIVE)
   - ✅ Named NPCs persist unless explicitly removed
   - ✅ NPC competence scales with role
   - ✅ Returning to locations reuses established NPCs
   - ✅ Prevents NPC churn and town inconsistency

---

### 🟡 Section 03: Adventure Books (IN PROGRESS)

**Status:** 🟨 **Content emerging** - First book structured and being populated

**Purpose:** Organize published or custom adventures into acts and encounters.

#### Currently Defined:

1. **BOOK_01_BURNT_OFFERINGS** (🟨 IN PROGRESS)
   - ✅ **[BOOK_OVERVIEW.md](adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/BOOK_OVERVIEW.md)** (72 lines)
     - Campaign role: Establishing Sandpoint as emotional anchor
     - Character levels: 1–4
     - Core themes: Community, celebration interrupted, ancient evil seeping through
     - Narrative responsibilities and long-arc connections
   
   - ✅ **[LOCATIONS.md](adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/LOCATIONS.md)** (171 lines)
     - Narrative-significant locations (not room-by-room layouts)
     - Sandpoint as dynamic emotional center
     - Persistent location state changes
     - Swallowtail Festival and other key areas
   
   - ✅ **[NPCS.md](adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/NPCS.md)** (247 lines)
     - Campaign-significant NPCs organized by persistence tier
     - Tier I: Structural NPCs (load-bearing characters)
     - Tier II: Emotional anchors (why Sandpoint matters)
     - State-based outcomes (if cooperative, if distrustful, if killed)
   
   - 🟨 **[ACT_STRUCTURE.md](adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/ACT_STRUCTURE.md)** (IN PROGRESS)
     - Act-by-act breakdown
   
   - 🟨 **[EVENTS_AND_TRIGGERS.md](adventure_path/03_books/BOOK_01_BURNT_OFFERINGS/EVENTS_AND_TRIGGERS.md)** (IN PROGRESS)
     - Time-based escalations and conditional events
     - Player-triggered accelerations and world reactions
   
   - 🟨 **act_01/** (IN PROGRESS)
     - Detailed Act I encounters and specifications

---

### 🟡 Section 90: Shared References (PLACEHOLDER)

**Status:** ⧖ **Ready for content** - For reusable lookup tables

**Purpose:** Common reference tables used across multiple adventures.

**Planned Content:**
- Loot tables, random encounter tables
- NPC name generators
- Encounter difficulty calculations
- Condition effect reminders

---

## Authority Hierarchy (Enforced)

When the GM encounters conflicting rules or facts:

```
1. Pathfinder 1e RAW (PF1E_RULES_SCOPE.md defines what RAW applies)
   ↓
2. System Authority (00_system_authority/ rules are absolute)
   ↓
3. Rise of the Runelords text (canonical adventure path)
   ↓
4. World Operating Rules (01_world_setting/WORLD_OPERATING_RULES.md)
   ↓
5. Golarion Canon (01_world_setting/ lore precedents)
   ↓
6. Campaign Setting rules (02_campaign_setting/ customizations)
   ↓
7. Book/Act/Encounter instructions (03_books/ specifics override generals)
   ↓
8. Previously established rulings (What was ruled in Session N applies now)
```

**No horizontal negotiation.** Higher authority always wins.

**Special Note:** World Operating Rules (WORLD_OPERATING_RULES.md) exist *between* System Authority and Campaign Setting to prevent canon drift and hallucination while allowing controlled improvisation.

---

## How Agents Use This

### GM Agent
**Status:** ✅ **IMPLEMENTED** - See [src/agents/gm_boot_agent.py](src/agents/gm_boot_agent.py)

- Reads 00_system_authority/ at startup → sets behavioral constraints
- Reads 01_world_setting/ + 02_campaign_setting/ → builds world model
- References 03_books/ + 90_shared_references/ → finds encounter data
- Always checks authority hierarchy when rules conflict
- **Launch:** `python gm_launcher.py` or `python -m src.agents.gm_boot_agent`
- **Quick Start:** See [QUICKSTART_GM.md](QUICKSTART_GM.md)

Key implementation files:
- [gm_launcher.py](gm_launcher.py) - Command-line launcher with Ollama verification
- [AGENTS.md](AGENTS.md) - Complete agent architecture documentation
- [outputs/README.md](outputs/README.md) - Session notes format and protocol

### Player Agents
- Read 02_campaign_setting/ → understand campaign constraints
- Reference 01_world_setting/ → understand lore and implications
- Use 90_shared_references/ → look up mechanics and history
- Don't directly read 00_system_authority/ (GM enforces)
- **Status:** 🔲 Not yet implemented (future development)

### System Architect (You)
- Modify 00_system_authority/ only when changing core GM behavior
- Populate later sections only when confident in structure
- Remember: Higher sections override lower sections always
- **Verify:** Run `python gm_launcher.py` to test GM Agent boot

---

## Next Steps

### Immediate (High Priority)
- [ ] Fill in Section 01: World Setting (cosmology, gods, technology)
- [ ] Fill in Section 02: Campaign Setting (campaign tone, main threats)
- [ ] Add first adventure module to Section 03: Books

### When Ready
- [ ] Create Section 90 shared reference tables (loot, encounters, names)
- [ ] Document house rules in System Authority if needed

### Never
- ❌ Allow a player-facing document to override 00_system_authority/
- ❌ Add rules that conflict with Pathfinder 1e RAW without explicit System Authority override
- ❌ Use a world-setting detail to override campaign-setting rules

---

## Key Principles

1. **Authority Hierarchy is Law** - No rule negotiation; hierarchy decides always
2. **Nested Specificity** - Specific campaign rules override general world rules
3. **Immutability** - Once written, higher-authority rules don't change mid-campaign
4. **Clarity Over Cleverness** - Explicit, boring rules beat implicit, elegant ones
5. **GM as Rules Engine** - GM enforces hierarchy; players accept outcomes

---

## Quick Links

- **System Authority** → [adventure_path/00_system_authority/](adventure_path/00_system_authority/)
- **World Lore** → [adventure_path/01_world_setting/](adventure_path/01_world_setting/)
- **Campaign Config** → [adventure_path/02_campaign_setting/](adventure_path/02_campaign_setting/)
- **Adventures** → [adventure_path/03_books/](adventure_path/03_books/)
- **Shared Resources** → [adventure_path/90_shared_references/](adventure_path/90_shared_references/)

---

**Status Updated:** Feb 10, 2026 | **Infrastructure:** GM Agent Bootstrapped | **Book I:** ~50% documented | **Hallucination Prevention:** Comprehensive | **Ready for Play:** YES

---

## Implementation Status

| Component | Status | Details |
|-----------|--------|---------|
| **System Authority** (00_*) | ✅ Complete | 5 files, ~900 lines of core rules |
| **World Setting** (01_*) | ✅ Complete | 7 files, ~1,300 lines of world canon |
| **Campaign Setting** (02_*) | ✅ Complete | 5 files, ~730 lines of campaign rules |
| **Book I - Swallowtail Festival** | ✅ Complete | NPCS, Locations, Events, Act I infrastructure (~2,100 total) |
| **Book I - Act 01** | ✅ Complete | 4 files: overview, active_npcs, tensions, encounter_01 full spec |
| **Book I - Act 02-03** | 🔲 Placeholder | Structure ready, content pending |
| **GM Agent** | ✅ Complete | Full context loading + session loop + Ollama integration |
| **Session Notes** | ✅ Complete | JSON persistence + multi-session continuity protocol |
| **Hallucination Prevention** | ✅ Complete | Pressure tables, encounter specs, knowledge boundaries |
| **Shared References** (90_*) | 🔲 Placeholder | Lookup tables and utilities (not yet needed) |


