# Exploratory Tests — Attack Resolution

> ⚠️ **DEPRECATED** — These chains no longer reflect the current attack flow.
>
> **What changed:**
> - NPC attacks no longer come from `%%ATTACK%%` blocks written by the LLM on a regular
>   player turn. They are resolved by the backend via `POST /enemy_turn` → `%%ACTION%%` →
>   `_resolve_npc_attack`. See `explore_combat_tracker.md` Chains A–D for current enemy flow.
> - PC attacks via `%%ATTACK%%` blocks (Chains B–H) are still in the codebase but the
>   intention is to replace them with `%%ACTION%%` on the player side in a future tier
>   (CB1.9 player-side action declaration). These chains may still work today but are not
>   maintained.
>
> **Do not use these chains as acceptance criteria.** Refer to:
> - `explore_combat_tracker.md` — CombatPanel, initiative, HP bars, End Combat
> - `explore_roll_initiatives.md` — initiative roll flow
> - *(future)* `explore_enemy_turn.md` — enemy turn via Enemy Turn button

Spec: specs/attack-resolution.feature

**What automated tests cover:** `_roll_dice`, `_parse_attack_line/block`, `_is_pc_attacker`,
`_resolve_npc_attack`, `resolve_attack_roll`, `resolve_damage_roll`, `stream_resume_combat`,
`_build_attack_history_message`, multi-attack queue progression, SSE events, stream filter.

**What these chains verified (historical):** the interactive dice flow as a player experiences
it — banner rendering, HP bar animation, attack log appearance, and the complete round-trip
from `%%ATTACK%%` block to resumed GM narration.

**Pre-requisites (historical):** `python dev.py --skip-tests` — stack running, Dev Mode OFF.

---

## Chain A — NPC auto-resolution updates HP bar immediately  <!-- AC-002, AC-007 -->

1. Boot a session and play until a `%%COMBAT%%` block fires (CombatPanel appears).
2. Send a turn where only an NPC attacks: `The goblin lunges at Shalelu!`
3. ✔ The GM response does NOT show an attack banner in the dice panel — no player action required.
4. ✔ An `attack_result` entry appears in the DicePanel history with the ⚔ prefix.
5. Open the CombatPanel.
6. ✔ Shalelu's HP bar has updated (reduced if the NPC hit, unchanged if it missed).
7. ✔ If the attack hit, the HP bar colour reflects the new HP tier (green / amber / red).
8. Open `outputs/api_log/` and inspect the turn's JSON.
9. ✔ No `attack_result` entry shows `is_pc: true` — only NPC attacks auto-resolve.

---

## Chain B — PC attack request shows to-hit banner  <!-- AC-002, AC-003 -->

1. Continue from Chain A or boot fresh. Get into active combat.
2. Send a turn where a PC attacks: `Thaelion swings at Goblin 1!`
   - The LLM must write an `%%ATTACK%%` line with your PC as `attacker`.
3. ✔ The DicePanel shows an **attack banner** (not the normal skill-roll banner) with:
   - Attacker and target names
   - Attack bonus (e.g. `+5`)
   - Target AC
4. ✔ The `dice-panel-active` highlight (amber border) is on the panel.
5. ✔ No to-hit roll outcome is shown yet — the player must roll.
6. ✔ The GM message is NOT yet streaming — the LLM is waiting.
7. **Judge:** is the attacker name correct? Is the AC value plausible for the target?

---

## Chain C — Hit path: damage banner appears, HP reduces  <!-- AC-003, AC-004 -->

1. With the to-hit banner active (from Chain B):
2. Click d20, click Roll.
3. **If hit:**
   - ✔ To-hit banner is replaced by a **damage banner** showing the damage expression (e.g. `1d8+3`).
   - ✔ Attack log shows the hit entry with attacker→target and "HIT" badge (no damage yet).
   - Click the damage dice shown in the banner, click Roll.
   - ✔ Damage banner disappears.
   - ✔ Attack log entry updates to show the damage total.
   - ✔ CombatPanel HP bar for the target reduces immediately.
   - ✔ If HP drops to 0, bar turns dark grey and status chip shows "unconscious" or "dead".
   - ✔ GM narrative streams automatically (no manual resume needed).
4. **If miss:** see Chain D.

---

## Chain D — Miss path: banner clears, GM resumes  <!-- AC-003 -->

1. With the to-hit banner active:
2. Roll a 1 (or click the lowest die value available).
3. ✔ If total < target AC: "MISS" badge appears in the attack log, no damage banner.
4. ✔ DicePanel returns to its normal (non-active) state.
5. ✔ If this was the only queued attack, the GM narrative streams automatically.
6. ✔ Target HP in CombatPanel is unchanged.

---

## Chain E — Multiple PC attacks in queue  <!-- AC-009 -->

1. Get into combat. Send a turn that produces two PC attack lines (e.g. a character with
   two attacks per round): both lines have a PC as attacker.
2. ✔ First `attack_request` SSE fires — banner shows the first attack.
3. Resolve the first attack (hit or miss).
4. ✔ Banner immediately switches to the **second attack** — attacker/bonus/AC update.
5. ✔ The GM does NOT stream between the two attacks — it waits for all dice.
6. Resolve the second attack.
7. ✔ Both entries appear in the attack log.
8. ✔ GM narrative streams only after both are resolved.
9. ✔ `queue_remaining` in the Network tab response drops 2 → 1 → 0 across the three calls.

---

## Chain F — Attack log visual  <!-- AC-002 -->

After any round with both NPC and PC attacks:

1. ✔ Attack log entries appear **above** the skill-roll history in the DicePanel.
2. ✔ Each entry shows ⚔ prefix, attacker→target, roll+bonus=total vs AC.
3. ✔ Hit entries show a green (or highlighted) "HIT" badge and damage total.
4. ✔ Miss entries show a red (or muted) "MISS" badge, no damage total.
5. ✔ NPC entries (`is_pc: false`) are styled consistently with PC entries.
6. ✔ Log does not overflow or push the roll queue off screen.

---

## Chain G — %%ATTACK%% block never visible to player  <!-- AC-008 -->

1. Boot with Dev Mode ON. Play through a combat turn that produces an `%%ATTACK%%` block.
2. ✔ In Dev Mode the raw `%%ATTACK%%` lines ARE visible in the chat stream — this is correct.
3. Reboot with Dev Mode OFF. Repeat the same turn.
4. ✔ The chat shows only the narrative prose — `%%ATTACK%%`, `attacker:`, `bonus:` are absent.
5. ✔ The DicePanel attack banner still appears (the SSE event fires even though the token
   is hidden from the player).

---

## Chain H — End Combat clears pending attack queue  <!-- AC-006 -->

1. With an `attack_request` banner active (player has not rolled yet):
2. Click **End Combat** in the CombatPanel.
3. ✔ CombatPanel disappears.
4. ✔ DicePanel attack banner disappears — no ghost banner state.
5. ✔ DicePanel returns to the right column (combat-active layout reverts).
6. Send a normal turn.
7. ✔ Turn processes without error — the cleared queue causes no crash.
