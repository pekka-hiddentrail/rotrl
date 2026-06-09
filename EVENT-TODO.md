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

- [ ] **E1-1 - Session state schema: event_runtime block**
  - [ ] Add event_runtime to state snapshot with: active_event_id, active_chain_id, active_node_id, warm_events, completed_events, cooldowns
  - [ ] Define warm_events entries with: readiness (0-100), threshold, failed_rolls, frozen, last_zone_match_turn
  - [ ] Keep schema backward compatible when loading old sessions (missing event_runtime -> defaults)
  - [ ] Gate all scheduler logic on session.event_scheduler (boot-time flag set via UI "Scheduler" checkbox); when off, only the %%EVENT%% LLM path runs

- [ ] **E1-2 - Event definition format (data files)**
  - [ ] Extend existing adventure_path/02_events files with a ## Schedule section; only files with this section are loaded as warm events by the scheduler
  - [ ] ## Schedule section fields: id, type (soft|chain_node), zones (list of location names), threshold, base_gain, action_gain_map (intent tag -> gain), priority
  - [ ] Add chain metadata fields: chain_id, node_id, next_node_id, hard_transition
  - [ ] Add a small validator for required keys to fail fast on malformed ## Schedule sections

- [ ] **E1-3 - Turn tick: readiness update**
  - [ ] Add tick step inside _inject_context, after zone/location detection (tick needs the resolved zone to evaluate match)
  - [ ] If current zone matches event's zones list: readiness += base_gain
  - [ ] If zone does not match: freeze readiness (no gain, no decay in MVP)
  - [ ] Apply action-based boosts from detected player intent tags (action_gain_map)
  - [ ] Clamp readiness to 0-100

- [ ] **E1-4 - Threshold trigger roll**
  - [ ] Start rolling only when readiness >= threshold
  - [ ] Roll once per turn: d100 <= readiness triggers event
  - [ ] Increment failed_rolls on miss
  - [ ] Add pity rule: auto-trigger after N failed rolls above threshold (start with N=6)

- [ ] **E1-5 - Active event lifecycle**
  - [ ] On trigger, set active_event_id, record turns_remaining (TTL), and mark event as in_progress
  - [ ] Prevent other soft events from starting while an event is active
  - [ ] Decrement turns_remaining each turn; on TTL expiry (backend-driven), clear active_event_id and write completed_events/cooldowns — no LLM signal needed

- [ ] **E1-6 - Hard-chain handling (basic)**
  - [ ] If active_chain_id exists, ignore soft-event rolls by default
  - [ ] Resolve next node via hard_transition fields when completion condition is met
  - [ ] On final node, clear active_chain_id and return control to soft scheduler

- [ ] **E1-7 - Prompt integration (minimal)**
  - [ ] Inject one compact [ACTIVE EVENT] block when active_event_id is set
  - [ ] Inject one compact [CHAIN STATE] block when active_chain_id is set
  - [ ] Do not inject full event map in MVP

- [ ] **E1-8 - Logging and diagnostics**
  - [ ] Log readiness changes and trigger rolls in session log
  - [ ] Log chain transitions and completion conditions
  - [ ] Add a debug endpoint or log section to inspect event_runtime at runtime

- [ ] **E1-T - Tests (must-have for MVP)**
  - [ ] Unit: readiness gain/freeze/clamp
  - [ ] Unit: threshold roll + pity behavior
  - [ ] Unit: hard-chain transitions and lockout of soft rolls
  - [ ] Integration: event_runtime written to and restored from state.json
  - [ ] Integration: active event injected to prompt context

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

- [ ] **E4-1 - GM event dashboard**
  - [ ] Read-only panel showing active event, warming events, readiness values, and pending interrupts
  - [ ] Optional GM controls: nudge readiness, force trigger, skip node

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
