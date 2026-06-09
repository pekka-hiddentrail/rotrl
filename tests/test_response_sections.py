"""Tests for response section parsing — _parse_response_sections, _parse_bracket_blocks,
_extract_knowledge_items, and old flat-block fallback format detection."""
from __future__ import annotations

import pytest

from api.session_manager import (
    _DELTA_BLOCK_RE,
    _HAS_SECTION_MARKERS_RE,
    _extract_knowledge_items,
    _parse_bracket_blocks,
    _parse_response_sections,
)


# ── _parse_response_sections ──────────────────────────────────────────────────

def test_sections_splits_narrative_and_deltas():
    text = "%%NARRATIVE%%\nHello there.\n\n%%DELTAS%%\n[\nnpc: Kendra\nsummary: Greeted.\n]"
    s = _parse_response_sections(text)
    assert "Hello there." in s["NARRATIVE"]
    assert "Kendra" in s["DELTAS"]


def test_sections_fallback_when_no_markers():
    text = "Plain response with no markers."
    s = _parse_response_sections(text)
    assert s == {"NARRATIVE": text}


def test_sections_deltas_without_narrative_uses_full_text():
    """When model writes %%DELTAS%% but omits %%NARRATIVE%%, full text becomes fallback narrative."""
    text = "%%DELTAS%%\n[\nnpc: Kendra\nsummary: Greeted.\n]"
    s = _parse_response_sections(text)
    assert "NARRATIVE" in s
    assert s["NARRATIVE"] == text.strip()


def test_sections_all_four_sections():
    text = (
        "%%NARRATIVE%%\nScene description.\n\n"
        "%%ROLL%%\n[\nskill: Diplomacy\ndc: 15\nsuccess: works\nfailure: fails\n]\n\n"
        "%%GENERATE%%\n[\nname: Gorvoth\nrole: pyromancer\n]\n\n"
        "%%DELTAS%%\n[\nnpc: Kendra Deverin\nsummary: Greeted.\n]"
    )
    s = _parse_response_sections(text)
    assert "Scene description." in s.get("NARRATIVE", "")
    assert "Diplomacy" in s.get("ROLL", "")
    assert "Gorvoth" in s.get("GENERATE", "")
    assert "Kendra" in s.get("DELTAS", "")


def test_sections_empty_response():
    s = _parse_response_sections("")
    assert "NARRATIVE" in s


def test_sections_whitespace_only():
    s = _parse_response_sections("   \n\n  ")
    assert "NARRATIVE" in s


def test_sections_generate_before_deltas():
    """%%GENERATE%% appears before %%DELTAS%% — both parsed correctly."""
    text = (
        "%%NARRATIVE%%\nScene.\n\n"
        "%%GENERATE%%\n[\nname: Gorvoth\nrole: shopkeeper\n]\n\n"
        "%%DELTAS%%\n[\nnpc: Kendra\nsummary: Talked.\n]"
    )
    s = _parse_response_sections(text)
    assert "Gorvoth" in s.get("GENERATE", "")
    assert "Kendra" in s.get("DELTAS", "")


def test_sections_multiple_generate_blocks():
    text = (
        "%%NARRATIVE%%\nScene.\n\n"
        "%%GENERATE%%\n[\nname: Gorvoth\nrole: pyromancer\n]\n[\nname: Bottled Solutions\ntype: location\n]\n\n"
        "%%DELTAS%%\n[\nnpc: Kendra\nsummary: Talked.\n]"
    )
    s = _parse_response_sections(text)
    gen = s.get("GENERATE", "")
    assert "Gorvoth" in gen
    assert "Bottled Solutions" in gen


# ── _parse_bracket_blocks ─────────────────────────────────────────────────────

def test_bracket_blocks_single():
    text = "[\nnpc: Kendra Deverin\nsummary: Greeted.\n]"
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["npc"] == "Kendra Deverin"
    assert blocks[0]["summary"] == "Greeted."


def test_bracket_blocks_multiple():
    text = "[\nnpc: Kendra\nsummary: First.\n]\n[\nnpc: Belor\nsummary: Second.\n]"
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["npc"] == "Kendra"
    assert blocks[1]["npc"] == "Belor"


def test_bracket_blocks_multiple_knowledge_lines():
    text = (
        "[\nnpc: Kendra\n"
        "knowledge: [pcs] Knows Yanyeeku.\n"
        "knowledge: [quest] Heard about fireworks.\n"
        "summary: Talked.\n]"
    )
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 1
    assert isinstance(blocks[0]["knowledge"], list)
    assert len(blocks[0]["knowledge"]) == 2
    assert "[pcs] Knows Yanyeeku." in blocks[0]["knowledge"]


def test_bracket_blocks_trailing_comma_still_parsed():
    text = "[\nnpc: Kendra\nsummary: Greeted.\n],\n[\nnpc: Belor\nsummary: Watched.\n]"
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 2


def test_bracket_blocks_empty_section():
    assert _parse_bracket_blocks("") == []


def test_bracket_blocks_no_brackets():
    assert _parse_bracket_blocks("npc: Kendra\nsummary: Greeted.") == []


def test_bracket_blocks_new_format_fields():
    text = "[\ntype: npc\nname: Gorvoth\nrole: apothecary\nsummary: Knows sailors.\n]"
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "npc"
    assert blocks[0]["name"] == "Gorvoth"
    assert blocks[0]["role"] == "apothecary"


def test_bracket_blocks_location_type():
    text = "[\ntype: location\nname: Bottled Solutions\nrole: apothecary shop\n]"
    blocks = _parse_bracket_blocks(text)
    assert blocks[0]["type"] == "location"
    assert blocks[0]["name"] == "Bottled Solutions"


# ── _parse_bracket_blocks — single-line (inline) format ──────────────────────

def test_bracket_blocks_inline_basic():
    text = "[ npc: Ameiko Kaijitsu  disposition: neutral→interested  summary: Engaging cautiously. ]"
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["npc"] == "Ameiko Kaijitsu"
    assert "interested" in blocks[0]["disposition"]
    assert "Engaging" in blocks[0]["summary"]


def test_bracket_blocks_inline_full_ameiko():
    """Exact single-line format produced by the LLM for Ameiko (real regression case)."""
    text = (
        "[ npc: Ameiko Kaijitsu  disposition: neutral→interested"
        "  location: Rusty Dragon serving station"
        "  knowledge: [pcs] Ani is a traveler seeking history of the Lost Coast;"
        " [world] Ancient ruins dot the Lost Coast; most people avoid them"
        "  summary: Ameiko recognizes the question as serious. ]"
    )
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 1
    b = blocks[0]
    assert b["npc"] == "Ameiko Kaijitsu"
    assert "Rusty Dragon" in b["location"]
    assert "[pcs]" in b["knowledge"]
    assert "serious" in b["summary"]


def test_bracket_blocks_inline_multiple():
    text = (
        "[ npc: Ameiko  disposition: neutral→friendly  summary: Warming up. ]\n"
        "[ npc: Zantus  disposition: neutral  summary: Calm. ]"
    )
    blocks = _parse_bracket_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["npc"] == "Ameiko"
    assert blocks[1]["npc"] == "Zantus"


def test_bracket_blocks_inline_empty_text():
    assert _parse_bracket_blocks("") == []


def test_bracket_blocks_multiline_takes_priority():
    """Multi-line blocks should be returned even when inline blocks are also present."""
    multiline = "[\nnpc: Kendra\nsummary: First.\n]"
    inline = "[ npc: Belor  summary: Ignored. ]"
    blocks = _parse_bracket_blocks(multiline + "\n" + inline)
    # Multi-line wins; inline fallback is not tried
    assert len(blocks) == 1
    assert blocks[0]["npc"] == "Kendra"


# ── _extract_knowledge_items ──────────────────────────────────────────────────

def test_extract_knowledge_single():
    body = "npc: Kendra\nknowledge: [pcs] Met Yanyeeku.\nsummary: Greeted."
    assert _extract_knowledge_items(body) == ["[pcs] Met Yanyeeku."]


def test_extract_knowledge_multiple():
    body = "npc: Kendra\nknowledge: [pcs] Item one.\nknowledge: [quest] Item two.\nsummary: Done."
    items = _extract_knowledge_items(body)
    assert len(items) == 2
    assert "[pcs] Item one." in items
    assert "[quest] Item two." in items


def test_extract_knowledge_none():
    assert _extract_knowledge_items("npc: Kendra\nsummary: Greeted.") == []


def test_extract_knowledge_case_insensitive():
    body = "Knowledge: [pcs] Something important."
    items = _extract_knowledge_items(body)
    assert len(items) == 1


# ── Section marker detection ──────────────────────────────────────────────────

def test_has_section_markers_detects_narrative():
    assert _HAS_SECTION_MARKERS_RE.search("%%NARRATIVE%%\nHello.")


def test_has_section_markers_detects_deltas():
    assert _HAS_SECTION_MARKERS_RE.search("%%DELTAS%%\n[...]")


def test_has_section_markers_detects_generate():
    assert _HAS_SECTION_MARKERS_RE.search("%%GENERATE%%\n[...]")


def test_has_section_markers_false_on_old_format():
    # Old flat %%DELTA%% (singular) should NOT trigger the section path
    assert not _HAS_SECTION_MARKERS_RE.search("%%DELTA%%\nnpc: Kendra\n%%END%%")


# ── Old flat-block fallback (_DELTA_BLOCK_RE) ─────────────────────────────────

def test_delta_block_re_parses_old_format():
    text = "%%DELTA%%\nnpc: Kendra Deverin\ndisposition: friendly\n%%END%%"
    m = _DELTA_BLOCK_RE.search(text)
    assert m is not None
    assert "Kendra Deverin" in m.group(1)


def test_delta_block_re_without_end_marker():
    text = "%%DELTA%%\nnpc: Kendra\nsummary: Greeted.\n"
    m = _DELTA_BLOCK_RE.search(text)
    assert m is not None
    assert "Kendra" in m.group(1)


def test_delta_block_re_multiple_blocks():
    text = (
        "%%DELTA%%\nnpc: Kendra\nsummary: First.\n%%END%%\n"
        "%%DELTA%%\nnpc: Belor\nsummary: Second.\n%%END%%"
    )
    matches = list(_DELTA_BLOCK_RE.finditer(text))
    assert len(matches) == 2
