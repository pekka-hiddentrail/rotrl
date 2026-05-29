"""Tests for the %%EVENT%% event injection system.

Covers: EventIndex loading/parsing, %%EVENT%% tag parsing, TTL countdown,
expiry, duplicate handling, unknown ID, injection into system prompt,
and the SSE context event.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from api.context.event_index import EventIndex, EventEntry, _parse_event_file
from .conftest import make_stream_response, parse_sse


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_event_file(tmp_path: Path, event_id: str, trigger: str, content: str) -> Path:
    """Write a minimal valid event file and return its path."""
    events_dir = tmp_path / "adventure_path" / "08_events"
    events_dir.mkdir(parents=True, exist_ok=True)
    f = events_dir / f"{event_id}.md"
    f.write_text(
        f"**Event:** {event_id}\n"
        f"**Trigger:** {trigger}\n"
        f"**Expires:** 5 turns\n\n"
        f"<!-- INJECT -->\n\n"
        f"{content}\n",
        encoding="utf-8",
    )
    return f


# ── EventIndex loading ────────────────────────────────────────────────────────

class TestEventIndexLoading:
    def test_loads_event_file(self, tmp_path):
        _make_event_file(tmp_path, "goblin_attack_starts", "When goblins attack", "## Goblins!\nAC 16, HP 5.")
        idx = EventIndex(_repo_root=tmp_path)
        entry = idx.get("goblin_attack_starts")
        assert entry is not None
        assert entry.event_id == "goblin_attack_starts"
        assert entry.trigger == "When goblins attack"
        assert "AC 16" in entry.content

    def test_skips_underscore_files(self, tmp_path):
        events_dir = tmp_path / "adventure_path" / "08_events"
        events_dir.mkdir(parents=True, exist_ok=True)
        (events_dir / "_TEMPLATE.md").write_text(
            "**Event:** _template\n**Trigger:** ignore\n\n<!-- INJECT -->\ncontent\n",
            encoding="utf-8",
        )
        idx = EventIndex(_repo_root=tmp_path)
        assert idx.get("_template") is None
        assert len(idx.known_event_ids) == 0

    def test_missing_08_events_dir_is_safe(self, tmp_path):
        idx = EventIndex(_repo_root=tmp_path)
        assert idx.get("anything") is None
        assert idx.known_event_ids == []

    def test_loaded_flag_prevents_double_scan(self, tmp_path):
        _make_event_file(tmp_path, "evt_a", "trigger a", "content a")
        idx = EventIndex(_repo_root=tmp_path)
        _ = idx.get("evt_a")  # triggers load
        # Add a second file after load — should NOT appear (already loaded)
        _make_event_file(tmp_path, "evt_b", "trigger b", "content b")
        assert idx.get("evt_b") is None

    def test_multiple_files_all_loaded(self, tmp_path):
        for i in range(3):
            _make_event_file(tmp_path, f"event_{i}", f"trigger {i}", f"content {i}")
        idx = EventIndex(_repo_root=tmp_path)
        assert len(idx.known_event_ids) == 3


class TestParseEventFile:
    def test_parses_id_trigger_content(self, tmp_path):
        f = _make_event_file(tmp_path, "fire_phase", "When fires start", "Fire! DC 12.")
        entry = _parse_event_file(f)
        assert entry.event_id == "fire_phase"
        assert entry.trigger == "When fires start"
        assert "DC 12" in entry.content

    def test_content_excludes_metadata(self, tmp_path):
        f = _make_event_file(tmp_path, "evt", "trigger", "injectable content here")
        entry = _parse_event_file(f)
        assert "**Event:**" not in entry.content
        assert "**Trigger:**" not in entry.content
        assert "<!-- INJECT -->" not in entry.content

    def test_missing_inject_marker_returns_none(self, tmp_path):
        events_dir = tmp_path / "adventure_path" / "08_events"
        events_dir.mkdir(parents=True, exist_ok=True)
        f = events_dir / "bad.md"
        f.write_text("**Event:** bad\n**Trigger:** something\nno inject marker\n", encoding="utf-8")
        assert _parse_event_file(f) is None

    def test_missing_event_id_returns_none(self, tmp_path):
        events_dir = tmp_path / "adventure_path" / "08_events"
        events_dir.mkdir(parents=True, exist_ok=True)
        f = events_dir / "bad.md"
        f.write_text("**Trigger:** something\n\n<!-- INJECT -->\ncontent\n", encoding="utf-8")
        assert _parse_event_file(f) is None

    def test_nonexistent_file_returns_none(self, tmp_path):
        assert _parse_event_file(tmp_path / "ghost.md") is None


class TestEventMapText:
    def test_empty_when_no_events(self, tmp_path):
        idx = EventIndex(_repo_root=tmp_path)
        assert idx.event_map_text() == ""

    def test_contains_event_id_and_trigger(self, tmp_path):
        _make_event_file(tmp_path, "goblin_attack_starts", "When goblins appear", "content")
        idx = EventIndex(_repo_root=tmp_path)
        text = idx.event_map_text()
        assert "goblin_attack_starts" in text
        assert "When goblins appear" in text

    def test_contains_syntax_instruction(self, tmp_path):
        _make_event_file(tmp_path, "evt", "trigger", "content")
        idx = EventIndex(_repo_root=tmp_path)
        assert "%%EVENT%%" in idx.event_map_text()


# ── Integration tests via HTTP client ─────────────────────────────────────────

def _fake_events_dir(tmp_path: Path) -> Path:
    """Create a minimal 08_events directory under tmp_path's adventure_path."""
    events_dir = tmp_path / "outputs" / ".." / "adventure_path" / "08_events"
    # The client fixture redirects _OUTPUTS_DIR but _REPO_ROOT stays as real repo.
    # We monkeypatch _REPO_ROOT separately in tests that need fake events.
    events_dir = tmp_path / "adventure_path" / "08_events"
    events_dir.mkdir(parents=True, exist_ok=True)
    return events_dir


class TestEventFiring:
    def test_event_fires_and_is_added_to_active_events(self, booted_session):
        """AC-001: LLM writes %%EVENT%% → entry appears in session.active_events."""
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm._sessions[session_id]

        tokens = ["%%NARRATIVE%%\n\nThe goblins attack!\n\n%%EVENT%% goblin_attack_starts"]
        mock_resp = make_stream_response(tokens)

        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager._get_event_index") as mock_idx:
            mock_entry = EventEntry(
                event_id="goblin_attack_starts",
                trigger="When goblins appear",
                content="## Goblins\nAC 16, HP 5.",
            )
            mock_idx.return_value.get.return_value = mock_entry
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "We look around."})

        assert len(session.active_events) == 1
        assert session.active_events[0].event_id == "goblin_attack_starts"
        assert session.active_events[0].turns_remaining == 5

    def test_unknown_event_id_is_ignored(self, booted_session):
        """AC-004: Unknown event ID produces no active_events entry."""
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm._sessions[session_id]

        tokens = ["%%NARRATIVE%%\n\nSomething happens.\n\n%%EVENT%% no_such_event"]
        mock_resp = make_stream_response(tokens)

        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager._get_event_index") as mock_idx:
            mock_idx.return_value.get.return_value = None  # not found
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "What happens?"})

        assert len(session.active_events) == 0

    def test_duplicate_event_does_not_reset_ttl(self, booted_session):
        """AC-005: Firing the same event twice keeps the original turns_remaining."""
        import api.session_manager as sm
        from api.session_manager import ActiveEvent
        client, session_id = booted_session
        session = sm._sessions[session_id]

        # Pre-load an active event with 2 turns remaining
        session.active_events.append(
            ActiveEvent(event_id="goblin_attack_starts", content="content", turns_remaining=2)
        )

        tokens = ["%%NARRATIVE%%\n\nStill fighting.\n\n%%EVENT%% goblin_attack_starts"]
        mock_resp = make_stream_response(tokens)

        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager._get_event_index") as mock_idx:
            mock_idx.return_value.get.return_value = EventEntry(
                event_id="goblin_attack_starts", trigger="t", content="c"
            )
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Continue."})

        # Should still be 1 entry (not duplicated), and TTL should NOT be reset to 5
        active = [e for e in session.active_events if e.event_id == "goblin_attack_starts"]
        assert len(active) == 1
        assert active[0].turns_remaining != 5  # was decremented, not reset


class TestEventExpiry:
    def test_event_expires_after_n_turns(self, booted_session):
        """AC-002: Event with turns_remaining=1 is removed after one turn."""
        import api.session_manager as sm
        from api.session_manager import ActiveEvent
        client, session_id = booted_session
        session = sm._sessions[session_id]

        session.active_events.append(
            ActiveEvent(event_id="goblin_attack_starts", content="content", turns_remaining=1)
        )

        mock_resp = make_stream_response(["%%NARRATIVE%%\n\nThe dust settles."])
        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager._get_event_index") as mock_idx:
            mock_idx.return_value.get.return_value = None
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Anything?"})

        assert len(session.active_events) == 0

    def test_two_events_decrement_independently(self, booted_session):
        """AC-003: Multiple active events each decrement their own TTL."""
        import api.session_manager as sm
        from api.session_manager import ActiveEvent
        client, session_id = booted_session
        session = sm._sessions[session_id]

        session.active_events.append(
            ActiveEvent(event_id="goblin_attack_starts", content="c1", turns_remaining=3)
        )
        session.active_events.append(
            ActiveEvent(event_id="fire_phase_begins", content="c2", turns_remaining=1)
        )

        mock_resp = make_stream_response(["%%NARRATIVE%%\n\nChaos continues."])
        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager._get_event_index") as mock_idx:
            mock_idx.return_value.get.return_value = None
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "What now?"})

        ids = [e.event_id for e in session.active_events]
        assert "goblin_attack_starts" in ids   # 3-1 = 2, still active
        assert "fire_phase_begins" not in ids  # 1-1 = 0, expired


class TestEventInjection:
    def test_active_event_content_appears_in_context(self, booted_session):
        """AC-001 (injection side): active event content is in the system prompt."""
        import api.session_manager as sm
        from api.session_manager import ActiveEvent
        client, session_id = booted_session
        session = sm._sessions[session_id]

        session.active_events.append(
            ActiveEvent(event_id="goblin_attack_starts", content="GOBLIN_CONTENT_MARKER", turns_remaining=5)
        )

        captured_prompts: list[str] = []

        original_post = __import__("requests").post

        def _capture(url, **kwargs):
            msgs = kwargs.get("json", {}).get("messages", [])
            if msgs:
                captured_prompts.append(msgs[0].get("content", ""))
            return make_stream_response(["%%NARRATIVE%%\n\nFighting."])

        with patch("api.session_manager._requests.post", side_effect=_capture):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Attack!"})

        assert any("GOBLIN_CONTENT_MARKER" in p for p in captured_prompts)

    def test_expired_event_content_not_injected(self, booted_session):
        """AC-002 (injection side): expired event is not in the system prompt."""
        import api.session_manager as sm
        from api.session_manager import ActiveEvent
        client, session_id = booted_session
        session = sm._sessions[session_id]

        session.active_events.append(
            ActiveEvent(event_id="goblin_attack_starts", content="EXPIRED_MARKER", turns_remaining=1)
        )

        # Turn 1: expires the event
        mock_resp1 = make_stream_response(["%%NARRATIVE%%\n\nFirst turn."])
        with patch("api.session_manager._requests.post", return_value=mock_resp1):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "First."})

        assert len(session.active_events) == 0

        captured_prompts: list[str] = []

        def _capture(url, **kwargs):
            msgs = kwargs.get("json", {}).get("messages", [])
            if msgs:
                captured_prompts.append(msgs[0].get("content", ""))
            return make_stream_response(["%%NARRATIVE%%\n\nSecond turn."])

        with patch("api.session_manager._requests.post", side_effect=_capture):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Second."})

        assert not any("EXPIRED_MARKER" in p for p in captured_prompts)


class TestActiveEventsSSE:
    def test_context_sse_includes_active_events(self, booted_session):
        """AC-008: SSE context event reports active event IDs."""
        import api.session_manager as sm
        from api.session_manager import ActiveEvent
        client, session_id = booted_session
        session = sm._sessions[session_id]

        session.active_events.append(
            ActiveEvent(event_id="goblin_attack_starts", content="c", turns_remaining=3)
        )

        mock_resp = make_stream_response(["%%NARRATIVE%%\n\nThe fight."])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Fight!"})

        events = parse_sse(resp)
        context_ev = next((e for e in events if e.get("type") == "context"), None)
        assert context_ev is not None
        # Event was active going into this turn (decremented to 2, still active)
        assert "goblin_attack_starts" in context_ev.get("active_events", [])

    def test_context_sse_empty_when_no_active_events(self, booted_session):
        """AC-008: active_events is an empty list when nothing is active."""
        client, session_id = booted_session
        mock_resp = make_stream_response(["%%NARRATIVE%%\n\nQuiet."])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Anything?"})

        events = parse_sse(resp)
        context_ev = next((e for e in events if e.get("type") == "context"), None)
        assert context_ev is not None
        assert context_ev.get("active_events") == []


class TestEventNotShownToPlayer:
    def test_event_line_not_in_token_stream(self, client):
        """AC-007: %%EVENT%% line is not emitted as a token (non-dev mode)."""
        # Boot with dev_mode=False so the narrative filter is active
        resp = client.post("/api/sessions", json={
            "session_number": 1,
            "model": "qwen3:4b",
            "host": "http://localhost:11434",
            "temperature": 0.3,
            "dev_mode": False,
        })
        events = parse_sse(resp)
        session_id = next(e for e in events if e["type"] == "done")["session_id"]

        tokens = ["%%NARRATIVE%%\n\nGoblins attack!\n\n%%EVENT%% goblin_attack_starts"]
        mock_resp = make_stream_response(tokens)

        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager._get_event_index") as mock_idx:
            mock_idx.return_value.get.return_value = EventEntry(
                event_id="goblin_attack_starts", trigger="t", content="c"
            )
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Look around."})

        events = parse_sse(resp)
        token_text = "".join(e["content"] for e in events if e.get("type") == "token")
        assert "%%EVENT%%" not in token_text
        assert "goblin_attack_starts" not in token_text
        assert "Goblins attack!" in token_text  # narrative still reaches player
