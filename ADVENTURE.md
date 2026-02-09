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
├── 03_books/                      - Adventure books/modules
│   └── temp.md                    ⧖ PLACEHOLDER - (for future adventure chapters)
│
└── 90_shared_references/          - Shared lookup tables & utilities
    └── temp.md                    ⧖ PLACEHOLDER - (for shared resources)
```

**Legend:**
- `✅ ACTIVE` = File has substantial content (used by GM)
- `🟨 IN PROGRESS` = File has evolving content (partially populated)
- `⧖ PLACEHOLDER` = File structure exists, content pending

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

### 🟡 Section 02: Campaign Setting (PLACEHOLDER)

**Status:** ⧖ **Ready for content** - Structure defined, awaiting campaign details

**Purpose:** Define campaign-specific elements that override world defaults.

**Planned Content:**
- CAMPAIGN_OVERVIEW.md - Campaign arc, timeline, scale
- THEME_AND_TONE.md - Emotional tone (gritty? heroic? noir?)
- FACTIONS_AND_POWERS.md - Major players, enemies, allies
- LONG_ARC_THREATS.md - Main antagonists and their goals
- PLAYER_AGENCY_RULES.md - What choices matter in this campaign

---

### 🟡 Section 03: Adventure Books (PLACEHOLDER)

**Status:** ⧖ **Ready for content** - For individual adventure chapters/modules

**Purpose:** Organize published or custom adventures into acts and encounters.

**Planned Structure:**
- Individual adventure files or subdirectories
- Each with encounters, NPC stats, treasure tables, etc.

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
- Reads 00_system_authority/ at startup → sets behavioral constraints
- Reads 01_world_setting/ + 02_campaign_setting/ → builds world model
- References 03_books/ + 90_shared_references/ → finds encounter data
- Always checks authority hierarchy when rules conflict

### Player Agents
- Read 02_campaign_setting/ → understand campaign constraints
- Reference 01_world_setting/ → understand lore and implications
- Use 90_shared_references/ → look up mechanics and history
- Don't directly read 00_system_authority/ (GM enforces)

### System Architect (You)
- Modify 00_system_authority/ only when changing core GM behavior
- Populate later sections only when confident in structure
- Remember: Higher sections override lower sections always

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

**Status Updated:** Feb 9, 2026 | **Total Defined Rules:** ~1,118 lines | **Complete Sections:** 1 (00) | **In Progress:** 1 (01) | **Placeholder:** 3 (02, 03, 90)
