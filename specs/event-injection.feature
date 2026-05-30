# FEATURE — Event Injection System (`%%EVENT%%`)

**ID:** event-injection
**Status:** Approved
**Area:** Backend
**Tags:** @event @injection @context @parsing @session

---

## Story

> As the **GM engine**,
> I want the LLM to signal game-state transitions using a `%%EVENT%%` tag,
> so that relevant encounter content is automatically injected into context for a bounded window of turns without bloating every prompt.

The existing RAG system injects context based on what the *player mentions*. Events inject context based on what the *LLM decides is happening*. When combat starts, or a scene shifts, the LLM writes `%%EVENT%% <id>` and the engine loads the corresponding content file — goblin stats, scene constraints, whatever that event requires — and keeps it in the system prompt for N turns (default 5).

---

## Background

- Given a session is active
- And the event index has been loaded from `adventure_path/02_events/`
- And the session's `active_events` list is available

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — LLM fires an event and content is injected the next turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes a valid `%%EVENT%%` tag

```gherkin
Given an event file `02_events/goblin_attack_starts.md` exists
And   the LLM response contains the line "%%EVENT%% goblin_attack_starts"
When  the turn is processed
Then  `goblin_attack_starts` is added to `session.active_events` with `turns_remaining = 5`
And   on the next turn, the event content is included in the system prompt payload
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Event content expires after N turns
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** An active event counts down and is removed

```gherkin
Given `goblin_attack_starts` is in `session.active_events` with `turns_remaining = 5`
When  5 player turns complete
Then  `turns_remaining` reaches 0 and the entry is removed from `active_events`
And   the event content is no longer included in the system prompt
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Multiple events can be active simultaneously
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A second event fires while a first is still active

```gherkin
Given `goblin_attack_starts` is active with `turns_remaining = 3`
And   the LLM writes "%%EVENT%% fire_phase_begins"
When  the turn is processed
Then  both events are in `active_events`
And   both events' content is injected into the system prompt
And   each event's `turns_remaining` decrements independently
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Unknown event ID is silently ignored
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes an event ID that has no corresponding file

```gherkin
Given no file `02_events/no_such_event.md` exists
When  the LLM response contains "%%EVENT%% no_such_event"
Then  no entry is added to `active_events`
And   no error is raised
And   the turn completes normally
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Duplicate event does not reset TTL
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM fires the same event twice

```gherkin
Given `goblin_attack_starts` is active with `turns_remaining = 2`
When  the LLM writes "%%EVENT%% goblin_attack_starts" again
Then  `turns_remaining` remains 2 (not reset to 5)
And   no duplicate entry is added to `active_events`
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Event map is included in the system prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Session has events available

```gherkin
Given the `02_events/` directory contains one or more event files
When  the system prompt is built for any turn
Then  the prompt includes a compact event map listing valid event IDs and their trigger conditions
And   the map includes the `%%EVENT%%` syntax instruction
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — `%%EVENT%%` section is not shown to the player
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes an event tag in its response

```gherkin
Given the LLM response contains "%%EVENT%% goblin_attack_starts"
When  the response is streamed in normal (non-dev) mode
Then  the event line is not emitted as a token event
And   the player chat shows only the %%NARRATIVE%% content
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Context SSE event includes active event IDs
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Active events are reported in the SSE context event

```gherkin
Given `goblin_attack_starts` is in `session.active_events`
When  a turn completes
Then  the SSE `context` event includes `active_events: ["goblin_attack_starts"]`
And   expired events are not included
```

---

## Out of Scope

- Event content file quality (adventure content, not code)
- Compressing active event content to a summary mid-window (deferred, noted in TODO)
- Per-event TTL override (all events use N=5 for now)
- Frontend display of active events (deferred)

---

## Notes

- `%%EVENT%%` is inline: `%%EVENT%% <event_id>` on a single line. No block form.
- One event per LLM response. If the LLM writes multiple `%%EVENT%%` lines, only the first is processed. (Revisit if needed.)
- The event map in the system prompt is injected only when `02_events/` contains files — zero-cost if no events are defined for a session.
- N=5 is a hardcoded starting point. See TODO open design note — needs tuning against real sessions.
- Related: [context-detection.feature](context-detection.feature) — same injection pipeline, different trigger source
- Related: [response-parsing.feature](response-parsing.feature) — `%%EVENT%%` extends the existing section marker set
- Related: [system-prompt.feature](system-prompt.feature) — event map is part of prompt assembly
