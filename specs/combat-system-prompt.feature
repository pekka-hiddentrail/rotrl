# FEATURE — Combat System Prompt (Tier 1.6)

**ID:** combat-system-prompt
**Status:** Approved
**Area:** Backend
**Tags:** @combat @prompt @injection @per-turn @token

---

## Story

> As the **GM engine**,
> I want a dedicated combat system prompt that replaces the narrative prompt when combat is active,
> so that the LLM receives only mechanically-relevant context and is explicitly prohibited from
> inventing dice outcomes, while spending fewer tokens on unused narrative guidance.

The current `_build_slim_system_prompt` is a general-purpose narrative prompt with combat sections
bolted on. In combat the priorities flip: mechanical accuracy over tone, no NPC knowledge prose,
no skill guidance, no `%%GENERATE%%`/`%%DELTAS%%`/`%%ROLL%%` sections. This feature introduces
`_build_combat_system_prompt` and a combat branch in `_inject_context` that activates whenever
`session.combat_state is not None`.

---

## Background

- Given a session has been booted
- And either `session.combat_state` is set (round ≥ 1), OR active events contain `%%COMBAT%%`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `_build_combat_system_prompt` produces no narrative section specs
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given _build_combat_system_prompt(session) is called
Then  the output does NOT contain "%%GENERATE%%"
And   the output does NOT contain "%%DELTAS%%"
And   the output does NOT contain "%%ROLL%%"
And   the output DOES contain "%%NARRATIVE%%"
And   the output DOES contain "%%COMBAT%%"
And   the output DOES contain "%%ATTACK%%"
And   the output DOES contain "%%HP%%"
And   the output DOES contain "FORBIDDEN" or an equivalent prohibition on those sections
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Combat prompt is significantly shorter than narrative prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given _build_combat_system_prompt(session) is called
And   _build_slim_system_prompt(session.session_number) is called with the same session
Then  len(_build_combat_system_prompt(session)) <= 0.60 * len(_build_slim_system_prompt(...))
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — `_inject_context` in combat mode uses the combat prompt as base
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is not None (round >= 1)
When  _inject_context(session) is called
Then  the returned system_content does NOT start with session.system_prompt
And   system_content starts with the output of _build_combat_system_prompt(session)
And   system_content does NOT contain the _FORMAT_EXAMPLE block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — `_inject_context` in combat mode skips NPC and skill detection
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is not None
When  _inject_context(session) is called
Then  NpcIndex.detect() is NOT called
And   SkillIndex.detect() is NOT called
And   LocationIndex.detect() is NOT called
And   context_info["npc"] is None
And   context_info["skill"] is None
And   context_info["location"] is None
And   context_info["loc"] is None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — `[INITIATIVE ORDER]` injected sorted descending, current actor marked
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state has combatants sorted by initiative: Shalelu 14, Thaelion 10, Goblin 5
When  _inject_context(session) is called in combat mode
Then  system_content contains "[INITIATIVE ORDER"
And   the order lists Shalelu before Thaelion before Goblin
And   Shalelu's line is marked with "→ " (highest active initiative = current actor)
And   other combatants are not marked
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Current actor is the highest-initiative *active* combatant
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given Shalelu (init 14) has status "unconscious"
And   Thaelion (init 10) has status "active"
And   Goblin (init 5) has status "active"
When  _inject_context assembles the [INITIATIVE ORDER] block
Then  Thaelion's line is marked with "→ " (highest active, not highest overall)
And   Shalelu's line is NOT marked
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — `[CURRENT HP]` block always injected in combat mode
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is not None
When  _inject_context(session) is called in combat mode
Then  system_content contains "[CURRENT HP]"
And   each combatant's name, hp_current/hp_max, and status appear in the block
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — `[PC COMBAT STATS]` injected for all PCs with mechanical profiles
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.pc_profiles contains entries for Thaelion and Yanyeeku
When  _inject_context(session) is called in combat mode
Then  system_content contains "PC Stats — Thaelion"
And   system_content contains "PC Stats — Yanyeeku"
And   each block includes HP, AC, saves, and initiative values from the mechanical profile
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — `[ACTIVE CONDITIONS]` only present when conditions are non-empty
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given all combatants have empty conditions lists
When  _inject_context(session) is called in combat mode
Then  system_content does NOT contain "[ACTIVE CONDITIONS]"

Given Goblin 1 has conditions: ["prone", "shaken"]
When  _inject_context(session) is called in combat mode
Then  system_content contains "[ACTIVE CONDITIONS]"
And   the block lists "Goblin 1" with "prone" and "shaken"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — `_COMBAT_SECTION_SPECS` used in place of narrative section specs
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is not None
When  _inject_context(session) is called in combat mode
Then  system_content contains "COMBAT MODE" (from _COMBAT_SECTION_SPECS)
And   system_content does NOT contain _NARRATIVE_SPEC (narrative-only wording)
And   system_content does NOT contain _GENERATE_SPEC
And   system_content does NOT contain _DELTAS_SPEC
And   system_content does NOT contain _ROLL_SPEC
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Normal narrative path is unchanged when combat is inactive
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is None
When  _inject_context(session) is called
Then  system_content starts with session.system_prompt
And   the narrative injection pipeline runs normally (NPC/skill/location detection active)
And   [INITIATIVE ORDER], [CURRENT HP], [PC COMBAT STATS] do NOT appear in system_content
And   _COMBAT_SECTION_SPECS does NOT appear in system_content
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Combat rules lookup still runs in combat mode
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is not None
And   the player input contains a combat rules trigger (e.g. "attacks of opportunity")
When  _inject_context(session) is called in combat mode
Then  CombatRulesIndex.detect() IS called
And   the matching rule content is appended to system_content
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — Active events still injected in combat mode
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is not None
And   session.active_events contains one event with id "goblin_attack_starts"
When  _inject_context(session) is called in combat mode
Then  system_content contains "goblin_attack_starts"
And   context_info["active_events"] includes "goblin_attack_starts"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — `_COMBAT_SECTION_SPECS` constant structure
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the _COMBAT_SECTION_SPECS constant
Then  it contains "COMBAT MODE"
And   it references %%NARRATIVE%%, %%COMBAT%%, %%ATTACK%%, %%HP%%
And   it does NOT reference %%GENERATE%%, %%DELTAS%%, %%ROLL%%
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-015 — Pre-combat branch fires when events require `%%COMBAT%%`
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is None
And   session.active_events contains an event whose content includes "%%COMBAT%%"
When  _inject_context(session) is called
Then  system_content starts with _build_combat_system_prompt (not session.system_prompt)
And   NPC/skill/location detection is skipped
And   the format example is not injected
And   narrative section specs (%%GENERATE%%, %%DELTAS%%, etc.) are absent
And   [COMBAT START FORMAT] block with _COMBAT_SPEC_ROUND1 and party roster is present
And   [PC COMBAT STATS] is present (LLM needs HP/AC/init to write round 1 %%COMBAT%%)
And   [INITIATIVE ORDER] is NOT present (no combatants yet)
And   [CURRENT HP] is NOT present (no combatants yet)
And   the active event content is injected
And   context_info["npc"] is None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-016 — Non-combat events still use the narrative path
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state is None
And   session.active_events contains an event whose content does NOT include "%%COMBAT%%"
When  _inject_context(session) is called
Then  system_content starts with session.system_prompt (narrative path)
And   [COMBAT START FORMAT] with round-1 spec is still appended as a hint
And   NPC/skill/location detection runs normally
```

---

## Out of Scope

- Enemy turn directive (`_ENEMY_TURN_DIRECTIVE`) — Tier 1.7
- Close combat narrative (`POST /close_combat`) — Tier 1.7
- Condition mechanical effects — Tier 1.8
- Initiative server-side rolling — Tier 1.9

---

## Notes

- `_build_combat_system_prompt(session: GameSession) -> str` in `api/session_manager.py`
- `_COMBAT_SECTION_SPECS` module-level constant in `api/session_manager.py`
- `_inject_context` branches at the top when `session.combat_state is not None` **OR** any active event's content contains `"%%COMBAT%%"` (pre-combat detection). The existing narrative path is a fallthrough with no changes.
- Pre-combat sub-branch: uses combat base prompt but injects `_COMBAT_SPEC_ROUND1` + party roster instead of initiative/HP/conditions; `[PC COMBAT STATS]` still injected so LLM has HP/AC/init to write the first %%COMBAT%% block.
- The `_FORMAT_EXAMPLE` injection guard (`len(session.messages) == 1`) is also bypassed in combat mode
- History trimming and Groq char-cap still apply in combat mode
- Active events TTL decrement still runs in combat mode (unchanged)
- `CombatRulesIndex` lookup still runs when combat is active (unchanged)
- Token target: combat-mode `system_content` ≤ 60% of narrative-mode `system_content` at equivalent session state
