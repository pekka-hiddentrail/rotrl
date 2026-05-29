# Adventure Path Structure

## Overview

The `adventure_path/` folder contains all rules, settings, campaign content, and live NPC state for RotRL. It uses a **hierarchical authority system** — higher-numbered folders have lower priority and are overridden by lower-numbered folders.

---

## Directory Structure

```
adventure_path/
│
├── 00_system_authority/          [HIGHEST PRIORITY] — non-negotiable GM rules
│   ├── GM_OPERATING_RULES.md               GM behavioral constraints & neutrality
│   ├── GM_OPERATING_RULES_01_CRITICAL.md   Critical enforcement rules
│   ├── GM_OPERATING_RULES_02_GUIDELINES.md Operational guidelines
│   ├── GM_OPERATING_RULES_03_TRIVIAL.md    Low-priority style rules
│   ├── ADJUDICATION_PRINCIPLES.md          Authority hierarchy & no-fudging rule
│   ├── COMBAT_AND_POSITIONING.md           Abstract grid model & token management
│   ├── PF1E_RULES_SCOPE.md                 Allowed rulebooks & banned sources
│   ├── PERSISTENCE_HANDLING_RULES.md       How NPC state, rolls, outcomes persist
│   └── SESSION_NOTES_PROTOCOL.md           Session note format & continuity rules
│
├── 01_world_setting/              — World cosmology, geography, culture
│   ├── WORLD_OPERATING_RULES.md            Canon authority ordering, hallucination prevention
│   ├── WORLD_CANON.md                      Golarion/Varisia lore grounding
│   ├── EMERGENT_CANON.md                   Rules for safe improvisation
│   ├── COSMOLOGY_AND_GODS.md               Pantheon, divine influence
│   ├── GEOGRAPHY_AND_LOCATIONS.md          Varisia regions and key places
│   ├── LOCATION_RULES.md                   How locations are described and persist
│   ├── MAGIC_AND_METAPHYSICS.md            How magic works in Golarion
│   └── TECHNOLOGY_AND_CULTURE.md           Technology level, Varisian cultures
│
├── 02_campaign_setting/           — Campaign-specific configuration
│   ├── CAMPAIGN_OVERVIEW.md                Campaign scope, narrative phases, failure model
│   ├── THEME_AND_TONE.md                   Emotional logic, descriptive framing guidelines
│   ├── PLAYER_AGENCY_RULES.md              Constrained agency model, guaranteed freedoms
│   ├── FACTIONS_AND_POWERS.md              Major factions and interaction logic
│   ├── NPC_MEMORY_AND_CONTINUITY.md        NPC persistence rules, reuse over invention
│   ├── NPC_STATE_LOG.md                    Running log of NPC state changes across sessions
│   ├── NPC_STATE_TEMPLATE.md               Template for NPC state entries
│   └── bestiary/                           Creature stat blocks used in Book I
│       ├── goblin.md
│       ├── goblin_commando.md
│       └── goblin_warchanter.md
│
├── 03_books/                      — Published adventure content
│   └── BOOK_01_BURNT_OFFERINGS/            Rise of the Runelords Book I (Levels 1–4)
│       ├── BOOK_OVERVIEW.md                Campaign role, themes, narrative arc
│       ├── ACT_STRUCTURE.md                Act-by-act breakdown with escalation mechanics
│       ├── LOCATIONS.md                    Narrative-significant locations & world state
│       ├── SANDPOINT_LOCATIONS.md          Sandpoint district map and location profiles
│       ├── NPCS.md                         Campaign NPCs by persistence tier
│       └── EVENTS_AND_TRIGGERS.md          Time-based escalations, pressure track
│
├── 04_persistence/                — Cross-session state tracking
│   └── PERSISTENCE_LEDGER.md               Record of permanent world-state changes
│
├── 05_npcs/                       — Live NPC profiles (read by NpcIndex at runtime)
│   ├── _NPC_TEMPLATE.md                    Template for new NPC directories
│   ├── _DELTA_TEMPLATE.md                  Template for per-turn delta blocks
│   ├── abstalar_zantus/                    base.md · knowledge.md · session_002.md
│   ├── aldern_foxglove/                    base.md
│   ├── ameiko_kaijitsu/                    base.md
│   ├── belor_hemlock/                      base.md · knowledge.md
│   ├── kendra_deverin/                     base.md · knowledge.md · session_003.md
│   ├── lonjiku_kaijitsu/                   base.md
│   ├── nualia_tobyn/                       base.md
│   ├── tsuto_kaijitsu/                     base.md
│   └── .{slug}/                            Dot-prefixed = session NPC (auto-created, not yet promoted)
│
├── 06_rules/                      — Skill and rule files (read by SkillIndex at runtime)
│   └── skills/
│       ├── _SKILL_TEMPLATE.md          Template for new skill files
│       ├── bluff.md
│       ├── diplomacy.md
│       ├── intimidate.md
│       ├── knowledge_arcana.md
│       ├── knowledge_history.md
│       ├── knowledge_local.md
│       ├── knowledge_nature.md
│       ├── knowledge_nobility.md
│       ├── knowledge_planes.md
│       ├── knowledge_religion.md
│       ├── perception.md
│       ├── sense_motive.md
│       └── stealth.md
│
├── 07_locations/                  — Location profiles (read by LocationIndex at runtime)
│   ├── _LOCATION_TEMPLATE.md       Template for new location directories
│   ├── festival_grounds/           base.md
│   ├── rusty_dragon/               base.md
│   ├── sage_stage/                 base.md
│   ├── sandpoint_boneyard/         base.md
│   ├── sandpoint_cathedral/        base.md
│   ├── sandpoint_garrison/         base.md
│   ├── sandpoint_glassworks/       base.md
│   └── white_deer/                 base.md
│
└── npc_library/                   — Text pools for auto-generated NPC descriptions
    ├── appearances.txt
    ├── narrative_functions.txt
    ├── personalities.txt
    └── reactions.txt
```

---

## Authority Hierarchy

When the GM encounters conflicting rules or facts, higher entries always win. No horizontal negotiation.

```
1. Pathfinder 1e RAW  (PF1E_RULES_SCOPE.md defines what RAW applies)
   ↓
2. System Authority   (00_system_authority/ — absolute, never overridden)
   ↓
3. RotRL adventure text  (canonical adventure path)
   ↓
4. World Operating Rules  (01_world_setting/WORLD_OPERATING_RULES.md)
   ↓
5. Golarion Canon  (01_world_setting/ lore)
   ↓
6. Campaign Setting  (02_campaign_setting/ customisations)
   ↓
7. Book / Act / Encounter specifics  (03_books/ — specific overrides general)
   ↓
8. Previously established rulings  (what was ruled in session N applies now)
```

---

## How the System Uses These Files

### Boot (`create_session`)

`_build_slim_system_prompt()` in [api/session_manager.py](api/session_manager.py) loads:

1. All files from `00_system_authority/` in filename order
2. All files from `01_world_setting/` in filename order
3. All files from `02_campaign_setting/` in filename order
4. Book-level files from `03_books/BOOK_01_BURNT_OFFERINGS/`

The assembled prompt is static for the entire session — it is never mutated after boot.

### Per-turn context injection

`_inject_context()` detects keywords in the player's last message and injects (in order):

- **NPC profiles** — `05_npcs/{slug}/base.md` + `knowledge.md` + latest `session_NNN.md`
- **Skill rules** — `06_rules/skills/{skill}.md` (content above the `<!-- REFERENCE -->` marker only)
- **NPC-at-location** — NPCs whose `**Locations:**` field matches a location keyword
- **Location profiles** — `07_locations/{slug}/base.md` (content above `<!-- REFERENCE -->` only)

Location profiles persist across turns via `session.scene_locations` — once the party enters a location it is re-injected as ambient context on every subsequent turn until the session ends.

### NPC lifecycle (`05_npcs/`)

Each NPC has a directory with up to three file types:

| File | Purpose |
|------|---------|
| `base.md` | Static profile: appearance, personality, stats, relationships |
| `knowledge.md` | Accumulating knowledge entries written by `%%DELTAS%%` blocks |
| `session_NNN.md` | Per-session delta buffer, cleared on next boot |

**Session NPCs** (auto-created from `%%GENERATE%%` blocks) live in dot-prefixed directories (`.{slug}/`). To promote a session NPC to a permanent record, rename the directory to drop the leading dot. The UI "Purge NPCs" button bulk-deletes all dot-prefixed directories via `DELETE /api/npcs/session`.

### Skill files (`06_rules/skills/`)

Each file has a payload section (above `<!-- REFERENCE -->`) injected into the system prompt when the skill is triggered, and a reader-reference section (below the marker) that is never loaded. This keeps injection size small while preserving full documentation for humans.

### Location files (`07_locations/`)

One directory per canonical location. Each `base.md` starts with `# Canonical Name` and `**Aliases:**` (comma-separated detection keywords). Content above `<!-- REFERENCE -->` is injected as a `## Location Reference — {name}` block. Content below the marker (district, type, author notes) is never injected.

Session-generated locations (from `%%GENERATE%%` blocks with `type: location`) are created in `07_locations/{slug}/` immediately and the `LocationIndex` is invalidated so they are detectable on the very next turn. Unlike session NPCs, location stubs are not dot-prefixed and are not purged between sessions.

---

## Key Files for Reference

| File | Purpose |
|------|---------|
| [api/session_manager.py](api/session_manager.py) | `_build_slim_system_prompt`, `_inject_context`, `_stream_chat`, NPC/delta writes |
| [api/main.py](api/main.py) | All FastAPI routes |
| [api/context/npc_lookup.py](api/context/npc_lookup.py) | `NpcIndex` singleton, alias detection |
| [api/context/skill_lookup.py](api/context/skill_lookup.py) | `SkillIndex`, trigger detection |
| [api/context/location_lookup.py](api/context/location_lookup.py) | `LocationIndex` singleton, location alias detection and profile injection |
| [README.md](README.md) | Setup, startup, and usage guide |
