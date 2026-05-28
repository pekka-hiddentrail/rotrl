"""Tests for POST /api/sessions/{id}/turn — player turns with mocked Ollama."""
from __future__ import annotations

from unittest.mock import patch

from .conftest import make_stream_response, parse_sse


def _send(client, session_id: str, text: str):
    return client.post(
        f"/api/sessions/{session_id}/turn",
        json={"input": text},
    )


def test_turn_streams_tokens(booted_session):
    client, session_id = booted_session
    mock_resp = make_stream_response(["Hello", " there", ", adventurer."])

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = _send(client, session_id, "We look around.")

    assert resp.status_code == 200
    events = parse_sse(resp)
    tokens = [e["content"] for e in events if e["type"] == "token"]
    assert tokens == ["Hello", " there", ", adventurer."]

    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1


def test_turn_assembles_full_response_in_log(booted_session):
    client, session_id = booted_session
    mock_resp = make_stream_response(["The square", " is busy."])

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        _send(client, session_id, "What do we see?")

    log = client.get(f"/api/sessions/{session_id}/log").text
    assert "What do we see?" in log
    assert "The square is busy." in log


def test_turn_appends_to_message_history(booted_session):
    client, session_id = booted_session

    with patch("api.session_manager._requests.post",
               return_value=make_stream_response(["First response."])):
        _send(client, session_id, "First question.")

    with patch("api.session_manager._requests.post",
               return_value=make_stream_response(["Second response."])):
        _send(client, session_id, "Second question.")

    info = client.get(f"/api/sessions/{session_id}").json()
    # 2 user messages + 2 assistant messages = 4 total
    assert info["message_count"] == 4


def test_turn_unknown_session_404(client):
    resp = client.post("/api/sessions/no-such-id/turn", json={"input": "Hello."})
    assert resp.status_code == 404


def test_turn_ollama_error_returns_error_event(booted_session):
    from unittest.mock import MagicMock
    client, session_id = booted_session

    broken = MagicMock()
    broken.raise_for_status.side_effect = Exception("connection refused")
    broken.__enter__ = lambda s: s
    broken.__exit__ = MagicMock(return_value=False)

    with patch("api.session_manager._requests.post", return_value=broken):
        resp = _send(client, session_id, "Hello?")

    events = parse_sse(resp)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "connection refused" in error_events[0]["message"]


# ── AC-008: section_format_ok passed to write_api_log ────────────────────────

def test_section_format_ok_true_when_response_has_markers(booted_session):
    client, session_id = booted_session
    tokens = ["%%NARRATIVE%%\n\n", "The festival begins."]
    mock_resp = make_stream_response(tokens)

    captured: list[dict] = []

    def _capture(**kwargs):
        captured.append(kwargs)
        from pathlib import Path
        import tempfile, json
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text(json.dumps({}))
        return p

    with patch("api.session_manager._requests.post", return_value=mock_resp), \
         patch("api.session_manager.write_api_log", side_effect=_capture):
        _send(client, session_id, "We look around.")

    assert len(captured) == 1
    assert captured[0]["section_format_ok"] is True


def test_section_format_ok_false_when_response_has_no_markers(booted_session):
    client, session_id = booted_session
    mock_resp = make_stream_response(["Plain prose with no markers."])

    captured: list[dict] = []

    def _capture(**kwargs):
        captured.append(kwargs)
        from pathlib import Path
        import tempfile, json
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text(json.dumps({}))
        return p

    with patch("api.session_manager._requests.post", return_value=mock_resp), \
         patch("api.session_manager.write_api_log", side_effect=_capture):
        _send(client, session_id, "We look around.")

    assert len(captured) == 1
    assert captured[0]["section_format_ok"] is False


def test_section_format_ok_none_when_error_before_content(booted_session):
    from unittest.mock import MagicMock
    client, session_id = booted_session

    broken = MagicMock()
    broken.raise_for_status.side_effect = Exception("timeout")
    broken.__enter__ = lambda s: s
    broken.__exit__ = MagicMock(return_value=False)

    captured: list[dict] = []

    def _capture(**kwargs):
        captured.append(kwargs)
        from pathlib import Path
        import tempfile, json
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text(json.dumps({}))
        return p

    with patch("api.session_manager._requests.post", return_value=broken), \
         patch("api.session_manager.write_api_log", side_effect=_capture):
        _send(client, session_id, "Hello?")

    assert len(captured) == 1
    assert captured[0]["section_format_ok"] is None


def test_section_format_ok_recognises_all_marker_types(booted_session):
    client, session_id = booted_session

    for marker in ["%%NARRATIVE%%", "%%ROLL%%", "%%DELTAS%%", "%%GENERATE%%"]:
        captured: list[dict] = []

        def _capture(**kwargs):
            captured.append(kwargs)
            from pathlib import Path
            import tempfile, json
            p = Path(tempfile.mktemp(suffix=".json"))
            p.write_text(json.dumps({}))
            return p

        mock_resp = make_stream_response([f"{marker}\n\nContent."])
        with patch("api.session_manager._requests.post", return_value=mock_resp), \
             patch("api.session_manager.write_api_log", side_effect=_capture):
            _send(client, session_id, "Test.")

        assert captured[0]["section_format_ok"] is True, f"failed for {marker}"
