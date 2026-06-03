# FEATURE — Action Economy — PC Turn Action Type Picker

**ID:** action-economy
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @pc @action @turn @input @economy

---

## Story

> As a **player**,
> when it is my character's turn in combat, I want to explicitly declare what kind of action
> I am taking (Standard, Move, or Full-Round) before typing my intent — so the backend knows
> my action type without having to infer it from prose, and the LLM never mistakes a move
> action for an attack.

Free-text intent inference is unreliable for action-type classification ("I run to the pillar"
could be a move action or part of a charge). Explicit buttons let the player pre-tag the turn,
giving the backend an authoritative hint that overrides keyword guessing.

---

## Background

- Given a session has been booted
- And `combat_state` is not `null`
- And `currentCombatantName` matches a PC in `characterMap` (i.e. it is the PC's turn)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Buttons only visible on a PC's combat turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The action-type row renders only when it is a player character's turn.

```gherkin
Given combat is active  (combatState != null)
And   current_actor is "Ani"  (a PC present in characterMap)
Then  the InputBar shows three action-type buttons: Standard, Move, Full-Round

Given combat is active
And   current_actor is "Goblin Warrior 1"  (not in characterMap — enemy)
Then  the action-type row is NOT rendered

Given no combat is active  (combatState == null)
Then  the action-type row is NOT rendered
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Selecting a button highlights it
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Clicking a button applies the `.active` CSS class and records the selection.

```gherkin
Given the action-type row is visible  (PC's turn)
And   no button is selected initially

When  the player clicks "Standard"
Then  the "Standard" button has class "btn-action-type active"
And   "Move" and "Full-Round" buttons do NOT have class "active"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Clicking an active button deselects it (toggle)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Re-clicking the selected button clears the selection.

```gherkin
Given "Move" is currently selected  (has class "active")

When  the player clicks "Move" again
Then  no button has class "active"
And   no action_type_hint will be sent on the next submit
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Selection resets when the turn advances
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The selected action type is cleared when the active speaker changes.

```gherkin
Given "Full-Round" is selected for Ani's turn

When  the turn advances and current_actor becomes "Goblin Warrior 1"
Then  no action-type button is selected  (actionType state resets to null)

When  the turn advances back to "Ani"
Then  no action-type button is selected  (fresh turn, no carry-over)
```

*Implementation note: a `useEffect` on `activeSpeaker?.name` resets `actionType` to `null`.*

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Selection resets after the player submits
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Sending a message clears the action-type selection for the next input.

```gherkin
Given "Standard" is selected

When  the player types text and presses Send (or Enter)
Then  the POST /pc_turn request carries  action_type_hint: "standard"
And   after the request fires, no button is selected
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Selected type is sent as action_type_hint in the POST body
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The chosen action type reaches the backend as a typed field.

```gherkin
Given "Move" is selected
And   the player types "I run behind the pillar"

When  the player submits
Then  POST /api/sessions/{id}/pc_turn is called with JSON body:
        { "input": "I run behind the pillar", "action_type_hint": "move" }

Given no button is selected
When  the player submits
Then  the JSON body is:
        { "input": "I run behind the pillar", "action_type_hint": null }
```

*Backend: `PcTurnRequest.action_type_hint: str | None = None` (FastAPI / Pydantic v2).*

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — "standard" and "full" hints map to attack action type
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Both single-attack and full-attack declarations route through the attack branch.

```gherkin
Given action_type_hint == "standard"
When  _extract_pc_combat_intent is called with attack-type text
Then  intent["action_type"] == "attack"

Given action_type_hint == "full"
When  _extract_pc_combat_intent is called with attack-type text
Then  intent["action_type"] == "attack"

Given action_type_hint == "standard"  (or "full")
And   player text triggers use_ability inference ("I channel", "I inspire", "I rage")
When  _extract_pc_combat_intent is called
Then  intent["action_type"] == "use_ability"  (hint does NOT suppress special-ability detection)
```

*`_HINT_TO_ACTION_TYPE = {"standard": "attack", "move": "move", "full": "attack"}`.
`"move"` is always authoritative; `"standard"` and `"full"` only override when inferred type is not `"use_ability"`.*

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — "move" hint maps to move action type
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Declaring a move action prevents the backend from guessing "attack".

```gherkin
Given action_type_hint == "move"
And   the player text contains attack keywords ("I swing")
When  _extract_pc_combat_intent is called
Then  intent["action_type"] == "move"
```

*The hint overrides keyword inference — the button is authoritative.*

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Null or unknown hint falls back to keyword inference
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Omitting a hint preserves the existing intent-detection behaviour.

```gherkin
Given action_type_hint is None (not provided)
And   player text is "I attack the goblin"
When  _extract_pc_combat_intent is called
Then  intent["action_type"] is determined by keyword inference  (== "attack")

Given action_type_hint is "sprint"  (unrecognised value)
When  _extract_pc_combat_intent is called
Then  intent["action_type"] is determined by keyword inference  (not overridden)
```

---

## Out of Scope

- **Swift and Free action buttons** — deferred pending per-turn action slot tracking
  (see COMBAT-TODO.md Tier 2.5: "Swift and immediate actions", "Free actions").
- **Visual graying of Swift after Full-Round** — no slot tracking exists yet.
- **Click-to-target enemy** — separate Tier 2.5 item ("Click-to-target enemy in CombatPanel").
- **`%%ACTION%%` block with `action_type` field** — enemy-turn action block extension is a
  separate Tier 2.5 item and covered by [enemy-turn.feature](enemy-turn.feature).
- **Validation that a full-round action wasn't used with a swift action** — requires slot
  tracking, which is not yet implemented.
