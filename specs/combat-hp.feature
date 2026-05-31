# FEATURE — Combat HP Authority

**ID:** combat-hp
**Status:** Approved
**Area:** Backend
**Tags:** @combat @hp @session @parsing

---

## Story

> As the **game system**,
> I want the backend to own HP values for all combatants,
> so that LLM arithmetic errors and round-to-round drift cannot corrupt the
> combat tracker, and so attack resolution has a reliable HP store to write into.

In Tier 1, the LLM writes `hp: cur/max` every turn for every combatant. In
practice the model miscounts damage, forgets a hit from two rounds ago, or
silently resets a dying goblin to full health. This feature fixes that: the LLM
initialises HP when a combatant first appears, the backend persists those values,
and the LLM never computes HP again — it reads current values from the injected
context and narrates accordingly.

Non-attack HP changes (traps, poison, healing) use a `%%HP%%` delta block that
the LLM writes instead of rewriting full HP values.

---

## Background

- Given a session is active
- And `session.combat_state` may be `None` (out of combat) or a `CombatState`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — HP initialised from LLM on combat start
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** First %%COMBAT%% block (no existing combat state)

```gherkin
Given session.combat_state is None
And   the LLM writes a %%COMBAT%% block with round: 1 and combatants including HP values
When  the turn is processed
Then  session.combat_state is set with hp_current and hp_max taken from the LLM block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — HP preserved from backend on subsequent turns
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes different HP values on round 2

```gherkin
Given session.combat_state has combatant "Shalelu" with hp_current=7, hp_max=24
And   the LLM writes a %%COMBAT%% block on round 2 with "Shalelu" hp: 24/24
When  the turn is processed
Then  session.combat_state.combatants["Shalelu"].hp_current is still 7
And   session.combat_state.combatants["Shalelu"].hp_max is still 24
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — New combatant entering after round 1 gets LLM HP
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Reinforcement arrives on round 3

```gherkin
Given session.combat_state has combatants "Shalelu" and "Goblin 1"
And   the LLM writes a %%COMBAT%% block introducing a new combatant "Goblin 2" with hp: 5/5
When  the turn is processed
Then  "Goblin 2" is added to session.combat_state.combatants with hp_current=5, hp_max=5
And   "Shalelu" and "Goblin 1" retain their backend HP values
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — HP context injected into per-turn system message
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Turn processed while combat is active

```gherkin
Given session.combat_state is set with round=2 and at least one combatant
When  _inject_context is called for the next turn
Then  the system_content contains a "[CURRENT HP]" block
And   the block lists each combatant with name, hp_current/hp_max, and status
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — %%HP%% delta applies damage
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Trap deals damage outside of an attack

```gherkin
Given session.combat_state has "Thaelion" with hp_current=22, hp_max=22
And   the LLM writes:
      %%HP%%
      - name: Thaelion · delta: -8
When  the turn is processed
Then  session.combat_state.combatants["Thaelion"].hp_current is 14
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — %%HP%% delta applies healing, clamped to hp_max
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Healing potion used

```gherkin
Given session.combat_state has "Shalelu" with hp_current=7, hp_max=24
And   the LLM writes:
      %%HP%%
      - name: Shalelu · delta: +20
When  the turn is processed
Then  session.combat_state.combatants["Shalelu"].hp_current is 24  (clamped to max)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — %%HP%% delta clamped at 0 (overkill)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Massive damage with overkill

```gherkin
Given session.combat_state has "Goblin 1" with hp_current=3, hp_max=5
And   the LLM writes:
      %%HP%%
      - name: Goblin 1 · delta: -50
When  the turn is processed
Then  session.combat_state.combatants["Goblin 1"].hp_current is 0  (not negative)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — %%HP%% for unknown combatant silently ignored
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM writes delta for a name not in combat_state

```gherkin
Given session.combat_state has only "Shalelu" and "Goblin 1"
And   the LLM writes "- name: Ghost · delta: -5" in %%HP%%
When  the turn is processed
Then  no error is raised
And   session.combat_state is unchanged
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — %%HP%% block stripped from player token stream
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Non-dev session streams a response with a %%HP%% block

```gherkin
Given dev_mode is False
And   the LLM response contains "%%NARRATIVE%%\nThe trap fires!\n\n%%HP%%\n- name: Shalelu · delta: -8\n"
When  the token stream is filtered
Then  the player sees "The trap fires!" in the chat
And   "%%HP%%", "delta:", and "name:" from the HP block are NOT in any token event
```

---

## Notes

- `%%HP%%` is a **section marker** (like `%%DELTAS%%`), not an inline tag.
  Its content is multi-line: one `- name:` line per affected combatant.
- The `delta:` field uses signed integers: `-8` for damage, `+6` or `6` for healing.
- HP clamping rules are identical to `Combatant.__post_init__`: `[0, hp_max]`.
- Name matching is **case-insensitive** to tolerate LLM capitalisation variance.
- `%%HP%%` has no effect when `session.combat_state` is `None` (silently ignored).
- Attack damage from `%%ATTACK%%` also uses `_apply_hp_deltas` — same code path.
- Related: [combat-tracker.feature](combat-tracker.feature) — visual tracker foundation
- Related: [attack-resolution.feature](attack-resolution.feature) — attack HP changes via the same delta path

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — HP-status guard: LLM cannot mark a combatant dead or unconscious while HP > 0
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM speculatively kills a combatant before damage is applied

```gherkin
Given session.combat_state has "Goblin 1" with hp_current=3, hp_max=5 (round 2+)
And   the LLM writes a %%COMBAT%% block with "Goblin 1" status: dead
When  the turn is processed
Then  the combatant's status is overridden to "active"
And   hp_current remains 3

Given session.combat_state has "Goblin 1" with hp_current=3, hp_max=5 (round 2+)
And   the LLM writes a %%COMBAT%% block with "Goblin 1" status: unconscious
When  the turn is processed
Then  the combatant's status is overridden to "active"

Given session.combat_state has "Goblin 1" with hp_current=0, hp_max=5 (round 2+)
And   the LLM writes a %%COMBAT%% block with "Goblin 1" status: dead
When  the turn is processed
Then  the combatant's status is "dead"  (HP is 0; guard allows the transition)

Given session.combat_state has "Goblin 1" with hp_current=0, hp_max=5 (round 2+)
And   the LLM writes a %%COMBAT%% block with "Goblin 1" status: unconscious
When  the turn is processed
Then  the combatant's status is "unconscious"  (HP is 0; guard allows the transition)
```

**Implementation note:** `_parse_combat_block` applies this guard inside the
`existing_state` HP-inheritance loop — after `c.hp_current` is set from the
backend, any LLM-written `status in ('dead', 'unconscious')` is overridden to
`'active'` when `c.hp_current > 0`.  The guard has no effect on round-1 blocks
(where `existing_state is None`) or on new combatants entering mid-combat
(whose HP comes from the LLM, so the guard would not be needed anyway).
