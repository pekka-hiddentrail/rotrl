"""Unit tests for _enforce_recap_header — guarantees canonical recap.md structure."""
from __future__ import annotations

import re

from api.session_manager import _enforce_recap_header


def _parse(text: str) -> dict:
    """Pull the structural parts out of a recap for easy assertions."""
    lines = text.splitlines()
    return {
        "heading": lines[0] if lines else "",
        "date_line": lines[2] if len(lines) > 2 else "",
        "separator1": lines[4] if len(lines) > 4 else "",
        "full": text,
    }


# ── Heading format ────────────────────────────────────────────────────────────

def test_heading_contains_session_number():
    out = _enforce_recap_header("Some prose here.", 3)
    assert out.startswith("# Session 3 — ")


def test_heading_extracts_llm_title():
    llm = "# Session 1 — The Burning Steeple\n\n*Sandpoint — 4707 AR*\n\n---\n\nProse."
    out = _enforce_recap_header(llm, 1)
    assert "The Burning Steeple" in out.splitlines()[0]


def test_heading_fallback_title_when_no_heading():
    out = _enforce_recap_header("Just prose, no heading at all.", 2)
    assert out.startswith("# Session 2 — ")


# ── Date/place line ───────────────────────────────────────────────────────────

def test_date_line_preserved_from_llm():
    llm = "# Session 1 — Title\n\n*Magnimar, Varisia — 2nd of Lamashan, 4707 AR*\n\n---\n\nBody."
    out = _enforce_recap_header(llm, 1)
    assert "*Magnimar, Varisia — 2nd of Lamashan, 4707 AR*" in out


def test_date_line_default_when_missing():
    out = _enforce_recap_header("Just a body paragraph.", 1)
    lines = out.splitlines()
    # Second non-blank line should be an italicised fallback
    assert lines[2].startswith("*") and lines[2].endswith("*")


# ── Separator lines ───────────────────────────────────────────────────────────

def test_separator_after_date():
    out = _enforce_recap_header("Body text.", 1)
    lines = out.splitlines()
    assert lines[4] == "---"


def test_ends_with_separator():
    out = _enforce_recap_header("Body text.", 1)
    # Last non-empty line should be ---
    non_empty = [l for l in out.splitlines() if l.strip()]
    assert non_empty[-1] == "---"


# ── Body preservation ─────────────────────────────────────────────────────────

def test_body_text_preserved():
    body = "The party stood in the square. Father Zantus waved from the steps."
    out = _enforce_recap_header(body, 1)
    assert body in out


def test_duplicate_separators_not_doubled():
    """LLM sometimes wraps body in --- ... --- — we should not get ---- or doubled lines."""
    llm = "# Session 1 — Title\n\n*Place*\n\n---\n\nBody text.\n\n---\n"
    out = _enforce_recap_header(llm, 1)
    assert "----" not in out
    assert out.count("\n---\n") <= 2  # opening + closing only


def test_no_markdown_leaked_into_heading():
    """Heading should never contain ##, **, or stray markdown."""
    out = _enforce_recap_header("## Bad heading\n\nBody.", 1)
    heading = out.splitlines()[0]
    assert not heading.startswith("##")
    assert "**" not in heading
