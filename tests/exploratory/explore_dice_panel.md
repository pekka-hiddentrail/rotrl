# Exploratory Tests — Dice Panel

Spec: specs/dice-panel.feature

**What automated tests cover:** queue accumulation, history limit, auto-bonus logic, toggle,
normalisation — all with mocked `onRoll`.

**Pre-requisites:** `python dev.py --skip-tests` — stack running.

---

## Chain A — Basic queue and roll  <!-- AC-001, AC-002 -->

1. Click d6 twice, then d20 once.
2. ✔ Queue shows `2d6+1d20`.
3. Click Roll.
4. ✔ History entry shows individual die results and sum, e.g. `4+3+17 = 24`.
5. ✔ Roll button is disabled after rolling (queue cleared).

---

## Chain B — Auto-bonus with pending roll  <!-- AC-007, AC-004, AC-005 -->

1. Trigger a Perception check from the GM (send: `I try to spot hidden danger.`).
2. Set Yanyeeku as the active character (she has Perception +7).
3. Click d20, click Roll.
4. ✔ History shows `13 + Perception +7 = 20 vs DC 18` (numbers will vary).
5. ✔ PASSED or FAILED badge appears.

---

## Chain C — Toggle off, then back on  <!-- AC-010 -->

1. With a pending Perception roll active and Yanyeeku set as active character:
2. Uncheck Auto Bonus.
3. Click d20, click Roll.
4. ✔ History shows no modifier, no label — raw total only.
5. Re-check Auto Bonus.
6. Click d20, click Roll again.
7. ✔ Modifier is applied again.

---

## Chain D — History cap  <!-- AC-006 -->

1. Without a pending roll, roll d20 twelve times in a row.
2. ✔ History shows exactly 10 rows after the 12th roll.
3. ✔ The most recent roll has the highlight style; older rows do not.
