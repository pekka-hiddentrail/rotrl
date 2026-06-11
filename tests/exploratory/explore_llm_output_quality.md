# Exploratory Tests — LLM Output Quality

Spec: specs/response-parsing.feature

**What automated tests cover:** SSE event order, streaming filter, section parsing with fixture inputs.

**Note:** This section covers areas that are subjective or require a live LLM to judge quality.
Run the automated suite first. If it's red, don't bother with this.

**Pre-requisites:** `python dev.py --skip-tests` — stack running.

---

## Chain A — Format compliance check  <!-- AC-001, AC-005 -->

1. Boot with Dev Mode ON.
2. Send: `We arrive at the Swallowtail Festival. I look around for anything unusual.`
3. ✔ Raw `%%NARRATIVE%%` marker is visible in the chat stream.
4. ✔ Any `%%DELTAS%%` or `%%GENERATE%%` blocks are visible if the model wrote them.
5. Reboot with Dev Mode OFF. Send the same input.
6. ✔ No `%%` markers appear in the chat — only narrative prose.

---

## Chain B — Narrative quality baseline  (subjective)

1. Boot session 1 with Dev Mode OFF (Groq, `llama-3.3-70b-versatile`).
2. Send these four inputs in sequence and read each response critically:

**Turn 1:** `We arrive at the Swallowtail Festival. I look around the square.`
- ✔ Intent bar shows a location chip: `Festival Grounds` (alias `square`).
- ✔ Response describes the festival scene without inventing locations outside Sandpoint canon.

**Turn 2:** `I approach Ameiko at the Rusty Dragon and ask if she's seen anything strange lately.`
- ✔ Intent bar shows NPC chip `Ameiko Kaijitsu` + location chip `The Rusty Dragon`.
- ✔ Response uses canonical spelling `Ameiko Kaijitsu` throughout.

**Turn 3:** `I tell Ameiko about the goblin I spotted near the north gate.`
- ✔ Response keeps Ameiko's established tone and does not jump scenes.

**Turn 4:** `I head to the cathedral and speak with Father Zantus about the consecration.`
- ✔ Intent bar shows location chip `Sandpoint Cathedral` + NPC chip `Abstalar Zantus`.
- ✔ Response uses canonical spelling `Abstalar Zantus`.

Check all four turns:
- Response is ≤ 3 paragraphs.
- No `%%` markers visible in chat.
- No invented Sandpoint geography.

---

## Chain C — Roll request trigger  <!-- AC-002 -->

1. Send: `I try to persuade the guard to let us into the garrison after hours.`
2. ✔ Pending roll banner appears on the Dice Tray showing "Diplomacy" and a DC.
3. ✔ Dice Tray border turns amber and a subtle shadow appears.
4. Click d20, click Roll.
5. ✔ PASSED or FAILED badge appears in history.
6. ✔ The pre-written success or failure sentence from the `%%ROLL%%` block appears as a GM
   message — no new LLM call is made.
7. **Judge:** is the DC between 12 and 20? A DC 5 Diplomacy check for after-hours garrison entry
   is a bug.

---

## Chain D — Combat narrative quality  (subjective)

1. Send: `A goblin leaps out from behind the barrel and attacks me with a dogslicer!`
2. ✔ GM narrates the attack with a stated mechanical result — damage, AC miss, or pending roll.
   Not vague prose.
3. ✔ No soft hand-waving: "you easily dodge", "you're fine", "it seems to miss" are quality failures.
4. Send: `I attack back with my longsword.`
5. ✔ GM either emits a `%%ROLL%%` block (pending banner appears) or resolves with a specific
   stated result — not both, not neither.
6. **Judge:** does each exchange have mechanical weight, or does the GM narrate combat at a summary
   level without involving the dice system?
