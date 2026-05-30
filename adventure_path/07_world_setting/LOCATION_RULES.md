# LOCATION_RULES.md

> **Authority Level:** Campaign Infrastructure
> This file defines the canonical rules for using locations and buildings in play, including scope, permissions, and templates. These rules are binding for all acts, scenes, encounters, and persistence handling unless overridden by higher-priority System Authority files.


## PURPOSE

Locations are a primary source of AI hallucination if not tightly constrained. This document exists to:

* Prevent spatial drift and location creep
* Separate *existence* from *use*
* Enforce consistent handling of buildings and interiors
* Provide standardized templates for location-related records

The AI GM MUST NOT introduce, modify, or resolve locations except as allowed here.


## LOCATION CATEGORIES

Locations are resolved at four distinct categories. Each category has different permissions.

### 1. WORLD LOCATIONS

Examples: Varisia, Sandpoint, Magnimar

**Rules:**

* Defined only in world canon files
* Never created, altered, or destroyed during play
* Acts may reference but never redefine them


### 2. ACT LOCATIONS

Examples: Festival Square, Cathedral District, Adjacent Streets

**Rules:**

* Declared explicitly in an act’s START STATE or SCENE DEFINITIONS
* Define the maximum navigable area during an act
* May be activated or deactivated by scenes

**Forbidden:**

* Adding new districts or travel destinations
* Expanding beyond declared scope


### 3. BUILDINGS (STATIC OBJECTS)

Buildings are static world objects. They are **not scenes, encounters, or locations by themselves**.

Buildings are divided into two types:

* **Named Buildings** (indexed)
* **Unnamed Buildings** (generic)

Buildings do not progress, act, or initiate events.


### 4. ENCOUNTER SPATIAL FEATURES

Temporary, encounter-bound elements (fire, debris, crowds).

**Rules:**

* Exist only for the duration of the encounter
* Must be observable and concrete
* Must not contradict known building facts


## NAMED BUILDINGS

Named buildings are fully indexed entities listed in a separate BUILDING_INDEX file (e.g. Sandpoint).

### Rules for Named Buildings

* May only be referenced if they exist in the index
* May not be created during play
* May not gain new properties, NPCs, or functions unless persisted explicitly
* Interiors are LOCKED by default

Named buildings represent *potential*, not guaranteed access.


## UNNAMED BUILDINGS

Unnamed buildings represent generic background structures.

### Rules for Unnamed Buildings

* Referred to only by size and function (e.g. “a two-storey shop”)
* Never receive names, ownership, or unique traits
* Interiors are FORBIDDEN unless explicitly unlocked by a scene or encounter
* Destruction is allowed but consequences remain generic

Unnamed buildings may never become named through play.


## INTERIOR ACCESS RULES

Interiors are restricted spaces.

* Default state: **Locked**
* Interiors may be accessed ONLY if:

  * The building record explicitly allows it, OR
  * A scene explicitly unlocks interior access, OR
  * A specific encounter grants access

If interior access is not unlocked, the AI GM MUST deny entry.


## SCENES AND BUILDINGS

Scenes:

* Activate ACT LOCATIONS
* Declare approximate numbers of unnamed buildings if relevant
* MUST NOT enumerate or individualize buildings

Scenes MUST NOT:

* Invent buildings
* Assign importance to unnamed structures
* Describe interiors


## ENCOUNTERS AND BUILDINGS

Encounters MAY:

* Reference buildings as environmental context
* Affect buildings temporarily (fire, collapse, damage)

Encounters MUST NOT:

* Create named buildings
* Assign NPC ownership
* Persist structural changes automatically

All permanent effects must be written to persistence outputs.


## PERSISTENCE AND BUILDINGS

* Buildings themselves do not change state
* Damage, closures, or access restrictions are persisted separately
* Persistence records reference buildings by ID (named) or generic descriptor (unnamed)


## TEMPLATES

### TEMPLATE: ACT LOCATION

```md
- Location ID:
- Name:
- Type:
- Default Accessibility:
- Notes (Non-executing):
```


### TEMPLATE: NAMED BUILDING RECORD

```md
- Building ID:
- Name:
- Type: (Civic / Commercial / Residential / Religious)
- Exterior Description: (1–2 factual sentences)
- Interior Access: Locked / Conditional / Always
- Associated NPCs:
  - Primary:
  - Secondary:
- Usage Constraints:
- Notes (Non-executing):
```


### TEMPLATE: UNNAMED BUILDING (REFERENCE ONLY)

```md
- Size: (1–3 storey)
- Function: (shop / home / warehouse / tavern / other)
```

Unnamed buildings MUST NOT be recorded individually.


## ANTI-HALLUCINATION ENFORCEMENT

If spatial uncertainty arises, the AI GM MUST:

1. Check LOCATION_RULES.md
2. Check LOCATION_INDEX / BUILDING_INDEX
3. Default to the most restrictive interpretation

If a violation occurs, LOCATION_RULES.md takes precedence and the AI GM MUST self-correct.


## DESIGN INTENT

These rules prioritize:

* World stability
* Replayability
* Auditability
* Controlled creativity

Locations are *constraints first*, flavor second.