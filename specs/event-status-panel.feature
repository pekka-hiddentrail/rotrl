# FEATURE — Event Status Panel

**ID:** event-status-panel
**Status:** Draft
**Area:** Backend | Frontend
**Tags:** @event @temperature @scheduler @debug @ui @api

---

## Story

> As the **GM / developer**,
> I want a live status panel showing event scheduler state,
> so that I can observe readiness values, active events, and transitions
> while testing the temperature-based scheduler without reading raw JSON or log files.

The panel is a debug/diagnostic tool, not a player-facing feature.
It opens from **Tools → 🌡 Event Status** (only when a session is booted)
and auto-refreshes every 3 seconds. It shows exactly what the scheduler
holds in memory at the time of the request.

---

## Background

- Given a session is booted
- And the session has event_runtime initialized (scheduler on or off)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — endpoint returns correct shape
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session exists with id S
When  GET /api/sessions/S/event_status is called
Then  response status is 200
And   body contains keys: scheduler_enabled, turn_number, active_event_id,
      warm_events, completed_events, cooldowns
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — unknown session returns 404
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given no session with id X exists
When  GET /api/sessions/X/event_status is called
Then  response status is 404
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — scheduler_enabled reflects boot flag
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session booted with event_scheduler=False
When  GET /api/sessions/S/event_status is called
Then  scheduler_enabled is false

Given a session booted with event_scheduler=True
When  GET /api/sessions/S/event_status is called
Then  scheduler_enabled is true
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — warm_events empty when scheduler disabled at boot
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session booted with event_scheduler=False
When  GET /api/sessions/S/event_status is called
Then  warm_events is an empty object {}
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — warm_events populated from schedulable event files at boot
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a session booted with event_scheduler=True
And   at least one event file has a ## Schedule section
When  GET /api/sessions/S/event_status is called
Then  warm_events contains an entry for each schedulable event
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — warm_events entries contain all WarmEvent fields
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given warm_events is non-empty
Then  each entry contains: readiness, threshold, base_gain, failed_rolls,
      frozen, last_zone_match_turn, turns_remaining, zones, action_gain_map
And   readiness is a float between 0.0 and 100.0
And   frozen is a boolean
And   zones is a list of strings
And   action_gain_map is an object mapping string keys to float values
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — active_event_id is null when no event is active
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a freshly booted session
When  GET /api/sessions/S/event_status is called
Then  active_event_id is null
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — active_event_id reflects runtime state when an event fires
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.event_runtime.active_event_id is set to "my_event"
When  GET /api/sessions/S/event_status is called
Then  active_event_id is "my_event"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — completed_events lists expired event ids
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given "evt_a" has been added to session.event_runtime.completed_events
When  GET /api/sessions/S/event_status is called
Then  completed_events contains "evt_a"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — turn_number reflects session.turn_number
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.turn_number is N
When  GET /api/sessions/S/event_status is called
Then  turn_number equals N
And   turn_number is an integer
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — panel button appears only when session is booted
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the UI is in pre-boot state
Then  "Event Status" is not visible in the Tools dropdown

Given a session is booted
Then  "Event Status" is visible in the Tools dropdown
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — panel displays active event card with TTL bar
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_event_id is set
When  the panel is open
Then  an ACTIVE EVENT card is shown at the top
And   the card includes the event id, TTL bar, and readiness at trigger

Given active_event_id is null
Then  "No active event" placeholder is shown instead
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — panel shows readiness bar and threshold marker per event
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given warm_events contains at least one entry
When  the panel is open
Then  each event row shows a readiness bar scaled 0–100
And   an amber threshold marker is overlaid at the threshold position
And   the Gap column shows (threshold - readiness) when readiness < threshold
And   the Gap column shows — when readiness >= threshold
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — status badges reflect scheduler state per event
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event is the active_event_id         → badge shows ACTIVE   (green)
Given an event is in completed_events         → shown in Completed section, not table
Given readiness >= threshold (not active)     → badge shows ELIGIBLE (amber)
Given frozen is True (not active or eligible) → badge shows FROZEN   (blue)
Given none of the above                       → badge shows WARMING  (grey)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-015 — panel auto-refreshes and supports manual refresh
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the panel is open with Auto checkbox enabled
Then  the panel polls GET /api/sessions/S/event_status every 3 seconds

Given the Auto checkbox is unchecked
Then  polling stops

Given the ↺ button is clicked
Then  a single immediate refresh is triggered
```

---

## Out of Scope

- GM controls (nudge readiness, force trigger) — E4-1 dashboard tier
- Event timeline export — E4-2
- Readiness history graph per event — E4-4
