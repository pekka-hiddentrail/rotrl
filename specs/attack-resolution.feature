# FEATURE — Attack Resolution

**ID:** attack-resolution
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @attack @dice @session @streaming @parsing

---

## Story

> As the **player**,
> I want to roll dice for my character's attacks in real time,
> so that the outcome is mechanical and transparent rather than narrated by the AI.

The LLM writes `%%ATTACK%%` blocks declaring what attacks occur this round (attacker,
target, bonus, damage expression). The backend splits them: enemy attacks are
auto-resolved immediately; PC attacks queue for the player to roll. Once all dice are
settled the backend calls the LLM once more to narrate outcomes and update `%%COMBAT%%`.

The LLM never rolls dice or invents outcomes — it only narrates what the resolved
dice determined.

---

## Background

- Given a session is active
- And `session.combat_state` is a valid `CombatState` with round ≥ 1
- And PC names are known via `session.pc_profiles`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — %%ATTACK%% block parsed into attack list
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the LLM response contains a %%ATTACK%% section with ≥ 1 attack lines
When  the turn is processed
Then  each valid line is parsed into an attack dict with attacker, target, bonus, damage, type
And   lines missing attacker or target are silently skipped
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — NPC attacks auto-resolved, PC attacks queued
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the %%ATTACK%% block contains one NPC attack and one PC attack
When  the turn is processed
Then  the NPC attack is auto-resolved (d20 + bonus vs AC) immediately
And   an attack_result SSE event is emitted for the NPC attack
And   the PC attack is added to session.attack_queue
And   an attack_request SSE event is emitted for the PC attack
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — attack_request drives to-hit roll
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.attack_queue has one PC attack pending
When  POST /resolve_attack_roll { rolled: 15 } is called and bonus + 15 ≥ target AC
Then  the response contains { hit: true, damage_expr, queue_remaining }
And   the attack remains in attack_queue (awaiting damage roll)

When  POST /resolve_attack_roll { rolled: 2 } is called and bonus + 2 < target AC
Then  the response contains { hit: false, queue_remaining: 0 }
And   the miss is added to session.attack_results
And   session.attack_queue is now empty
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Damage roll applied on hit
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the PC attack in attack_queue has hit = True
When  POST /resolve_damage_roll { rolls: [4, 3], total: 9 } is called
Then  the hit + damage is added to session.attack_results
And   session.combat_state HP for the target is reduced by 9
And   session.attack_queue is now empty
And   the response contains { damage_total: 9, queue_remaining: 0 }
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — resume_combat injects results and calls LLM
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.attack_queue is empty
And   session.attack_results has ≥ 1 resolved attack
When  POST /resume_combat is called
Then  a "[ATTACK RESULTS — round N]" message is appended to session.messages
And   session.attack_results is cleared
And   the LLM is called and a token SSE stream is returned
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — resume_combat rejected if attack_queue not empty
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.attack_queue still has PC attacks pending
When  POST /resume_combat is called
Then  the response is 409 Conflict
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — NPC hit reduces target HP immediately
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a combatant "Shalelu" with hp_current=18 in session.combat_state
And   an NPC attack hits Shalelu for 5 damage (damage_total = 5)
When  the turn is processed
Then  session.combat_state.combatants["Shalelu"].hp_current == 13
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — %%ATTACK%% stripped from player token stream
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given dev_mode is False
And   the LLM response contains "%%NARRATIVE%%\nFight!\n\n%%ATTACK%%\n- attacker: ..."
When  the token stream is filtered
Then  the player sees "Fight!" in the chat
And   "%%ATTACK%%", "attacker:", "target:", "bonus:" are NOT in any token event
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Multiple PC attacks processed in queue order
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the %%ATTACK%% block has two PC attack lines in order: Thaelion then Yanyeeku
When  the turn is processed
Then  session.attack_queue contains [Thaelion attack, Yanyeeku attack] in that order
And   attack_request SSE is emitted for Thaelion's attack only
When  Thaelion's attack is resolved
Then  next_attack in the response describes Yanyeeku's attack
```

---

## Notes

- `%%ATTACK%%` is a **section marker** (like `%%COMBAT%%`). Multi-line; one `-` line per attack.
- Attack lines use the same `·` (U+00B7) / `•` (U+2022) separator as `%%COMBAT%%` combatant lines.
- PC detection: attacker name matched case-insensitively against `session.pc_profiles` (lowercase dict
  built at boot from `ui/public/data/player_*.json`). Non-matching names → NPC, auto-resolved.
- `%%ATTACK%%` added to `_END_MARKERS` (stripped from player stream).
  NOT added to `_HAS_SECTION_MARKERS_RE` — same reason as `%%COMBAT%%` and `%%HP%%`.
- NPC HP changes use `_apply_hp_deltas` — same code path as `%%HP%%` deltas.
- Frontend: `attackPhase` state drives DicePanel banners (to-hit → damage); `attackLog` shows
  results in DicePanel history. Auto-calls `/resume_combat` when `queue_remaining === 0`.
- Related: [combat-tracker.feature](combat-tracker.feature) — initiative tracker the LLM updates after resolution
- Related: [combat-hp.feature](combat-hp.feature) — HP authority that attack damage writes into
- Related: [dice-panel.feature](dice-panel.feature) — DicePanel skill-check flow (unchanged by this feature)
