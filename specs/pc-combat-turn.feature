# FEATURE — PC Combat Action System

**ID:** pc-combat-turn
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @pc @action @turn @streaming @parsing

---

## Story

> As a **player**,
> when it is my character's turn in combat and I type an action (e.g. "I attack the goblin
> with my sword"), I want the backend to interpret my intent, resolve the mechanics from my
> character profile, and guide me through the dice rolls — so I never have to worry about
> whether the LLM invented the wrong bonus or forgot to queue my attack.

The player types free text. The backend extracts weapon and target from the text (with a
robust fallback), queues the attack from the PC's actual profile data, activates the dice
tray, and — after all rolls are complete — calls the LLM with the fully-resolved outcome
already known. The LLM narrates what happened; the backend handles every number.

---

## Background

- Given a session is in combat (`session.combat_state` is not None)
- And `currentCombatantName` is a PC (present in `session.pc_profiles`)
- And `session.pc_profiles[pc_name]["weapons"]` contains the PC's weapon list

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `_extract_pc_combat_intent` resolves weapon from text
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given actor "Ani" has weapons: [longsword (+4, 1d8+2, melee), dagger (+4, 1d4+2, melee)]

When  player types "I swing my longsword at the goblin"
Then  intent["weapon_name"] == "longsword"
And   intent["weapon_atk"]  == "+4"
And   intent["weapon_dmg"]  == "1d8+2"

When  player types "I use my sword"
Then  intent["weapon_name"] == "longsword"  (substring match)

When  player types "I attack with my halberd"  (not in profile)
Then  intent["weapon_name"] == "longsword"  (fallback to first/equipped weapon)
And   intent["action_type"] == "attack"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — `_extract_pc_combat_intent` resolves target from text
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given combat_state has active enemies: ["Goblin Warrior 1", "Goblin Warchanter"]

When  player types "at Goblin Warrior 1"
Then  intent["target"] == "Goblin Warrior 1"

When  player types "at the goblin"
Then  intent["target"] == "Goblin Warrior 1"  (first active enemy matching "goblin")

When  player types "I attack!"
Then  intent["target"] is any active enemy  (random fallback)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Fallback: vague or unparseable input defaults to standard attack
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given player types anything that cannot be parsed into a clear weapon + target
Then  intent["action_type"] == "attack"
And   intent["weapon_name"] == first weapon in pc_profiles[actor]["weapons"]
And   intent["target"]      == a random active enemy combatant
```

> **Design principle:** player's fault if they were too vague. No confirmation prompt.
> The fallback fires silently and the dice tray activates with the best guess.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — `stream_pc_turn` queues attack from PC profile, not LLM output
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given intent["weapon_atk"] == "+4" and intent["weapon_dmg"] == "1d8+2"
When  stream_pc_turn processes the turn
Then  session.attack_queue contains a PendingAttack with:
        bonus        == 4         (parsed from "+4")
        damage_expr  == "1d8+2"  (from profile)
        attacker     == actor name
        target       == resolved target
        is_pc        == True

And   the player's original text is appended to session.messages as a user message
And   session._pending_pc_narration is populated with the intent dict
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — `stream_pc_turn` emits attack_request SSE immediately
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
When  stream_pc_turn is called
Then  an "attack_request" SSE event is emitted with:
        attacker, target, bonus, ac, damage_expr, attack_type
And   a "done" SSE event follows
And   NO LLM call is made at this stage
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — `_build_pc_turn_system` includes actor, target, roll outcome, context
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given result == {roll: 12, bonus: 4, total: 16, ac: 16, hit: True, damage_total: 7, ...}
And   actor "Ani" has hp 8/11, target "Goblin Warrior 1" has hp 2/5

When  _build_pc_turn_system(session, intent, result) is called
Then  the system message contains "[PC TURN BRIEFING]"
And   contains "Actor: Ani"
And   contains "Target: Goblin Warrior 1"
And   contains "To hit:" and "HIT" (or "MISS" for a miss)
And   contains "Damage: 7"  (only on hit)
And   contains HP descriptors: "badly wounded" for <33% HP
And   lists all active PCs with HP
And   lists all active enemies with HP descriptor
And   does NOT contain raw weapon stats like "+4 (1d8+2)"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — `_stream_pc_turn_narration` uses known outcome; LLM writes %%NARRATIVE%% only
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session._pending_pc_narration is set (stream_pc_turn was called)
And   all PC dice have been resolved (attack_queue is empty)

When  stream_resume_combat is called
Then  it detects _pending_pc_narration and delegates to _stream_pc_turn_narration
And   _stream_pc_turn_narration calls _call_blocking with:
        system = _PC_TURN_SYSTEM + [PC TURN BRIEFING] (outcome already known)
        user   = player's original text
And   the LLM writes %%NARRATIVE%% only
And   session._pending_pc_narration is cleared after use

Given the LLM mistakenly writes %%ACTION%%, %%COMBAT%%, %%ATTACK%%, etc.
Then  those sections are not streamed to the player (only %%NARRATIVE%% is extracted)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — action_card emitted before narrative in PC turn narration
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
When  _stream_pc_turn_narration processes a hit
Then  "action_card" SSE is emitted before the "token" SSE
And   action_card carries: attacker, target, roll, bonus, total, ac, hit, damage_total

When  _stream_pc_turn_narration processes a miss
Then  "action_card" SSE is emitted with hit: false, damage_total: 0
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — advance_combat_turn fires automatically after PC narration
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
When  _stream_pc_turn_narration completes
Then  advance_combat_turn(session) is called
And   the final "combat_update" SSE carries the new current_actor
And   no manual "Next Turn" click is required
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Frontend routes to /pc_turn when it is a PC's combat turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given combat is active
And   currentCombatantName is in characterMap (it is a PC's turn)
When  player submits input via the Send button
Then  App.tsx calls pcTurn(session.id, input)  (POST /pc_turn)
And   NOT sendTurn(session.id, input)  (POST /turn)

Given combat is active and currentCombatantName is an enemy
Then  App.tsx still calls sendTurn (no routing change for enemy turns)

Given combat is NOT active
Then  App.tsx calls sendTurn regardless of any character selection
```

---

## Out of Scope

- "I charge" / movement actions — attack_type=attack fallback fires; full charge mechanic (move + attack + bonus) deferred to a future tier
- Full attack (multiple iterative attacks from high BAB) — single attack only for now
- Ability/spell use — `use_ability` action type extracted but not mechanically resolved; narration only
- Combat maneuvers (trip, disarm, grapple) — fall back to standard attack
- Confirmation prompt for ambiguous input — player's fault; fallback fires

---

## Notes

- `_extract_pc_combat_intent(text, session) → dict` — pure function; no LLM call; uses substring matching against `pc_profiles[actor]["weapons"]` and `combat_state.combatants`
- `_PC_TURN_SYSTEM` — GM identity + %%NARRATIVE%% only instruction; does NOT include `%%HP%%` in the prohibition list (healing spells may need it in future)
- `_build_pc_turn_system(session, intent, result) → str` — system = `_PC_TURN_SYSTEM` + `[PC TURN BRIEFING]` with actor/target/roll/combat snapshot. Does NOT pass raw weapon stats to LLM.
- `session._pending_pc_narration: Optional[dict]` — set by `stream_pc_turn`, consumed by `stream_resume_combat` → `_stream_pc_turn_narration`. Cleared after use.
- `pc_profiles[name]["weapons"]` — populated by `_build_pc_profiles` from `player_*.json["weapons"]` array. First weapon = equipped (primary).
- HP descriptor: >66% = "healthy", 33–66% = "wounded", <33% = "badly wounded", 0 = "dying/unconscious"
- Tests: `tests/test_pc_combat_turn.py`; Vitest: `App.pc-combat-turn.test.tsx`; Playwright: `pc-combat-turn.spec.ts`
