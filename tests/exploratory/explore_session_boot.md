# Exploratory Tests — Session Boot

Spec: specs/session-boot.feature

**What automated tests cover:** prompt assembly, file loading, boot endpoint, intro card SSE, NPC cleanup;
`_FORMAT_EXAMPLE`, `_COMBAT_SPEC_ROUND1`, and `_COMBAT_SPEC_ONGOING` constants verified by unit tests.

**Pre-requisites:** `python dev.py --skip-tests` — stack running at http://localhost:5173.

---

## Chain A — Happy path boot  <!-- AC-001, AC-002 -->

1. Set session number to 1, provider Groq, model `llama-3.3-70b-versatile`, Dev Mode OFF.
2. Click Boot Session.
3. ✔ Intro card appears immediately (before boot finishes) and renders markdown — check headers, italics, bullet lists.
4. ✔ Session badge (`Session 1 · llama-3.3-70b-versatile`) appears after boot, not before.
5. ✔ No error bar.

---

## Chain B — Invalid session number  <!-- AC-005 -->

1. Set session number to 99 (no boot files exist for that session).
2. Click Boot Session.
3. ✔ Error bar shows a readable message (not a raw Python traceback or blank hang).

---

## Chain C — Re-boot without page refresh  <!-- AC-001, AC-003 -->

1. Boot session 1, send one turn, perform a dice roll.
2. Click End Session, wait for UI to clear.
3. Boot session 1 again immediately.
4. ✔ Dice panel history is empty.
5. ✔ Pending roll banner is gone.
6. ✔ Intent bar is empty.
7. ✔ Chat window is empty (no ghost messages from previous session).
