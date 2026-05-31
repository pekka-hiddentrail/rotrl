"""Contract tests for server-sent event payload shapes."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from .conftest import make_stream_response, parse_sse


KNOWN_EVENT_TYPES = {
    "attack_request",
    "attack_result",
    "combat_update",
    "context",
    "done",
    "error",
    "patch_last",
    "rate_limits",
    "roll_request",
    "status",
    "token",
}

REQUIRED_KEYS_BY_TYPE = {
    "attack_request": {"type", "attacker", "target", "bonus", "ac", "damage_expr", "attack_type"},
    "attack_result": {"type", "attacker", "target", "roll", "bonus", "total", "ac", "hit", "damage_total", "attack_type", "is_pc"},
    "combat_update": {"type", "combat_state"},
    "context": {"type", "npc", "skill", "location", "active_events", "scene_npcs"},
    "done": {"type"},
    "error": {"type", "message"},
    "patch_last": {"type", "content"},
    "rate_limits": {"type"},
    "roll_request": {"type", "skill", "dc", "success", "failure"},
    "status": {"type", "message"},
    "token": {"type", "content"},
}


def assert_sse_contract(events: list[dict]) -> None:
    assert events, "expected at least one SSE event"
    for event in events:
        assert "type" in event, f"SSE event missing type: {event}"
        assert event["type"] in KNOWN_EVENT_TYPES, f"unknown SSE event type: {event}"
        missing = REQUIRED_KEYS_BY_TYPE[event["type"]] - set(event)
        assert not missing, f"{event['type']} event missing keys {sorted(missing)}: {event}"


def test_boot_sse_events_match_contract(client):
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "provider": "ollama",
        "dev_mode": True,
    })

    events = parse_sse(resp)

    assert_sse_contract(events)
    assert [e["type"] for e in events] == ["done"]
    assert events[0]["session_id"]


def test_turn_sse_events_match_contract(booted_session):
    client, session_id = booted_session
    mock_resp = make_stream_response([
        "%%NARRATIVE%%\n\nA goblin darts behind a stall.\n\n",
        "%%ROLL%%\n",
        "[ skill: Perception  dc: 15  success: You spot it.  failure: It vanishes. ]",
    ])

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Do I spot the goblin?"})

    events = parse_sse(resp)

    assert_sse_contract(events)
    assert any(e["type"] == "context" for e in events)
    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "roll_request" for e in events)
    assert any(e["type"] == "combat_update" for e in events)
    assert events[-1]["type"] == "done"


def test_end_session_sse_events_match_contract(client, tmp_path, monkeypatch):
    import api.session_manager as sm

    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "provider": "ollama",
        "dev_mode": True,
    })
    session_id = next(e["session_id"] for e in parse_sse(resp) if e["type"] == "done")

    log_path = tmp_path / "session_001.log.md"
    log_path.write_text(
        "### [10:00:00] PLAYER\nWe ask Hemlock about the alarm.\n\n"
        "### [10:01:00] GM\nHemlock points toward the north gate.\n",
        encoding="utf-8",
    )
    sm._sessions[session_id].log_path = log_path

    recap = (
        "# Session 1 - Alarm Bells\n\n"
        "*Sandpoint, Varisia - 1st of Lamashan, 4707 AR*\n\n"
        "---\n\n"
        "The square changed in an instant as alarm bells cut through festival noise. "
        "Hemlock pointed you toward danger and the town began to move around you. "
        "People fled, shouted, and searched for safety while you took stock of the threat.\n\n"
        "---\n"
    )
    boot = (
        "# Session 2 Boot Context\n\n"
        "## Scene State\n- Act: Book 1\n- Location: Sandpoint\n\n"
        "## What Is Happening Right Now\nThe alarm is still sounding near the north gate.\n\n"
        "## Who Is Present\n- Sheriff Belor Hemlock\n\n"
        "## Party Status\nThe party is alert and ready.\n\n"
        "## What the GM Must Not Do in This Scene\n- Do not reveal hidden motives.\n"
    )

    with patch("api.session_manager._call_blocking", side_effect=[recap, boot]):
        end_resp = client.post(f"/api/sessions/{session_id}/end")

    events = parse_sse(end_resp)

    assert_sse_contract(events)
    assert all(e["type"] == "status" for e in events[:-1])
    assert [e["message"] for e in events[:-1]] == [
        "Parsing session log…",
        "Generating session recap…",
        "Generating GM boot context…",
        "Writing session files…",
        "Saving session…",
    ]
    assert events[-1]["type"] == "done"
    assert Path(events[-1]["recap_path"]).name == "recap.md"
    assert Path(events[-1]["boot_path"]).name == "boot.md"
    assert Path(events[-1]["saved_to"]).name == "session_001_notes.json"
