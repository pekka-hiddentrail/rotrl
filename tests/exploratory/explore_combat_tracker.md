# Exploratory Tests — Combat Tracker

Spec: specs/combat-tracker.feature

**What automated tests cover:** `_parse_combatant_line`, `_parse_combat_block`,
`_serialize_combat_state`, `CombatState`/`Combatant` dataclasses, `%%COMBAT%%` SSE integration,
narrative filter stripping, DELETE /combat endpoint, HpBar colours (Vitest), CombatPanel
initiative order / conditions chips / End Combat button (Vitest), combat-active layout (Vitest).

**What these chains verify:** the live visual experience a GM observes — panel appearance,
HP bar colour shifts as HP changes, condition chip tooltips, and the End Combat cleanup flow.

**Pre-requisites:** `python dev.py --skip-tests` — full stack running. Dev Mode is ON for
Chain A and OFF for Chain C (so the player token stream is clean).

---

## Chain A — CombatPanel appears on first %%COMBAT%% block  <!-- AC-001, AC-004, AC-006, AC-007 -->

1. Boot a session. Send a turn that will trigger combat:
   > `"The goblins attack! Thaelion draws his sword!"`
2. ✔ A `%%COMBAT%%` block appears in the raw Dev Mode stream (token panel).
3. ✔ The CombatPanel slides into the right column — "⚔ Combat" header and "Round 1" badge visible.
4. ✔ Combatants are listed **highest-initiative-first** (not in the order the LLM wrote them).
5. ✔ The top combatant's row has a gold glow border (`.combatant-current` style).
6. ✔ Each row shows ⚡ init and 🛡 AC values.
7. ✔ The DicePanel shifts to the left column (between sidebar and chat).
8. ✔ `.main-content` has class `combat-active` (inspect element in DevTools).
9. **Judge:** are the initiative values plausible? Is HP initialised from the character data?

---

## Chain B — HP bar colour shifts through tiers as HP changes  <!-- AC-009 -->

1. Continue from Chain A or establish combat (round ≥ 1) with a combatant that has hp_max ≥ 15.
2. In DevTools, inspect the `.hp-bar-fill` style for that combatant.
3. ✔ When `hp_current / hp_max > 0.66` → `background: #3a9a6a` (green).
4. Send turns or manually edit the session until HP drops to 33–66 %:
   - e.g. `"The goblin hits Shalelu for 8 damage"` (adjust to reach 33–66 %)
5. ✔ HP bar fill is now `#c9a84c` (amber) after the `%%COMBAT%%` update fires.
6. Drop HP below 33 %:
7. ✔ HP bar fill is now `#b04040` (red).
8. Drop to 0:
9. ✔ HP bar fill is `#444` (dark grey) and status badge "KO" appears on the row.
10. ✔ Row has `combatant-inactive` dim styling.
11. **Judge:** does HP change immediately on the same turn, or only on the next `combat_update`?
    It should update on the same turn the damage is applied.

---

## Chain C — Condition chip renders with tooltip  <!-- AC-012 -->

1. Reboot with Dev Mode OFF.
2. Send a turn asking the LLM to write a condition on a combatant:
   > `"The goblin shaman casts Cause Fear — Thaelion is shaken."`
3. ✔ The LLM writes `conditions: [shaken]` in the `%%COMBAT%%` block (verify via network tab → SSE response body).
4. ✔ A small "shaken" chip appears below Thaelion's HP bar in the CombatPanel.
5. **Hover** the chip.
6. ✔ Tooltip shows: `"Shaken: -2 attack rolls, saving throws, skill and ability checks"`.
7. Now get the condition removed (next LLM turn without the condition field):
8. ✔ The chip disappears on the next `combat_update`.
9. **Negative:** ask the LLM to write an invalid condition (e.g. `conditions: [cursed]`).
10. ✔ "cursed" does NOT appear as a chip — backend drops unknown conditions silently.
    Verify in the `combat_update` SSE event payload (Network tab): `conditions` array should be `[]`.

---

## Chain D — End Combat clears the panel and backend state  <!-- AC-008 -->

1. With CombatPanel active (round ≥ 1):
2. Note the session id from the header badge.
3. Open Network tab, filter by `combat`.
4. Click **End Combat** in the CombatPanel.
5. ✔ A `DELETE /api/sessions/{id}/combat` request fires immediately.
6. ✔ Response is `{"combat_state": null}`.
7. ✔ CombatPanel disappears from the UI.
8. ✔ DicePanel returns to the right column (combat-active layout reverts).
9. ✔ `.main-content` no longer has `combat-active` class.
10. Send a normal (non-combat) turn.
11. ✔ Turn processes without error — no ghost banner, no stale combat state.
12. ✔ The turn's `combat_update` SSE event carries `combat_state: null`.
13. **Judge:** if a new `%%COMBAT%%` block arrives after End Combat, does the panel re-appear?
    It should — End Combat only clears the current session, not future combats.
