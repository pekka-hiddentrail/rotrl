# Exploratory Tests — System Prompt Injection

Spec: specs/system-prompt.feature

**What automated tests cover:** static prompt assembly, per-turn copy, Groq cap, PC profile building,
conditional section specs, format-example gate, combat spec gate — all with fixture-based unit tests.

**Pre-requisites:** `python dev.py --skip-tests` — stack running. Dev Mode ON recommended for chains
that require reading the raw system message.

---

## Chain A — Format example on turn 1 only  <!-- AC-007, AC-002 -->

1. Boot a session (Dev Mode OFF, Groq).
2. Send turn 1: `We arrive at the Swallowtail Festival.`
3. Open `outputs/api_log/` and find the JSON for this first turn.
4. Read `raw_request.messages[0].content` (the system message sent to the LLM).
5. ✔ The system message contains `Gerhard Pickle` — the format example was injected on turn 1.
6. ✔ `prompt_tokens` is reasonable. Rough guideline: base ~800 + ~250 for FORMAT_EXAMPLE
   (turn 1 only) + ~50 per NPC short stub + ~500 per full NPC profile + ~250 per location.
   A turn 1 with 1 NPC (no skill) and 1 location should be ~1350–1800 prompt tokens.
   Much over 3500 with no injections = investigate trim.
7. Send turn 2: `I admire the decorations.` (avoid skill/search words).
8. Open the JSON for turn 2.
9. ✔ `raw_request.messages[0].content` does **not** contain `Gerhard Pickle` — format example absent.
10. ✔ `prompt_tokens` for turn 2 is lower than turn 1 by ~250 tokens (FORMAT_EXAMPLE size),
    unless new context was injected.

> Use the in-app **API Logs** button (header, post-boot) to browse log files without leaving the browser.

---

## Chain B — Combat spec injected only during combat  <!-- AC-008 -->

1. Boot a session. Send two non-combat turns.
2. Open the API log for turn 2.
3. ✔ `raw_request.messages[0].content` does NOT contain `round: N` — combat rules absent.
4. Send a turn that triggers combat: `A goblin leaps at me!` — play through until the LLM writes
   a `%%COMBAT%%` block (CombatPanel appears).
5. Open the API log for the next turn (the one where combat is active).
6. ✔ `raw_request.messages[0].content` contains the full combat spec including
   `sort descending by initiative` and `round: 0 ends combat`.
7. ✔ The `[COMBAT ONGOING — round N]` header is present with the correct round number.

---

## Chain C — Combat rules reference injection  <!-- AC-004 -->

Verifies that `CombatRulesIndex` injects a rule reference only during active combat and only when
a trigger phrase matches.

1. Boot a session. Trigger combat (`A goblin attacks!`) — play until `CombatPanel` appears.
2. Send: `I try to charge the goblin archer.`
3. Open the API log for this turn.
4. ✔ `raw_request.messages[0].content` contains `## Combat Reference — Actions in Combat`.
5. ✔ Content after `<!-- REFERENCE -->` (e.g. `## Casting a Spell`) is **absent**.
6. Send: `I step away from the goblin.` — triggers the AoO rule.
7. ✔ `## Combat Reference — Attacks of Opportunity` appears (not Actions) — longest trigger wins.
8. Click End Combat. Send: `I look around for survivors.`
9. Open the API log. ✔ No `## Combat Reference` block — lookup does not fire outside combat.

---

## Chain D — Conditional section specs and PC profile injection  <!-- AC-009, AC-010 -->

1. Boot a session. Send a pure observation turn with no NPC or skill: `I admire the butterflies.`
2. Open the API log for this turn.
3. ✔ `raw_request.messages[0].content` contains `[SECTIONS ACTIVE THIS TURN]`.
4. ✔ `%%GENERATE%%` spec is present (always injected).
5. ✔ `%%ROLL%%` spec (`dc: <N>`) is **absent** — no skill detected.
6. ✔ `%%DELTAS%%` spec (`Tags: [persistent]`) is **absent** — no NPCs in scene yet.
7. Send a turn that names a skill: `Yanyeeku tries to Perception check the rooftops.`
8. Open the API log for this turn.
9. ✔ `%%ROLL%%` spec is **present**.
10. ✔ Yanyeeku's narrative profile (`## PC — Yanyeeku`) is present in the system message.
11. ✔ Yanyeeku's mechanical profile (`## PC Stats — Yanyeeku`) is also present (skill detected).
12. Send a plain social turn that names Yanyeeku but no skill: `Yanyeeku greets the mayor.`
13. ✔ `## PC — Yanyeeku` (narrative) is present.
14. ✔ `## PC Stats — Yanyeeku` (mechanical) is **absent** — no skill detected this turn.
