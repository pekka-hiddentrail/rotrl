"""Tests for end-of-session recap/boot generation.

Covers:
  - _parse_turns_from_log: edge cases (empty log, no markers, details blocks, multi-turn)
  - _enforce_recap_header: canonical header injection, LLM heading stripping
  - stream_end_session: error paths (missing log, empty turns, missing API key)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from api.session_manager import (
    _enforce_recap_header,
    _parse_turns_from_log,
)


# ── _parse_turns_from_log ─────────────────────────────────────────────────────

def _write_log(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_turns_empty_log(tmp_path):
    log = _write_log(tmp_path / "session.md", "")
    assert _parse_turns_from_log(log) == []


def test_parse_turns_no_headers(tmp_path):
    log = _write_log(tmp_path / "session.md", "Some preamble without turn headers.\n")
    assert _parse_turns_from_log(log) == []


def test_parse_turns_single_player(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] PLAYER\nWe look around the square.\n")
    turns = _parse_turns_from_log(log)
    assert len(turns) == 1
    assert turns[0]["role"] == "PLAYER"
    assert "look around" in turns[0]["content"]


def test_parse_turns_single_gm(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:01:00] GM\nThe crowd parts before you.\n")
    turns = _parse_turns_from_log(log)
    assert len(turns) == 1
    assert turns[0]["role"] == "GM"
    assert "crowd" in turns[0]["content"]


def test_parse_turns_player_then_gm(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] PLAYER\nWe approach the mayor.\n\n"
        "### [10:01:00] GM\nShe turns to greet you.\n")
    turns = _parse_turns_from_log(log)
    assert len(turns) == 2
    assert turns[0]["role"] == "PLAYER"
    assert turns[1]["role"] == "GM"


def test_parse_turns_strips_details_blocks(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] PLAYER\nApproach the inn.\n"
        "<details><summary>LLM payload</summary>\n"
        "Secret system prompt content.\n"
        "</details>\n"
        "### [10:01:00] GM\nThe inn is warm.\n")
    turns = _parse_turns_from_log(log)
    roles = [t["role"] for t in turns]
    assert "PLAYER" in roles
    assert "GM" in roles
    assert all("Secret" not in t["content"] for t in turns)


def test_parse_turns_stops_at_h2_separator(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] PLAYER\nApproach the inn.\n"
        "## SYSTEM PROMPT\n"
        "You are the GM…\n"
        "### [10:01:00] GM\nThe inn is warm.\n")
    turns = _parse_turns_from_log(log)
    assert all("You are the GM" not in t["content"] for t in turns)


def test_parse_turns_stops_at_dash_separator(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] PLAYER\nWe ask about fireworks.\n"
        "---\n"
        "GM directive should not appear\n"
        "### [10:01:00] GM\nFireworks are lovely.\n")
    turns = _parse_turns_from_log(log)
    player_turn = next(t for t in turns if t["role"] == "PLAYER")
    assert "GM directive" not in player_turn["content"]


def test_parse_turns_multiple_turns_all_captured(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] PLAYER\nTurn 1.\n"
        "### [10:01:00] GM\nReply 1.\n"
        "### [10:02:00] PLAYER\nTurn 2.\n"
        "### [10:03:00] GM\nReply 2.\n")
    turns = _parse_turns_from_log(log)
    assert len(turns) == 4


def test_parse_turns_skips_gm_directive_lines(tmp_path):
    log = _write_log(tmp_path / "session.md",
        "### [10:00:00] GM\nThe festival is bright.\n"
        "> *[GM directive injected]*\n"
        "More GM narration.\n")
    turns = _parse_turns_from_log(log)
    assert len(turns) == 1
    assert "GM directive" not in turns[0]["content"]
    assert "festival" in turns[0]["content"]


# ── _enforce_recap_header ─────────────────────────────────────────────────────

def test_enforce_recap_header_injects_canonical_form():
    body = "The party fought goblins and saved the festival."
    result = _enforce_recap_header(body, 1)
    assert result.startswith("# Session 1 — ")
    assert "---" in result
    assert "goblins" in result


def test_enforce_recap_header_strips_llm_heading():
    text = "# Session 1 — The Swallowtail Festival\n\nThe goblins attacked."
    result = _enforce_recap_header(text, 1)
    lines = result.splitlines()
    h1_lines = [l for l in lines if l.startswith("# Session")]
    assert len(h1_lines) == 1
    assert "Swallowtail" in h1_lines[0]


def test_enforce_recap_header_preserves_place_date():
    text = "# Session 2 — Goblin War\n\n*Sandpoint, Varisia — 4707 AR*\n\n---\n\nBody text."
    result = _enforce_recap_header(text, 2)
    assert "*Sandpoint, Varisia — 4707 AR*" in result


def test_enforce_recap_header_adds_default_place_date_when_missing():
    text = "The goblins attacked the town."
    result = _enforce_recap_header(text, 3)
    assert "*Sandpoint" in result or "4707 AR" in result


def test_enforce_recap_header_strips_trailing_separator():
    text = "Body text.\n\n---\n"
    result = _enforce_recap_header(text, 1)
    # Should not have double trailing ---
    assert result.count("---") <= 2


def test_enforce_recap_header_session_number_in_output():
    result = _enforce_recap_header("Some body.", 5)
    assert "# Session 5 — " in result


# ── stream_end_session error paths ────────────────────────────────────────────

def test_stream_end_session_no_log_file(client):
    """End-session with no log file yields an error event."""
    import api.session_manager as sm

    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "provider": "ollama",
        "dev_mode": True,
    })
    from tests.conftest import parse_sse
    events = parse_sse(resp)
    done = next((e for e in events if e["type"] == "done"), None)
    assert done is not None, f"Boot did not return a 'done' event; got: {events}"
    session_id = done["session_id"]

    # Patch log_path to a non-existent path so stream_end_session hits the error branch.
    session = sm._sessions[session_id]
    session.log_path = Path("/nonexistent/path/session.md")

    resp2 = client.post(f"/api/sessions/{session_id}/end")
    events2 = parse_sse(resp2)
    error_events = [e for e in events2 if e["type"] == "error"]
    assert len(error_events) >= 1
    assert any("log" in e["message"].lower() or "No log" in e["message"] for e in error_events)


def test_stream_end_session_empty_turns(client, tmp_path):
    """End-session with a log that has no PLAYER/GM turns yields an error event."""
    import api.session_manager as sm

    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "provider": "ollama",
        "dev_mode": True,
    })
    from tests.conftest import parse_sse
    events = parse_sse(resp)
    done = next((e for e in events if e["type"] == "done"), None)
    assert done is not None, f"Boot did not return a 'done' event; got: {events}"
    session_id = done["session_id"]

    # Write an empty log file.
    log_path = tmp_path / "empty_session.md"
    log_path.write_text("# System Prompt\nYou are the GM.\n", encoding="utf-8")
    sm._sessions[session_id].log_path = log_path

    resp2 = client.post(f"/api/sessions/{session_id}/end")
    events2 = parse_sse(resp2)
    error_events = [e for e in events2 if e["type"] == "error"]
    assert len(error_events) >= 1
    assert any("turn" in e["message"].lower() for e in error_events)
