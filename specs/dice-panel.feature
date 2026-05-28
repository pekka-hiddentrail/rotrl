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
### AC-003 — Roll result is shown as a player speech bubble in the chat
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player rolls and the result appears as a chat message

```gherkin
Given the player rolls 1d20 with result 14
And   no modifier is applied
When  the roll completes
Then  a player-style speech bubble appears in the chat: "<Name> rolled a 14."
And   the InputBar text field is NOT modified

Given Yanyeeku is the active character with Perception +7
And   a pending Perception DC 18 roll is active
When  the player rolls 1d20 with result 13
Then  a player-style speech bubble appears: "Yanyeeku rolled a 13. With bonus of +7 it is a total of 20."
And   the speech bubble is shown in the UI only — it is not sent to the backend as a turn
```

> **Implementation note:** The bubble uses `role: 'player'` and is appended to the message list
> before `logRoll` / `resolveRoll` are called. It is never transmitted as a chat turn.

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

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Skill bonus is auto-applied when active character and pending roll are both set
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player rolls d20 while a skill check is pending and a character is active

```gherkin
Given a pending roll for Perception DC 18 is active
And   Yanyeeku is the active character
And   Yanyeeku has a Perception modifier of +7
When  the player rolls 1d20 and gets 13
Then  the UI computes finalTotal = 13 + 7 = 20
And   POST /api/sessions/{id}/resolve_roll is called with rolled=20
And   the roll history shows "1d20(13) + Perception +7 = 20 vs DC 18 — passed"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Skill bonus is not applied when no character is active
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Pending roll exists but no active character is set

```gherkin
Given a pending roll for Diplomacy DC 15 is active
And   no character is active
When  the player rolls 1d20 and gets 11
Then  POST /api/sessions/{id}/resolve_roll is called with rolled=11 (raw total)
And   no modifier is added
And   the dice panel shows "No active character — raw roll only"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Unknown skill mapping falls back to raw roll with indicator
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Pending skill name cannot be mapped to the active character's data

```gherkin
Given a pending roll for "Spellcraft" DC 20 is active
And   Yanyeeku is the active character
And   Yanyeeku's character data does not include a Spellcraft entry
When  the player rolls 1d20
Then  the raw total is sent to resolve_roll unchanged
And   the dice panel shows "No mapped bonus for Spellcraft"
And   no modifier is added to the total
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Auto-bonus toggle allows player to override and roll raw
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player wants to override the auto-bonus and roll without modifier

```gherkin
Given a pending skill roll and an active character with a mapped modifier
When  the player turns off the "Auto-apply skill bonus" toggle in the dice panel
Then  the modifier is not applied and the raw d20 total is submitted
And   the toggle state is preserved for the remainder of the session
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Skill mapping uses normalised name comparison
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Pending skill name varies in case or spacing vs. character data key

```gherkin
Given the pending skill name is "sense motive"
And   the active character's skills include "Sense Motive" with modifier +4
Then  the modifier is correctly resolved to +4
And   the auto-bonus is applied
```

---

## Out of Scope

- Backend DC storage (covered by SPEC-006 %%ROLL%% parsing)
- Chat narrative showing roll outcome (covered by SPEC-002)
- Manual modifier override input field (post-MVP)
- Storing active character across browser refresh (covered by character-system.feature)

---

## Notes

- See: [INDEX.md §12 — Frontend: Dice Panel](INDEX.md)
- Die types: d4 · d6 · d8 · d10 · d12 · d20 · d100 (SVG polygon shapes)
- `onRoll(expr, rolls[], total)` callback passed from App.tsx to DicePanel. Returns `Promise<{ passed: boolean } | null>`.
- Roll speech bubble is built in App.tsx's `onRoll` handler: `rawTotal = rolls.reduce(…)`, `modifier = total − rawTotal`. Speaker name taken from `activeCharacter` → `characterMap`.
- The bubble is local-only. It is **not** sent to the backend as a player turn.
- `InputBar` no longer has `injectedValue` / `injectionId` props — injection was removed in favour of the speech bubble.
- `POST /api/sessions/{id}/roll` only fires when a session is active; silently skipped otherwise
- AC-007 through AC-011 implemented in `DicePanel.tsx`. Key exports: `normaliseSkill(s)`, `lookupSkillBonus(skill, speaker)` (pure helpers, independently testable).
- `onRoll` callback signature changed to `(expr, rolls, total) => Promise<{ passed: boolean } | null>`. App.tsx returns `{ passed }` from `resolveRoll`; DicePanel awaits and updates the history record to show PASSED/FAILED badge.
- `autoBonus` toggle state lives in DicePanel; resets to ON on session boot (DicePanel is keyed with `diceKey` which increments on boot).
- Skill modifier read from `activeSpeaker.skills[i].total` (matches `CharacterData.skills[i]`). DicePanel accepts a narrower `ActiveSpeaker` interface so it does not depend on the full `CharacterData` type.
- Skill name normalisation: `trim → lowercase → collapse whitespace/hyphens/underscores → single space` before map lookup.
