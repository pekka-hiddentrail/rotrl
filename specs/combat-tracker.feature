# FEATURE — Combat Tracker (Tier 1)

**ID:** combat-tracker
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @parsing @session @streaming @layout

---

## Story

> As the **GM engine**,
> I want the LLM to write a `%%COMBAT%%` block each turn while combat is in progress,
> so that a live initiative tracker with HP bars and status chips appears in the UI
> without the GM needing to maintain state manually.

The LLM owns the combat narrative and decides when encounters start and end. The system
parses a structured `%%COMBAT%%` block — round number, combatant names, HP, AC, initiative,
and status — into a `CombatState` object, stores it on the session, and pushes a
`combat_update` SSE event so the frontend can render the panel. When the LLM writes
`round: 0` the state is cleared and the panel disappears.

---

## Background

- Given a session is active
- And `session.combat_state` is `None` initially

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — %%COMBAT%% block populates session.combat_state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes a valid combat block

```gherkin
Given the LLM response contains a %%COMBAT%% section with round ≥ 1 and ≥ 1 combatant rows
When  the turn is processed
Then  session.combat_state is a CombatState with the correct round number
And   session.combat_state.combatants contains one Combatant per row
And   each Combatant has name, hp_current, hp_max, ac, initiative, and status populated
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — round: 0 clears combat state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM signals combat ended

```gherkin
Given session.combat_state is set from a previous turn
And   the LLM response contains "%%COMBAT%%\nround: 0\ncombatants:\n"
When  the turn is processed
Then  session.combat_state is None
And   the combat_update SSE event carries combat_state: null
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — HP is clamped and status validated
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes out-of-range HP or an unknown status

```gherkin
Given a combatant row with hp_current > hp_max
Then  hp_current is clamped to hp_max
Given a combatant row with hp_current < 0
Then  hp_current is clamped to 0
Given a combatant row with an unrecognised status value
Then  status defaults to "active"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — combat_update SSE event is emitted every turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Turn completes with and without combat

```gherkin
Given the LLM response does NOT contain a %%COMBAT%% block
When  the turn completes
Then  a combat_update SSE event is emitted with combat_state: null

Given the LLM response DOES contain a valid %%COMBAT%% block
When  the turn completes
Then  a combat_update SSE event is emitted with a serialised CombatState dict
And   the dict contains "round", "combatants" (array of combatant objects)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — %%COMBAT%% block is stripped from the player-visible stream
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Non-dev session streams a response with a %%COMBAT%% block

```gherkin
Given dev_mode is False
And   the LLM response contains "%%NARRATIVE%%\nBlades clash!\n\n%%COMBAT%%\nround: 1\n..."
When  the token stream is filtered
Then  the player sees "Blades clash!" in the chat
And   "%%COMBAT%%", "round:", and "combatants:" are NOT present in any token event
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — CombatPanel appears and disappears with combat state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** combat_update event drives panel visibility in the UI

```gherkin
Given combatState in App.tsx is null
Then  CombatPanel is not rendered
And   DicePanel is in the right column (order: 3)

Given a combat_update event arrives with a non-null combat_state
Then  combatState is set in App.tsx
And   CombatPanel is rendered in the right column (order: 4)
And   DicePanel moves to the left column (order: 2) adjacent to CharacterSidebar
And   .main-content has the "combat-active" CSS class
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — CombatPanel shows initiative order with current actor highlighted
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Multiple combatants with different initiative scores

```gherkin
Given combatants with initiative values 14, 8, 6
When  CombatPanel renders
Then  combatants are listed highest-initiative-first
And   the top combatant (init 14) has the "combatant-current" CSS class (gold glow)
And   inactive combatants (unconscious / fled / dead) have the "combatant-inactive" class (dimmed)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — End Combat button clears state on client and backend
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM clicks End Combat

```gherkin
Given CombatPanel is visible with an active CombatState
When  the GM clicks "End Combat"
Then  DELETE /api/sessions/{id}/combat is called
And   the backend sets session.combat_state = None
And   combatState in App.tsx is set to null
And   CombatPanel is no longer rendered
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — HpBar colour reflects health percentage
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** HpBar renders at various health levels

```gherkin
Given hp_current / hp_max > 0.66
Then  the fill colour is green (#3a9a6a)
Given hp_current / hp_max is between 0.33 and 0.66
Then  the fill colour is amber (#c9a84c)
Given hp_current / hp_max is between 0 and 0.33
Then  the fill colour is red (#b04040)
Given hp_current = 0
Then  the fill colour is dark grey (#444)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Per-turn combat reminder injected into GM directive
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Combat is in progress when a new turn is assembled

```gherkin
Given session.combat_state is a CombatState with round ≥ 1
When  _inject_context assembles the system prompt for the next turn
Then  a "[COMBAT ONGOING — round N]" block is appended to system_content
And   the block instructs the LLM to write a %%COMBAT%% block this turn
And   the block includes the current round number from session.combat_state.round

Given session.combat_state is None
When  _inject_context assembles the system prompt
Then  no combat reminder block is appended

Given session.combat_state.round == 0
When  _inject_context assembles the system prompt
Then  no combat reminder block is appended
```

---

## Out of Scope (Tier 1)

- Automatic dice resolution for attacks (Tier 2 — `%%ATTACK%%` block)
- Map / grid positioning (Tier 3)
- Condition tracking beyond the four status values (Tier 3)
- Spell slot tracking (Tier 3)
- Per-turn initiative reordering (movement within a round not modelled)

---

## Notes

- `%%COMBAT%%` is a **section marker** (like `%%DELTAS%%`), not an inline tag like `%%EVENT%%`.
  Its content is multi-line: one `round:` line and one `-name:` line per combatant.
- The combatant separator is `·` (U+00B7 MIDDLE DOT) or `•` (U+2022 BULLET).
  Parser splits on either.
- The LLM owns HP values — they are written into the block each turn, not computed by the server.
  Server-owned deltas are a Tier 2 concern (automatic attack resolution).
- `session.combat_state` is not persisted across sessions; the session-end recap is the continuity record.
- Layout reversion on session end: `setCombatState(null)` is called in both `handleEnd` and `handleKillEnd`.
- Related: [response-parsing.feature](response-parsing.feature) — `%%COMBAT%%` extends the section marker set
- Related: [event-injection.feature](event-injection.feature) — `goblin_attack_starts` event typically co-fires with the first `%%COMBAT%%` block. Combat-starting event files (`02_events/goblin_attack_starts.md`, `fire_phase_begins.md`, `cavalry_arrives.md`) include a `### REQUIRED — Combat tracker` section in their injectable content that instructs the LLM to write `%%COMBAT%%` every turn the event is active. `attack_repelled.md` instructs `round: 0` to clear the panel.
- Related: [dice-panel.feature](dice-panel.feature) — DicePanel repositions during combat
