# Event Scheduler — Exploratory Test Cases

Use these alongside the **Event Status** panel (Tools → 🌡 Event Status) to observe live scheduler state while playing. Auto-refresh is on by default; the panel polls every 3 seconds.

---

## Setup

1. Boot a session with the **Scheduler** checkbox enabled.
2. Open **Tools → 🌡 Event Status**.
3. Confirm the panel shows "Scheduler ON" and the `festival_social_phase` event in the Warming Events table at readiness 0.

---

## ET-01 — Basic readiness gain in zone

**Goal:** Confirm readiness increases each turn while the party is in Festival Square.

**Steps:**
1. Send any message that names the festival square, e.g. "I walk through the festival square looking at the stalls."
2. Check Event Status: `festival_social_phase` readiness should increase by base_gain (2) + any action bonuses.
3. Send another message from the same location: "I continue exploring the square."
4. Readiness increases again.

**Pass:** Readiness grows by ≥2 per turn while in the festival square zone.

---

## ET-02 — Zone freeze

**Goal:** Confirm readiness stops when the party leaves the zone.

**Steps:**
1. Get `festival_social_phase` to some readiness > 0 (e.g., ≥ 10) via ET-01.
2. Send a message set outside the festival square: "I walk down the alley toward the garrison."
3. Check Event Status: readiness stays the same, Status badge shows **FROZEN**.
4. Send another out-of-zone message: "I look around the garrison."
5. Readiness is still frozen.

**Pass:** Readiness does not change while frozen; Status shows FROZEN.

---

## ET-03 — Zone re-entry unfreezes

**Goal:** Confirm frozen events resume gaining readiness when the party returns.

**Steps:**
1. Complete ET-02 (event is frozen).
2. Return to the festival square: "We head back to the festival square."
3. Check Event Status: Status badge should switch from FROZEN to WARMING (or ELIGIBLE if above threshold).
4. Readiness increases on the next message.

**Pass:** Frozen clears on re-entry; readiness resumes climbing.

---

## ET-04 — action_gain_map bonus

**Goal:** Confirm that socialize and explore actions add extra readiness.

**Steps:**
1. Send a neutral message in festival square (no socialize/explore keywords): "I look around."
   Note readiness gain (should be 2).
2. Send a socialize-tagged message: "I socialize with the merchants at the stalls."
   Note readiness gain (should be 2 + 3 = 5).
3. Send an explore-tagged message: "I explore the stalls along the east wall."
   Note readiness gain (should be 2 + 2 = 4).

**Pass:** Gains in step 2/3 are higher than step 1 by the configured bonus amounts.

**Note:** Intent tags are single words matched in the player message. "I socialize" matches `socialize:3`; "I explore" matches `explore:2`.

---

## ET-05 — Threshold eligibility

**Goal:** Confirm the ELIGIBLE badge appears once readiness crosses threshold (60).

**Steps:**
1. Keep sending in-zone messages until readiness reaches ≥ 60.
2. Check Event Status: Status badge should show **ELIGIBLE**.
3. Gap column should show — (no gap).

**Pass:** Badge changes from WARMING to ELIGIBLE at threshold. Roll attempts begin.

---

## ET-06 — Trigger roll and event firing

**Goal:** Confirm the event eventually fires once eligible.

**Steps:**
1. Get `festival_social_phase` to ELIGIBLE (readiness ≥ 60).
2. Keep sending messages. Watch the Event Status panel.
3. At some point the event should fire: Event Status shows **ACTIVE EVENT** at the top with a TTL bar, and the Status badge shows **ACTIVE**.
4. Check the system prompt or session log — should contain `[ACTIVE EVENT]` block.

**Pass:** Event fires within a few eligible turns (pity guarantee: 6 failed rolls max).

**Variance:** Firing is probabilistic (d100 ≤ readiness). At readiness 75 it fires ~75% of turns. At readiness 90 it fires ~90%.

---

## ET-07 — Pity guarantee

**Goal:** Confirm the event fires after exactly 6 missed rolls (pity rule).

**Steps:**
1. Set readiness to just above threshold (e.g., 61). This lowers the trigger probability.
2. Keep sending messages until the event fires.
3. Check the session log (`Tools → View Session Log`) — count the `miss — roll` lines for the event.

**Pass:** The event fires no later than the 6th eligible turn (failed_rolls = 6 triggers pity).

---

## ET-08 — Active event TTL countdown

**Goal:** Confirm the active event expires automatically after 5 turns.

**Steps:**
1. Let an event fire (ACTIVE state).
2. Note the TTL bar value (should start at 5 turns).
3. Send 5 messages (any content — even from outside the zone).
4. After the 5th message, Event Status should show "No active event" and the event should appear in **Completed**.

**Pass:** Active event clears after exactly 5 turns. No LLM output needed.

---

## ET-09 — TTL ticks during combat

**Goal:** Confirm TTL continues to decrement during combat even without zone detection.

**Steps:**
1. Let an event fire (ACTIVE state, TTL = 5).
2. Start a combat encounter (trigger a goblin fight or use a %%COMBAT%% scenario).
3. Take a few combat turns.
4. Check Event Status: TTL should have decremented by the number of combat turns taken.

**Pass:** TTL decrements in combat; event expires on schedule even mid-fight.

---

## ET-10 — Active event blocks new triggers

**Goal:** Confirm a second warm event cannot fire while one is already active.

**Steps:**
1. Let `festival_social_phase` fire (ACTIVE).
2. Imagine a second event is also warm and eligible (or observe it if one exists).
3. Send several messages in its zone.
4. Event Status should still show only `festival_social_phase` as ACTIVE.

**Pass:** No second event fires while first is active. The blocking is intentional (MVP: one at a time).

---

## ET-11 — Completed event does not re-trigger

**Goal:** Confirm a completed event is permanently excluded from the trigger pool.

**Steps:**
1. Let an event expire (TTL hits 0, appears in Completed).
2. Keep sending messages in its zone.
3. Event Status shows it in the Completed list, not in Warming Events.
4. No trigger roll is made for it.

**Pass:** Completed events do not re-enter the warming pool within the session.

---

## ET-12 — Scheduler OFF leaves %%EVENT%% path active

**Goal:** Confirm the original LLM-triggered %%EVENT%% path still works when Scheduler is OFF.

**Steps:**
1. Boot session with **Scheduler unchecked**.
2. Open Event Status: should show "Scheduler OFF" and no warm events.
3. Play through to a natural %%EVENT%% trigger point (e.g., sunset → cathedral_alarm).
4. The event should still fire via the LLM path.

**Pass:** %%EVENT%% path unaffected by scheduler flag; Event Status shows no warm events.

---

## ET-13 — Session log entries

**Goal:** Confirm the session log captures all scheduler transitions.

**Steps:**
1. Play through a cycle: zone entry → readiness gain → eligible → trigger → TTL expiry.
2. Open `Tools → View Session Log`.
3. Search for `[Scheduler:`.

**Expected log entries:**
- `[Scheduler: festival_social_phase readiness 0→2 (+2 @ Festival Square)]` — gain
- `[Scheduler: festival_social_phase miss — roll 85 vs 62 (failed=1)]` — miss
- `[Scheduler: festival_social_phase TRIGGERED via roll(47) — readiness=72, failed_rolls=2]` — fire
- `[Scheduler: festival_social_phase EXPIRED (TTL exhausted)]` — expiry

**Pass:** All four transition types appear in the log at their correct turns.

---

## ET-14 — Readiness bar visual accuracy

**Goal:** Confirm the readiness bar and threshold marker are visually correct.

**Steps:**
1. Open Event Status with an event at ~40% readiness (below threshold 60).
2. Observe: bar fill should be short, threshold marker (amber line) visible on the right side of the fill.
3. Raise readiness above threshold.
4. Observe: bar fill passes the threshold marker, badge changes to ELIGIBLE.

**Pass:** Bar fill width matches readiness %; threshold line is at the correct position.

---

## Common failure patterns to watch for

| Symptom | Likely cause |
|---------|-------------|
| Readiness stuck at 0 forever | Location file missing or alias doesn't match player text |
| Readiness gains every turn regardless of location | Zone list in `## Schedule` is empty or zone name typo normalises to always match |
| Event never triggers despite readiness 100 | Pity limit not firing — check `failed_rolls` column in Event Status |
| Active event doesn't expire | TTL not ticking — confirm `_tick_event_scheduler` is being called in both narrative and combat branches |
| [ACTIVE EVENT] block missing from LLM output | Scheduler flag may be off, or `active_event_id` cleared before `_format_active_event_context` is called |
