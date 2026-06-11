# FEATURE — Automatic Initiative Roll on Combat Event

**ID:** roll-initiatives
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @initiative @session @layout

---

## Story

> As the **GM engine**,
> when a combat event fires (`%%EVENT%%` with `event_type == "combat"`),
> I want initiatives rolled automatically for all combatants using d20 + the correct modifier,
> so that the initiative order is server-authoritative from the moment combat begins — with no
> player action required.

When a combat event fires, the backend seeds initiative modifiers from the event file's
`## Combatants` table into `session.pending_combatants`. On the same turn, when the LLM
writes `%%COMBAT%%` for round 1, the backend immediately calls `roll_combat_initiatives()`,
which rolls `1d20 + modifier` for every combatant, sets `current_actor` to the highest active
combatant, and persists to `state.json`. The resulting `combat_update` SSE carries the fully
sorted, server-rolled state — the LLM's `init:` values are discarded.

---

## Background

- Given a session is booted
- And a combat event file exists with `**Type:** combat` and a `## Combatants` table
- And the LLM writes `%%EVENT%% <combat_event_id>` followed by `%%COMBAT%%` (round 1) in the same turn

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `roll_combat_initiatives` rolls d20 for every combatant
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state has three combatants with arbitrary initiative values
When  roll_combat_initiatives(session) is called
Then  every combatant's initiative is replaced with a fresh roll (old value discarded)
And   each new value is in range [1, 20] for enemies with no modifier
And   the same call does NOT raise or leave any combatant with initiative = 0 unless
      the combatant had a −19 modifier (not a real case)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — PC modifier read from pc_profiles.combat_stats.initiative
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.pc_profiles contains Thaelion with initiative "+3"
And   Thaelion is a combatant in session.combat_state
When  roll_combat_initiatives(session) is called
Then  Thaelion's new initiative is in range [4, 23]  (d20 + 3)

Given a PC with initiative modifier "-1"
Then  that PC's new initiative is in range [0, 19]

Given a PC with initiative modifier "+0"
Then  that PC's new initiative is in range [1, 20]
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Enemy modifier from pending_combatants; flat d20 if absent
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a combatant whose name does NOT match any key in session.pc_profiles
And   session.pending_combatants contains that name with init_mod: +3
When  roll_combat_initiatives(session) is called
Then  that combatant's new initiative is in range [4, 23]  (d20 + 3)

Given a combatant whose name is absent from both pc_profiles and pending_combatants
Then  that combatant's new initiative is in range [1, 20]  (flat d20, modifier = 0)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — current_actor set to new highest-initiative active combatant
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given roll_combat_initiatives produces: Shalelu 18, Goblin 11, Thaelion 7
And   all three are "active"
When  roll_combat_initiatives returns
Then  session.combat_state.current_actor = "Shalelu"

Given the highest-initiative combatant has status "unconscious"
And   the next one is "active"
When  roll_combat_initiatives returns
Then  current_actor = the highest active combatant (not the unconscious one)

Given all combatants are unconscious or dead
When  roll_combat_initiatives returns
Then  current_actor = None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Inactive combatants still receive a roll
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a combatant has status "unconscious"
When  roll_combat_initiatives(session) is called
Then  that combatant's initiative is re-rolled
And   it is NOT set as current_actor
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — state.json written after every roll
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given roll_combat_initiatives is called
When  it returns
Then  _write_session_state(session) has been called
And   state.json contains the updated active_character (= new current_actor)
And   state.json combatants list reflects the new initiative values
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — POST /sessions/{id}/combat/roll_initiatives endpoint (debug)
<!-- ─────────────────────────────────────────────────────────────────────── -->

The endpoint is retained for testing and tooling but is not exposed in the player UI.

```gherkin
Given a valid session with active combat
When  POST /sessions/{id}/combat/roll_initiatives is called
Then  it returns 200
And   the response body is { "combat_state": { "round": N, "current_actor": "...", "combatants": [...] } }
And   every combatant has a new initiative value
And   the combatant list is sorted descending by initiative

Given session.combat_state is None
Then  it returns 409 Conflict

Given an unknown session id
Then  it returns 404 Not Found
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — initiative_pending SSE emitted when combat event fires with round-1 %%COMBAT%%
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the LLM fires %%EVENT%% goblin_attack_starts (event_type == "combat")
And   the same turn contains a %%COMBAT%% block with round: 1
When  the response is fully processed
Then  session._await_initiative_roll is True
And   the "initiative_pending" SSE event is emitted (not "combat_update")
And   combat_state in the event contains seeded combatants (real PC HP/AC, individual enemy names)
And   CombatPanel does NOT appear (no combat_update received)
And   DiceTray shows "⚔ Combat begins — roll for initiative" banner with a roll button

Given the player clicks "Roll for all combatants"
When  POST /sessions/{id}/combat/roll_initiatives is called
Then  roll_combat_initiatives(session) rolls d20+modifier for every combatant
And   the response carries the rolled combat_state sorted by initiative
And   the frontend receives { combat_state } and calls setCombatState
And   CombatPanel appears with server-rolled initiative order
And   the initiative banner disappears

Given the LLM fires %%EVENT%% attack_repelled (event_type == "aftermath")
And   the same turn contains a %%COMBAT%% block with round: 1
Then  _await_initiative_roll is NOT set
And   "combat_update" SSE is emitted as usual (no initiative prompt)
```

> **Implementation note:** `_seed_round1_combatants(session, combat_state)` is called before
> setting `_await_initiative_roll`. It overwrites PC combatants with real HP/AC from
> `pc_profiles` and replaces all non-PC combatants with individual entries from
> `pending_combatants` (event file `## Combatants` table). This prevents 0/0 HP and
> grouped notation (e.g. "Goblin Mob (Wave 1)") from reaching the UI.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — _parse_event_combatants reads ## Combatants table
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given event content with a ## Combatants markdown table containing init_mod column
When  _parse_event_combatants(content) is called
Then  it returns a dict keyed by name (case-insensitive) with "init_mod" as int
And   rows with missing or unparseable init_mod default to 0
And   the function never raises — malformed tables return {}

Given event content with no ## Combatants section
Then  _parse_event_combatants returns {}
```

---

## Out of Scope

- Tie-breaking rules (PF1e dex-modifier tiebreak) — ties left as-is
- Enemy modifier seeding from bestiary (SA-4) — currently from event file `## Combatants` table or flat d20
- Full stat seeding (HP, AC, attacks) from event file — SA-2 tracks this; `pending_combatants` is already the shared structure
- Fully automatic silent roll — removed in favour of player-triggered button in DiceTray

---

## Notes

- `roll_combat_initiatives(session)` in `api/session_manager.py` — mutates `session.combat_state` in-place, calls `_write_session_state`, returns serialised dict.
- `_parse_event_combatants(content)` in `api/session_manager.py` — tolerant parser; returns `{}` on any failure. Stores `"name"` (original case) alongside `"init_mod"`, `"hp"`, `"ac"`.
- `_seed_round1_combatants(session, combat_state)` — called before `_await_initiative_roll` is set. Overwrites PC HP/AC with `pc_profiles` values; replaces non-PC combatants with `pending_combatants` entries when non-empty.
- `session.pending_combatants: dict` on `GameSession` — populated when combat event fires; consumed (cleared) by `roll_combat_initiatives`.
- `session._await_initiative_roll: bool` — set True on round-1 combat event; causes the SSE layer to emit `initiative_pending` instead of `combat_update`; cleared after emission or after `roll_combat_initiatives`.
- PC modifier: `pc_profiles[name.lower()]["combat_stats"]["initiative"]` as signed string; parse fails silently to `+0`.
- Enemy modifier: `pending_combatants[name]["init_mod"]` if present; otherwise `0`.
- SSE `initiative_pending` carries the seeded-but-unrolled `combat_state`; frontend shows roll button in DiceTray.
- SSE `combat_update` carries the rolled, sorted state after `POST /roll_initiatives`.
- `rollInitiatives(sessionId)` in `ui/src/api.ts`; `handleRollInitiatives` in `App.tsx`.
- Initiative banner: `.initiative-banner` in `DiceTray.tsx`; `initiativePending` prop from App.tsx.
- Endpoint `POST /combat/roll_initiatives` is the roll trigger; also usable for debug/tooling.
