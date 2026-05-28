# FEATURE — Dice Panel

**ID:** dice-panel
**Status:** Approved
**Area:** Frontend
**Tags:** @dice @roll @pending-roll @history

---

## Story

> As a **player**,
> I want a dice panel where I can roll any combination of dice,
> so that physical rolls are not needed and skill check results are automatically resolved against the pending DC.

The panel accumulates a pending queue of dice, rolls them all at once, and reports the result to both the chat log and the session backend.

---

## Background

- Given the dice panel is visible in the UI

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Clicking die buttons accumulates a pending roll queue
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player queues multiple dice

```gherkin
Given no dice are queued
When  the player clicks d6 twice then d20 once
Then  the pending queue shows "2d6 + 1d20"
And   the Roll button is enabled
And   clicking a die button again adds to the queue (does not replace it)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Roll button executes the roll and logs it
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player clicks Roll

```gherkin
Given the pending queue contains "1d20"
When  the player clicks Roll
Then  the die is rolled and a result between 1 and 20 is produced
And   the result is added to the roll history (last 10 entries)
And   the most recent roll is highlighted in the history
And   POST /api/sessions/{id}/roll is called with the expression, per-die breakdown, and total
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Roll result is injected into the input bar
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player rolls and the result appears in the chat input

```gherkin
Given the player rolls 1d20 with result 14
When  the roll completes
Then  the total (14) is injected into the InputBar text field
And   the player can then submit it as part of their next action
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Pending roll banner activates on roll_request SSE event
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM requests a skill check

```gherkin
Given a roll_request SSE event is received with skill="Diplomacy", dc=15
When  the event is processed
Then  the dice panel displays a pending roll banner showing "Diplomacy DC 15 — roll d20"
And   the panel background changes colour to indicate a skill check is pending
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Pending roll is resolved when the player rolls d20
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player rolls d20 while a skill check is pending

```gherkin
Given a pending roll for Diplomacy DC 15 is active
When  the player rolls 1d20 and gets 17
Then  POST /api/sessions/{id}/resolve_roll is called with rolled=17
And   the response returns passed=true, outcome text from the success field
And   the pending roll banner is dismissed
And   the outcome is visible to the player
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Roll history shows last 10 rolls
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player has rolled many times

```gherkin
Given the player has completed 12 dice rolls this session
When  the dice panel roll history is visible
Then  only the most recent 10 rolls are shown
And   the oldest rolls are discarded from the display
And   each history entry shows the expression, per-die breakdown, and total
```

---

## Out of Scope

- Backend DC storage (covered by SPEC-006 %%ROLL%% parsing)
- Chat narrative showing roll outcome (covered by SPEC-002)

---

## Notes

- See: [INDEX.md §12 — Frontend: Dice Panel](INDEX.md)
- Die types: d4 · d6 · d8 · d10 · d12 · d20 · d100 (SVG polygon shapes)
- `onRoll(expr, rolls[], total)` callback passed from App.tsx to DicePanel
- `POST /api/sessions/{id}/roll` only fires when a session is active; silently skipped otherwise
