# FEATURE - Location Zones

**ID:** location-zones
**Status:** Draft
**Area:** Backend | Frontend | Content
**Tags:** @location @zone @movement @ui @api @generator @context

---

## Story

> As a **player**,
> I want locations to show their internal zones and the access points between them,
> so that character movement inside a place is clear, constrained, and playable from the GUI.

Location zones are canonical sub-areas inside a location: Common Room, Hearth Corner,
Rear Hallway, Stables, Bell Tower, Crypt Entrance. They are not freeform chips.
Characters can move only through defined access points, so the GUI should offer
`Stables -> Common Room` while refusing a direct `Stables -> Hearth Corner` move
unless an access point exists.

---

## Background

- Given a session is active
- And the party is in a known location from `adventure_path/03_locations/`
- And the location may have authored zones, generated zones, or no zone data yet

---

## Acceptance Criteria

### LZ-001 - Location files can define zones and access points

**Scenario:** A location `base.md` contains canonical zone data.

```gherkin
Given a location file contains a "## Zones" section above "<!-- REFERENCE -->"
And   it contains a "## Access Points" section above "<!-- REFERENCE -->"
When  the location profile is loaded
Then  each zone has a stable id, display name, description, visibility state, source, and optional tags
And   each access point has a stable id, from_zone_id, to_zone_id, label, state, directionality, requirements, and description
And   the location can be represented as a graph of zones connected by access points
```

**Canonical markdown shape:**

```markdown
## Zones

| id | name | description | visible | source | tags |
|----|------|-------------|---------|--------|------|
| common_room | Common Room | The main public floor of the inn. | yes | authored | social, interior |
| hearth_corner | Hearth Corner | A quieter cluster of benches near the fire. | yes | authored | warm, social |
| stables | Stables | Weathered stalls behind the inn. | yes | authored | exterior, animals |

## Access Points

| id | from | to | label | state | bidirectional | requirements | description |
|----|------|----|-------|-------|---------------|--------------|-------------|
| common_room_hearth | common_room | hearth_corner | Hearthside benches | open | yes | - | A narrow path between crowded tables. |
| common_room_stables | common_room | stables | Rear stable door | open | yes | - | A warped back door leading into the yard. |
```

---

### LZ-002 - `LocationIndex` parses location zone graphs

**Scenario:** Zone graph data is loaded from a location file.

```gherkin
Given The Rusty Dragon has valid Zones and Access Points tables
When  LocationIndex loads the location
Then  LocationIndex can return the location's zones by id
And   LocationIndex can return visible zones in display order
And   LocationIndex can return access points connected to a given zone
And   malformed rows are ignored with a non-fatal warning
```

---

### LZ-003 - Session state tracks current location zone

**Scenario:** The party enters a zoned location.

```gherkin
Given the party enters The Rusty Dragon
And   The Rusty Dragon defines default zone "common_room"
When  the location becomes the active scene location
Then  session state stores current_location_id="rusty_dragon"
And   session state stores party_zone_id="common_room"
And   visible_zone_ids are populated from the location graph
And   the state can be serialized and restored with the session
```

---

### LZ-004 - Zone state is exposed to the frontend

**Scenario:** The GUI needs to render the active location's zone map.

```gherkin
Given a session is active inside a zoned location
When  GET /api/sessions/{session_id}/location_zones is called
Then  the response contains current_location, current_zone_id, zones, access_points, occupants, and available_moves
And   available_moves contains only open access points from the actor's current zone
And   hidden access points are omitted unless discovered
And   locked or blocked access points are included only when visible, with their state and requirements
```

**Response sketch:**

```json
{
  "current_location": { "id": "rusty_dragon", "name": "The Rusty Dragon" },
  "current_zone_id": "common_room",
  "zones": [
    { "id": "common_room", "name": "Common Room", "description": "...", "visible": true, "source": "authored", "tags": ["social"] }
  ],
  "access_points": [
    { "id": "common_room_stables", "from": "common_room", "to": "stables", "label": "Rear stable door", "state": "open", "bidirectional": true }
  ],
  "occupants": [
    { "actor_id": "party", "label": "Party", "zone_id": "common_room" }
  ],
  "available_moves": [
    { "access_point_id": "common_room_stables", "to_zone_id": "stables", "label": "Rear stable door", "state": "open" }
  ]
}
```

---

### LZ-005 - Movement is validated by access points

**Scenario:** A character attempts to move between zones.

```gherkin
Given Ani is in zone "stables"
And   there is an open access point from "stables" to "common_room"
And   there is an open access point from "common_room" to "hearth_corner"
And   there is no access point from "stables" to "hearth_corner"
When  Ani moves through the access point to "common_room"
Then  the move succeeds
And   Ani's zone becomes "common_room"

When  Ani attempts to move directly from "stables" to "hearth_corner"
Then  the move is rejected
And   the response explains that "hearth_corner" is not directly reachable from "stables"
And   the response includes the available moves from "stables"
```

---

### LZ-006 - Movement endpoint updates actor zone state

**Scenario:** The frontend submits a valid zone move.

```gherkin
Given a session has location zone state
When  POST /api/sessions/{session_id}/zone_move receives actor_id="party" and access_point_id="common_room_stables"
Then  the server validates the access point from the actor's current zone
And   the actor's zone is updated to the access point destination
And   the response returns the refreshed location zone state
And   the session log records the zone move
```

---

### LZ-007 - The GUI shows current zone and available access points

**Scenario:** The party is in a zoned location.

```gherkin
Given the current location is The Rusty Dragon
And   the party is in the Common Room
When  the main interface renders
Then  a Location Zones panel is visible without opening a debug tool
And   the current zone name and description are visible
And   available access points from the current zone are shown as movement controls
And   each movement control names both the access point and destination zone
```

---

### LZ-008 - The GUI provides an accessible zone list

**Scenario:** The player wants to inspect the known zones in the current location.

```gherkin
Given the active location has visible zones
When  the player opens or focuses the zone list
Then  all visible zones are listed
And   the actor's current zone is highlighted
And   zones directly reachable from the current zone are marked reachable
And   visible but non-reachable zones remain inspectable but are not offered as direct movement buttons
```

---

### LZ-009 - Access point states are clear in the GUI

**Scenario:** Some exits are locked, blocked, or hidden.

```gherkin
Given a zone has one open access point, one locked access point, one blocked access point, and one hidden access point
When  the Location Zones panel renders
Then  the open access point appears as an enabled move button
And   the locked access point appears disabled with its requirement if known
And   the blocked access point appears disabled with its block reason if known
And   the hidden access point does not appear until discovered
```

---

### LZ-010 - Character occupancy is visible

**Scenario:** Characters are in different zones.

```gherkin
Given Ani is in "common_room"
And   Vale is in "stables"
When  the Location Zones panel renders
Then  the zone list shows character markers or names for each occupied zone
And   selecting a character or active speaker makes that character the movement actor
And   party movement remains available for moving all unsplit party members together
```

---

### LZ-011 - Description-only locations can generate draft zones

**Scenario:** A location has a Description but no authored zone graph.

```gherkin
Given a location file has Description, Typical Occupants, and Current State
And   it has no Zones or Access Points sections
When  zone generation is requested for that location
Then  the generator creates a draft zone graph from the existing prose
And   each generated zone has source="generated"
And   each generated access point has source="generated"
And   every visible generated zone is reachable from at least one other visible zone unless the location has only one zone
And   generated data is persisted in the location file without overwriting authored sections
```

---

### LZ-012 - Generated topology avoids false direct travel

**Scenario:** The generator infers zones for an inn.

```gherkin
Given the prose implies stables behind the inn, a common room, and a hearth corner inside the common room
When  zones are generated
Then  the graph includes an access path between stables and common_room
And   the graph includes an access path between common_room and hearth_corner
And   the graph does not create a direct stables to hearth_corner access point unless the prose explicitly supports it
```

---

### LZ-013 - Zone data integrates with combat zones without duplicating models

**Scenario:** Combat starts inside a location with zones.

```gherkin
Given the party is in a location with a zone graph
When  combat starts in that location
Then  combatants can use the same zone ids as the location graph
And   combat zone badges continue to render from Combatant.zone
And   combat-specific inline Zones sections may override or narrow the location graph for that encounter
And   ending combat preserves the non-combat location zone state
```

---

## Out of Scope

- Grid maps, distance matrices, coordinates, compass-facing, or measured tactical movement
- Automatic map drawing beyond a simple list/graph view
- Procedural dungeon generation or room stocking
- Final PF1e action-economy costs for every movement edge; this spec only requires reachability and UI movement
- Full hidden-door discovery mechanics; this spec only defines how hidden access points become representable once discovered

---

## Implementation Plan

1. Extend the location file format with `## Zones` and `## Access Points`.
2. Add backend parsing and serialization in the location/context layer.
3. Add session zone state for current location, current actor zone, visible zones, and occupants.
4. Add read and move APIs for the frontend.
5. Build the Location Zones GUI panel: current zone, zone list, access-point movement controls, and occupant markers.
6. Add description-only zone generation as a draft writer for locations that lack authored zone data.
7. Bridge location zone ids into combat zone state so combat and exploration do not drift.

---

## Related Specs

- [location-system.feature](location-system.feature) - canonical location files, alias detection, location stubs
- [zone-combat.feature](zone-combat.feature) - combatant zone field, combat serialization, combat panel badge
- [combat-tracker.feature](combat-tracker.feature) - combat state lifecycle and CombatPanel integration
- [event-temperature-mvp.feature](event-temperature-mvp.feature) - event scheduler zone/location dependency
