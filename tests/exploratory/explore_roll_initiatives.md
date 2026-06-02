# Exploratory Tests — Automatic Initiative Roll

Spec: specs/roll-initiatives.feature

**What automated tests cover:** `roll_combat_initiatives()` fresh d20 rolls, PC modifier
from `pc_profiles`, enemy modifier from `pending_combatants` (event file table), flat d20
fallback, `current_actor` set to highest active, inactive combatants re-rolled but excluded,
`state.json` written after roll, endpoint guards 200/409/404, `_parse_event_combatants`
table parsing, auto-roll trigger detection (AC-008), `CombatPanel` server-rolled order display.

**What these chains verify:** the live initiative-roll experience — that when a combat event
fires, the CombatPanel immediately shows server-rolled initiatives with no player action, PCs
have the right modifier applied, and the current actor is correctly highlighted.

**Pre-requisites:** `python dev.py --skip-tests` — full stack running. Dev Mode ON for
Chain A so the raw `%%EVENT%%` and `%%COMBAT%%` blocks are visible in the stream.

---

## Chain A — Initiatives auto-roll when %%EVENT%% fires  <!-- AC-008 -->

1. Boot a session. Ensure Dev Mode is ON.
2. Send a turn that will trigger the goblin attack event:
   > `"The festival crowd parts — goblins pour into the square, weapons drawn!"`
3. ✔ In the raw token stream (Dev Mode panel): `%%EVENT%% goblin_attack_starts` appears.
4. ✔ On the same turn or the next: `%%COMBAT%%` block appears with combatant lines.
5. ✔ CombatPanel appears in the right column. **Without any button click**, the initiative
   values already reflect server-rolled d20 results (values 1–20 + modifier, not the LLM's
   totals).
6. ✔ The top combatant in the CombatPanel has the highest initiative value.
7. ✔ The gold-glow `.combatant-current` row highlights that top combatant.
8. Open DevTools → Network → filter by `turn`. Inspect the SSE stream body:
9. ✔ `combat_update` event carries the combatants sorted descending by initiative.
10. **Note:** there is no "Roll Initiatives" button — the roll is fully automatic.

---

## Chain B — PC modifier is applied from character data  <!-- AC-002 -->

1. Continue from Chain A. The party contains Ani, Yanyeeku, and Vanx.
2. Open `ui/public/data/player_ani.json` — note `combat_stats.initiative` value (e.g. `+2`).
3. ✔ Ani's initiative in CombatPanel is in the range `[1+mod, 20+mod]` for that modifier.
4. **Negative check:** in Dev Mode, note the LLM-written `init:` value in the `%%COMBAT%%`
   block for Ani. The displayed CombatPanel value should be different (rolled, not the
   LLM total) — at least occasionally across multiple test runs.
5. ✔ Enemy combatants (Goblin Warchanter, Goblin Warrior 1–4) show rolled values consistent
   with their `init_mod` from the event file table (+3 for Warchanter, +2 for Warriors).

---

## Chain C — Round 2+ does not re-roll  <!-- AC-001, AC-004 -->

1. Continue in combat. Advance to round 2 (use Next Turn until "Round 2" badge appears).
2. ✔ CombatPanel shows "Round 2" badge.
3. ✔ Confirm: subsequent turns do NOT change the initiative order — the values from the
   auto-roll on round 1 are preserved.
4. Check DevTools: no new `POST /roll_initiatives` request fires between rounds.

---

## Chain D — Combat re-entry starts fresh  <!-- AC-001 -->

1. After at least one round of combat, click **End Combat**.
2. ✔ CombatPanel disappears.
3. Trigger a new combat encounter (new `%%EVENT%%` + `%%COMBAT%%` on round 1).
4. ✔ CombatPanel reappears with a fresh auto-roll — new values, new order.
5. ✔ No stale initiatives from the previous combat bleed through.
