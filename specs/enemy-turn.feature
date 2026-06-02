# FEATURE — Enemy Turn (Tier 1.7)

**ID:** enemy-turn
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @combat @enemy @action @session @streaming @layout

---

## Story

> As the **player**,
> I want to click "Enemy Turn" to trigger each enemy's action,
> so that the GM engine resolves it using authoritative backend data — dice rolled
> server-side, no LLM-invented stats, narrative streamed as flavor text only.

The backend asks the LLM one focused question per enemy: *"What does X do?"* The LLM
returns a structured `%%ACTION%%` block (decision keywords) plus one sentence of narrative.
The backend resolves the decision using its own data from `session.combat_state`. The player
sees only the narrative; all mechanics are invisible.

---

## Background

- Given a session is active
- And `session.combat_state` is a valid `CombatState` with round ≥ 1
- And the current actor (`session.combat_state.current_actor`) is an enemy (not a PC)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `_parse_action_block` parses well-formed %%ACTION%% text
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a text string containing:
  %%ACTION%%
  combatant: Goblin Warchanter
  action_type: standard
  action: attack
  weapon: shortbow
  target: Yanyeeku

When  _parse_action_block(text) is called
Then  it returns {
    "combatant": "Goblin Warchanter",
    "action_type": "standard",
    "action": "attack",
    "weapon": "shortbow",
    "target": "Yanyeeku"
  }

Given a text with action: use_ability and ability: inspire_courage
Then  the returned dict contains "action": "use_ability" and "ability": "inspire_courage"

Given a text with action: move_toward and target: Thaelion
Then  the returned dict contains "action": "move_toward" and "target": "Thaelion"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — `_parse_action_block` handles malformed or absent blocks
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given text with no %%ACTION%% marker
When  _parse_action_block(text) is called
Then  it returns None

Given text with %%ACTION%% but missing required "action" field
Then  it returns None (malformed block — action field is mandatory)

Given text with %%ACTION%% and an unrecognised action value (e.g. "action: teleport")
Then  it returns a dict with "action": "delay" (unknown actions default to delay)

Given empty string or None
Then  it returns None
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — `_build_enemy_turn_query` contains the acting combatant's situation
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state has:
  - Goblin Warchanter: 6/8 HP, active, no conditions — the acting combatant
  - Goblin 1: 3/5 HP, active — ally
  - Thaelion: 18/22 HP, active — PC
  - Yanyeeku: 4/7 HP, active — PC

When  _build_enemy_turn_query(session, "Goblin Warchanter") is called
Then  the output contains "Actor: Goblin Warchanter, active"
And   the output contains "Equipped weapon" or "Available weapon" lines
And   allies are listed by name and status only (no HP — enemies don't track each other's HP)
And   PCs are listed with HP ("Thaelion: hp 18/22") so the enemy knows who is wounded
And   the output contains "Standard:" and "Full-round:" action instructions
And   the output contains the %%ACTION%% format specification
And   the output does NOT contain "bonus:" or "damage:" fields (backend owns mechanics)
And   the output does NOT contain "%%END%%" or "reason:" fields
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — `_build_enemy_turn_query` adjusts action budget for conditions
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the acting combatant has condition: "nauseated"
When  _build_enemy_turn_query is called
Then  the action budget states "move action only" (nauseated restricts to move only)

Given the acting combatant has condition: "staggered"
When  _build_enemy_turn_query is called
Then  the action budget states "one standard OR one move action" (staggered)

Given the acting combatant has condition: "paralyzed"
When  _build_enemy_turn_query is called
Then  the action budget states "cannot act" and instructs: write action: delay
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — `_build_enemy_turn_query` does NOT include enemy AC values
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the acting combatant has ac: 14
And   a PC has ac: 16
When  _build_enemy_turn_query is called
Then  the query does NOT contain "ac:" or "AC:" for any combatant
And   the query does NOT contain "14" or "16" as standalone AC references
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — `stream_enemy_turn` uses _ENEMY_TURN_SYSTEM, not _build_combat_system_prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given stream_enemy_turn(session, "Goblin 1") is called
Then  the LLM is called with _ENEMY_TURN_SYSTEM as the system message
And   _ENEMY_TURN_SYSTEM is much shorter than _build_combat_system_prompt output
And   session.messages (chat history) is NOT included in the LLM payload
And   the payload contains exactly one user message: the enemy turn query
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — stream_enemy_turn emits token SSE for the narrative sentence
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the LLM response contains:
  %%NARRATIVE%%
  The goblin looses an arrow at the sorcerer.
  %%ACTION%%
  combatant: Goblin 1
  action_type: standard
  action: attack
  target: Yanyeeku

When  stream_enemy_turn processes the response
Then  a "token" SSE event is emitted containing the narrative sentence
And   the %%ACTION%% block text is NOT included in the streamed tokens
And   the %%NARRATIVE%% marker itself is NOT included in the streamed tokens
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — stream_enemy_turn with action:attack resolves via _resolve_npc_attack
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the %%ACTION%% block has action: attack, target: Yanyeeku
And   session.combat_state has Yanyeeku with ac: 12
When  stream_enemy_turn processes the action
Then  _resolve_npc_attack is called with target="Yanyeeku"
And   the target's AC (12) is used for the hit/miss calculation
And   an "attack_result" SSE event is emitted with hit, roll, total, damage_total
And   session.combat_state HP is updated via _apply_hp_deltas if the attack hit
And   a "combat_update" SSE event is emitted reflecting the new HP
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — stream_enemy_turn with action:delay emits no attack_result
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given the %%ACTION%% block has action: delay
When  stream_enemy_turn processes the action
Then  no "attack_result" SSE event is emitted
And   session.combat_state HP values are unchanged
And   a "combat_update" SSE event is still emitted (round/status unchanged)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — POST /sessions/{id}/enemy_turn endpoint
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a valid session with active combat and no pending PC attacks
When  POST /sessions/{id}/enemy_turn is called
Then  it returns 200 and streams SSE events (token, attack_result, combat_update, done)

Given session.attack_queue is non-empty (PC attack dice still pending)
When  POST /sessions/{id}/enemy_turn is called
Then  it returns 409 Conflict

Given session.combat_state is None
When  POST /sessions/{id}/enemy_turn is called
Then  it returns 409 Conflict

Given an unknown session id
When  POST /sessions/{id}/enemy_turn is called
Then  it returns 404 Not Found
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — POST /sessions/{id}/close_combat streams closure narrative then clears
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a valid session with active combat
When  POST /sessions/{id}/close_combat is called
Then  the LLM is called with the current combat snapshot (enemy HP/status + party HP/status)
And   the instruction is: write 1–2 paragraphs narrating how it ends; no %%COMBAT%%/%%ACTION%%
And   the narrative streams as "token" SSE events visible in the chat window
And   after the stream completes, session.combat_state is set to None
And   state.json is updated (mode: social, combatants: [])
And   a final "done" SSE event is emitted

Given session.combat_state is None
When  POST /sessions/{id}/close_combat is called
Then  it returns 409 Conflict

Given the LLM call fails (timeout or provider error)
When  POST /sessions/{id}/close_combat is called
Then  it falls back to silent clear (session.combat_state = None, state.json updated)
And   the response still completes with a "done" SSE event (no error surfaced to player)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — _build_combat_close_directive includes combat snapshot
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.combat_state.round = 4
And   enemies: Goblin Warchanter (2/8 HP, active), Goblin 1 (0/5 HP, unconscious)
And   PCs: Thaelion (18/22 HP, active), Yanyeeku (4/7 HP, active)

When  _build_combat_close_directive(session) is called
Then  the output contains "round 4"
And   the output contains "Goblin Warchanter" with "2/8" HP
And   the output contains "Goblin 1" as unconscious
And   the output contains both PC names and their HP
And   the output instructs "do NOT write %%COMBAT%%, %%ATTACK%%, %%ACTION%%"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — CombatPanel "Enemy Turn" button (Tier 1.7 UI)
<!-- ─────────────────────────────────────────────────────────────────────── -->

*(See also combat-tracker.feature AC-016)*

```gherkin
Given CombatPanel renders with a valid combatState and onEnemyTurn callback
Then  "Enemy Turn" button is present and enabled
And   clicking it calls onEnemyTurn

Given the disabled prop is true
Then  "Enemy Turn" button is disabled

Given attackPhase is not null (App-level state: PC attack pending)
Then  "Enemy Turn" button receives disabled=true so it cannot be clicked
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — App.tsx enemy turn wiring
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given a booted session with active combat
When  the user clicks "Enemy Turn"
Then  App.tsx calls POST /sessions/{id}/enemy_turn
And   enemyTurnStreaming is set to true while the stream is in progress
And   "token" events from the stream appear in the chat window
And   "attack_result" events update the attack log (same as PC attack results)
And   "combat_update" events update the CombatPanel HP display
And   enemyTurnStreaming is set to false when "done" is received

Given POST /enemy_turn returns 409 (attack pending)
Then  an error message is shown and enemyTurnStreaming stays false

When  the user clicks "End Combat" (which calls POST /close_combat)
Then  App.tsx calls POST /sessions/{id}/close_combat
And   the closing narrative appears in the chat window
And   setCombatState(null) is called after the stream completes
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-015 — stream_resume_combat clears stale attack_queue before LLM call
<!-- ─────────────────────────────────────────────────────────────────────── -->

```gherkin
Given session.attack_queue has one stale PendingAttack entry from a previous turn
When  stream_resume_combat(session) is called
Then  session.attack_queue is cleared before the LLM call runs
And   a log entry notes the number of stale entries purged

Given session.attack_queue is already empty
When  stream_resume_combat(session) is called
Then  no log entry is written for the queue (nothing to clear)

Given doResumeCombat receives an attack_request event during the resume SSE stream
When  the event arrives in the for-await loop
Then  setAttackPhaseSync is called with the attack details
And   the Enemy Turn button becomes disabled (attackPhase is now non-null)
And   a subsequent POST /enemy_turn call returns 200 (not 409) once attacks are resolved
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-016 — _build_enemy_turn_query includes actor's attack names by type (CB1.9-1)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Actor has a known attack profile in pending_combatants

```gherkin
Given session.pending_combatants["goblin warchanter"]["attacks"] ==
      {"melee": ["bite"], "ranged": ["shortbow"]}
When  _build_enemy_turn_query(session, "Goblin Warchanter") is called
Then  the output contains "Melee attacks: bite"
And   the output contains "Ranged attacks: shortbow"
And   the output does NOT contain "+5" or "1d4"  (mechanics stripped — LLM sees names only)
And   no attack names from other combatants appear in the actor's section
```

**Scenario:** No profile exists for the actor

```gherkin
Given session.pending_combatants is empty
When  _build_enemy_turn_query is called for any combatant
Then  no "Melee attacks" or "Ranged attacks" line appears in the output
And   the query is otherwise identical to the profile-absent case
```

> **Design note:** The LLM sees weapon names only — no bonuses, no damage dice. The backend
> owns the mechanics and looks them up from `pending_combatants` when resolving the attack.
> The split into `melee` / `ranged` categories gives the LLM enough tactical context to make
> a sensible decision (does the target need to be adjacent?).

---

## Out of Scope

- `_execute_action` full dispatch table (Tier 2 SA-6) — actions beyond `attack` and `delay`
  are logged but not mechanically resolved in Tier 1.7
- PC `attack_request` during enemy turn — enemy attacks are always auto-resolved server-side
- Multi-combatant enemy turn loop — CB1.7-3 endpoint resolves one combatant per call;
  the UI calls it per-combatant by advancing with `combat/advance_turn` between enemy actions

---

## Notes

- `_ENEMY_TURN_SYSTEM` module-level constant (~4 lines): instructs the LLM to return exactly
  `%%NARRATIVE%%` (one sentence) + `%%ACTION%%` block. No other sections permitted.
- `_build_enemy_turn_query(session, combatant_name) → str` — builds the tactical briefing.
  **Does not use** `_build_combat_system_prompt`; the query is the user message, `_ENEMY_TURN_SYSTEM` is the system message. Chat history is NOT injected.
- `_parse_action_block(text) → Optional[dict]` — same field-separator pattern (`·`) as
  `_parse_combatant_line`. `%%ACTION%%` added to `_END_MARKERS` (stripped from player stream).
  `%%ACTION%%` NOT added to `_HAS_SECTION_MARKERS_RE` (same pattern as `%%ATTACK%%`).
- `stream_enemy_turn(session, combatant_name)` — makes a **blocking LLM call** (no streaming
  infrastructure reuse; response is short ~150 tokens). Collects full response, parses sections,
  yields SSE events. Uses `_call_blocking` provider dispatch.
- `_get_attack_for_enemy(session, attacker_name, weapon_name) → dict` — returns
  `{"bonus": N, "damage_expr": "NdN+M", "type": "melee|ranged"}` from `combatant.attacks`
  when available; falls back to `{"bonus": 0, "damage_expr": "1d4", "type": "melee"}`.
- `_extract_attack_names(raw: str) → list[str]` (CB1.9-1) — strips bonus and damage from a
  single weapon string. `"shortbow +5 (1d4+1)"` → `["shortbow"]`. Splits on comma first for
  multi-weapon strings.
- **`pending_combatants[name]["attacks"]` shape (CB1.9-1):** `{"melee": ["bite"], "ranged": ["shortbow"]}`.
  Parsed by `_parse_event_combatants` from the `melee` and `ranged` columns of the
  `## Combatants` table. Names only — bonuses and damage dice stripped at parse time.
- `_build_combat_close_directive(session) → str` — injects the combat snapshot without using
  `_build_combat_system_prompt`. Short directive (~10 lines).
- `stream_close_combat(session)` — blocking LLM call, streams narrative as tokens, clears
  combat state, writes state.json. Fallback: clear combat state silently on error.
- Tests: `tests/test_enemy_turn.py`; Vitest: `CombatPanelEnemyTurn.test.tsx`
- **B-C07 fix (2026-05-31):** `stream_resume_combat` clears `session.attack_queue` defensively
  before the LLM call. When the LLM writes `%%ATTACK%%` blocks inside the resume narration, PC
  attacks were added to the backend queue but the frontend's `doResumeCombat` had no
  `attack_request` handler — `attackPhase` stayed null while the queue was non-empty, causing
  the next enemy-turn call to return 409. Fixed in two places:
  1. Backend: `stream_resume_combat` clears stale entries before the LLM call.
  2. Frontend: `doResumeCombat` in `App.tsx` now handles `attack_request` and `attack_result`
     events so new attacks are tracked and the Enemy Turn button is correctly disabled.
  Regression tests: `TestResumeCombatClearsStaleQueue`, `TestEnemyTurnStaleQueue` in
  `test_enemy_turn.py`; B-C07 describe block in `App.test.tsx`.
