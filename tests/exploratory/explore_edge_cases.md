# Exploratory Tests — Edge Cases

<!-- Multi-feature: session-boot, context-detection, npc-system, system-prompt, session-controls -->
<!-- No single Spec: header; unambiguous AC IDs matched automatically. -->

**Pre-requisites:** `python dev.py --skip-tests` — stack running.

---

## Chain A — Very long player input

Send this wall of text as a single turn:

> `I want to give a full account of everything we've seen so far. We arrived at the Swallowtail
> Festival this morning and spent time at the stalls. I spoke with Ameiko at the Rusty Dragon, then
> watched the consecration with Father Zantus. During the ceremony a group of goblins attacked from
> the north gate — we fought them off, though one of the festival-goers was injured. After the
> fight, Sheriff Hemlock arrived and began organising a perimeter. I also noticed a goblin carrying
> a crude map that appeared to show the Glassworks. I want to report all of this to the Mayor and
> ask what the official response will be, and also find out whether the Sandpoint Mercantile League
> has heard anything about unusual goblin activity in the Hinterlands before today.`

- ✔ GM responds coherently and addresses the main beats.
- ✔ No Python error or 500 response.
- ✔ Session prompt was not truncated mid-block (check dev mode — context should be intact).

---

## Chain B — NPC name typo

Send: `I find Ameikko at the tavern.` (double-k typo)

- ✗ Intent bar shows **no NPC detected** — `NpcIndex` uses strict word-boundary regex;
  typos are never caught unless explicitly added as an alias.

Then send: `I ask Hemlock about the raids.` (surname only)

- ✔ Intent bar shows Belor Hemlock detected (single-word exact alias match).

---

## Chain C — Two NPCs in one turn

Send: `I introduce Ameiko to Father Zantus and watch their reaction.`

- ✔ Intent bar shows both NPCs detected.
- ✔ Both NPC profiles were injected (check in dev mode).

---

## Chain D — Session length stress

Send 16 turns of short inputs (just `ok`, `I look around`, `I wait`, etc.) to trigger history
trimming.

- ✔ Response latency does not noticeably increase by turn 15–16 vs turn 1–2.
- ✔ No SSE errors or session corruption.

---

## Chain E — Dev Mode delta inspection

1. Boot with Dev Mode ON.
2. Send: `I speak at length with Ameiko about her father Lonjiku and her plans for the Rusty Dragon.`
3. Read the full raw response.
4. ✔ A `%%DELTAS%%` block is present and contains at least one bracket entry for `ameiko_kaijitsu`.
5. ✔ Each delta uses the bracket format exactly:
   `[ npc: Ameiko Kaijitsu  disposition: ...  location: ...  knowledge: [tag] ...  summary: ... ]`
   — **never bullet points**.
6. ✔ The block contains only Ameiko (an NPC) — no PCs, no groups ("crowd"), no objects, no scene
   state entries.
7. ✔ The `knowledge:` lines are readable English sentences, not truncated or escaped JSON.
