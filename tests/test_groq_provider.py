"""Tests for Groq provider — _groq_post retry logic and Groq turn streaming."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import api.session_manager as sm
from api.session_manager import _groq_post

from .conftest import parse_sse


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_resp(status_code: int, headers: dict = None) -> MagicMock:
    import requests as _req
    mock = MagicMock()
    mock.status_code = status_code
    mock.headers = headers or {}
    if status_code == 200:
        mock.raise_for_status = MagicMock()
    else:
        mock.raise_for_status.side_effect = _req.HTTPError(response=mock)
    return mock


def make_groq_stream_response(tokens: list[str]) -> MagicMock:
    lines = [
        f'data: {json.dumps({"choices": [{"delta": {"content": t}}]})}'.encode()
        for t in tokens
    ]
    lines.append(b"data: [DONE]")
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status = MagicMock()
    mock.iter_lines = MagicMock(return_value=iter(lines))
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


@pytest.fixture()
def groq_session(client, monkeypatch):
    """Boot a Groq-provider session."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "temperature": 0.3,
        "dev_mode": False,
    })
    assert resp.status_code == 200
    events = parse_sse(resp)
    done = next(e for e in events if e["type"] == "done")
    return client, done["session_id"]


# ── _groq_post unit tests ─────────────────────────────────────────────────────

def test_groq_post_returns_on_200(monkeypatch):
    ok = _make_resp(200)
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: ok)
    assert _groq_post("key", {"model": "x"}) is ok


def test_groq_post_retries_on_429_then_succeeds(monkeypatch):
    ok = _make_resp(200)
    rate = _make_resp(429)
    seq = iter([rate, ok])
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: next(seq))
    monkeypatch.setattr(sm._time, "sleep", lambda s: None)
    assert _groq_post("key", {"model": "x"}) is ok


def test_groq_post_uses_retry_after_header(monkeypatch):
    ok = _make_resp(200)
    rate = _make_resp(429, headers={"retry-after": "7"})
    seq = iter([rate, ok])
    slept: list[float] = []
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: next(seq))
    monkeypatch.setattr(sm._time, "sleep", lambda s: slept.append(s))
    _groq_post("key", {"model": "x"})
    assert slept == [7.0]


def test_groq_post_uses_x_ratelimit_header(monkeypatch):
    ok = _make_resp(200)
    rate = _make_resp(429, headers={"x-ratelimit-reset-requests": "3"})
    seq = iter([rate, ok])
    slept: list[float] = []
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: next(seq))
    monkeypatch.setattr(sm._time, "sleep", lambda s: slept.append(s))
    _groq_post("key", {"model": "x"})
    assert slept == [3.0]


def test_groq_post_exponential_backoff_without_header(monkeypatch):
    ok = _make_resp(200)
    rate1 = _make_resp(429)
    rate2 = _make_resp(429)
    seq = iter([rate1, rate2, ok])
    slept: list[float] = []
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: next(seq))
    monkeypatch.setattr(sm._time, "sleep", lambda s: slept.append(s))
    _groq_post("key", {"model": "x"})
    # second wait should be doubled from first
    assert len(slept) == 2
    assert slept[1] >= slept[0]


def test_groq_post_raises_on_413(monkeypatch):
    resp = MagicMock()
    resp.status_code = 413
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: resp)
    with pytest.raises(RuntimeError, match="payload too large"):
        _groq_post("key", {"model": "x"})


def test_groq_post_raises_after_max_retries(monkeypatch):
    rate = _make_resp(429)
    monkeypatch.setattr(sm._requests, "post", lambda *a, **kw: rate)
    monkeypatch.setattr(sm._time, "sleep", lambda s: None)
    with pytest.raises(Exception):
        _groq_post("key", {"model": "x"})


def test_groq_post_raises_on_500_immediately(monkeypatch):
    err = _make_resp(500)
    call_count = 0
    def mock_post(*a, **kw):
        nonlocal call_count
        call_count += 1
        return err
    monkeypatch.setattr(sm._requests, "post", mock_post)
    with pytest.raises(Exception):
        _groq_post("key", {"model": "x"})
    assert call_count == 1  # did not retry


# ── Groq turn streaming via the API ──────────────────────────────────────────

def test_groq_turn_streams_narrative(groq_session):
    client, session_id = groq_session
    mock_resp = make_groq_stream_response([
        "%%NARRATIVE%%\n", "The square is busy.", " What do you do?"
    ])
    with patch("api.session_manager._requests.post", return_value=mock_resp):
        resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "We look around."})

    assert resp.status_code == 200
    events = parse_sse(resp)
    tokens = [e["content"] for e in events if e["type"] == "token"]
    # In non-dev mode the narrative filter passes only %%NARRATIVE%% content
    full = "".join(tokens)
    assert "The square is busy." in full


def test_groq_missing_api_key_returns_error(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "temperature": 0.3,
    })
    events = parse_sse(resp)
    done = next(e for e in events if e["type"] == "done")
    session_id = done["session_id"]

    resp2 = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Hello."})
    events2 = parse_sse(resp2)
    error_events = [e for e in events2 if e["type"] == "error"]
    assert any("GROQ_API_KEY" in e["message"] for e in error_events)


def test_groq_max_history_respected(groq_session, monkeypatch):
    client, session_id = groq_session
    captured: list[dict] = []

    def fake_post(url, headers, json, stream, timeout):
        captured.append(json)
        return make_groq_stream_response(["%%NARRATIVE%%\nReply."])

    # Send enough turns to exceed GROQ_MAX_HISTORY
    with patch("api.session_manager._requests.post", side_effect=fake_post):
        for i in range(sm._GROQ_MAX_HISTORY + 2):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": f"Turn {i}."})

    # On the last call, messages sent should not exceed limit + system prompt
    last_payload = captured[-1]
    assert len(last_payload["messages"]) <= sm._GROQ_MAX_HISTORY + 1
