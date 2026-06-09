# Bug Tracker

Open bugs found by code review. Use the same markup rules as TODO.md.

- [ ] Item text - open bug
- [x] Item text - fixed
- ~~[ ] Item text~~ - obsolete / won't fix

---

## Event Scheduler (feat/characters branch)

Found by automated code review, 2026-06-09.

---

### BUG-001 — `frozen` flag not enforced in `_trigger_phase` *(FIXED)*

- [x] **Severity: High** — events fire out-of-zone, violating the freeze contract
- **File:** `api/session_manager.py` — `_trigger_phase`
- **Symptom:** An event that accumulated `readiness >= threshold` while in-zone will still
  be triggered by roll or pity on a turn the player is not in the required zone.
  `_tick_event_scheduler` sets `we.frozen = True` then unconditionally calls
  `_trigger_phase`, which checks `readiness`, `completed_events`, `cooldowns`, and
  `failed_rolls` — but never `we.frozen`. The freeze flag was cosmetic state only.
- **Fix:** Add `if we.frozen: continue` at the top of the eligible-event loop in
  `_trigger_phase`, before the pity and roll checks.

---

### BUG-002 — Cooldown only decrements when `readiness >= threshold` *(FIXED)*

- [x] **Severity: High** — cooldown semantics are wrong; a cooldown below threshold never ticks
- **File:** `api/session_manager.py` — `_trigger_phase`
- **Symptom:** `rt.cooldowns[event_id] -= 1` is inside the block guarded by
  `if we.readiness < we.threshold: continue`. An event whose readiness drops (or was
  never raised) below threshold while a cooldown is active will never have its cooldown
  decremented — it becomes permanent until readiness rises again. A designer who sets a
  cooldown expecting "re-fires after N turns" gets "re-fires after N above-threshold turns".
- **Fix:** Move cooldown decrement to a dedicated pass in `_tick_event_scheduler` that
  runs unconditionally every turn (before the readiness-gain loop). Remove the decrement
  from `_trigger_phase`; keep only the `> 0` skip guard there.

---

### BUG-003 — `event_runtime` written to `state.json` but never restored *(FIXED — documented)*

- [x] **Severity: Medium** — scheduler progress (readiness, completed_events, cooldowns)
  is silently lost on server restart
- **File:** `api/session_manager.py` — `_write_session_state` / `create_session`
- **Symptom:** `_serialize_event_runtime` writes the full `EventRuntime` to `state.json`
  every turn. There is no `_load_session_state` or equivalent read path anywhere in the
  codebase. `create_session` always initialises `event_runtime` from scratch (zeroed
  readiness, empty completed_events) using only static definitions from event files.
  The persisted data is dead weight.
- **Fix (interim):** Added explicit comments to `_write_session_state` and `create_session`
  documenting that `event_runtime` in `state.json` is written for external inspection only
  and is not read back on restart. Proper state restoration is tracked as `E1-9` in
  `EVENT-TODO.md`.

---

### BUG-004 — `_SCHEDULER_DEFAULT_TTL` duplicated across Python and TypeScript

- [ ] **Severity: Low** — visual TTL bar shows wrong scale if backend constant changes
- **File:** `api/session_manager.py:2678`, `ui/src/components/EventStatus.tsx:5`
- **Symptom:** Both files independently define the same constant as `5`. `EventStatus.tsx`
  uses it as the denominator for the `TtlBar` width calculation. If the Python value is
  changed (e.g. to 8 for longer event arcs), the bar overflows or clips with no warning.
- **Fix:** Expose the value via the `/api/sessions/{id}/event_status` response (add a
  `default_ttl` field) and derive the bar scale from the API rather than a hardcoded local
  constant.

---

### BUG-005 — `completed_events` is a `list`, not a `set` — O(n) membership per turn

- [ ] **Severity: Low** — negligible at current session scale; structural inconsistency
- **File:** `api/session_manager.py:1152`
- **Symptom:** `event_id in rt.completed_events` is checked inside the warm_events loop
  in both `_tick_event_scheduler` (line ~2757) and `_trigger_phase` (line ~2705) — two
  O(n) list scans per warm event per turn. As completed_events grows the loop degrades.
- **Fix:** Change `completed_events: list = field(default_factory=list)` to
  `completed_events: set = field(default_factory=set)`. Change the one write site
  (`.append` → `.add`). Wrap in `list()` in `_serialize_event_runtime` and confirm the
  explicit `list(rt.completed_events)` in `get_event_status` still works.

---

### BUG-006 — `_serialize_event_runtime` and `get_event_status` serialize `WarmEvent` independently

- [ ] **Severity: Low** — maintenance risk; serialization paths can diverge silently
- **File:** `api/session_manager.py:1289`, `api/main.py:136`
- **Symptom:** `_serialize_event_runtime` calls `dataclasses.asdict(rt)` (serializes the
  whole `EventRuntime` for `state.json`). `get_event_status` in `main.py` calls
  `_dc.asdict(we)` inline for each `WarmEvent` in the API response. These are independent
  code paths. A field rename or transformation applied to one will not propagate to the
  other, causing `state.json` and the debug panel to show different shapes.
- **Fix:** Extract a `_serialize_warm_event(we: WarmEvent) -> dict` helper and use it in
  both `_serialize_event_runtime` and `get_event_status`.
