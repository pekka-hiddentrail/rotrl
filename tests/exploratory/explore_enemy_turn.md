# Exploratory Tests — Enemy Turn

Spec: specs/enemy-turn.feature

**What automated tests cover:** `_parse_action_block` (AC-001, AC-002), `_build_enemy_turn_system`
actor/weapon/ally/PC format (AC-003–AC-006, AC-016), narrative extraction (AC-007),
attack resolution and HP update (AC-008–AC-009), endpoint guards (AC-010), close-combat
stream (AC-011), close directive (AC-012), CombatPanel UI (AC-013–AC-014), stale-queue
clear (AC-015), if_hit/if_miss conditional narration (AC-017), action card SSE and
centering (AC-018).

**What these chains verify:** the full live enemy-turn experience — action card appears
before narrative, correct weapon is used, narrative + outcome reads naturally, HP updates,
and initiative advances automatically after the turn resolves.

**Pre-requisites:** `python dev.py --skip-tests` — stack running. Dev Mode ON so raw
`%%ACTION%%` and `[HIT]`/`[MISS]` annotations are visible alongside the action card.

---

## Chain A — Enemy turn fires, action card appears before narrative  <!-- AC-018 -->

1. Boot a session. Trigger combat (send a turn that produces a `%%COMBAT%%` block with
   goblins). Roll initiatives. Advance to a goblin's turn.
2. Click **Enemy Turn**.
3. ✔ A centered **action card** appears in the chat BEFORE the narrative text:
   ```
   ⚔ Goblin Warrior 1 → Vanx
   melee · 9 +2 = 11 vs AC 12
   MISS
   ```
4. ✔ The narrative text appears immediately after:
   *"Goblin Warrior 1 charges forward…\n\nVanx sidesteps and the blow glances off."*
5. ✔ In Dev Mode, the raw `[MISS]` annotation is visible before `%%ACTION%%`.
6. ✔ The HP bar for Vanx is unchanged (miss — no damage).
7. ✔ The CombatPanel automatically advances to the next combatant after the turn resolves —
   no "Next Turn" click required.

---

## Chain B — Hit path: damage shown in card and HP reduces  <!-- AC-008, AC-018 -->

1. Continue from Chain A. Wait for a goblin turn where the attack hits (roll high enough
   vs the target's AC, or temporarily lower a PC's AC to force a hit for testing).
2. ✔ Action card shows `HIT — N damage` in red.
3. ✔ The narrative ends with the `if_hit` sentence from the LLM.
4. ✔ The target PC's HP bar in CombatPanel reduces by the damage amount immediately.
5. ✔ The `attack_result` entry in the Dice Tray history shows the correct roll/total/AC/damage.
6. Open DevTools → Network → find the `/enemy_turn` SSE stream.
7. ✔ `action_card` event appears before the `token` event in the stream.

---

## Chain C — Weapon is constrained to profile  <!-- AC-016 -->

1. In Dev Mode, observe the `[ENEMY TURN BRIEFING]` in the API Logs panel (visible after
   clicking **API Logs** → selecting the most recent enemy turn entry).
2. ✔ The briefing shows `Equipped weapon: dogslicer` and `Available weapon: shortbow`
   (or similar) for a Goblin Warrior.
3. ✔ The `%%ACTION%%` block in the raw response stream uses one of those weapon names,
   not a hallucinated one like "longsword".
4. **Negative:** if the LLM does write an unknown weapon (inspect raw stream in Dev Mode),
   the session log (`outputs/*.log.md`) should contain:
   `[CB1.9-2: weapon '...' not in profile — using 'dogslicer']`
   confirming the backend silently corrected it.

---

## Chain D — Close combat clears the panel  <!-- AC-011 -->

1. With combat active and CombatPanel visible:
2. Click **End Combat**.
3. ✔ A brief closure narrative streams into the chat (e.g. "The goblins scatter…").
4. ✔ CombatPanel disappears.
5. ✔ DiceTray returns to the right column.
6. ✔ Sending a normal narrative turn processes without error.

---

## Chain E — Unexpected sections warning in dev mode  <!-- AC-006 (B-C04 fix) -->

1. Boot with Dev Mode ON.
2. If the LLM writes `%%COMBAT%%` or `%%ATTACK%%` inside an enemy turn response (visible
   in the raw stream), a `[DEV WARNING: unexpected sections [...] in enemy turn response]`
   token should appear in the chat.
3. ✔ The `%%COMBAT%%`/`%%ATTACK%%` content does NOT update the CombatPanel or attack log —
   it is silently discarded.
4. ✔ The `%%ACTION%%` block is still parsed correctly and the attack resolves normally.
