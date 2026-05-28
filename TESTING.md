# Manual Testing Guide

This document covers areas the automated suite (352 pytest + 88 Vitest) cannot reach: real LLM behaviour, streaming feel in a live browser, on-disk side effects, and UI interactions that require a human to judge quality.

**Run the automated suite first.** If it's red, don't bother with this.

```
pytest && cd ui && npx vitest run
```

Then start the stack:

```
python dev.py --skip-tests
```

---

## 1. Session Boot

**What automated tests cover:** prompt assembly, file loading, boot endpoint, intro card SSE.

**Chains to run:**

**Chain A — happy path**
1. Set session number to 1, provider Groq, model `llama-3.3-70b-versatile`, Dev Mode OFF.
2. Click Boot Session.
3. ✔ Intro card appears immediately (before boot finishes) and renders markdown — check headers, italics, bullet lists.
4. ✔ Session badge (`Session 1 · llama-3.3-70b-versatile`) appears after boot, not before.
5. ✔ No error bar.

**Chain B — invalid session number**
1. Set session number to 99 (no boot files exist for that session).
2. Click Boot Session.
3. ✔ Error bar shows a readable message (not a raw Python traceback or blank hang).

**Chain C — re-boot without page refresh**
1. Boot session 1, send one turn, perform a dice roll.
2. Click End Session, wait for UI to clear.
3. Boot session 1 again immediately.
4. ✔ Dice panel history is empty.
5. ✔ Pending roll banner is gone.
6. ✔ Intent bar is empty.
7. ✔ Chat window is empty (no ghost messages from previous session).

---

## 2. GM Turn — LLM Output Quality

**What automated tests cover:** SSE event order, streaming filter, section parsing with fixture inputs.

**Chains to run — this is the hardest area to automate:**

**Chain A — format compliance check (Dev Mode ON)**
1. Boot with Dev Mode ON.
2. Send: `We arrive at the Swallowtail Festival. I look around for anything unusual.`
3. ✔ Raw `%%NARRATIVE%%` marker is visible in the chat stream.
4. ✔ Any `%%DELTAS%%` or `%%GENERATE%%` blocks are visible if the model wrote them.
5. Reboot with Dev Mode OFF. Send the same input.
6. ✔ No `%%` markers appear in the chat — only narrative prose.

**Chain B — narrative quality baseline**
Send these four inputs in sequence and read each response critically:

1. `We arrive at the Swallowtail Festival. I look around the square.`
2. `I approach Ameiko at the Rusty Dragon and ask if she's seen anything strange lately.`
3. `I tell Ameiko about the goblin I spotted near the north gate.`
4. `I head to the cathedral and speak with Father Zantus about the festival consecration.`

Check after each:
- Response is ≤ 3 paragraphs.
- NPC names match canonical spellings (`Ameiko Kaijitsu`, `Abstalar Zantus`).
- No invented geography (no locations that don't exist in Sandpoint canon).
- Intent bar updates with the NPC name detected in the turn.

**Chain C — roll request trigger**
1. Send: `I try to persuade the guard to let us into the garrison after hours.`
2. ✔ Pending roll banner appears on the dice panel showing "Diplomacy" and a DC.
3. ✔ Dice panel background changes colour.
4. Click d20, click Roll.
5. ✔ PASSED or FAILED badge appears in history.
6. ✔ A follow-up GM message describes the outcome.
7. **Judge:** is the DC between 12 and 20? A DC 5 Diplomacy check for after-hours garrison entry is a bug.

**Chain D — combat and mechanical grounding**
1. Send: `A goblin leaps out from behind the barrel and attacks me with a dogslicer!`
2. ✔ GM describes the attack with a roll result or calls for a roll.
3. ✔ No narrative hand-waving of mechanical outcomes ("you easily dodge").
4. Send: `I attack back with my longsword.`
5. ✔ GM either calls for an attack roll (`%%ROLL%%`) or resolves with a stated result.

---

## 3. NPC System — On-Disk Side Effects

**What automated tests cover:** `NpcIndex` singleton, `npc_dir_for`, stub creation, delta write functions — all with temp directories.

**Chains to run (requires real disk state):**

**Chain A — delta write to known NPC**
1. Boot a session.
2. Send: `I find Belor Hemlock at the garrison and ask him about the goblin raids.`
3. Open `adventure_path/05_npcs/belor_hemlock/session_NNN.md`.
4. ✔ A `%%DELTA%%` block was appended with the current session number and a turn count.
5. ✔ The `knowledge:` lines contain readable prose about what happened (not garbled JSON).
6. Send a second turn mentioning Belor: `I press Hemlock on whether Nualia is involved.`
7. ✔ A second delta block was appended to the same file (not a new file).

**Chain B — auto-stub creation for new NPC**
1. Send: `I walk over to the elderly woman selling amulets near the fountain and introduce myself. Her name is Marta Hask.`
2. Wait 5 seconds.
3. ✔ A directory `.marta_hask/` (or similar slug) exists under `adventure_path/05_npcs/`.
4. ✔ `base.md` contains at least `name:`, `role:`, and `appearance:` fields with non-empty values.
5. ✔ Directory has the dot prefix (session NPC).

**Chain C — NPC promotion**
1. After Chain B, rename `.marta_hask/` → `marta_hask/` in the file system.
2. End the session, boot a new one.
3. Send: `I look for Marta Hask at the fountain again.`
4. ✔ Intent bar shows `marta_hask` (or her name) as a detected NPC.
5. ✔ Her profile was injected into the system prompt (visible in dev mode as context in the response).

**Chain D — purge session NPCs**
1. Without an active session, confirm at least one dot-prefixed directory exists under `05_npcs/`.
2. Click Purge NPCs.
3. ✔ Inline confirm appears: "Purge session NPCs? Yes / No".
4. Click Yes.
5. ✔ Toast notification shows e.g. "2 session NPC directories removed."
6. ✔ Dot-prefixed directories are gone; `belor_hemlock/`, `ameiko_kaijitsu/` etc. are untouched.
7. Click Purge NPCs again (nothing to purge).
8. ✔ Toast shows "0 session NPC directories removed." (no error).

---

## 4. Dice Panel

**What automated tests cover:** queue accumulation, history limit, auto-bonus logic, toggle, normalisation — all with mocked `onRoll`.

**Chains to run:**

**Chain A — basic queue and roll**
1. Click d6 twice, then d20 once.
2. ✔ Queue shows `2d6+1d20`.
3. Click Roll.
4. ✔ History entry shows individual die results and sum, e.g. `4+3+17 = 24`.
5. ✔ Roll button is disabled after rolling (queue cleared).

**Chain B — auto-bonus with pending roll**
1. Trigger a Perception check from the GM (see section 2 Chain C).
2. Set Yanyeeku as the active character (she has Perception +7).
3. Click d20, click Roll.
4. ✔ History shows `13 + Perception +7 = 20 vs DC 18` (numbers will vary).
5. ✔ PASSED or FAILED badge appears.

**Chain C — toggle off, then back on**
1. With a pending Perception roll active and Yanyeeku set as active character:
2. Uncheck Auto Bonus.
3. Click d20, click Roll.
4. ✔ `onRoll` was called with raw total only — history shows no modifier, no label.
5. Re-check Auto Bonus.
6. Click d20, click Roll again.
7. ✔ Modifier is applied again.

**Chain D — history cap**
1. Without a pending roll, roll d20 twelve times in a row.
2. ✔ History shows exactly 10 rows after the 12th roll.
3. ✔ The most recent roll has the highlight style; older rows do not.

---

## 5. Location System

**What automated tests cover:** `LocationIndex` loading (skips `_` dirs, missing `base.md`), alias detection, longest-alias-wins, `<!-- REFERENCE -->` boundary, `format_context` header, `scene_locations` accumulation and re-injection across turns, `context_info` `loc`/`loc_trigger` fields, `%%GENERATE%% type: location` stub creation and index invalidation — all with temp directories.

**What to probe manually (real files and LLM behaviour):**

**Chain A — location detection and intent bar**
1. Boot a session (normal mode, Dev Mode OFF).
2. Send: `We head to the garrison to report the goblin attack.`
3. ✔ Intent bar updates — a location chip shows `Sandpoint Garrison` (or the matched alias `garrison`).
4. ✔ The GM response describes the garrison using the physical/social details from its `base.md` (stone building, duty desk, weapon rack, Hemlock).
5. ✔ No `## Location Reference —` header leaks into the player-facing chat.

**Chain B — longest alias wins in practice**
1. Send: `We enter the Desna Cathedral for the consecration.`
2. ✔ Intent bar shows `Sandpoint Cathedral` — alias matched is `desna cathedral`, not just `cathedral`.
3. Send: `We go to the cathedral.`
4. ✔ Intent bar still shows `Sandpoint Cathedral` — shorter alias also works.

**Chain C — scene_locations persistence across turns**
1. Send: `We enter the Rusty Dragon.` — confirm intent bar shows `The Rusty Dragon`.
2. Send: `Ani orders a drink and sits down.` (no location keyword).
3. ✔ Intent bar still shows `The Rusty Dragon` (location re-injected from `scene_locations`).
4. ✔ The GM response continues to describe the inn context without being told again.
5. Send five more turns with no location keyword.
6. ✔ Location context persists throughout — GM does not suddenly forget where the party is.

**Chain D — location + NPC-at-location combined injection**
1. Send: `We go to the garrison and look for Sheriff Hemlock.`
2. ✔ Intent bar shows both a location (`Sandpoint Garrison`) and an NPC (`Belor Hemlock`).
3. ✔ GM response references both the physical garrison and Hemlock's presence specifically.
4. In Dev Mode, confirm two context blocks appear in the raw output — one `## Location Reference — Sandpoint Garrison` and one `## NPC Reference — Belor Hemlock` — separated by `---`.

**Chain E — all eight seed locations reachable by alias**

Send one turn for each location using one of its aliases. Confirm intent bar fires and the GM response reflects each location's character:

| Input | Expected location |
|---|---|
| `We go to the garrison.` | Sandpoint Garrison |
| `We enter the cathedral.` | Sandpoint Cathedral |
| `We head to the Rusty Dragon.` | The Rusty Dragon |
| `We walk through the festival grounds.` | Festival Grounds |
| `We visit the boneyard at the edge of town.` | Sandpoint Boneyard |
| `We investigate the glassworks.` | Sandpoint Glassworks |
| `We stop at the White Deer for the night.` | The White Deer |
| `We find a spot near the sage stage.` | Sage Stage |

**Chain F — auto-stub from `%%GENERATE%% type: location`**
1. Boot with Dev Mode ON so you can see raw blocks.
2. Send: `I notice a small apothecary called Bottled Solutions on the main street, run by a gossipy old man named Gerhard Pickle.`
3. Wait for the GM response. Look for a `%%GENERATE%%` block with `type: location` in the raw output.
4. If the model wrote one: open `adventure_path/07_locations/` and confirm a new directory (`bottled_solutions/` or similar) was created with a `base.md`.
5. ✔ `base.md` starts with `# Bottled Solutions`.
6. ✔ `**Aliases:**` line is present and includes at least `bottled solutions`.
7. Send: `We step inside Bottled Solutions to browse.`
8. ✔ Intent bar detects the new location — index was invalidated and reloaded after stub creation.

**Chain G — seed file quality audit (read-only)**

Open each `base.md` in `adventure_path/07_locations/` and verify it meets the format spec:

- Starts with `# Canonical Name`
- `**Aliases:**` line is present and has at least 2 aliases
- `## Description`, `## Typical Occupants`, and `## Current State` sections all exist above `<!-- REFERENCE -->`
- Nothing below `<!-- REFERENCE -->` is present in the injected context (verify in dev mode)
- `Current State` reflects the current world state accurately (e.g. garrison is on routine alert before the goblin attack, high alert after)

---

## 5. Character Sidebar and Sheet

**What automated tests cover:** sidebar action menu open/close, Set Active / Clear Active, Open Sheet callbacks, halo class, loading state.

**Chains to run:**

**Chain A — sheet completeness**
1. Click a character avatar → click Open Sheet.
2. Scroll through every section: Abilities, Saves, Skills, Weapons, Spells, Inventory.
3. ✔ No section shows `undefined`, `null`, or `[object Object]`.
4. ✔ HP bar is visible and coloured (green at full HP).
5. Press Escape or click the close button.
6. ✔ Sheet closes; background UI is still interactive.

**Chain B — active speaker in chat**
1. Click a character avatar → click Set Active.
2. ✔ Halo/ring appears on that avatar.
3. ✔ Input bar shows "Speaking as \<Name\>" badge.
4. Type `I ask Ameiko about the raid.` and send.
5. ✔ Player bubble in chat shows `@Yanyeeku: "I ask Ameiko about the raid."`.
6. Click the same avatar → click Clear Active.
7. Type `I look around.` and send.
8. ✔ Player bubble shows `I look around.` with no prefix.

**Chain C — sheet open during streaming**
1. Send a turn that will produce a long GM response.
2. Immediately click a character avatar → Open Sheet while tokens are streaming.
3. ✔ Sheet opens normally.
4. ✔ Tokens continue to appear in the background; no freeze or error.

**Chain D — HP bar colour (requires JSON edit)**
1. Open `ui/public/data/player_01.json`, set `hp.current` to 2 (low HP), save.
2. Refresh the browser, open the character sheet.
3. ✔ HP bar is red.
4. Restore the value.

---

## 6. Streaming Feel

**What automated tests cover:** SSE event parsing, token append, `patch_last` replacement — with mocked streams.

**Chains to run (feel is subjective):**

**Chain A — smooth token flow**
1. Send: `Describe the Swallowtail Festival in vivid detail.` (prompts a longer response)
2. Watch the chat window as tokens arrive.
3. ✔ Text appears token-by-token at a steady rate — no 2–3 second pause then a sudden flood.
4. ✔ Thinking indicator (animated dots) is visible before the first token arrives.
5. ✔ Indicator disappears immediately when the first token appears.

**Chain B — patch_last replacement**
1. Boot with Dev Mode OFF (section filter active).
2. Send any turn.
3. Watch the final message as streaming completes.
4. ✔ No visible flash or duplicate content — the final message replaces the in-progress one cleanly.

**Chain C — input lockout during streaming**
1. Send a turn.
2. Immediately try to type and send another message while streaming is active.
3. ✔ Input bar is disabled (greyed out or non-interactive).
4. ✔ Once streaming ends, input bar becomes active again.

**Chain D — error recovery**
1. Send a turn, then disconnect the network (toggle WiFi off) mid-stream.
2. ✔ An error message appears in the error bar (not a blank hang).
3. Reconnect network. Send another turn.
4. ✔ The session continues; the previous partial message is not duplicated.

---

## 7. Session End

**What automated tests cover:** `stream_end_session` status events, recap header enforcement, boot file write — with mocked Groq.

**Chains to run:**

**Chain A — full end-session flow**
1. Run a session with at least 3 turns.
2. Click End Session.
3. Watch the status bubble: `Wrapping up the session…` → at least one intermediate status → `Session saved. See you next time.`
4. ✔ UI clears (messages gone, session badge gone) after ~2 seconds.
5. Open `outputs/` and confirm `session_001.log.md` exists and contains the turn transcript.
6. Open `sessions/session_002/boot.md` (or the next session number).
7. ✔ File exists and contains a recap section and NPC continuity context.

**Chain B — Kill button (abort before LLM responds)**
1. Start a session, send a couple of turns.
2. Click End Session.
3. Within 2 seconds, click Kill.
4. ✔ Inline confirm appears: "Discard and quit? Yes / No".
5. Click No.
6. ✔ Confirm dismisses; "Ending…" button is still shown; session end continues.
7. Click End Session again on a new session. Click Kill → Yes.
8. ✔ UI resets to pre-boot immediately — no "Session saved" message, no spinner, no ghost session badge.
9. Reboot normally.
10. ✔ No errors; previous incomplete end-session left no broken state.

---

## 8. Provider and Model Switching

**What automated tests cover:** provider branch logic in `_stream_chat`, model payload differences — with mocked HTTP.

**Chains to run:**

**Chain A — model change before boot**
1. Set provider to Groq, change model to `llama-3.1-8b-instant`.
2. Boot a session.
3. ✔ Session badge shows `llama-3.1-8b-instant`.
4. Send: `What is happening at the festival?`
5. ✔ Response streams normally.

**Chain B — Groq rate-limit badge**
1. Boot with Groq (any model). Send 2–3 turns.
2. ✔ Rate-limit badge appears in the header: `⚡ N/M TPM · N/M RPM`.
3. Hover over the badge.
4. ✔ Tooltip shows RPM and TPM reset times.

**Chain C — Groq to Ollama switch (requires Ollama running locally)**
1. Boot session with Groq. Send one turn to confirm Groq works.
2. End session.
3. Switch provider to Ollama, model to `qwen3:4b`.
4. Boot a new session.
5. ✔ Rate-limit badge disappears (Ollama has no rate limits).
6. Send: `Where are we?`
7. ✔ Response streams from Ollama.
8. Switch back to Groq.
9. ✔ Model dropdown resets to the Groq default model.
10. ✔ Rate-limit badge reappears after the first turn.

---

## 9. Edge Cases Worth Probing

**Chain A — very long player input**

Send this wall of text as a single turn:

> `I want to give a full account of everything we've seen so far. We arrived at the Swallowtail Festival this morning and spent time at the stalls. I spoke with Ameiko at the Rusty Dragon, then watched the consecration with Father Zantus. During the ceremony a group of goblins attacked from the north gate — we fought them off, though one of the festival-goers was injured. After the fight, Sheriff Hemlock arrived and began organising a perimeter. I also noticed a goblin carrying a crude map that appeared to show the Glassworks. I want to report all of this to the Mayor and ask what the official response will be, and also find out whether the Sandpoint Mercantile League has heard anything about unusual goblin activity in the Hinterlands before today.`

- ✔ GM responds coherently and addresses the main beats.
- ✔ No Python error or 500 response.
- ✔ Session prompt was not truncated mid-block (check dev mode — context should be intact).

**Chain B — NPC name typo**

Send: `I find Ameikko at the tavern.` (double-k typo)

- ✔ `NpcIndex` alias matching catches it — intent bar shows Ameiko detected.
- ✗ If intent bar is empty, the alias is not registered for this variant.

Then send: `I ask Hemlock about the raids.` (surname only)

- ✔ Intent bar shows Belor Hemlock detected (single-word match via exact index lookup).

**Chain C — two NPCs in one turn**

Send: `I introduce Ameiko to Father Zantus and watch their reaction.`

- ✔ Intent bar shows both NPCs detected.
- ✔ Both NPC profiles were injected (check in dev mode — the system content should reference both).

**Chain D — session length stress**

Send 16 turns of short inputs (just `ok`, `I look around`, `I wait`, etc.) to trigger history trimming.

- ✔ Response latency does not noticeably increase by turn 15–16 vs turn 1–2.
- ✔ No SSE errors or session corruption.

**Chain E — Dev Mode delta inspection**

1. Boot with Dev Mode ON.
2. Send: `I speak at length with Ameiko about her father Lonjiku and her plans for the Rusty Dragon.`
3. Read the full raw response.
4. ✔ A `%%DELTAS%%` block is present and contains at least one entry for `ameiko_kaijitsu`.
5. ✔ The `knowledge:` lines are readable English sentences, not truncated or escaped JSON.

---

## 10. Log Sanity Check

**Chain A — log structure**
After a session with at least 4 turns:

1. Open `http://localhost:8000/api/log/api` in a new tab.
2. Click the most recent log filename.
3. ✔ `duration_ms` values are plausible: 800–20 000 ms for normal Groq turns.
4. ✔ `usage.total_tokens` is present and non-zero (may be `null` for older Groq models).
5. ✔ `messages[0].role` is `"system"` and `messages[0].content` is non-empty.
6. ✔ `preview` field contains the first ~200 characters of the GM response with no garbled escaping.

**Chain B — path traversal guard**
In the browser address bar, try:

```
http://localhost:8000/api/log/api/../../api/session_manager.py
```

- ✔ Server returns 400 or 404, not the contents of `session_manager.py`.
