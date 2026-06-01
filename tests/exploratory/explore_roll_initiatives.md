# Exploratory Tests — Roll Initiatives

Spec: specs/roll-initiatives.feature

**What automated tests cover:** `_parse_combat_block` round-1 initiative rolling,
`_parse_combatant_line` modifier extraction, PC modifier read from `pc_profiles`,
round-2 initiative preservation, new-combatant mid-combat roll, `advance_combat_turn`
initiative order, CombatPanel initiative display (Vitest).

**What these chains verify:** the live initiative-roll experience — the 🎲 Roll Initiatives
button, dice animation, reordered initiative list, and correct PC modifier sourcing from
character data.

**Pre-requisites:** `python dev.py --skip-tests` — full stack running. Dev Mode ON for
Chain A so the raw `%%COMBAT%%` block is visible.

---

## Chain A — 🎲 Roll Initiatives button rolls d20+modifier and reorders the list  <!-- AC-001, AC-002 -->

1. Boot a session. Trigger combat (send a turn that produces a `%%COMBAT%%` block).
2. ✔ CombatPanel appears with combatants in LLM-written order.
3. ✔ A 🎲 **Roll Initiatives** button is visible above the initiative list.
4. Click **Roll Initiatives**.
5. ✔ Each combatant row briefly animates (dice roll indicator or flash).
6. ✔ Initiative values change from LLM-written totals to server-rolled values (1d20 + modifier).
7. ✔ The list reorders so the highest initiative is at the top.
8. ✔ The gold-glow `.combatant-current` highlight follows the new first combatant.
9. Open DevTools → Network → filter by `roll_initiatives`.
10. ✔ `POST /api/sessions/{id}/combat/roll_initiatives` fired; response body contains each combatant name with their rolled total.

---

## Chain B — PC modifiers come from character data, not LLM values  <!-- AC-003 -->

1. Continue from Chain A. Note which combatants are PCs (Ani, Yanyeeku, Vanx).
2. Open `ui/public/data/player_ani.json` — check `combat_stats.initiative` value.
3. After rolling, note Ani's new initiative value in CombatPanel.
4. ✔ Ani's initiative is in the range `[1 + modifier, 20 + modifier]` (d20 + her modifier).
5. **Negative:** in Dev Mode, inspect the raw `%%COMBAT%%` block. The LLM may have written
   `init: 14` for Ani. Confirm that the rolled value differs from the LLM-written value
   (they should diverge at least occasionally — identical values on every run would indicate
   the LLM total is being used instead of rolling).

---

## Chain C — Round-2 initiative is preserved, not re-rolled  <!-- AC-004 -->

1. Continue in combat. Advance to round 2 (all combatants have acted once).
2. ✔ CombatPanel shows "Round 2" badge.
3. The 🎲 Roll Initiatives button should either be hidden or disabled on round 2+.
4. ✔ Confirm: sending a new turn with a `%%COMBAT%%` block on round 2 does NOT change
   the initiative values — the CombatPanel order stays the same.
5. **If a new combatant appears mid-combat** (e.g. a goblin arrives from offscreen):
6. ✔ The new combatant receives a freshly-rolled initiative; existing combatants are unchanged.

---

## Chain D — Initiative reorder survives End Combat + re-entry  <!-- AC-001, AC-004 -->

1. After rolling initiatives, note the current order (e.g. Goblin Warchanter 18, Ani 14, ...).
2. Click **End Combat**.
3. ✔ CombatPanel clears.
4. Trigger a new combat via a new `%%COMBAT%%` block.
5. ✔ CombatPanel reappears with default LLM-written order (roll has not been applied yet).
6. Click 🎲 **Roll Initiatives** again.
7. ✔ New rolls produce a different order than round 1 (probabilistically — may coincidentally match).
8. ✔ No stale values from the previous combat bleed through.
