# FEATURE — Session State File

**ID:** session-state
**Status:** Approved
**Area:** Backend
**Tags:** @session @state @persistence @boot

---

## Story

> As the **GM engine**,
> I want a lightweight state file written to `sessions/session_NNN/state.json` on every
> relevant state change,
> so that the current mode (social / combat), active round, and fired events are always
> readable from disk without inspecting logs or memory.

The in-memory `GameSession` object holds all runtime state, but it is lost when the server
restarts. This feature introduces a minimal snapshot — deliberately small — that captures only
the three most important pieces of session context: whether the session is in social or combat
mode, which round combat is on, and which events are currently active. It is not a full session
restore; it is a "state of play" indicator that can be read by tooling, tests, and future
features (e.g. auto-resuming a session after a restart).

---

## Background

- Given a `sessions/state.template.json` exists at the repo root with
  `{"mode":"social","round":0,"events":[]}`
- And a session has been created via `create_session(session_number, ...)`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Template file exists and has the correct shape
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the repository root
Then  sessions/state.template.json exists
And   it is valid JSON with keys "mode", "round", "events"
And   "mode"   == "social"
And   "round"  == 0
And   "events" == []
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Boot initialises state.json from template
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given create_session(session_number=1, ...) is called
Then  sessions/session_001/state.json is created
And   "mode"   == "social"
And   "round"  == 0
And   "events" == []
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Boot creates the session directory if it does not exist
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given sessions/session_099/ does not exist
When  create_session(session_number=99, ...) is called
Then  sessions/session_099/state.json is created with the template defaults
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Combat start sets mode to "combat" and records the round
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session in social mode
When  session.combat_state is set to CombatState(round=1, combatants=[...])
Then  state.json "mode"  == "combat"
And   state.json "round" == 1
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Round advance updates the round field
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given state.json shows round=1
When  session.combat_state is updated to round=2
Then  state.json "round" == 2
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Combat clear resets mode to "social" and round to 0
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given state.json shows mode="combat", round=2
When  session.combat_state is set to None
Then  state.json "mode"  == "social"
And   state.json "round" == 0
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — DELETE /combat endpoint updates state.json
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an active session with combat_state set
When  DELETE /api/sessions/{id}/combat is called
Then  state.json "mode"  == "social"
And   state.json "round" == 0
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Event fire adds the event_id to the events list
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given state.json "events" == []
When  an ActiveEvent with event_id="goblin_raid" is appended to session.active_events
Then  state.json "events" == ["goblin_raid"]
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Multiple simultaneous events all appear in the list
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given two active events with ids "evt_a" and "evt_b"
Then  state.json "events" contains both "evt_a" and "evt_b"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Event expiry removes the event_id from the list
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given state.json "events" == ["goblin_raid"]
When  the event expires and is removed from session.active_events
Then  state.json "events" == []
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — state.json is valid JSON on every write
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given any call to _write_session_state(session)
Then  the resulting file parses without error with json.loads()
And   all four keys "mode", "round", "events", "active_character" are present
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Boot overwrites an existing state.json from a prior run
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given sessions/session_001/state.json already exists with mode="combat", round=4
When  create_session(session_number=1, ...) is called again
Then  state.json "mode"             == "social"
And   state.json "round"            == 0
And   state.json "events"           == []
And   state.json "active_character" == "party"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — Boot defaults active_character to "party"
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given create_session(session_number=1, ...) is called
Then  state.json "active_character" == "party"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — PUT /active_character updates the field
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an active session
When  PUT /api/sessions/{id}/active_character with body {"name": "Ani"} is called
Then  state.json "active_character" == "Ani"
And   the response body contains {"active_character": "Ani"}
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-015 — Sending "party" deselects the active character
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given state.json "active_character" == "Ani"
When  PUT /api/sessions/{id}/active_character with body {"name": "party"} is called
Then  state.json "active_character" == "party"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-016 — Sending an empty string falls back to "party"
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given any active session
When  set_active_character(session, "") is called
Then  session.active_character == "party"
And   state.json "active_character" == "party"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-017 — active_character persists across other state changes
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given state.json "active_character" == "Yanyeeku"
When  session.combat_state is updated (round advances or combat clears)
Then  state.json "active_character" is still "Yanyeeku"
```

---

## Out of Scope

- Automatic active_character update when combat turn advances (Tier 1.10 — CB1.10-1)
- Frontend reading of state.json directly (backend owns this file)
- Full session restore from state.json (future work)
- HP, initiative order, or combatant list in state.json (Tier 1.5 owns combat state in memory)
