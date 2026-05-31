"""Tests for the %%NARRATIVE%% buffer+retry guard in _stream_chat().

# Covers: response-parsing.feature AC-006

When the LLM returns a section-format response (contains %% markers) that lacks
a %%NARRATIVE%% block, _stream_chat() discards the buffered tokens and retries
the LLM call up to _MAX_NARRATIVE_RETRIES times.

Flat-format responses (no %% markers at all) bypass the guard entirely — any
non-empty content is accepted.

Each attempt is logged independently via write_api_log, so the API log will
contain one entry per attempt.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from .conftest import make_stream_response, parse_sse


def _send(client, session_id: str, text: str = "We look around."):
    return client.post(f"/api/sessions/{session_id}/turn", json={"input": text})


# ── Section format with %%NARRATIVE%% present → accepted on first attempt ─────

def test_guard_passes_valid_section_response(booted_session):
    """A section-format response that contains %%NARRATIVE%% needs no retry."""
    client, session_id = booted_session
    mock = make_stream_response([
        "%%NARRATIVE%%\n", "The tavern bustles with noise.",
        "\n%%DELTAS%%\n", "[npc: Ameiko\ndisposition: friendly\n]",
    ])
    with patch("api.session_manager._requests.post", return_value=mock) as patched:
        resp = _send(client, session_id)

    assert resp.status_code == 200
    assert patched.call_count == 1


def test_guard_emits_narrative_tokens_on_valid_response(booted_session):
    """Token events contain the %%NARRATIVE%% content when no retry is needed."""
    client, session_id = booted_session
    mock = make_stream_response(["%%NARRATIVE%%\n", "The square is quiet."])
    with patch("api.session_manager._requests.post", return_value=mock):
        resp = _send(client, session_id)

    tokens = [e["content"] for e in parse_sse(resp) if e.get("type") == "token"]
    assert "The square is quiet." in "".join(tokens)


# ── Section format without %%NARRATIVE%% → retry once ────────────────────────

def test_guard_retries_on_missing_narrative(booted_session):
    """When the first attempt has no %%NARRATIVE%%, a second LLM call is made."""
    client, session_id = booted_session
    bad = make_stream_response([
        "%%ROLL%%\n", "skill: Perception\ndc: 15\nsuccess: You see it.\nfailure: Nothing.",
    ])
    good = make_stream_response(["%%NARRATIVE%%\n", "The chamber gleams."])

    with patch("api.session_manager._requests.post", side_effect=[bad, good]) as patched:
        resp = _send(client, session_id)

    assert resp.status_code == 200
    assert patched.call_count == 2


def test_guard_emits_retry_response_tokens(booted_session):
    """After a retry, the tokens emitted are from the second (valid) attempt."""
    client, session_id = booted_session
    bad = make_stream_response(["%%ROLL%%\n", "skill: Stealth\ndc: 12\nsuccess: Hidden.\nfailure: Seen."])
    good = make_stream_response(["%%NARRATIVE%%\n", "You slip into the shadows."])

    with patch("api.session_manager._requests.post", side_effect=[bad, good]):
        resp = _send(client, session_id)

    full_text = "".join(
        e.get("content", "") for e in parse_sse(resp) if e.get("type") == "token"
    )
    assert "You slip into the shadows." in full_text
    # Content from the failed first attempt must not appear
    assert "Stealth" not in full_text


# ── Both attempts lack %%NARRATIVE%% → proceed as-is after retries exhausted ─

def test_guard_proceeds_after_exhausting_retries(booted_session):
    """Guard does not abort the turn when all attempts lack %%NARRATIVE%%."""
    client, session_id = booted_session
    bad1 = make_stream_response(["%%ROLL%%\n", "skill: Perception\ndc: 10\nsuccess: Yes.\nfailure: No."])
    bad2 = make_stream_response(["%%DELTAS%%\n", "[npc: Guard\ndisposition: hostile\n]"])

    with patch("api.session_manager._requests.post", side_effect=[bad1, bad2]):
        resp = _send(client, session_id)

    assert resp.status_code == 200
    events = parse_sse(resp)
    assert any(e["type"] == "done" for e in events)


def test_guard_exhausted_retries_makes_two_llm_calls(booted_session):
    """Exactly two LLM calls are made when all retry attempts are exhausted."""
    client, session_id = booted_session
    bad1 = make_stream_response(["%%ROLL%%\n", "skill: Arcana\ndc: 18\nsuccess: Arcane.\nfailure: Blank."])
    bad2 = make_stream_response(["%%ROLL%%\n", "skill: Arcana\ndc: 18\nsuccess: Arcane.\nfailure: Blank."])

    with patch("api.session_manager._requests.post", side_effect=[bad1, bad2]) as patched:
        _send(client, session_id)

    assert patched.call_count == 2


# ── Flat-format responses (no %% markers) bypass the guard ───────────────────

def test_guard_skips_check_for_flat_format(booted_session):
    """Flat responses with no %% markers pass the guard unconditionally."""
    client, session_id = booted_session
    flat = make_stream_response(["The road winds through dark pines."])

    with patch("api.session_manager._requests.post", return_value=flat):
        resp = _send(client, session_id)

    assert resp.status_code == 200
    tokens = [e["content"] for e in parse_sse(resp) if e.get("type") == "token"]
    assert "The road winds through dark pines." in "".join(tokens)


def test_guard_flat_format_only_one_llm_call(booted_session):
    """Flat-format triggers exactly one LLM call — no retry attempted."""
    client, session_id = booted_session
    # side_effect list with one item: a second call would raise StopIteration
    flat = make_stream_response(["Arson is afoot in Sandpoint."])

    with patch("api.session_manager._requests.post", side_effect=[flat]) as patched:
        resp = _send(client, session_id)

    assert resp.status_code == 200
    assert patched.call_count == 1


# ── Retry is recorded in the session log ─────────────────────────────────────

def test_guard_retry_logged_to_session(booted_session):
    """A retry notice is appended to the session log when %%NARRATIVE%% is absent."""
    client, session_id = booted_session
    bad = make_stream_response(["%%ROLL%%\n", "skill: Arcana\ndc: 18\nsuccess: Know.\nfailure: Blank."])
    good = make_stream_response(["%%NARRATIVE%%\n", "Ancient runes line the wall."])

    with patch("api.session_manager._requests.post", side_effect=[bad, good]):
        _send(client, session_id)

    log = client.get(f"/api/sessions/{session_id}/log").text
    assert "%%NARRATIVE%% missing" in log
