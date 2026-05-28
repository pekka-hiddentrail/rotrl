# FEATURE — Location System

**ID:** location-system
**Status:** Approved
**Area:** Backend
**Tags:** @location @index @generator @context @injection

---

## Story

> As the **GM engine**,
> I want a structured location database with profile files and keyword detection,
> so that when the player moves to or mentions a named place, the GM receives
> a description of that location — what it looks like, who is typically there,
> and what its current state is — without any extra LLM calls.

Locations live in `adventure_path/07_locations/`. A `LocationIndex` singleton detects
location keywords in player input and injects the matching profile into the per-turn
system prompt alongside (not instead of) any NPC-at-location injection already produced
by `NpcIndex.detect_by_location()`. The GM receives the physical and social context of
the place; the NPC profiles provide the people found there — both are needed.

---

## Background

- Given a session is active
- And `adventure_path/07_locations/` exists and contains location directories
- And the `LocationIndex` has been loaded

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `LocationIndex` loads canonical locations and skips underscore-prefixed dirs
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** `LocationIndex` is initialised

```gherkin
Given adventure_path/07_locations/ contains sandpoint_garrison/, rusty_dragon/, and _LOCATION_TEMPLATE/
When  the LocationIndex is loaded
Then  sandpoint_garrison and rusty_dragon are in the index
And   _LOCATION_TEMPLATE is not in the index
And   any directory whose base.md is missing is silently skipped
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — `base.md` follows the canonical location format
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A location `base.md` file is authored or auto-generated

```gherkin
Given a location base.md file
Then  the file starts with "# Canonical Location Name"
And   "**Aliases:**" appears before "<!-- REFERENCE -->" — a comma-separated list of detection keywords
And   the payload section (above "<!-- REFERENCE -->") contains Description, Typical Occupants, and Current State sections
And   District, Type, and any author notes appear after "<!-- REFERENCE -->" and are never injected
And   content below "<!-- REFERENCE -->" is never included in the injected context block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Location profile injected when an alias matches player input
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input mentions a location by alias

```gherkin
Given Sandpoint Garrison has aliases: "garrison", "town garrison", "guard post", "barracks"
When  the player inputs "We head to the garrison to report the attack"
Then  the per-turn prompt includes a "## Location Reference — Sandpoint Garrison" block
And   the block contains the garrison's Description, Typical Occupants, and Current State
And   the context SSE event contains loc="Sandpoint Garrison" and loc_trigger="garrison"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Longest alias wins when multiple location aliases match
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input matches both a short and a long alias for the same location

```gherkin
Given Sandpoint Cathedral has aliases "cathedral" (10 chars) and "desna cathedral" (15 chars)
When  the player inputs "We enter the Desna Cathedral"
Then  the matched alias is "desna cathedral" (the longer match wins)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Location profile injection supplements NPC-at-location injection
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input mentions a location that has both a location profile and stationed NPCs

```gherkin
Given Belor Hemlock has location keyword "garrison" (via NpcIndex)
And   Sandpoint Garrison has alias "garrison" (via LocationIndex)
When  the player inputs "We go to the garrison"
Then  the per-turn prompt includes the Sandpoint Garrison Location Reference block
And   the per-turn prompt also includes the Belor Hemlock NPC Reference block
And   the location block and the NPC block are both present and separated by "---"
And   Hemlock's NPC block is not duplicated
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — `context` SSE event exposes `loc` and `loc_trigger`; null when no match
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario A:** Location alias matched

```gherkin
When  the player inputs text that matches a location alias
Then  the context SSE event contains loc="<canonical name>" and loc_trigger="<matched alias>"
```

**Scenario B:** No location alias matched

```gherkin
When  the player inputs text that matches no location alias
Then  the context SSE event contains loc=null and loc_trigger=null
And   the existing location and location_npcs fields from NpcIndex are unaffected
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — `scene_locations` persists location context across subsequent turns
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Party is in a location for multiple consecutive turns

```gherkin
Given on turn 1 the player inputs "We enter the cathedral" and Sandpoint Cathedral is detected
When  on turn 2 the player inputs "Ani speaks to the priest" with no location keyword
Then  the per-turn prompt on turn 2 still includes the Sandpoint Cathedral Location Reference block
And   the context SSE event on turn 2 still contains loc="Sandpoint Cathedral"
And   this persists for all subsequent turns until the session ends
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — `%%GENERATE%%` with `type: location` creates a stub in `07_locations/`
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM response introduces a new named location via `%%GENERATE%%`

```gherkin
Given the %%GENERATE%% section contains a block with:
  type: location
  name: Bottled Solutions
  role: apothecary shop
  appearance: a cluttered storefront filled with strange ingredients
  location: main street
  summary: run by Gerhard Pickle, a font of local gossip
When  the section is parsed
Then  adventure_path/07_locations/bottled_solutions/base.md is created
And   the file starts with "# Bottled Solutions"
And   the payload section includes role, appearance, and summary content
And   the file contains "**Aliases:**" with at least the slugified name as a keyword
And   no base.md is created if a directory for this location already exists
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — `LocationIndex` is invalidated after stub creation; new location detectable immediately
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A `%%GENERATE%%` location block fires mid-session

```gherkin
Given Bottled Solutions does not exist in the LocationIndex before this turn
When  _process_generate_block() creates adventure_path/07_locations/bottled_solutions/base.md
Then  _invalidate_location_index() is called immediately after the write
And   on the next player turn, "bottled solutions" or "apothecary" in player input detects the new location
And   the new Location Reference block is injected into that turn's prompt
```

---

## Out of Scope

- `%%DELTAS%%` for locations — locations do not have per-turn disposition changes; world-state changes are recorded in `adventure_path/04_persistence/PERSISTENCE_LEDGER.md`
- Location-to-NPC reverse lookup (`LocationIndex` does not declare which NPCs are present — NPC files own that relationship via `**Locations:**`)
- UI intent bar changes for the new `loc` / `loc_trigger` fields (can follow separately)
- Multi-location detection in a single turn (single best match only, same as NPC detection)

---

## Implementation Notes

### File layout

```
adventure_path/07_locations/
  _LOCATION_TEMPLATE.md         Template for new location directories
  sandpoint_garrison/
    base.md
  sandpoint_cathedral/
    base.md
  rusty_dragon/
    base.md
  ... (one directory per canonical location)
```

No `knowledge.md` or `session_NNN.md` — locations are static within a session.

### `base.md` format

```markdown
# Sandpoint Garrison
**Aliases:** garrison, town garrison, guard post, barracks

## Description
[3–5 sensory details, one social/atmospheric detail, one interactive element]

## Typical Occupants
[who the party will find here by default — do not duplicate NPC profiles]

## Current State
[access rules, default alert level, anything that changes depending on world state]

<!-- REFERENCE -->
**District:** North Sandpoint
**Type:** Military / Civic
**Associated NPCs:** Belor Hemlock (commander)
```

### `LocationIndex` — `api/context/location_lookup.py`

Mirrors `NpcIndex` but simpler: no status or knowledge reads. Public API:

| Method | Returns | Notes |
|--------|---------|-------|
| `detect(text)` | `LocationMatch \| None` | longest alias wins |
| `format_context(match)` | `str` | `## Location Reference — {name}` block |
| `lookup(name)` | `LocationMatch \| None` | direct canonical lookup |
| `known_locations` | `list[str]` | all canonical names |

Module-level singleton in `api/session_manager.py`:

```python
_location_index: Optional[LocationIndex] = None

def _get_location_index() -> LocationIndex: ...
def _invalidate_location_index() -> None: ...
```

### `_inject_context()` changes

- Add `LocationIndex.detect(last_user)` call after NPC and skill detection
- Append profile to `injected` list if matched
- Add `loc` and `loc_trigger` to `context_info`
- Accumulate canonical name into `session.scene_locations` (new `list[str]` field on `GameSession`)
- On subsequent turns with no new location match, re-inject from `scene_locations` (same pattern as `scene_npcs` delta-reminder, but location profiles are injected in full — no directive change needed)

### `context` SSE event shape (after this feature)

```json
{
  "type": "context",
  "npc": "...",
  "npc_trigger": "...",
  "skill": "...",
  "skill_trigger": "...",
  "location": "...",
  "location_npcs": [...],
  "loc": "...",
  "loc_trigger": "..."
}
```

`location` / `location_npcs` — NPC-at-location match (existing, unchanged).
`loc` / `loc_trigger` — location profile match (new).

### Seed locations for Act I

Minimum viable set for Swallowtail Festival / Act I:

| Slug | Canonical Name | Key Aliases |
|------|---------------|-------------|
| `sandpoint_cathedral` | Sandpoint Cathedral | cathedral, desna cathedral, chapel, temple |
| `sandpoint_garrison` | Sandpoint Garrison | garrison, guard post, barracks |
| `rusty_dragon` | The Rusty Dragon | rusty dragon, inn, tavern, ameiko's inn |
| `festival_grounds` | Festival Grounds | festival, town square, square, market, plaza |
| `sandpoint_boneyard` | Sandpoint Boneyard | boneyard, cemetery, graveyard |
| `sandpoint_glassworks` | Sandpoint Glassworks | glassworks, glass factory |
| `white_deer` | The White Deer | white deer, the deer |
| `sage_stage` | Sage Stage | sage stage, sage, stage |

---

## Related Specs

- [context-detection.feature](context-detection.feature) — existing NPC / skill detection pipeline; location profile detection integrates as a third detection pass
- [npc-system.feature](npc-system.feature) — `NpcIndex`, `base.md` format, `detect_by_location()` (NPC side of location lookup; orthogonal to `LocationIndex`)
- [system-prompt.feature](system-prompt.feature) — `_inject_context()` is the function modified by this feature
