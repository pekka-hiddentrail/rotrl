# FEATURE — Combat Initiative Active Character

**ID:** combat-active-character
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @session @prompt @streaming @layout

---

## Story

> As the **player**,
> I want the UI to always reflect whose turn it is in initiative order —
> including enemy turns — so I can track the flow of combat at a glance
> and the system can write the current actor to session state for continuity.

When combat is active, `active_character` is driven by the initiative tracker
rather than the player's manual selection. PC turns look normal; enemy turns
flip the input panel to a hostile red state with a skull icon, the enemy's name,
and a taunting placeholder so it's immediately clear the enemy is acting.

---

## Background

- Given a session has been booted
- And `session.combat_state` is not None (round ≥ 1)
- And `session.combat_state.current_actor` tracks the name of whoever is acting

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `CombatState` carries `current_actor`
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the CombatState dataclass
Then  it has a field: current_actor: Optional[str] = None
And   _serialize_combat_state() includes "current_actor" in the serialized dict
And   the value is null when current_actor is None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — `_parse_combat_block` seeds `current_actor` on round 1
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a %%COMBAT%% block with round: 1 and multiple combatants
When  _parse_combat_block is called with existing_state=None
Then  current_actor is set to the combatant with the highest initiative whose status is "active"

Given two combatants with equal initiative
Then  the one appearing first in the sorted order is chosen

Given all combatants are unconscious/dead
Then  current_actor is None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — `current_actor` is preserved on round 2+ (not re-seeded by parse)
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given existing_state.current_actor = "Thaelion"
And   a new %%COMBAT%% block for round 2 arrives
When  _parse_combat_block is called with existing_state set
Then  result.current_actor = "Thaelion" (carried over from existing_state)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — `combat_update` SSE includes `current_actor`
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is set with current_actor = "Goblin 1"
When  the combat_update SSE event is emitted
Then  the event payload contains combat_state.current_actor = "Goblin 1"
When  session.combat_state is None
Then  the combat_update payload is { type: "combat_update", combat_state: null }
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — `POST /sessions/{id}/combat/advance_turn` endpoint
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given combat is active with combatants sorted by initiative: Shalelu(14), Thaelion(10), Goblin(5)
And   current_actor = "Shalelu"
When  POST /sessions/{id}/combat/advance_turn is called
Then  current_actor advances to "Thaelion" (next active combatant in initiative order)
And   the response is { "current_actor": "Thaelion", "is_pc": true }
And   state.json is updated with the new current_actor

When  POST /sessions/{id}/combat/advance_turn is called again
Then  current_actor advances to "Goblin" (next active)
And   response is { "current_actor": "Goblin", "is_pc": false }

When  advance_turn is called while current_actor = "Goblin" (last in order)
Then  current_actor wraps back to "Shalelu" (first active combatant, new round)

Given session has no active combat
When  POST /sessions/{id}/combat/advance_turn is called
Then  response is 409 Conflict

Given unknown session id
When  POST /sessions/{id}/combat/advance_turn is called
Then  response is 404 Not Found
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Unconscious/dead combatants are skipped on advance
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given combatants: Shalelu(init 14, active), Goblin(init 10, unconscious), Thaelion(init 5, active)
And   current_actor = "Shalelu"
When  advance_turn is called
Then  current_actor = "Thaelion" (Goblin skipped — unconscious)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — `_write_session_state` writes `current_actor` as `active_character`
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state.current_actor = "Goblin 1"
When  _write_session_state(session) is called
Then  state.json contains active_character = "Goblin 1"

Given session.combat_state is None
When  _write_session_state(session) is called
Then  state.json contains active_character = session.active_character (normal path unchanged)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Frontend reads `current_actor` from `combat_update` SSE
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a combat_update SSE event arrives with combat_state.current_actor = "Goblin 1"
When  App.tsx processes the event
Then  currentCombatantName = "Goblin 1"
And   activeSpeaker is derived from "Goblin 1" (enemy variant)

Given combat_update arrives with current_actor = "Thaelion"
And   "Thaelion" is in the loaded character list
When  App.tsx processes the event
Then  currentCombatantName = "Thaelion"
And   activeSpeaker is derived from Thaelion's character data (PC variant, normal styling)

Given combat_update arrives with combat_state = null
When  App.tsx processes the event
Then  currentCombatantName = null
And   activeSpeaker reverts to the previously selected character or null
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — `doAdvanceTurn` calls the backend endpoint
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the user clicks "Next Turn →" in CombatPanel
When  App.tsx handles onAdvanceTurn
Then  POST /sessions/{id}/combat/advance_turn is called
And   currentCombatantName is updated from the response's current_actor
And   activeSpeaker is recomputed from the new current_actor
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — `ActiveSpeaker` interface has `isEnemy` flag
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an ActiveSpeaker object built from a PC name
Then  isEnemy is false or absent

Given an ActiveSpeaker object built from an enemy name (not in character list)
Then  isEnemy is true
And   name is the enemy's name (e.g. "Goblin 1")
And   rune is null or empty (not a PC rune)
And   color is a hostile red/amber palette value
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — InputBar shows skull icon and hostile styling for enemy turns
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given activeSpeaker.isEnemy = true
When  InputBar renders
Then  the speaker icon is a skull SVG (not the character portrait)
And   the container has class "hostile" applied
And   the enemy name is shown as the speaker label
And   the placeholder text is a taunting phrase (e.g. "The enemy acts…")
And   the textarea background / border uses the hostile (red) color scheme

Given activeSpeaker.isEnemy = false (or no activeSpeaker)
When  InputBar renders
Then  no "hostile" class is applied
And   the normal character portrait or generic icon is shown
And   placeholder is "What do you do?  (Enter to send · Shift+Enter for newline)"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Hostile placeholder rotates by enemy name
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a pool of taunting placeholder strings
When  InputBar renders with isEnemy = true
Then  one phrase from the pool is shown as placeholder
And   the chosen phrase is deterministic for a given enemy name
      (same enemy always gets the same phrase)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — InputBar returns to normal when combat ends
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given activeSpeaker.isEnemy = true (enemy's turn)
When  the combat_update event with combat_state = null arrives (combat ended)
Then  currentCombatantName = null
And   activeSpeaker no longer has isEnemy = true
And   InputBar loses the "hostile" class and skull icon
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — CombatPanel highlighted row driven by current_actor from backend
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given combat_update arrives with current_actor = "Goblin 1"
When  CombatPanel renders
Then  the "Goblin 1" row has the combatant-current highlight class
And   other rows do not
```

---

## Out of Scope

- Enemy turn endpoint (`POST /enemy_turn`) — Tier 1.7
- PC selection overriding combat initiative — manual override not exposed while combat is active
- Persisting enemy taunt phrases across sessions

---

## Notes

- `CombatState.current_actor` is `Optional[str]` in Python / `string | null` in TypeScript
- `is_pc` computed in backend by checking if `current_actor` matches any key in `session.pc_profiles` (case-insensitive)
- Taunting placeholder pool in `ui/src/components/InputBar.tsx`: at least 5 strings, selected by `name.length % pool.length` for determinism
- `_write_session_state` already writes `active_character`; in combat it writes `combat_state.current_actor` instead
- `advance_turn` advances within the current round's sorted-by-initiative active combatant list; wrapping at the end does NOT increment `round` (round increment is the LLM's responsibility via `%%COMBAT%%`)
- `POST /sessions/{id}/combat/advance_turn` — no body required; returns `{ current_actor: string | null, is_pc: bool }`
- Tests: `tests/test_combat_active_character.py` (pytest), `ui/src/components/__tests__/InputBar.test.tsx` additions, `ui/src/__tests__/App.test.tsx` additions
