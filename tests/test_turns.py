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


# ── Inline %%ROLL%% block (single-line bracket format) ───────────────────────

def test_inline_roll_block_sets_pending_roll(booted_session):
    """LLM writes [ skill: X  dc: N  success: ...  failure: ... ] on one line.

    _BRACKET_BLOCK_RE requires [ on its own line, so _parse_bracket_blocks
    returns nothing.  The inline fallback regex must catch it and set pending_roll.
    """
    import api.session_manager as sm

    client, session_id = booted_session
    tokens = [
        "%%NARRATIVE%%\n\n",
        "Ani scans the crowd.\n\n",
        "%%ROLL%%\n",
        "[ skill: Perception  dc: 15"
        "  success: You spot three goblins crouching in the alley."
        "  failure: Nothing resolves into a clear threat. ]",
    ]
    mock_resp = make_stream_response(tokens)

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = _send(client, session_id, "Ani scans the square.")

    events = parse_sse(resp)
    roll_events = [e for e in events if e["type"] == "roll_request"]
    assert len(roll_events) == 1
    assert roll_events[0]["skill"] == "Perception"
    assert roll_events[0]["dc"] == 15

    session = sm._sessions[session_id]
    assert session.pending_roll is not None
    assert session.pending_roll["skill"] == "Perception"
    assert session.pending_roll["dc"] == 15
    assert "goblins" in session.pending_roll["success"]
    assert "clear threat" in session.pending_roll["failure"]


def test_multiline_roll_block_still_works(booted_session):
    """Multi-line bracket format (existing behavior) must not regress."""
    import api.session_manager as sm

    client, session_id = booted_session
    tokens = [
        "%%NARRATIVE%%\n\nVanx eyes the lock.\n\n",
        "%%ROLL%%\n",
        "[\nskill: Disable Device\ndc: 20\n",
        "success: The lock clicks open.\n",
        "failure: The pick snaps.\n]",
    ]
    mock_resp = make_stream_response(tokens)

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = _send(client, session_id, "Vanx tries to pick the lock.")

    events = parse_sse(resp)
    roll_events = [e for e in events if e["type"] == "roll_request"]
    assert len(roll_events) == 1
    assert roll_events[0]["skill"] == "Disable Device"
    assert roll_events[0]["dc"] == 20


def test_unbracketed_section_roll_block_sets_pending_roll(booted_session):
    """Section parser accepts live-model plain field ROLL blocks."""
    import api.session_manager as sm

    client, session_id = booted_session
    tokens = [
        "%%NARRATIVE%%\n\nYanyeeku listens for the singer.\n\n",
        "%%ROLL%%\n",
        "skill: Perception\n",
        "dc: 15\n",
        "success: You spot the goblin warchanter on a stall.\n\n",
        "She is clearly directing the warriors.\n",
        "failure: The shrieking crowd hides her position.\n",
        "%%ROLL%%\n",
        "%%DELTAS%%\n[]",
    ]
    mock_resp = make_stream_response(tokens)

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = _send(client, session_id, "Yanyeeku scans the square.")

    events = parse_sse(resp)
    roll_events = [e for e in events if e["type"] == "roll_request"]
    assert len(roll_events) == 1
    assert roll_events[0]["skill"] == "Perception"
    assert roll_events[0]["dc"] == 15

    session = sm._sessions[session_id]
    assert session.pending_roll is not None
    assert session.pending_roll["skill"] == "Perception"
    assert "warchanter" in session.pending_roll["success"]
    assert "directing the warriors" in session.pending_roll["success"]


def test_roll_request_preserves_active_speaker_for_resolution(booted_session):
    """A roll prompted by @Vanx resolves as Vanx, not generic player."""
    import api.session_manager as sm

    client, session_id = booted_session
    tokens = [
        "%%NARRATIVE%%\n\nVanx listens at the south wall.\n\n",
        "%%ROLL%%\n",
        "[ skill: Perception  dc: 10  success: Vanx hears movement.  failure: Vanx hears only festival noise. ]",
    ]
    mock_resp = make_stream_response(tokens)

    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = _send(client, session_id, '@Vanx: "I listen at the south wall."')

    roll_event = next(e for e in parse_sse(resp) if e["type"] == "roll_request")
    assert roll_event["speaker"] == "Vanx"

    resolved = client.post(f"/api/sessions/{session_id}/resolve_roll", json={"rolled": 11}).json()

    assert resolved["speaker"] == "Vanx"
    assert "Vanx's Perception check" in sm._sessions[session_id].messages[-1]["content"]


def test_parse_response_sections_keeps_first_nonempty_duplicate_marker():
    """A repeated empty section marker must not erase the real section body."""
    import api.session_manager as sm

    sections = sm._parse_response_sections(
        "%%ROLL%%\n"
        "skill: Perception\n"
        "dc: 15\n"
        "success: You see her.\n"
        "failure: You lose her.\n"
        "%%ROLL%%"
    )

    assert sections["ROLL"].startswith("skill: Perception")
    assert "You lose her" in sections["ROLL"]

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
