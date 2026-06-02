"""
Tests for _stream_with_narrative_filter in api/session_manager.py.

Covers:
  - dev_mode=True: all tokens pass through unmodified
  - non-dev mode: only %%NARRATIVE%% section content is streamed
  - non-token SSE events (done, patch_last, etc.) always pass through
  - holdback buffer prevents partial section markers from leaking
  - old-format fallback: streams everything after 200 chars without %%NARRATIVE%%
  - stop markers: %%ROLL%%, %%DELTAS%%, %%GENERATE%% all terminate narrative output
"""
from __future__ import annotations

import json
from typing import Generator

import pytest

from api.session_manager import _stream_with_narrative_filter


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tok(text: str) -> str:
    """Encode a token SSE event."""
    return f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"


def _evt(payload: dict) -> str:
    """Encode a non-token SSE event."""
    return f"data: {json.dumps(payload)}\n\n"


def _collect(gen: Generator[str, None, None]) -> list[str]:
    """Drain generator into a list of raw SSE strings."""
    return list(gen)


def _content(events: list[str]) -> str:
    """Concatenate the 'content' field of all token events."""
    out = []
    for ev in events:
        try:
            d = json.loads(ev[6:])
            if d.get("type") == "token":
                out.append(d["content"])
        except Exception:
            pass
    return "".join(out)


def _gen_from(*parts: str) -> Generator[str, None, None]:
    """Yield each part as a pre-formed SSE string."""
    yield from parts


# ── Dev mode ─────────────────────────────────────────────────────────────────

def test_dev_mode_passes_all_tokens():
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("Hello world"),
        _tok("\n%%DELTAS%%\n"),
        _tok("npc: Foo"),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=True))
    assert result == events


def test_dev_mode_passes_event_trigger_tokens():
    events = [
        _tok("%%NARRATIVE%%\nGoblins spill into the square.\n"),
        _tok("%%EVENT%% goblin_attack_starts\n"),
        _tok("%%DELTAS%%\nnpc: Foo"),
    ]

    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=True))
    assert result == events


def test_dev_mode_passes_non_token_events():
    events = [
        _evt({"type": "done"}),
        _tok("some text"),
        _evt({"type": "patch_last", "content": "x"}),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=True))
    assert result == events


# ── Non-dev: basic narrative extraction ──────────────────────────────────────

def test_non_dev_extracts_narrative_content():
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("The tavern glows warmly."),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert _content(result) == "The tavern glows warmly."


def test_non_dev_strips_preamble_before_narrative():
    events = [
        _tok("Some preamble text\n"),
        _tok("%%NARRATIVE%%\n"),
        _tok("Actual story."),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert _content(result) == "Actual story."


def test_non_dev_stops_at_roll_marker():
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("Story text."),
        _tok("\n%%ROLL%%\n"),
        _tok("dc: 15"),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert _content(result) == "Story text."


def test_non_dev_stops_at_deltas_marker():
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("Story continues."),
        _tok("\n%%DELTAS%%\n"),
        _tok("["),
        _tok("npc: Bar"),
        _tok("]"),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert _content(result) == "Story continues."


def test_non_dev_stops_at_generate_marker():
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("A stranger arrives."),
        _tok("\n%%GENERATE%%\n"),
        _tok("["),
        _tok("npc: Stranger"),
        _tok("]"),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert _content(result) == "A stranger arrives."


def test_non_dev_stops_at_event_marker():
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("Goblins spill into the square."),
        _tok("\n%%EVENT%% goblin_attack_starts\n"),
        _tok("%%DELTAS%%\nnpc: Foo"),
    ]

    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    content = _content(result)

    assert content == "Goblins spill into the square."
    assert "%%EVENT%%" not in content
    assert "goblin_attack_starts" not in content


# ── Non-token events always pass through ─────────────────────────────────────

def test_non_dev_passes_non_token_events_through():
    done_ev = _evt({"type": "done"})
    patch_ev = _evt({"type": "patch_last", "content": "clean"})
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("Narrative."),
        done_ev,
        patch_ev,
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert done_ev in result
    assert patch_ev in result


# ── Cross-boundary holdback ───────────────────────────────────────────────────

def test_holdback_prevents_marker_leak():
    """A section marker split across two tokens must not partially leak."""
    # Deliver the end marker split across two token events
    events = [
        _tok("%%NARRATIVE%%\n"),
        _tok("Good text here. "),
        _tok("\n%%DELTA"),   # partial marker — should be held back
        _tok("S%%\nnpc: X"),  # completes the marker
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    content = _content(result)
    # "%%DELTAS%%" and content after it must not appear
    assert "%%DELTA" not in content
    assert "npc: X" not in content
    # The narrative text before the marker should be present
    assert "Good text here." in content


# ── Old-format fallback ───────────────────────────────────────────────────────

def test_old_format_fallback_streams_after_200_chars():
    """If no %%NARRATIVE%% found after 200 chars, stream everything."""
    long_preamble = "x" * 201
    events = [_tok(long_preamble), _tok(" final text")]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    combined = _content(result)
    assert "final text" in combined


def test_old_format_fallback_does_not_trigger_before_200_chars():
    """Short preamble without %%NARRATIVE%% should not yield tokens yet."""
    events = [_tok("Short preamble")]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    # No narrative section found, holdback still buffering — content may be empty
    # (the holdback keeps up to 16 chars, short preamble < 200 chars → no emit)
    assert _content(result) == ""


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_stream_produces_no_output():
    result = _collect(_stream_with_narrative_filter(_gen_from(), dev_mode=False))
    assert result == []


def test_narrative_marker_split_across_tokens():
    """%%NARRATIVE%%\\n split across two tokens should still be detected."""
    events = [
        _tok("%%NARR"),
        _tok("ATIVE%%\n"),
        _tok("Content after split."),
    ]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert _content(result) == "Content after split."


def test_malformed_sse_event_passed_through():
    """Unparseable SSE lines pass through unchanged (belt-and-suspenders)."""
    bad = "data: not-json\n\n"
    events = [bad, _tok("%%NARRATIVE%%\n"), _tok("Hello.")]
    result = _collect(_stream_with_narrative_filter(_gen_from(*events), dev_mode=False))
    assert bad in result
