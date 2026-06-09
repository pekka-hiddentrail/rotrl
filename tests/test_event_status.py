"""Tests for GET /api/sessions/{session_id}/event_status (specs/event-status-panel.feature).

Covers AC-001 through AC-010 (backend endpoint).
AC-011 through AC-015 are UI/frontend and covered by exploratory tests.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _boot(client, *, event_scheduler: bool = False) -> str:
    """Boot a session and return its session_id."""
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "host": "http://localhost:11434",
        "temperature": 0.3,
        "dev_mode": True,
        "event_scheduler": event_scheduler,
    })
    assert resp.status_code == 200
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            import json as _json
            ev = _json.loads(line[6:])
            if ev.get("type") == "done":
                return ev["session_id"]
    raise AssertionError("no done event in boot response")


def _get_status(client, session_id: str) -> dict:
    resp = client.get(f"/api/sessions/{session_id}/event_status")
    assert resp.status_code == 200
    return resp.json()


# ── AC-001 — response shape ───────────────────────────────────────────────────

class TestEndpointShape:
    """AC-001: endpoint returns 200 with all required top-level keys."""

    def test_status_200(self, client):
        sid = _boot(client)
        resp = client.get(f"/api/sessions/{sid}/event_status")
        assert resp.status_code == 200

    def test_top_level_keys(self, client):
        sid = _boot(client)
        data = _get_status(client, sid)
        for key in ("scheduler_enabled", "turn_number", "active_event_id",
                    "warm_events", "completed_events", "cooldowns"):
            assert key in data, f"missing key: {key}"

    def test_warm_events_is_dict(self, client):
        sid = _boot(client)
        data = _get_status(client, sid)
        assert isinstance(data["warm_events"], dict)

    def test_completed_events_is_list(self, client):
        sid = _boot(client)
        data = _get_status(client, sid)
        assert isinstance(data["completed_events"], list)

    def test_cooldowns_is_dict(self, client):
        sid = _boot(client)
        data = _get_status(client, sid)
        assert isinstance(data["cooldowns"], dict)


# ── AC-002 — 404 for unknown session ─────────────────────────────────────────

class TestUnknownSession:
    """AC-002: unknown session_id returns 404."""

    def test_unknown_session_404(self, client):
        resp = client.get(f"/api/sessions/{uuid.uuid4()}/event_status")
        assert resp.status_code == 404

    def test_malformed_session_id_404(self, client):
        resp = client.get("/api/sessions/not-a-real-id/event_status")
        assert resp.status_code == 404


# ── AC-003 — scheduler_enabled reflects boot flag ────────────────────────────

class TestSchedulerEnabled:
    """AC-003: scheduler_enabled mirrors the boot-time event_scheduler flag."""

    def test_scheduler_disabled_by_default(self, client):
        sid = _boot(client, event_scheduler=False)
        assert _get_status(client, sid)["scheduler_enabled"] is False

    def test_scheduler_enabled_when_flagged(self, client):
        sid = _boot(client, event_scheduler=True)
        assert _get_status(client, sid)["scheduler_enabled"] is True


# ── AC-004 — warm_events empty when scheduler off ────────────────────────────

class TestWarmEventsDisabled:
    """AC-004: warm_events is {} when session booted without scheduler."""

    def test_warm_events_empty_when_off(self, client):
        sid = _boot(client, event_scheduler=False)
        assert _get_status(client, sid)["warm_events"] == {}


# ── AC-005 — warm_events populated when scheduler on ─────────────────────────

class TestWarmEventsEnabled:
    """AC-005: warm_events contains schedulable events when scheduler is on."""

    def test_warm_events_non_empty(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        # festival_social_phase.md has a ## Schedule section
        assert len(data["warm_events"]) > 0

    def test_festival_social_phase_present(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        assert "festival_social_phase" in data["warm_events"]


# ── AC-006 — WarmEvent field shape ───────────────────────────────────────────

class TestWarmEventFields:
    """AC-006: each warm_events entry contains all WarmEvent fields with correct types."""

    def test_all_fields_present(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        we = next(iter(data["warm_events"].values()))
        for field in ("readiness", "threshold", "base_gain", "failed_rolls",
                      "frozen", "last_zone_match_turn", "turns_remaining",
                      "zones", "action_gain_map"):
            assert field in we, f"missing field: {field}"

    def test_readiness_is_float_in_range(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        for we in data["warm_events"].values():
            assert isinstance(we["readiness"], (int, float))
            assert 0.0 <= we["readiness"] <= 100.0

    def test_frozen_is_bool(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        for we in data["warm_events"].values():
            assert isinstance(we["frozen"], bool)

    def test_zones_is_list(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        for we in data["warm_events"].values():
            assert isinstance(we["zones"], list)

    def test_action_gain_map_is_dict(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        for we in data["warm_events"].values():
            assert isinstance(we["action_gain_map"], dict)

    def test_festival_social_phase_threshold(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        we = data["warm_events"]["festival_social_phase"]
        assert we["threshold"] == 60.0

    def test_festival_social_phase_zones(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        we = data["warm_events"]["festival_social_phase"]
        assert "festival_square" in we["zones"]

    def test_festival_social_phase_action_gain_map(self, client):
        sid = _boot(client, event_scheduler=True)
        data = _get_status(client, sid)
        we = data["warm_events"]["festival_social_phase"]
        assert "socialize" in we["action_gain_map"]
        assert "explore" in we["action_gain_map"]


# ── AC-007 — active_event_id null by default ─────────────────────────────────

class TestActiveEventIdDefault:
    """AC-007: active_event_id is null on a fresh session."""

    def test_active_event_id_null(self, client):
        sid = _boot(client)
        assert _get_status(client, sid)["active_event_id"] is None

    def test_active_event_id_null_with_scheduler_on(self, client):
        sid = _boot(client, event_scheduler=True)
        assert _get_status(client, sid)["active_event_id"] is None


# ── AC-008 — active_event_id reflects runtime when set ───────────────────────

class TestActiveEventIdSet:
    """AC-008: active_event_id matches session.event_runtime.active_event_id."""

    def test_active_event_id_reflected(self, client):
        import api.session_manager as sm
        sid = _boot(client, event_scheduler=True)
        session = sm.get_session(sid)
        session.event_runtime.warm_events["festival_social_phase"].turns_remaining = 3
        session.event_runtime.active_event_id = "festival_social_phase"
        data = _get_status(client, sid)
        assert data["active_event_id"] == "festival_social_phase"

    def test_active_event_id_cleared_after_complete(self, client):
        import api.session_manager as sm
        from api.session_manager import _complete_active_event
        sid = _boot(client, event_scheduler=True)
        session = sm.get_session(sid)
        session.event_runtime.warm_events["festival_social_phase"].turns_remaining = 1
        session.event_runtime.active_event_id = "festival_social_phase"
        _complete_active_event(session)
        data = _get_status(client, sid)
        assert data["active_event_id"] is None


# ── AC-009 — completed_events listed ─────────────────────────────────────────

class TestCompletedEvents:
    """AC-009: completed_events contains expired event ids."""

    def test_completed_empty_by_default(self, client):
        sid = _boot(client)
        assert _get_status(client, sid)["completed_events"] == []

    def test_completed_event_appears(self, client):
        import api.session_manager as sm
        sid = _boot(client, event_scheduler=True)
        session = sm.get_session(sid)
        session.event_runtime.completed_events.append("festival_social_phase")
        data = _get_status(client, sid)
        assert "festival_social_phase" in data["completed_events"]

    def test_multiple_completed_events(self, client):
        import api.session_manager as sm
        sid = _boot(client, event_scheduler=True)
        session = sm.get_session(sid)
        session.event_runtime.completed_events.extend(["evt_a", "evt_b"])
        data = _get_status(client, sid)
        assert "evt_a" in data["completed_events"]
        assert "evt_b" in data["completed_events"]


# ── AC-010 — turn_number ──────────────────────────────────────────────────────

class TestTurnNumber:
    """AC-010: turn_number reflects session.turn_number."""

    def test_turn_number_zero_on_boot(self, client):
        sid = _boot(client)
        data = _get_status(client, sid)
        assert data["turn_number"] == 0
        assert isinstance(data["turn_number"], int)

    def test_turn_number_increments(self, client):
        import api.session_manager as sm
        sid = _boot(client)
        session = sm.get_session(sid)
        session.turn_number = 7
        data = _get_status(client, sid)
        assert data["turn_number"] == 7
