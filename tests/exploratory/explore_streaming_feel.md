# Exploratory Tests — Streaming Feel and Chat Display

Spec: specs/chat-display.feature

**What automated tests cover:** SSE event parsing, token append, `patch_last` replacement — with
mocked streams.

**Pre-requisites:** `python dev.py --skip-tests` — stack running. These tests are subjective; the
automated suite must be green first.

---

## Chain A — Smooth token flow  <!-- AC-002, AC-003 -->

1. Send: `Describe the Swallowtail Festival in vivid detail.` (prompts a longer response)
2. Watch the chat window as tokens arrive.
3. ✔ Text appears token-by-token at a steady rate — no 2–3 second pause then a sudden flood.
4. ✔ Thinking indicator (animated dots) is visible before the first token arrives.
5. ✔ Indicator disappears immediately when the first token appears.

---

## Chain B — patch_last replacement  <!-- AC-001 -->

1. Boot with Dev Mode OFF (section filter active).
2. Send any turn.
3. Watch the final message as streaming completes.
4. ✔ No visible flash or duplicate content — the final message replaces the in-progress one
   cleanly.

---

## Chain C — Input lockout during streaming  <!-- AC-005 -->

Note: AC-005 is in `player-turn.feature` (input rejected/disabled while streaming).

1. Send a turn.
2. Immediately try to type and send another message while streaming is active.
3. ✔ Input bar is disabled (greyed out or non-interactive).
4. ✔ Once streaming ends, input bar becomes active again.

---

## Chain D — Error recovery

1. Send a turn, then disconnect the network (toggle WiFi off) mid-stream.
2. ✔ An error message appears in the error bar (not a blank hang).
3. Reconnect network. Send another turn.
4. ✔ The session continues; the previous partial message is not duplicated.
