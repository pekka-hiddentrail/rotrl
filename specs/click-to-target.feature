# FEATURE — Click-to-Target Enemy in CombatPanel

**ID:** click-to-target
**Status:** Draft
**Area:** Frontend | Backend
**Tags:** @combat @pc @action @target @input @economy

---

## Story

> As a **player**,
> when it is my character's turn in combat, I want to click on an enemy row in the
> CombatPanel to designate them as my target — so the backend receives an unambiguous
> target name and the LLM never has to guess who I am attacking.

Free-text targeting ("I attack the goblin near me") is ambiguous when multiple enemies
of the same type are alive. Explicit click-to-target eliminates the guessing and lets the
backend route the `%%ATTACK%%` block to the correct combatant's HP and AC without the LLM
having to infer the name.

---

## Background

- Given a session has been booted
- And `combat_state` is not `null`
- And it is a PC's turn (`currentCombatantName` matches a character in `characterMap`)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Clicking an enemy row selects it as the target
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player clicks a live enemy in the CombatPanel during their turn.

```gherkin
Given it is "Ani"'s turn  (PC)
And   the CombatPanel shows "Goblin Warrior 1" as a live enemy

When  the player clicks the "Goblin Warrior 1" row
Then  `selectedTarget` state in App.tsx is set to "Goblin Warrior 1"
And   the "Goblin Warrior 1" row receives the CSS class "combatant-targeted"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Target badge appears near the InputBar
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A visual indicator shows the current target above the InputBar.

```gherkin
Given "Goblin Warrior 1" is the selected target

Then  a target badge is rendered near the InputBar
And   the badge displays "🎯 Goblin Warrior 1"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Clicking the same row again deselects the target
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Re-clicking the already-selected enemy row toggles the selection off.

```gherkin
Given "Goblin Warrior 1" is the selected target

When  the player clicks the "Goblin Warrior 1" row again
Then  `selectedTarget` is null
And   no row has the "combatant-targeted" class
And   the target badge is NOT rendered
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Target is sent as `target_hint` in the POST body
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The selected target name travels to the backend alongside the player's text.

```gherkin
Given "Goblin Warrior 2" is the selected target
And   the player types "I attack" and presses Send

When  POST /api/sessions/{id}/pc_turn is called
Then  the request body contains:  target_hint: "Goblin Warrior 2"

Given no target is selected
And   the player types "I attack" and presses Send
Then  the request body contains:  target_hint: null
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Backend uses `target_hint` in intent extraction
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** `_extract_pc_combat_intent` uses the hint to set the attack target.

```gherkin
Given the session has enemies ["Goblin Warrior 1", "Goblin Warrior 2"]
And   target_hint == "Goblin Warrior 2"

When  _extract_pc_combat_intent("I attack", session, target_hint="Goblin Warrior 2") is called
Then  intent["target"] == "Goblin Warrior 2"

Given target_hint is None
And   the text contains "I attack Goblin Warrior 1"
Then  intent["target"] == "Goblin Warrior 1"  (keyword inference still works)

Given target_hint is None
And   the text does not name a target
Then  intent["target"] is set to the first living enemy  (existing fallback)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Target is passed to `_build_pc_turn_system` briefing
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The LLM briefing names the intended target explicitly.

```gherkin
Given intent["target"] == "Goblin Warrior 2"

When  _build_pc_turn_system(session, intent, result) is called
Then  the returned system string contains "Target: Goblin Warrior 2"
```

*This AC is already satisfied by the existing briefing format; it is listed here
to make the contract explicit and guard against regression.*

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Selection clears when the turn advances
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The selected target does not carry over to the next combatant's turn.

```gherkin
Given "Goblin Warrior 1" is selected while it is "Ani"'s turn

When  the turn advances to "Goblin Warrior 1" (enemy turn)
Then  `selectedTarget` is null
And   no row has the "combatant-targeted" class
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Selection clears after the player submits
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Sending a message clears the target for the next input.

```gherkin
Given "Goblin Warrior 1" is the selected target

When  the player submits their turn
Then  `selectedTarget` is reset to null  (no stale target on next action)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Dead / inactive enemies cannot be targeted
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Clicking a defeated enemy row has no effect.

```gherkin
Given "Goblin Warrior 1" has status "dead"

When  the player clicks the "Goblin Warrior 1" row
Then  `selectedTarget` is NOT set to "Goblin Warrior 1"
And   the row does NOT receive the "combatant-targeted" class
```

---

## Out of Scope

- Targeting allies or PCs (e.g. for healing spells) — separate feature
- Multi-target selection (AoE spells) — covered by CB3-1
- Target name validation in the backend against the live enemy list — future hardening
- Click-to-target during an enemy turn — only active on PC turns
