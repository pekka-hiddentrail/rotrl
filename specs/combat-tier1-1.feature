# FEATURE — Combat Tier 1.1: HP Authority Shift

**ID:** combat-tier1-1
**Status:** Approved
**Area:** Backend
**Tags:** @combat @hp @session @parsing

---

## Story

> As the **game system**,
> I want the backend to own HP values for all combatants,
> so that LLM arithmetic errors and round-to-round drift cannot corrupt the
> combat tracker, and so Tier 1.5 attack resolution has a reliable HP store
> to write into.

In Tier 1, the LLM writes `hp: cur/max` every turn for every combatant. In
practice the model miscounts damage, forgets a hit from two rounds ago, or
silently resets a dying goblin to full health. Tier 1.1 fixes this: the LLM
initialises HP when a combatant first appears, and the backend persists those
values. The LLM never computes HP again — it reads current values from the
injected context and narrates accordingly.

Non-attack HP changes (traps, poison, healing) are handled by a new `%%HP%%`
delta block that the LLM writes instead of rewriting full HP values.

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
- Related: [combat-tracker.feature](combat-tracker.feature) — Tier 1 foundation
- Related: TODO.md CB1.1-1 through CB1.1-4
