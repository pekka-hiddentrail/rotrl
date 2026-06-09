# FEATURE — Event Temperature Stability Layer

**ID:** event-temperature-stability
**Status:** Draft
**Area:** Backend
**Tags:** @event @temperature @stability @interrupt @cooldown

---

## Story

> As the **GM engine**,
> I want stable conflict-resolution and interruption rules for temperature events,
> so that pacing remains believable when multiple events compete or trigger mid-action.

This layer extends MVP scheduling with readiness-vs-urgency separation, arbitration of simultaneous winners,
interrupt safety, and repeat protection.

The `%%EVENT%%` LLM-triggered path remains available as a parallel mechanism throughout this layer as well.
The scheduler flag (`event_scheduler`) and the coexistence model established in the MVP carry forward here
unchanged — this tier only adds fields and logic on top of the existing MVP scheduler.

---

## Background

- Given MVP event temperature scheduling is implemented
- And event definitions may declare interrupt_policy, priority, cooldown_turns, and max_fires_per_session

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — readiness and urgency are tracked independently
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a warm event has readiness and urgency runtime fields
When  scheduler tick updates event state
Then  readiness is used for trigger eligibility/chance
And   urgency is used for interruption timing decisions
And   changing urgency does not directly change trigger chance
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — interrupt_policy controls mid-action behavior
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event triggers while another action is in progress
And   interrupt_policy is "none"
When  runtime evaluates interruption
Then  the event is queued and does not start immediately

Given interrupt_policy is "hard"
Then  runtime starts event at the next allowed handoff point
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — pending_interrupt queues exactly one event handoff
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given pending_interrupt is empty
And   an interrupt-eligible event wins trigger arbitration
When  current action has not reached a handoff point
Then  pending_interrupt is set with that event id
And   the event starts only after current action closes
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — simultaneous eligible events are arbitrated once per turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given two or more events trigger eligibility in the same turn
When  arbitration runs
Then  exactly one winner is selected for immediate start
And   non-winning events are preserved for later consideration
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — arbitration weight uses readiness and priority
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given event A and event B are both eligible
And   event A has higher weighted score from readiness*priority (or equivalent configured formula)
When  deterministic test seed is fixed
Then  winner selection is reproducible
And   higher weighted candidates win more frequently across repeated trials
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — cooldown prevents immediate re-fire
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event completed with cooldown_turns > 0
When  subsequent turns occur before cooldown reaches 0
Then  the event cannot trigger even if readiness >= threshold
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — max_fires_per_session hard-limits repeats
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event has max_fires_per_session = 1
And   it has already fired once
When  scheduler evaluates triggers later in the same session
Then  that event is excluded from triggering
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — optional decay activates only when configured
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given an event has no decay_after_freeze setting
When  it is out-of-context for multiple turns
Then  readiness remains frozen

Given an event has decay_after_freeze configured
When  out-of-context freeze duration is exceeded
Then  readiness decreases by configured decay per turn
And   readiness does not drop below 0
```

---

## Out of Scope

- GM UI controls for manual nudge/force-trigger
- Adaptive machine-learned pacing
