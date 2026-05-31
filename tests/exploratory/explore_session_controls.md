# Exploratory Tests — Session Controls and Header

Spec: specs/session-controls.feature

**What automated tests cover:** Header component renders all controls in correct states; provider
toggle + model dropdown; Benchmarks/Coverage buttons; purge/Kill inline confirms; rate-limit badge.

**Pre-requisites:** `python dev.py --skip-tests` — stack running.

---

## Chain A — Pre-boot control state  <!-- AC-001, AC-002, AC-003 -->

1. Open `http://localhost:5173` without booting.
2. ✔ Provider dropdown and model dropdown are visible and interactive.
3. ✔ Session number input is editable.
4. ✔ Boot button is enabled.
5. Change provider from Groq to Ollama.
6. ✔ Model dropdown options change to Ollama models.
7. Change back to Groq.
8. ✔ Model dropdown resets to Groq models.

---

## Chain B — Post-boot header state  <!-- AC-004, AC-005 -->

1. Boot session 1 (Groq).
2. ✔ Session badge appears: `Session 1 · <model>`.
3. ✔ Provider and session number controls are now hidden or locked.
4. ✔ View Log, API Logs, Benchmarks, Coverage, Purge NPCs, End Session buttons are all visible.
5. Click **View Log**.
6. ✔ A new browser tab opens pointing to the session log.

---

## Chain C — Purge NPCs inline confirm  <!-- AC-006 -->

1. Ensure at least one dot-prefixed NPC directory exists.
2. Click **Purge NPCs**.
3. ✔ Inline confirm appears: "Purge session NPCs? Yes / No".
4. Click **No**.
5. ✔ Confirm dismisses; no NPCs were removed.
6. Click **Purge NPCs** → **Yes**.
7. ✔ Toast notification shows count removed; dot-prefixed dirs gone.

---

## Chain D — Groq rate-limit badge  <!-- AC-007 -->

1. Boot with Groq. Send 2 turns.
2. ✔ `⚡ N/M TPM · N/M RPM` badge appears in the header.
3. Hover the badge. ✔ Tooltip shows reset times.

---

## Chain E — Kill button aborts end session  <!-- AC-008 -->

1. Boot a session, send a couple of turns.
2. Click **End Session**.
3. Within 2 seconds, click **Kill** → **Yes**.
4. ✔ UI resets to pre-boot state immediately.
5. Reboot normally. ✔ No errors.

---

## Chain F — Benchmarks and Coverage buttons  <!-- (session-controls: AC-004) -->

1. Boot a session.
2. Click **Benchmarks**.
3. ✔ Token Benchmarks modal opens; Escape closes it.
4. Click **Coverage**.
5. ✔ Feature Coverage Matrix modal opens; shows summary bar with covered/total/gap counts.
6. Escape closes it.
