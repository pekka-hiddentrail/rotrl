# FEATURE — Enemy Turn `%%ACTION%%` Action Type Field

**ID:** enemy-action-type
**Status:** Draft
**Area:** Backend
**Tags:** @combat @enemy @action @economy @parsing @session

---

## Story

> As the **backend**,
> I want every enemy `%%ACTION%%` block to declare a PF1e `action_type`
> (`standard`, `move`, `full`, `swift`, `free`, `five_foot_step`) — so the system
> can log what action economy was spent each turn, validate simple constraints
> (e.g. only one swift per turn), and build toward full action-economy enforcement.

Today, `%%ACTION%%` carries `action: attack|use_ability|move|delay` but says nothing
about which PF1e action slot was consumed. Adding `action_type` as an explicit field
lets the LLM declare its budget choice and lets the backend record and eventually validate it.

---

## Background

- Given a session is active with a live `CombatState`
- And the current actor is an enemy (not a PC)
- And `_build_enemy_turn_system` generates the per-turn briefing prompt

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `_parse_action_block` extracts `action_type` when present
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The LLM writes an `action_type` field; the parser reads it.

```gherkin
Given a %%ACTION%% block containing:
  action: attack
  action_type: standard
  weapon: shortbow
  target: Yanyeeku

When  _parse_action_block(text) is called
Then  result["action_type"] == "standard"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Unknown `action_type` values are normalised to `"standard"`
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The LLM writes a non-canonical value; the backend falls back safely.

```gherkin
Given a %%ACTION%% block containing:
  action: attack
  action_type: complicated_maneuver

When  _parse_action_block(text) is called
Then  result["action_type"] == "standard"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — `action_type` is inferred from `action` when absent
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Older or minimal LLM responses omit `action_type`; a sensible default is derived.

```gherkin
Given a %%ACTION%% block with  action: attack  (no action_type field)
Then  result["action_type"] == "standard"

Given a %%ACTION%% block with  action: move    (no action_type field)
Then  result["action_type"] == "move"

Given a %%ACTION%% block with  action: delay   (no action_type field)
Then  result["action_type"] == "delay"

Given a %%ACTION%% block with  action: use_ability  (no action_type field)
Then  result["action_type"] == "standard"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — All canonical `action_type` values are accepted unchanged
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The full set of legal values passes through without modification.

```gherkin
For each value in {"standard", "move", "full", "swift", "free", "five_foot_step", "delay"}:
  Given a %%ACTION%% block with  action_type: <value>
  Then  result["action_type"] == <value>
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Enemy-turn briefing prompt includes the `action_type:` instruction
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The LLM is asked to declare an action type in every response.

```gherkin
When  _build_enemy_turn_system(session, name) is called
Then  the returned string contains "action_type:"
And   it lists the legal values: standard | move | full | swift | free | five_foot_step
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — `action_type` is included in the `action_card` SSE event
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The resolved action type is visible in the streamed event.

```gherkin
Given the LLM writes  action_type: full  in its %%ACTION%% block

When  stream_enemy_turn resolves and emits the action_card event
Then  the event payload contains  action_type: "full"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — `action_type` is included in the session log
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The action type is visible in the dev/session log for diagnostics.

```gherkin
Given an enemy resolves an action with  action_type: "swift"

When  the turn completes
Then  the session log contains a line noting the actor, action, and action_type
```

---

## Out of Scope

- Enforcement of action-slot budgets per turn (one standard, one move, etc.) — deferred to a future validation tier
- Swift / immediate tracking across turns — deferred (CB2.5-3/4)
- `action_type` on the PC side (`%%ACTION%%` is enemy-only; PC uses `action_type_hint`) — see `action-economy.feature`
- 5-foot-step flanking / reach consequences — deferred (E in COMBAT-TODO.md Tier 2.5)
