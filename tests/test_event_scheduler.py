"""Tests for the temperature-based event scheduler (specs/event-temperature-mvp.feature).

Covers AC-001 through AC-013:
  AC-001  event_runtime serialized to state.json
  AC-002  missing event_runtime backfilled on load (dataclass defaults)
  AC-003  zone match increases readiness
  AC-004  non-matching zone freezes readiness
  AC-005  action_gain_map boost applied per-event
  AC-006  trigger roll only starts at threshold
  AC-007  d100 <= readiness triggers; miss increments failed_rolls
  AC-008  pity fires after N=6 failed rolls
  AC-009  active event expires after TTL (no LLM signal)
  AC-010  active event blocks other soft triggers
  AC-011  [ACTIVE EVENT] block injected into system prompt
  AC-012  scheduler transitions logged in session log
  AC-013  zone detection requires a matching location entry
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api.context.event_index import EventIndex
from api.context.location_lookup import LocationIndex
from api.session_manager import (
    EventRuntime,
    GameSession,
    WarmEvent,
    _fire_event,
    _format_active_event_context,
    _inject_context,
    _tick_event_scheduler,
    _trigger_phase,
    _write_session_state,
)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_session(**kwargs) -> GameSession:
    defaults = dict(
        id=str(uuid.uuid4()),
        session_number=1,
        model="test-model",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=False,
        event_scheduler=True,
        provider="ollama",
        num_ctx=2048,
        num_gpu=999,
        system_prompt="BASE",
        log_path=None,
    )
    defaults.update(kwargs)
    return GameSession(**defaults)


def _make_warm_event(**kwargs) -> WarmEvent:
    defaults = dict(
        readiness=0.0,
        threshold=75.0,
        base_gain=1.0,
        zones=["festival_square"],
    )
    defaults.update(kwargs)
    return WarmEvent(**defaults)


def _make_schedulable_file(tmp_path: Path, event_id: str, zones: str = "festival_square",
                            threshold: float = 60.0, base_gain: float = 2.0,
                            action_gain: str = "") -> Path:
    events_dir = tmp_path / "adventure_path" / "02_events"
    events_dir.mkdir(parents=True, exist_ok=True)
    action_line = f"action gain: {action_gain}\n" if action_gain else ""
    f = events_dir / f"{event_id}.md"
    f.write_text(
        f"**Event:** {event_id}\n"
        f"**Trigger:** test trigger\n\n"
        f"## Schedule\n"
        f"zones: {zones}\n"
        f"threshold: {threshold}\n"
        f"base gain: {base_gain}\n"
        f"{action_line}"
        f"\n<!-- INJECT -->\n\nEvent content.\n",
        encoding="utf-8",
    )
    return f


def _patch_state_root(tmp_path: Path):
    def _fake_path(session):
        return tmp_path / f"session_{session.session_number:03d}" / "state.json"
    return patch("api.session_manager._session_state_path", side_effect=_fake_path)


def _read_state(tmp_path: Path, session_number: int = 1) -> dict:
    return json.loads((tmp_path / f"session_{session_number:03d}" / "state.json").read_text(encoding="utf-8"))


# ── AC-001/002 — state.json serialization ────────────────────────────────────

class TestEventRuntimeSerialization:
    """AC-001: event_runtime written to state.json. AC-002: missing key backfills safely."""

    def test_event_runtime_key_present(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        assert "event_runtime" in _read_state(tmp_path)

    def test_event_runtime_has_required_keys(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        rt = _read_state(tmp_path)["event_runtime"]
        for key in ("active_event_id", "active_chain_id", "active_node_id",
                    "warm_events", "completed_events", "cooldowns"):
            assert key in rt, f"missing key: {key}"

    def test_warm_events_serialized(self, tmp_path):
        session = _make_session()
        session.event_runtime.warm_events["my_event"] = _make_warm_event(readiness=42.0, threshold=60.0)
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        we = _read_state(tmp_path)["event_runtime"]["warm_events"]["my_event"]
        assert we["readiness"] == pytest.approx(42.0)
        assert we["threshold"] == pytest.approx(60.0)

    def test_active_event_id_serialized(self, tmp_path):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event()
        session.event_runtime.active_event_id = "evt"
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        assert _read_state(tmp_path)["event_runtime"]["active_event_id"] == "evt"

    def test_default_event_runtime_is_safe(self):
        """AC-002: GameSession with no explicit event_runtime still has safe defaults."""
        session = _make_session()
        rt = session.event_runtime
        assert rt.active_event_id is None
        assert rt.warm_events == {}
        assert rt.completed_events == []
        assert rt.cooldowns == {}


# ── AC-003/004 — readiness gain and freeze ───────────────────────────────────

class TestReadinessGainAndFreeze:
    """AC-003: zone match increases readiness. AC-004: no match freezes it."""

    def test_zone_match_increases_readiness(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=20.0, base_gain=1.0,
                                                                     threshold=200.0,
                                                                     zones=["festival_square"])
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(21.0)

    def test_readiness_clamped_at_100(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=99.5, base_gain=5.0,
                                                                     threshold=200.0,
                                                                     zones=["festival_square"])
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(100.0)

    def test_zone_mismatch_freezes_readiness(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=48.0, threshold=200.0,
                                                                     zones=["festival_square"])
        _tick_event_scheduler(session, current_location="Rusty Dragon", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(48.0)
        assert session.event_runtime.warm_events["evt"].frozen is True

    def test_no_location_freezes_readiness(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=30.0, threshold=200.0,
                                                                     zones=["festival_square"])
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(30.0)

    def test_zone_match_clears_frozen_flag(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=10.0, base_gain=1.0,
                                                                     threshold=200.0,
                                                                     frozen=True, zones=["festival_square"])
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].frozen is False


# ── Zone normalization ────────────────────────────────────────────────────────

class TestZoneNormalization:
    """Underscore slugs and display-name canonicals both match."""

    def test_slug_matches_display_name(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=0.0, base_gain=1.0,
                                                                     threshold=200.0,
                                                                     zones=["festival_square"])
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(1.0)

    def test_display_name_matches_slug(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=0.0, base_gain=1.0,
                                                                     threshold=200.0,
                                                                     zones=["Festival Square"])
        _tick_event_scheduler(session, current_location="festival_square", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(1.0)

    def test_mismatched_name_does_not_gain(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=0.0, base_gain=1.0,
                                                                     threshold=200.0,
                                                                     zones=["cathedral_square"])
        _tick_event_scheduler(session, current_location="festival_square", intent_tags=[])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(0.0)


# ── AC-005 — action_gain_map ──────────────────────────────────────────────────

class TestActionGainMap:
    """AC-005: action_gain_map adds per-event bonus; unrelated events unaffected."""

    def test_matching_tag_adds_bonus(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=50.0, base_gain=1.0, threshold=200.0,
            zones=["festival_square"], action_gain_map={"explore": 3.0},
        )
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=["explore"])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(54.0)

    def test_non_matching_tag_no_bonus(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=50.0, base_gain=1.0, threshold=200.0,
            zones=["festival_square"], action_gain_map={"explore": 3.0},
        )
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=["attack"])
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(51.0)

    def test_bonus_not_applied_to_unrelated_event(self):
        session = _make_session()
        session.event_runtime.warm_events["evt_a"] = _make_warm_event(
            readiness=50.0, base_gain=1.0, threshold=200.0,
            zones=["festival_square"], action_gain_map={"explore": 3.0},
        )
        session.event_runtime.warm_events["evt_b"] = _make_warm_event(
            readiness=50.0, base_gain=1.0, threshold=200.0,
            zones=["festival_square"], action_gain_map={},
        )
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=["explore"])
        assert session.event_runtime.warm_events["evt_a"].readiness == pytest.approx(54.0)
        assert session.event_runtime.warm_events["evt_b"].readiness == pytest.approx(51.0)


# ── AC-006/007 — trigger roll ─────────────────────────────────────────────────

class TestTriggerRoll:
    """AC-006: roll only at threshold. AC-007: d100 <= readiness triggers; miss increments."""

    def test_no_roll_below_threshold(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=74.9, threshold=75.0)
        with patch("api.session_manager.random.randint") as mock_roll:
            _trigger_phase(session)
            mock_roll.assert_not_called()

    def test_roll_at_threshold(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=75.0, threshold=75.0)
        with patch("api.session_manager.random.randint", return_value=50):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id == "evt"

    def test_roll_hit_triggers_event(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=80.0, threshold=75.0)
        with patch("api.session_manager.random.randint", return_value=65):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id == "evt"

    def test_roll_miss_increments_failed_rolls(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=80.0, threshold=75.0)
        with patch("api.session_manager.random.randint", return_value=92):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id is None
        assert session.event_runtime.warm_events["evt"].failed_rolls == 1

    def test_roll_miss_does_not_trigger(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=80.0, threshold=75.0)
        with patch("api.session_manager.random.randint", return_value=81):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id is None


# ── AC-008 — pity rule ────────────────────────────────────────────────────────

class TestPityRule:
    """AC-008: event fires automatically after N=6 failed rolls."""

    def test_pity_fires_at_limit(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=80.0, threshold=75.0, failed_rolls=6,
        )
        with patch("api.session_manager.random.randint") as mock_roll:
            _trigger_phase(session)
            mock_roll.assert_not_called()
        assert session.event_runtime.active_event_id == "evt"

    def test_pity_not_fires_before_limit(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=80.0, threshold=75.0, failed_rolls=5,
        )
        with patch("api.session_manager.random.randint", return_value=99):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id is None
        assert session.event_runtime.warm_events["evt"].failed_rolls == 6


# ── AC-009 — TTL expiry ───────────────────────────────────────────────────────

class TestTTLExpiry:
    """AC-009: active event expires after TTL without LLM signal."""

    def test_ttl_decrements_each_tick(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(turns_remaining=3)
        session.event_runtime.active_event_id = "evt"
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        assert session.event_runtime.warm_events["evt"].turns_remaining == 2

    def test_ttl_expiry_clears_active_event(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(turns_remaining=1)
        session.event_runtime.active_event_id = "evt"
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        assert session.event_runtime.active_event_id is None

    def test_expired_event_added_to_completed(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(turns_remaining=1)
        session.event_runtime.active_event_id = "evt"
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        assert "evt" in session.event_runtime.completed_events

    def test_ttl_ticks_during_combat_no_location(self):
        """Combat branch calls tick with location=None — TTL decrements, readiness not changed."""
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=50.0, turns_remaining=3, threshold=200.0,
        )
        session.event_runtime.active_event_id = "evt"
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        assert session.event_runtime.warm_events["evt"].turns_remaining == 2
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(50.0)

    def test_completed_event_skipped_by_trigger(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=90.0, threshold=75.0)
        session.event_runtime.completed_events.append("evt")
        with patch("api.session_manager.random.randint", return_value=1):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id is None


# ── AC-010 — active event lockout ────────────────────────────────────────────

class TestActiveEventLockout:
    """AC-010: while an event is active, other soft events cannot trigger."""

    def test_active_event_blocks_trigger_phase(self):
        session = _make_session()
        session.event_runtime.warm_events["evt_a"] = _make_warm_event(turns_remaining=3)
        session.event_runtime.warm_events["evt_b"] = _make_warm_event(readiness=90.0, threshold=75.0)
        session.event_runtime.active_event_id = "evt_a"
        with patch("api.session_manager.random.randint", return_value=1):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id == "evt_a"

    def test_active_event_blocks_tick_trigger(self):
        session = _make_session()
        session.event_runtime.warm_events["active"] = _make_warm_event(turns_remaining=3)
        session.event_runtime.warm_events["waiting"] = _make_warm_event(
            readiness=90.0, threshold=75.0, zones=["festival_square"],
        )
        session.event_runtime.active_event_id = "active"
        with patch("api.session_manager.random.randint", return_value=1):
            _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.active_event_id == "active"


# ── AC-011 — [ACTIVE EVENT] prompt injection ──────────────────────────────────

class TestActiveEventInjection:
    """AC-011: [ACTIVE EVENT] block appears in system prompt when active_event_id is set."""

    def _no_index(self):
        idx = MagicMock()
        idx.detect.return_value = None
        idx.detect_by_location.return_value = []
        idx.lookup.return_value = None
        return idx

    def _call(self, session):
        with patch("api.session_manager._get_npc_index", return_value=self._no_index()), \
             patch("api.session_manager._get_skill_index", return_value=self._no_index()), \
             patch("api.session_manager._get_location_index", return_value=self._no_index()):
            return _inject_context(session)

    def test_active_event_block_injected(self):
        session = _make_session(event_scheduler=True)
        session.messages = [{"role": "user", "content": "I look around the square."}]
        session.event_runtime.warm_events["festival_social_phase"] = _make_warm_event(turns_remaining=3)
        session.event_runtime.active_event_id = "festival_social_phase"
        content, _ = self._call(session)
        assert "[ACTIVE EVENT]" in content
        assert "festival_social_phase" in content

    def test_active_event_block_includes_turns_remaining(self):
        session = _make_session(event_scheduler=True)
        session.messages = [{"role": "user", "content": "We walk through the square."}]
        # Start with 5 turns; _inject_context ticks TTL down to 4 before building the block.
        session.event_runtime.warm_events["evt"] = _make_warm_event(turns_remaining=5)
        session.event_runtime.active_event_id = "evt"
        content, _ = self._call(session)
        assert "Turns remaining: 4" in content

    def test_no_block_when_scheduler_off(self):
        session = _make_session(event_scheduler=False)
        session.messages = [{"role": "user", "content": "I look around."}]
        session.event_runtime.warm_events["evt"] = _make_warm_event(turns_remaining=3)
        session.event_runtime.active_event_id = "evt"
        content, _ = self._call(session)
        assert "[ACTIVE EVENT]" not in content

    def test_no_block_when_no_active_event(self):
        session = _make_session(event_scheduler=True)
        session.messages = [{"role": "user", "content": "I look around."}]
        content, _ = self._call(session)
        assert "[ACTIVE EVENT]" not in content

    def test_format_helper_returns_none_when_no_active_event(self):
        rt = EventRuntime()
        assert _format_active_event_context(rt) is None

    def test_format_helper_includes_event_id(self):
        rt = EventRuntime(active_event_id="my_event")
        rt.warm_events["my_event"] = _make_warm_event(readiness=77.0, turns_remaining=2)
        block = _format_active_event_context(rt)
        assert block is not None
        assert "my_event" in block
        assert "Turns remaining: 2" in block


# ── EventIndex.schedulable_entries() ─────────────────────────────────────────

class TestSchedulableEntries:
    """schedulable_entries() returns only events with a ## Schedule section."""

    def test_returns_schedulable_only(self, tmp_path):
        _make_schedulable_file(tmp_path, "sched_event")
        events_dir = tmp_path / "adventure_path" / "02_events"
        (events_dir / "plain_event.md").write_text(
            "**Event:** plain_event\n**Trigger:** when X happens\n\n<!-- INJECT -->\nContent.\n",
            encoding="utf-8",
        )
        idx = EventIndex(_repo_root=tmp_path)
        ids = [e.event_id for e in idx.schedulable_entries()]
        assert "sched_event" in ids
        assert "plain_event" not in ids

    def test_empty_when_no_schedulable_events(self, tmp_path):
        events_dir = tmp_path / "adventure_path" / "02_events"
        events_dir.mkdir(parents=True, exist_ok=True)
        (events_dir / "plain.md").write_text(
            "**Event:** plain\n**Trigger:** x\n\n<!-- INJECT -->\nContent.\n",
            encoding="utf-8",
        )
        idx = EventIndex(_repo_root=tmp_path)
        assert idx.schedulable_entries() == []

    def test_schedule_section_fields_loaded(self, tmp_path):
        _make_schedulable_file(tmp_path, "my_event", zones="festival_square, rusty_dragon",
                               threshold=55.0, base_gain=3.0, action_gain="explore:4")
        idx = EventIndex(_repo_root=tmp_path)
        entry = idx.schedulable_entries()[0]
        assert entry.threshold == pytest.approx(55.0)
        assert entry.base_gain == pytest.approx(3.0)
        assert "festival_square" in entry.zones
        assert "rusty_dragon" in entry.zones
        assert entry.action_gain_map.get("explore") == pytest.approx(4.0)


# ── AC-012 — scheduler logging ───────────────────────────────────────────────

class TestSchedulerLogging:
    """AC-012: readiness changes and trigger events are logged to the session log."""

    def test_readiness_change_logged(self, tmp_path):
        log_path = tmp_path / "session.log.md"
        session = _make_session(log_path=log_path)
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=20.0, base_gain=1.0, threshold=200.0, zones=["festival_square"],
        )
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        log = log_path.read_text(encoding="utf-8")
        assert "evt" in log
        assert "20" in log

    def test_trigger_logged_with_source(self, tmp_path):
        log_path = tmp_path / "session.log.md"
        session = _make_session(log_path=log_path)
        session.event_runtime.warm_events["evt"] = _make_warm_event(readiness=80.0, threshold=75.0)
        with patch("api.session_manager.random.randint", return_value=50):
            _trigger_phase(session)
        log = log_path.read_text(encoding="utf-8")
        assert "TRIGGERED" in log
        assert "evt" in log

    def test_pity_trigger_logged(self, tmp_path):
        log_path = tmp_path / "session.log.md"
        session = _make_session(log_path=log_path)
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=80.0, threshold=75.0, failed_rolls=6,
        )
        _trigger_phase(session)
        log = log_path.read_text(encoding="utf-8")
        assert "pity" in log

    def test_expiry_logged(self, tmp_path):
        log_path = tmp_path / "session.log.md"
        session = _make_session(log_path=log_path)
        session.event_runtime.warm_events["evt"] = _make_warm_event(turns_remaining=1)
        session.event_runtime.active_event_id = "evt"
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        log = log_path.read_text(encoding="utf-8")
        assert "EXPIRED" in log
        assert "evt" in log


# ── AC-013 — zone detection via LocationIndex ─────────────────────────────────

class TestLocationZoneIntegration:
    """AC-013: zone detection feeds from LocationIndex; a matching location file is required."""

    def _make_location_file(self, tmp_path: Path, canonical: str, aliases: list[str]) -> None:
        slug = canonical.lower().replace(" ", "_")
        loc_dir = tmp_path / "adventure_path" / "03_locations" / slug
        loc_dir.mkdir(parents=True, exist_ok=True)
        (loc_dir / "base.md").write_text(
            f"# {canonical}\n"
            f"**Aliases:** {', '.join(aliases)}\n\n"
            f"## Description\n\nA place.\n\n"
            f"## Typical Occupants\n\nPeople.\n\n"
            f"## Current State\n\nOpen.\n\n"
            f"<!-- REFERENCE -->\n",
            encoding="utf-8",
        )

    def _no_npc_skill(self):
        m = MagicMock()
        m.detect.return_value = None
        m.detect_by_location.return_value = []
        m.lookup.return_value = None
        return m

    def _call(self, session, loc_idx):
        ns = self._no_npc_skill()
        with patch("api.session_manager._get_npc_index", return_value=ns), \
             patch("api.session_manager._get_skill_index", return_value=ns), \
             patch("api.session_manager._get_location_index", return_value=loc_idx):
            return _inject_context(session)

    def test_alias_in_message_increases_readiness(self, tmp_path):
        self._make_location_file(tmp_path, "Festival Square",
                                 ["festival square", "the square", "square"])
        loc_idx = LocationIndex(_repo_root=tmp_path)
        session = _make_session(event_scheduler=True)
        session.messages = [{"role": "user", "content": "I walk through the festival square."}]
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=10.0, base_gain=1.0, threshold=200.0, zones=["festival_square"],
        )
        self._call(session, loc_idx)
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(11.0)

    def test_unmatched_message_freezes_readiness(self, tmp_path):
        self._make_location_file(tmp_path, "Festival Square",
                                 ["festival square", "the square", "square"])
        loc_idx = LocationIndex(_repo_root=tmp_path)
        session = _make_session(event_scheduler=True)
        session.messages = [{"role": "user", "content": "I head into the tavern."}]
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=20.0, base_gain=1.0, threshold=200.0, zones=["festival_square"],
        )
        self._call(session, loc_idx)
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(20.0)
        assert session.event_runtime.warm_events["evt"].frozen is True

    def test_no_location_file_means_always_frozen(self, tmp_path):
        """A zone with no location file never produces a loc_canonical match."""
        loc_idx = LocationIndex(_repo_root=tmp_path)  # empty — no location files
        session = _make_session(event_scheduler=True)
        session.messages = [{"role": "user", "content": "I walk to the festival square."}]
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=20.0, base_gain=1.0, threshold=200.0, zones=["festival_square"],
        )
        self._call(session, loc_idx)
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(20.0)

    def test_scene_locations_carry_zone_forward(self, tmp_path):
        """Party visited the zone on a prior turn; readiness gains even without re-mentioning it."""
        loc_idx = LocationIndex(_repo_root=tmp_path)  # lookup will return None but that's fine
        session = _make_session(event_scheduler=True)
        session.scene_locations = ["Festival Square"]
        session.messages = [{"role": "user", "content": "I talk to the merchant."}]
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=10.0, base_gain=1.0, threshold=200.0, zones=["festival_square"],
        )
        self._call(session, loc_idx)
        assert session.event_runtime.warm_events["evt"].readiness == pytest.approx(11.0)


# ── BUG-001 — frozen flag enforced in _trigger_phase ─────────────────────────

class TestFrozenEventNotTriggered:
    """BUG-001: a frozen event must not fire via roll or pity even when readiness >= threshold."""

    def test_frozen_event_skipped_by_roll(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=90.0, threshold=75.0, frozen=True,
        )
        with patch("api.session_manager.random.randint", return_value=1):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id is None

    def test_frozen_event_skipped_by_pity(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=90.0, threshold=75.0, frozen=True, failed_rolls=6,
        )
        with patch("api.session_manager.random.randint") as mock_roll:
            _trigger_phase(session)
            mock_roll.assert_not_called()
        assert session.event_runtime.active_event_id is None

    def test_unfrozen_event_can_trigger(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=90.0, threshold=75.0, frozen=False,
        )
        with patch("api.session_manager.random.randint", return_value=1):
            _trigger_phase(session)
        assert session.event_runtime.active_event_id == "evt"

    def test_zone_entry_unfreezes_and_allows_trigger_same_tick(self):
        """Entering the zone sets frozen=False then _trigger_phase can fire."""
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=90.0, threshold=75.0, frozen=True, zones=["festival_square"],
        )
        with patch("api.session_manager.random.randint", return_value=1):
            _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.active_event_id == "evt"


# ── BUG-002 — cooldown ticks every calendar turn ─────────────────────────────

class TestCooldownCalendarTick:
    """BUG-002: cooldown must decrement every turn, not only when readiness >= threshold."""

    def test_cooldown_ticks_when_below_threshold(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=30.0, threshold=75.0, zones=["festival_square"],
        )
        session.event_runtime.cooldowns["evt"] = 3
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.cooldowns["evt"] == 2

    def test_cooldown_ticks_when_out_of_zone(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=80.0, threshold=75.0, frozen=True, zones=["festival_square"],
        )
        session.event_runtime.cooldowns["evt"] = 5
        _tick_event_scheduler(session, current_location=None, intent_tags=[])
        assert session.event_runtime.cooldowns["evt"] == 4

    def test_cooldown_reaches_zero_and_event_becomes_eligible(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=80.0, threshold=75.0, zones=["festival_square"],
        )
        session.event_runtime.cooldowns["evt"] = 1
        with patch("api.session_manager.random.randint", return_value=1):
            _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.cooldowns["evt"] == 0
        assert session.event_runtime.active_event_id == "evt"

    def test_cooldown_not_decremented_below_zero(self):
        session = _make_session()
        session.event_runtime.warm_events["evt"] = _make_warm_event(
            readiness=30.0, threshold=75.0, zones=["festival_square"],
        )
        session.event_runtime.cooldowns["evt"] = 0
        _tick_event_scheduler(session, current_location="Festival Square", intent_tags=[])
        assert session.event_runtime.cooldowns["evt"] == 0
