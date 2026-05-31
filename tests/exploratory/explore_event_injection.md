# Exploratory Tests — Event Injection

Spec: specs/event-injection.feature

**What automated tests cover:** `EventIndex` loading, file parsing, event firing from `%%EVENT%%`
tags, TTL decrement and expiry, duplicate guard, unknown-ID guard, event map in system prompt,
`%%EVENT%%` hidden from player token stream, `active_events` in SSE context event, and a
double-write regression — all with temp directories.

**Pre-requisites:** `python dev.py --skip-tests` — stack running.

---

## Chain A — Event fires from goblin attack  <!-- AC-001, AC-006, AC-008 -->

1. Boot a session (Dev Mode ON).
2. Send: `I hear an alarm bell and shouts from the north gate — goblins!`
3. ✔ The raw GM response contains `%%EVENT%% goblin_attack_starts` on its own line.
4. Send a follow-up turn: `I draw my weapon and charge toward the commotion.`
5. Open `outputs/api_log/` and inspect the JSON for this second turn.
6. ✔ `messages[0].content` contains a block starting with `## Active Event — goblin_attack_starts`.
7. ✔ GM response references combat details drawn from the injected event content.

> **Note:** Active events are injected silently into the system prompt — they do not appear in the
> intent bar. The intent bar shows only NPCs, skills, and locations.

> **Known LLM quirk:** The model sometimes writes `%%EVENT%%` on its own line (as a section header)
> followed by `%%EVENT%% goblin_attack_starts` on the next line. Both lines in dev output = event
> still fires correctly.

---

## Chain B — Event hidden from player (non-dev)  <!-- AC-007 -->

1. Boot a session with Dev Mode OFF.
2. Play through to a point where the GM fires `%%EVENT%% goblin_attack_starts`.
3. ✔ No `%%EVENT%%` line appears in the player chat — only narrative prose is visible.
4. ✔ The intent bar still updates normally.

---

## Chain C — Event expires after N turns  <!-- AC-002 -->

1. Trigger `goblin_attack_starts` (see Chain A, step 3).
2. Send 3 more player turns (any content — "I look around", "I wait", etc.).
3. After each turn, open the corresponding API log JSON and check
   `raw_request.messages[0].content`.
4. ✔ `## Active Event — goblin_attack_starts` block is present on each of those turns.
5. Keep sending turns until the block disappears from `messages[0].content`.
6. ✔ On that same turn, the `context` SSE event has `active_events: []`.
7. Note how many turns the event was active — should match the `**Expires:**` value in
   `adventure_path/02_events/goblin_attack_starts.md`.

> The system prompt is never visible in the chat window. Inspect it via the API log JSON
> (`messages[0].content`) or the session log (`outputs/session_NNN_*.log.md`,
> inside each `<details>LLM payload</details>` block).

---

## Chain D — Wave transition replaces active event  <!-- AC-001, AC-003 -->

1. Boot a session. Trigger `goblin_attack_starts` (Chain A).
2. Send turns until the GM produces `%%EVENT%% fire_phase_begins`.
3. Open the API log for the turn *after* `fire_phase_begins` fires.
4. ✔ `messages[0].content` contains `## Active Event — fire_phase_begins` (Wave 2 content).
5. ✔ The `context` SSE event has `active_events` containing `fire_phase_begins`.
6. ✔ If `goblin_attack_starts` still has turns remaining, both events appear simultaneously.

---

## Chain E — Event map visible in system prompt  <!-- AC-006 -->

1. Boot Dev Mode ON.
2. Inspect the first LLM payload in `outputs/api_log/`.
3. ✔ The system prompt contains an `EVENT MAP` section listing at minimum `goblin_attack_starts`,
   `fire_phase_begins`, `cavalry_arrives`, `attack_repelled` with their trigger conditions.
4. ✔ The map includes the `%%EVENT%%` syntax instruction.
