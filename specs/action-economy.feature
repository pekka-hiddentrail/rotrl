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

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Standard + Move can be active simultaneously (multi-select)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A player can declare both a Standard and a Move action in the same turn.

```gherkin
Given the action-type row is visible  (PC's turn)
And   no button is selected

When  the player clicks "Standard"
Then  "Standard" has class "btn-action-type active"

When  the player also clicks "Move"
Then  "Standard" AND "Move" both have class "btn-action-type active"
And   "Full-Round" does NOT have class "active"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Full-Round is exclusive: deselects Standard and Move
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Clicking Full-Round clears Standard and Move (mutually exclusive).

```gherkin
Given "Standard" and "Move" are both active

When  the player clicks "Full-Round"
Then  "Full-Round" has class "active"
And   "Standard" and "Move" do NOT have class "active"

Given "Full-Round" is active
When  the player clicks "Standard" or "Move"
Then  the clicked button becomes active
And   "Full-Round" loses class "active"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Swift and Free can be added to any combination
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Swift and Free action buttons are non-exclusive modifiers.

```gherkin
Given "Full-Round" is selected

When  the player also clicks "Swift"
Then  "Full-Round" AND "Swift" are both active
And   other buttons are unchanged

Given "Standard" and "Move" are selected
When  the player clicks "Free"
Then  "Standard", "Move", AND "Free" are all active
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — action_type_hints array sent in POST body (replaces single hint)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The full ordered list of selected action types is sent on submit.

```gherkin
Given "Standard" and "Move" are selected
When  the player submits
Then  POST /api/sessions/{id}/pc_turn is called with JSON body:
        { "input": "…", "action_type_hints": ["standard", "move"], "action_type_hint": null }

Given "Full-Round" and "Swift" are selected
When  the player submits
Then  the JSON body contains:
        { "action_type_hints": ["full", "swift"], "action_type_hint": null }

Given no action buttons are selected
When  the player submits
Then  the JSON body contains:
        { "action_type_hints": [], "action_type_hint": null }
```

*Order within the array: primary (standard/full) first, move second, swift third, free last.*

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — Backend: Standard+Move applies attack AND zone move together
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** When `action_type_hints` contains both "standard" (or "full") and "move", the
backend processes both actions atomically.

```gherkin
Given action_type_hints == ["standard", "move"]
And   player text = "I attack the goblin and move behind the pillar"
And   "behind the pillar" is a known zone

When  stream_pc_turn is called
Then  an attack is queued (PendingAttack) for the Standard action
And   the PC's zone is updated to "behind the pillar" immediately
And   a combat_update SSE is emitted with the new zone
And   an attack_request SSE is emitted for the to-hit dice roll
And   the move is logged as "[Zone move: <actor> <old> → <new>]"
```

```gherkin
Given action_type_hints == ["standard", "move"]
And   player text does NOT name a known zone
When  stream_pc_turn is called
Then  the attack is still queued normally (move with unknown zone is silently skipped)
And   NO attention SSE is emitted (unknown zone does not block a Standard+Move combo)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-015 — Backend: action_type_hints takes priority over action_type_hint
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The multi-action hints list supersedes the legacy single-hint field when both
are provided, ensuring the backend always uses the richer signal.

```gherkin
Given action_type_hints == ["move"]
And   action_type_hint  == "standard"
When  _extract_pc_combat_intent is called
Then  intent["action_type"] == "move"   (action_type_hints wins)

Given action_type_hints == []
And   action_type_hint  == "standard"
When  _extract_pc_combat_intent is called
Then  intent["action_type"] falls back to keyword inference
  (empty list treated as absent — legacy single hint is NOT used for the fallback)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-016 — Swift and Free actions are informational context only
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Swift and Free selections are logged and passed to the LLM briefing as context,
but do not trigger separate mechanical processing.

```gherkin
Given action_type_hints == ["standard", "swift"]
When  stream_pc_turn is called
Then  the attack is queued for the standard action
And   the session log contains "swift" in the pc turn line
And   NO extra attack_request or move event is emitted for the swift action

Given action_type_hints == ["full", "free"]
When  stream_pc_turn is called
Then  the full-round attack is queued as normal
And   the session log contains "free" in the pc turn line
```

---

## Out of Scope

- **Click-to-target enemy** — separate Tier 2.5 item ("Click-to-target enemy in CombatPanel");
  already implemented.
- **`%%ACTION%%` block with `action_type` field** — covered by [enemy-turn.feature](enemy-turn.feature);
  already implemented.
- **Validation that a full-round action wasn't used with a swift action** — requires slot
  tracking, which is not yet implemented.
- **5-foot step button** — exclusive of Move; deferred with the rest of Tier 2.5 conditions.
- **Two-Move (double move / run)** — deferred; covered by selecting Move twice or a dedicated
  button; not yet in scope.
