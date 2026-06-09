# FEATURE — Event Temperature Scheduler (MVP)

**ID:** event-temperature-mvp
**Status:** Draft
**Area:** Backend
**Tags:** @event @temperature @scheduler @session @state

---

## Story

> As the **GM engine**,
> I want candidate events to accumulate readiness over turns and trigger probabilistically after a threshold,
> so that scenes fire naturally without rigid turn timers.

This feature adds a lightweight event scheduler on top of existing event injection. Events can warm in
the background, freeze when context no longer matches, and trigger once they are ready. Runtime state is
stored in `state.json` so the scheduler survives restarts.

The scheduler runs alongside the existing `%%EVENT%%` LLM-triggered path — both are active at the same
time and write to separate state fields (`session.event_runtime` vs `session.active_events`). The
scheduler is enabled per-session via the **Scheduler** checkbox in the UI header (boot-time flag
`event_scheduler`). When the flag is off, the tick and trigger logic are skipped entirely and only the
`%%EVENT%%` path runs. This allows parallel testing until the scheduler is promoted to primary.

---

## Background

- Given a session is active
- And `session.event_runtime` exists with default fields
- And one or more event definitions with a `## Schedule` section are loaded from `adventure_path/02_events/` as warm events at boot
- And `session.event_scheduler` is True (set via the UI Scheduler checkbox at boot)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — state.json includes event_runtime snapshot
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session has event runtime data in memory
When  _write_session_state(session) is called
Then  sessions/session_NNN/state.json contains an "event_runtime" object
And   event_runtime contains keys: active_event_id, active_chain_id, active_node_id,
      warm_events, completed_events, cooldowns
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — missing event_runtime is backfilled on load
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a legacy state.json with no event_runtime key
When  session state is loaded or initialized for a new turn
Then  event_runtime is created with safe defaults
And   no exception is raised
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — matching context increases readiness
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a warm event with readiness 20 and base_gain 1
And   the current turn context matches its zone/tag conditions
When  the event scheduler tick runs
Then  the event readiness becomes 21
And   readiness is clamped to a maximum of 100
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — non-matching context freezes readiness in MVP
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a warm event with readiness 48
And   the current turn context does not match its zone/tag conditions
When  the scheduler tick runs
Then  readiness remains 48
And   the event is marked frozen for this tick
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — desired actions apply per-event readiness boosts
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event defines action_gain_map for a detected intent tag
And   readiness is 50 before tick
When  the player turn includes the matching intent tag
Then  the configured gain is added for that event
And   unrelated events do not receive that gain
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — trigger rolls start only at threshold
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event threshold is 75
And   readiness is 74
When  the trigger phase runs
Then  no d100 roll is made

Given readiness is 75
When  the trigger phase runs
Then  a d100 roll is made for that event
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — readiness-based trigger chance uses d100 <= readiness
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event has readiness 80 and is eligible
When  the trigger roll result is 65
Then  the event triggers

Given the roll result is 92
Then  the event does not trigger
And   failed_rolls increments by 1
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — pity rule guarantees eventual trigger
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event is eligible (readiness >= threshold)
And   failed_rolls reaches the configured pity limit
When  the next trigger phase runs
Then  the event triggers without requiring a successful random roll
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — active event expires after TTL without LLM signal
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_event_id is set with turns_remaining = N
When  N turns pass
Then  active_event_id is cleared by the backend
And   the event is added to completed_events
And   no signal from the LLM is required for this to happen
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — active event locks out other soft triggers in MVP
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given event A is active_event_id
And   event B is warm and eligible
When  the trigger phase runs
Then  event B is not started while event A remains active
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — active event context is injected compactly
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_event_id is set on event_runtime
When  _inject_context assembles the system prompt
Then  an [ACTIVE EVENT] block is included
And   the block includes event ID and minimal runtime state
And   full event-map text is not duplicated in this block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — scheduler transitions are logged in session log
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given readiness changed during the tick
When  the turn completes
Then  session log contains a scheduler line with event id and readiness delta

Given an event triggers
Then  session log contains trigger source (roll or pity)
```

---

## Out of Scope

- Multi-event arbitration among simultaneous winners
- Urgency-based interruption behavior
- Decay after freeze
- GM dashboard controls
