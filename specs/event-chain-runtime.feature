# FEATURE — Event Chain Runtime (Hard Triggers)

**ID:** event-chain-runtime
**Status:** Draft
**Area:** Backend
**Tags:** @event @chain @runtime @session @state

---

## Story

> As the **GM engine**,
> I want event chains to progress deterministically once entered,
> so that critical story beats happen in reliable order while still allowing soft scheduling outside chain lock.

This feature defines chain node progression, chain lock behavior, and completion semantics independent of
temperature rolls.

---

## Background

- Given chain definitions are loaded from event metadata
- And event_runtime tracks `active_chain_id` and `active_node_id`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — chain entry sets active_chain_id and active_node_id
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a chain entry event is triggered
When  runtime applies chain activation
Then  event_runtime.active_chain_id is set to the chain id
And   event_runtime.active_node_id is set to the first node id
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — chain lock suppresses unrelated soft triggers by default
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_chain_id is set
And   a soft event is eligible but not marked chain-allowed
When  trigger evaluation runs
Then  the soft event does not trigger during chain lock
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — node completion advances via hard transition rules
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_node_id is "node_a"
And   node_a completion condition is met
When  chain runtime evaluates transitions
Then  active_node_id becomes the configured next node id
And   no readiness roll is used for this transition
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — branch transitions choose next node by condition
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_node_id has two conditional next nodes
When  branch condition X is true
Then  active_node_id becomes node_x
And   branch condition Y path is not selected
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — final node completion exits chain lock
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_node_id is the terminal node of active_chain_id
And   its completion condition is met
When  chain runtime applies completion
Then  active_chain_id is cleared
And   active_node_id is cleared
And   soft scheduler resumes normal trigger evaluation on later turns
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — chain state is persisted to state.json each turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_chain_id and active_node_id are set in memory
When  _write_session_state(session) runs
Then  state.json event_runtime includes the same chain identifiers
And   values survive process restart when session is reloaded
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — compact chain context is injected to prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given active_chain_id and active_node_id are set
When  _inject_context assembles system prompt content
Then  a [CHAIN STATE] block is included
And   the block names current chain and node
And   it does not include full chain file bodies unless explicitly needed
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — chain transitions are logged with from->to node IDs
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a chain transition occurs
When  the turn completes
Then  session log includes chain id, previous node id, and next node id
And   final completion is logged as chain exited
```

---

## Out of Scope

- Interrupt urgency policy
- Simultaneous chain execution in one session
- Visual chain editor
