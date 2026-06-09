# Event System Backlog

All event-triggering and event-chain work lives here. [TODO.md](TODO.md) links here.

Same markup rules as TODO.md apply.

- [ ] Item text - open task
- [x] Item text - completed task
- ~~[ ] Item text~~ - obsolete / cancelled task
- Sub-bullets use the same - [ ] format, indented two spaces
- Never use plain - bullets for tasks - everything actionable must have a checkbox
- Bold the item title when it has a longer description below it

---

## Goal

Build an event system that supports both:

- Soft pacing events (temperature/readiness based; probabilistic)
- Hard story chains (deterministic once entered)

The system should persist per-session in sessions/session_NNN/state.json so events can pause, resume, and survive restarts.

---

## Tier E1 - MVP (ship this first)

Minimum useful implementation: one active event, warming events, threshold roll, and simple hard-chain progression.

- [x] **E1-1 - Session state schema: event_runtime block**
  - [x] Add event_runtime to state snapshot with: active_event_id, active_chain_id, active_node_id, warm_events, completed_events, cooldowns
  - [x] Define warm_events entries with: readiness (0-100), threshold, failed_rolls, frozen, last_zone_match_turn
  - [x] Keep schema backward compatible when loading old sessions (missing event_runtime -> defaults via dataclass default_factory)
  - [x] Gate all scheduler logic on session.event_scheduler (boot-time flag set via UI "Scheduler" checkbox); when off, only the %%EVENT%% LLM path runs

- [x] **E1-2 - Event definition format (data files)**
  - [x] Extend existing adventure_path/02_events files with a ## Schedule section; only files with this section are loaded as warm events by the scheduler
  - [x] ## Schedule section fields: zones (comma-separated location names), threshold, base gain, action gain (tag:value pairs), priority
  - [x] EventIndex.schedulable_entries() public method returns only schedulable entries; create_session uses this to populate warm_events at boot
  - [x] Zone names normalize underscores↔spaces so slug-style names ("festival_square") match display-name canonicals ("Festival Square")
  - [x] action_gain_map keys must be single words — whitespace split is used for matching; documented in code and here
  - [ ] Add chain metadata fields: chain_id, node_id, next_node_id, hard_transition (E1-6)
  - [ ] Add a small validator for required keys to fail fast on malformed ## Schedule sections

- [x] **E1-3 - Turn tick: readiness update**
  - [x] Tick runs inside _inject_context after zone/location detection (loc_canonical available)
  - [x] If current zone matches event's zones list: readiness += base_gain + action_gain_map bonuses
  - [x] If zone does not match: freeze readiness (no gain, no decay in MVP)
  - [x] Clamp readiness to 0-100
  - [x] TTL tick also runs in combat branch (location=None, no new gains) so active events expire correctly during combat

- [x] **E1-4 - Threshold trigger roll**
  - [x] Start rolling only when readiness >= threshold
  - [x] Roll once per turn: d100 <= readiness triggers event
  - [x] Increment failed_rolls on miss
  - [x] Pity rule: auto-trigger after N=6 failed rolls above threshold

- [x] **E1-5 - Active event lifecycle**
  - [x] On trigger, set active_event_id, record turns_remaining (TTL=5), log source (roll or pity)
  - [x] Prevent other soft events from starting while an event is active (_trigger_phase returns early)
  - [x] Decrement turns_remaining each turn; on TTL expiry clear active_event_id and append to completed_events

- [ ] **E1-6 - Hard-chain handling (basic)**
  - [ ] If active_chain_id exists, ignore soft-event rolls by default
  - [ ] Resolve next node via hard_transition fields when completion condition is met
  - [ ] On final node, clear active_chain_id and return control to soft scheduler

- [x] **E1-7 - Prompt integration (minimal)**
  - [x] Inject compact [ACTIVE EVENT] block (event id, readiness at trigger, turns remaining) via _format_active_event_context() helper
  - [ ] Inject one compact [CHAIN STATE] block when active_chain_id is set (E1-6)
  - [x] Full event-map text not duplicated in this block

- [x] **E1-8 - Logging and diagnostics**
  - [x] Log readiness changes (old→new, gain, zone) in session log each tick
  - [x] Log trigger source (roll value or pity) and readiness/failed_rolls at trigger time
  - [x] Log TTL expiry on completion
  - [ ] Add a debug endpoint or log section to inspect event_runtime at runtime

- [ ] **E1-9 - Restore event_runtime from state.json on session reload (BUG-003)**
  - [ ] Add `_restore_event_runtime(session, state_dict)` called from `create_session` when state.json exists
  - [ ] Reconstruct `WarmEvent` instances from stored dicts; restore readiness, failed_rolls, completed_events, cooldowns
  - [ ] Merge with current event file definitions so newly-added schedulable events appear correctly
  - [ ] Add round-trip integration test: boot → tick several turns → reload → assert readiness preserved

- [x] **E1-T - Tests (must-have for MVP)**
  - [x] Unit: readiness gain when zone matches, freeze when not
  - [x] Unit: action_gain_map bonus applied only to matching event
  - [x] Unit: threshold roll hit/miss, failed_rolls increment
  - [x] Unit: pity fires at exactly N=6 failed rolls
  - [x] Unit: active event blocks other soft triggers
  - [x] Unit: TTL decrement and expiry → completed_events
  - [x] Unit: TTL ticks during combat (location=None, no gain, only decrement)
  - [x] Unit: zone normalization — underscore slug matches display-name canonical
  - [x] Unit: schedulable_entries() returns only events with ## Schedule section
  - [x] Integration: event_runtime serialized to and round-tripped from state.json
  - [x] Integration: [ACTIVE EVENT] block appears in system_content when active_event_id set
  - [x] Integration: scheduler transitions (gain, trigger, pity, expiry) logged to session log
  - Tests live in tests/test_event_scheduler.py — 43 tests, AC-001–AC-012

---

## Tier E2 - Recommended Stability Improvements

Important quality and pacing controls, but not strictly required to get the first version running.

- [ ] **E2-1 - Split readiness and urgency**
  - [ ] Add urgency (0-100) so interruption policy can be separated from trigger chance
  - [ ] Use readiness for trigger eligibility; use urgency for whether to cut in immediately

- [ ] **E2-2 - Scene-safe interrupt policy**
  - [ ] Add per-event interrupt_policy: none | soft | hard
  - [ ] If trigger occurs mid-action, queue pending_interrupt and start after a short action close

- [ ] **E2-3 - Multi-event arbitration**
  - [ ] If multiple events trigger on same turn, choose winner by weighted roll
  - [ ] Suggested weight: readiness * priority * narrative_fit
  - [ ] Queue losers instead of resetting them

- [ ] **E2-4 - Cooldowns and anti-repeat guards**
  - [ ] Add per-event cooldown_turns and max_fires_per_session
  - [ ] Prevent immediate re-fire loops for ambient events

- [ ] **E2-5 - Out-of-zone decay option**
  - [ ] Add optional decay_after_freeze (for long detours)
  - [ ] Default behavior remains freeze-only unless event opts in

- [ ] **E2-T - Tests**
  - [ ] Arbitration determinism under fixed random seed
  - [ ] Interrupt queue behavior during active actions
  - [ ] Cooldown and max-fires constraints

---

## Tier E3 - Authoring and Content Scale

Tooling and content quality features for larger campaigns.

- [ ] **E3-1 - Event authoring template and linter**
  - [ ] Add EVENT_TEMPLATE.md for soft events and chain nodes
  - [ ] Add linter script that validates IDs, chain references, and duplicate node IDs

- [ ] **E3-2 - Chain graph checks**
  - [ ] Detect dead-end nodes, orphaned nodes, and cycles unless explicitly allowed
  - [ ] Fail CI (or local script) on broken chain graphs

- [ ] **E3-3 - Event balancing data pass**
  - [ ] Add per-event recommended gains and thresholds in docs
  - [ ] Review Act I event timings against real session logs

- [ ] **E3-T - Tests**
  - [ ] Validation tests for malformed graphs and missing references
  - [ ] Golden tests for known good chain files

---

## Tier E4 - Optional Nice-to-Have

Useful UX and analytics, not required for core gameplay.

- [x] **E4-1a - Event Status debug panel (MVP read-only dashboard)**
  - [x] GET /api/sessions/{id}/event_status endpoint — returns scheduler_enabled, turn_number, active_event_id, warm_events (full WarmEvent), completed_events, cooldowns
  - [x] EventStatus.tsx — overlay panel in Tools dropdown (session-only); active event card with TTL bar; warm events table with readiness bars and threshold markers; status badges (ACTIVE/ELIGIBLE/FROZEN/WARMING/DONE); auto-refresh every 3 s; manual refresh button
  - [x] Spec: specs/event-status-panel.feature (AC-001–AC-015)
  - [x] Tests: tests/test_event_status.py (AC-001–AC-010 backend)
  - [x] Exploratory test cases: docs/event_scheduler_exploratory_tests.md (ET-01–ET-14)

- [ ] **E4-1b - GM event dashboard (controls)**
  - [ ] Optional GM controls: nudge readiness, force trigger, skip node
  - [ ] Depends on E4-1a

- [ ] **E4-2 - Event timeline export**
  - [ ] Write an event timeline artifact per session to outputs/
  - [ ] Include: trigger turn, cause, chain transitions, completion turn

- [ ] **E4-3 - Adaptive pacing heuristics**
  - [ ] Adjust gains based on session length or inactivity
  - [ ] Keep this opt-in and logged for transparency

- [ ] **E4-4 - Readiness history log per event**
  - [ ] For each warm event, record a history of every readiness change: turn number, zone where the gain happened, gain amount, and cumulative readiness at that point
  - [ ] Also record freeze turns: turn number and zone/reason the tick was skipped
  - [ ] Write the history to the session log (or a dedicated outputs/ artifact) so it is readable after the session
  - [ ] Useful for tuning base_gain, threshold, and zone definitions against real session data

---

## Suggested implementation order

- [ ] Build E1-1 through E1-4 first (state + tick + trigger)
- [ ] Then E1-5 through E1-7 (lifecycle + chain lock + prompt injection)
- [ ] Then E1-T before moving on
- [ ] After MVP is stable, pick E2-2 and E2-4 first for player-facing quality
