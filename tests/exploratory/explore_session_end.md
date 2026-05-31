# Exploratory Tests — Session End and Recap

Spec: specs/session-end-recap.feature

**What automated tests cover:** `stream_end_session` status events, recap header enforcement,
boot file write — with mocked Groq.

**Pre-requisites:** `python dev.py --skip-tests` — stack running with at least one active session.

---

## Chain A — Full end-session flow  <!-- AC-001, AC-002, AC-003 -->

1. Run a session with at least 3 turns.
2. Click End Session.
3. Watch the status bubble: `Wrapping up the session…` → at least one intermediate status →
   `Session saved. See you next time.`
4. ✔ UI clears (messages gone, session badge gone) after ~2 seconds.
5. Open `outputs/` and confirm `session_001.log.md` exists and contains the turn transcript.
6. Open `sessions/session_002/boot.md` (or the next session number).
7. ✔ File exists and contains a recap section and NPC continuity context.

---

## Chain B — Kill button (abort before LLM responds)  <!-- AC-004, AC-001 -->

1. Start a session, send a couple of turns.
2. Click End Session.
3. Within 2 seconds, click Kill.
4. ✔ Inline confirm appears: "Discard and quit? Yes / No".
5. Click No.
6. ✔ Confirm dismisses; "Ending…" button is still shown; session end continues.
7. Click End Session again on a new session. Click Kill → Yes.
8. ✔ UI resets to pre-boot immediately — no "Session saved" message, no spinner,
   no ghost session badge.
9. Reboot normally.
10. ✔ No errors; previous incomplete end-session left no broken state.
