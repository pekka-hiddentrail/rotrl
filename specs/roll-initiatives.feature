# FEATURE — Roll Initiatives

**ID:** roll-initiatives
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @initiative @session @layout

---

## Story

> As the **player**,
> I want a "🎲 Roll Initiatives" button in the combat tracker header,
> so that I can re-roll all combatant initiatives at any point during combat
> using d20 + the correct modifier for each combatant, and see the initiative
> order update immediately.

When combat is active a compact button appears in the CombatPanel header
beside the round badge. Clicking it asks the backend to roll d20 + each
combatant's initiative modifier, sort the order, set the new first actor,
persist to `state.json`, and return the updated state — all in a single
REST call with no streaming required.

---

## Background

- Given a session is booted
- And `session.combat_state` is set (round ≥ 1)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `roll_combat_initiatives` rolls d20 for every combatant
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state has three combatants with arbitrary initiative values
When  roll_combat_initiatives(session) is called
Then  every combatant's initiative is replaced with a fresh roll (old value discarded)
And   each new value is an integer in range [1, 20] for enemies (no modifier)
And   the same call does NOT raise or leave any combatant with initiative = 0 unless
      the combatant had a −19 modifier (which is not a real case)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — PC modifier read from pc_profiles.combat_stats.initiative
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.pc_profiles contains Thaelion with initiative "+3"
And   Thaelion is a combatant in session.combat_state
When  roll_combat_initiatives(session) is called
Then  Thaelion's new initiative is in range [4, 23]  (d20 + 3)

Given a PC with initiative modifier "-1"
Then  that PC's new initiative is in range [0, 19]  (d20 - 1, clamped to ≥ 0 by the result)

Given a PC with initiative modifier "+0"
Then  that PC's new initiative is in range [1, 20]
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Enemy modifier defaults to +0 (flat d20)
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a combatant whose name does NOT match any key in session.pc_profiles
When  roll_combat_initiatives(session) is called
Then  that combatant's new initiative is in range [1, 20]
And   no modifier is applied (SA-2 bestiary seeding will supply real modifiers later)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — current_actor set to new highest-initiative active combatant
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given roll_combat_initiatives produces initiatives: Shalelu 18, Goblin 11, Thaelion 7
And   all three are "active"
When  roll_combat_initiatives returns
Then  session.combat_state.current_actor = "Shalelu"

Given the highest-initiative combatant has status "unconscious"
And   the next one is "active"
When  roll_combat_initiatives returns
Then  current_actor = the highest active combatant (not the unconscious one)

Given all combatants are unconscious or dead
When  roll_combat_initiatives returns
Then  current_actor = None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Inactive combatants still receive a roll
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a combatant has status "unconscious"
When  roll_combat_initiatives(session) is called
Then  that combatant's initiative is re-rolled (value changes)
And   it is NOT set as current_actor
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — state.json written after every roll
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given roll_combat_initiatives is called
When  it returns
Then  _write_session_state(session) has been called
And   state.json contains the updated active_character (= new current_actor)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — POST /sessions/{id}/combat/roll_initiatives endpoint
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a valid session with active combat
When  POST /sessions/{id}/combat/roll_initiatives is called
Then  it returns 200
And   the response body is { "combat_state": { "round": N, "current_actor": "...", "combatants": [...] } }
And   every combatant in the response has a new initiative value (not the old one)
And   the combatant list is sorted descending by initiative

Given session.combat_state is None
When  POST /sessions/{id}/combat/roll_initiatives is called
Then  it returns 409 Conflict

Given an unknown session id
When  POST /sessions/{id}/combat/roll_initiatives is called
Then  it returns 404 Not Found
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — "🎲 Roll Initiatives" button in CombatPanel header
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given CombatPanel renders with a valid combatState and an onRollInitiatives callback
Then  a "🎲 Roll Initiatives" button is visible in the header area (beside the Round badge)
And   clicking the button calls onRollInitiatives

Given onRollInitiatives prop is not provided
Then  the button is not rendered

Given the disabled prop is true
Then  "🎲 Roll Initiatives" is disabled

Given enemyTurnStreaming is true
Then  "🎲 Roll Initiatives" is disabled

Given combatClosing is true
Then  "🎲 Roll Initiatives" is disabled

Given attackPhase is set (a PC attack is in progress)
Then  "🎲 Roll Initiatives" is disabled
      (rerolling initiatives mid-attack would corrupt the active resolution flow)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — App.tsx wiring: click → API → state update
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a booted session with active combat
When  the user clicks "🎲 Roll Initiatives"
Then  App.tsx calls POST /sessions/{id}/combat/roll_initiatives
And   combatState in App.tsx is replaced with the response combat_state
And   currentCombatantName is set from combat_state.current_actor
And   the CombatPanel initiative list re-renders with the new order immediately

Given the API call fails (network error)
Then  an error message is shown
And   the existing combatState is unchanged
```

---

## Out of Scope

- Initiative modifier seeding from event files / bestiary (Tier 2 SA-2) — enemies always
  get a flat d20 until SA-2 provides their real modifiers
- Automatic initiative roll on combat start (Tier 1.9) — this button is the manual
  trigger; Tier 1.9 will make it happen automatically on round 1 parse
- Tie-breaking rules (PF1e dex-modifier tiebreak) — not implemented; ties left as-is

---

## Notes

- `roll_combat_initiatives(session: GameSession) → Optional[dict]` in `api/session_manager.py`
  Returns the serialised `CombatState` dict, or `None` when no combat is active.
- PC modifier parsed from `pc_profiles[name.lower()]["combat_stats"]["initiative"]`
  as a signed string (e.g. `"+2"`, `"-1"`, `"0"`). Parse fails silently to `+0`.
- Enemy modifier is `0` until `Combatant.attacks` / SA-2 supplies per-enemy stats.
- `_write_session_state` called after every roll; `state.json` `active_character` = new `current_actor`.
- `rollInitiatives(sessionId)` in `ui/src/api.ts`; `handleRollInitiatives` in `App.tsx`.
- Button placed in `.combat-panel-badges` in `CombatPanel.tsx`; CSS class `combat-roll-init-btn`.
- Tests: `tests/test_roll_initiatives.py` (pytest); `CombatPanelRollInit.test.tsx` (Vitest).
