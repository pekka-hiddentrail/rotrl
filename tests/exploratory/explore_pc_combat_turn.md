# Exploratory Tests — PC Combat Turn

Spec: specs/pc-combat-turn.feature

**What automated tests cover:** `_extract_pc_combat_intent` weapon+target extraction and
fallbacks (AC-001–003), `_build_pc_turn_system` briefing format with HP descriptors (AC-006),
`stream_pc_turn` attack queue from profile + attack_request SSE + narration flag (AC-004/005),
`_stream_pc_turn_narration` action_card before token + advance turn (AC-007–009),
frontend routing to `/pc_turn` vs `/turn` (AC-010).

**What these chains verify:** the live experience of playing a PC combat turn — the player
types naturally, the dice tray activates with real profile data, the action card summarises
the outcome, and the narrative reads naturally because the LLM knows the result.

**Pre-requisites:** `python dev.py --skip-tests` — stack running. Trigger combat first
(get a `%%COMBAT%%` block with goblins). Roll initiatives. Advance to a PC's turn.

---

## Chain A — Weapon match: exact name  <!-- AC-001 -->

1. It is Ani's turn (InputBar shows her portrait + "Speaking as Ani").
2. Type: `"I strike the goblin with my morningstar!"`
3. ✔ Dice tray shows attack banner: **⚔ Ani → Goblin Warrior 1 · melee · bonus +4**
4. Open API Logs → find the most recent non-`/turn` call.
5. ✔ No API log entry for this message (no LLM call was made for intent extraction).
6. ✔ The attack bonus (+4) and damage (1d8+2) match Ani's morningstar profile in `player_*.json`.

---

## Chain B — Weapon match: substring  <!-- AC-001 -->

1. It is Ani's turn.
2. Type: `"I use my star weapon"` or `"I hit with my morning weapon"` (partial match).
3. ✔ Dice tray still activates — morningstar matched by substring.
4. ✔ Banner shows the correct bonus from profile (not LLM-invented).

---

## Chain C — Fallback: vague input  <!-- AC-003 -->

1. Type: `"I attack!"` (no weapon or target specified).
2. ✔ Dice tray activates with the equipped (first) weapon and a random active enemy.
3. ✔ No prompt / confirmation appears — fallback fires silently.
4. Roll the dice. ✔ Attack resolves normally with profile bonus/damage.

---

## Chain D — Hit path: action card then narrative  <!-- AC-008, AC-009 -->

1. It is Ani's turn. Type an attack.
2. Dice tray shows attack banner. Click d20 and roll high (force a hit by targeting a
   low-AC enemy, or just roll until you get one).
3. ✔ If HIT: damage banner appears with correct dice (from profile).
4. Roll damage.
5. ✔ **Action card appears centered in chat BEFORE the narrative:**
   ```
   ⚔ Ani → Goblin Warrior 1
   melee · 14 +4 = 18 vs AC 16
   HIT — 7 damage
   ```
6. ✔ Narrative follows: 2–5 sentences narrating what happened (outcome already known).
7. ✔ HP bar for Goblin Warrior 1 reduces immediately.
8. ✔ Initiative tracker advances to next combatant (no "Next Turn" click needed).

---

## Chain E — Miss path  <!-- AC-008, AC-009 -->

1. Same as Chain D but roll low (miss).
2. ✔ Action card shows MISS in grey — no damage line.
3. ✔ Narrative narrates a near-miss without mentioning dice numbers.
4. ✔ Target HP unchanged. ✔ Initiative still advances.
