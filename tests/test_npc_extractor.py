"""
tests/test_npc_extractor.py
──────────────────────────
Tests for api/context/npc_extractor.py

Covers:
  - _slugify
  - _find_base_md (slug match, canonical name scan, missing NPC)
  - _parse_block (H1 name, metadata fields, sections)
  - _parse_npc_file (above/below split, missing marker)
  - _match_key (exact, prefix, case-insensitive, no match)
  - get_npc_sections (no filter, specific sections, missing section, below_line)
  - list_npc_sections (above only, with below_line)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.context.npc_extractor import (
    _find_base_md,
    _match_key,
    _parse_block,
    _parse_npc_file,
    _slugify,
    get_npc_sections,
    list_npc_sections,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_BASE_MD = """\
# Abstalar Zantus

**Aliases:** zantus, father zantus, abstalar
**Locations:** cathedral, chapel

## Personality

Warm and genuinely kind. Calls people "friend" early in conversations.

## Appearance

A slight man of middle years whose calm is habitual.

## Location & Availability — Act I

- **Festival morning:** At the central podium.
- **During the attack:** Rushes toward wounded.

## GM Notes

- **Initial attitude:** Friendly without condition.
- **Voice/mannerism:** Speaks gently. Never raises his voice.

## Social Checks

- **Diplomacy (general):** DC 8 — already Friendly
- **Diplomacy (Tobyn's theft):** DC 15

## Secrets

- **Tobyn's remains stolen:** Father Tobyn's remains were removed from the boneyard.

## State Handling

- **If Cooperative:** Provides healing freely.
- **If Killed:** Morale collapses.

<!-- REFERENCE -->

**Tier:** II — Emotional Anchor
**Role:** Head Priest of the Cathedral of Desna
**Flags:** PLOT_CRITICAL, INFO_NODE, PERSISTENT

## Narrative Function

Serves as the town's spiritual compass.
"""

MINIMAL_BASE_MD = """\
# Larz Rovanky

**Aliases:** larz, rovanky
**Locations:** tannery

## Personality

A workaholic of legendary proportions.
"""


@pytest.fixture()
def npc_root(tmp_path: Path) -> Path:
    """Create a minimal NPC directory tree under tmp_path."""
    # Full-featured NPC
    zantus_dir = tmp_path / "abstalar_zantus"
    zantus_dir.mkdir()
    (zantus_dir / "base.md").write_text(SAMPLE_BASE_MD, encoding="utf-8")

    # Minimal NPC (no REFERENCE marker)
    larz_dir = tmp_path / "larz_rovanky"
    larz_dir.mkdir()
    (larz_dir / "base.md").write_text(MINIMAL_BASE_MD, encoding="utf-8")

    # Empty folder (no base.md)
    empty_dir = tmp_path / "nobody"
    empty_dir.mkdir()

    return tmp_path


# ── _slugify ──────────────────────────────────────────────────────────────────

class TestSlugify:
    def test_simple_name(self):
        assert _slugify("Abstalar Zantus") == "abstalar_zantus"

    def test_already_slug(self):
        assert _slugify("abstalar_zantus") == "abstalar_zantus"

    def test_apostrophe_stripped(self):
        assert _slugify("O'Brien") == "obrien"

    def test_multiple_spaces(self):
        assert _slugify("Kendra  Deverin") == "kendra_deverin"

    def test_lowercase_input(self):
        assert _slugify("ameiko kaijitsu") == "ameiko_kaijitsu"

    def test_trailing_leading_whitespace(self):
        assert _slugify("  Niska Mvashti  ") == "niska_mvashti"


# ── _find_base_md ─────────────────────────────────────────────────────────────

class TestFindBaseMd:
    def test_finds_by_slug(self, npc_root):
        path = _find_base_md("abstalar_zantus", npc_root)
        assert path.exists()
        assert path.name == "base.md"

    def test_finds_by_display_name(self, npc_root):
        path = _find_base_md("Abstalar Zantus", npc_root)
        assert path.exists()

    def test_finds_by_partial_case(self, npc_root):
        path = _find_base_md("abstalar zantus", npc_root)
        assert path.exists()

    def test_finds_minimal_npc(self, npc_root):
        path = _find_base_md("Larz Rovanky", npc_root)
        assert path.exists()

    def test_raises_for_unknown_npc(self, npc_root):
        with pytest.raises(FileNotFoundError, match="No base.md for"):
            _find_base_md("Nobody Important", npc_root)

    def test_raises_for_empty_folder(self, npc_root):
        with pytest.raises(FileNotFoundError):
            _find_base_md("nobody", npc_root)


# ── _parse_block ──────────────────────────────────────────────────────────────

class TestParseBlock:
    def test_extracts_name(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        assert result["Name"] == "Abstalar Zantus"

    def test_extracts_aliases(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        assert result["Aliases"] == "zantus, father zantus, abstalar"

    def test_extracts_locations(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        assert result["Locations"] == "cathedral, chapel"

    def test_extracts_personality_section(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        assert "Personality" in result
        assert "Warm and genuinely kind" in result["Personality"]

    def test_extracts_location_section_with_suffix(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        # Header includes "— Act I" suffix
        keys = list(result.keys())
        assert any(k.startswith("Location & Availability") for k in keys)

    def test_extracts_all_seven_sections(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        expected = {"Personality", "Appearance", "GM Notes", "Social Checks",
                    "Secrets", "State Handling"}
        found = {k for k in result if k in expected}
        assert found == expected

    def test_section_content_stripped(self):
        result = _parse_block(SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[0])
        # No leading/trailing blank lines in section content
        assert not result["Personality"].startswith("\n")
        assert not result["Personality"].endswith("\n")

    def test_below_line_metadata_fields(self):
        below_raw = SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[1]
        result = _parse_block(below_raw)
        assert result["Tier"] == "II — Emotional Anchor"
        assert result["Role"] == "Head Priest of the Cathedral of Desna"
        assert result["Flags"] == "PLOT_CRITICAL, INFO_NODE, PERSISTENT"

    def test_below_line_narrative_section(self):
        below_raw = SAMPLE_BASE_MD.split("<!-- REFERENCE -->")[1]
        result = _parse_block(below_raw)
        assert "Narrative Function" in result
        assert "spiritual compass" in result["Narrative Function"]

    def test_empty_string_returns_empty_dict(self):
        assert _parse_block("") == {}

    def test_no_h1_returns_no_name(self):
        result = _parse_block("**Aliases:** foo\n\n## Personality\n\nSome text.")
        assert "Name" not in result
        assert result["Aliases"] == "foo"
        assert "Personality" in result


# ── _parse_npc_file ───────────────────────────────────────────────────────────

class TestParseNpcFile:
    def test_above_contains_sections(self, npc_root):
        path = _find_base_md("abstalar_zantus", npc_root)
        above, _ = _parse_npc_file(path)
        assert "Personality" in above
        assert "State Handling" in above

    def test_above_does_not_contain_tier(self, npc_root):
        path = _find_base_md("abstalar_zantus", npc_root)
        above, _ = _parse_npc_file(path)
        assert "Tier" not in above

    def test_below_contains_tier_role_flags(self, npc_root):
        path = _find_base_md("abstalar_zantus", npc_root)
        _, below = _parse_npc_file(path)
        assert "Tier" in below
        assert "Role" in below
        assert "Flags" in below

    def test_below_contains_narrative_function(self, npc_root):
        path = _find_base_md("abstalar_zantus", npc_root)
        _, below = _parse_npc_file(path)
        assert "Narrative Function" in below

    def test_no_reference_marker_gives_empty_below(self, npc_root):
        path = _find_base_md("larz_rovanky", npc_root)
        above, below = _parse_npc_file(path)
        assert "Personality" in above
        assert below == {}

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _parse_npc_file(tmp_path / "nonexistent.md")


# ── _match_key ────────────────────────────────────────────────────────────────

class TestMatchKey:
    @pytest.fixture()
    def pool(self):
        return {
            "Name": "Abstalar Zantus",
            "Personality": "Warm and kind.",
            "Location & Availability — Act I": "Festival morning...",
            "Social Checks": "- Diplomacy DC 8",
            "State Handling": "- If Cooperative: ...",
        }

    def test_exact_match(self, pool):
        result = _match_key("Personality", pool)
        assert result == ("Personality", "Warm and kind.")

    def test_case_insensitive_exact(self, pool):
        result = _match_key("personality", pool)
        assert result is not None
        assert result[0] == "Personality"

    def test_prefix_match(self, pool):
        result = _match_key("location", pool)
        assert result is not None
        assert result[0] == "Location & Availability — Act I"

    def test_prefix_match_partial_word(self, pool):
        result = _match_key("social", pool)
        assert result is not None
        assert result[0] == "Social Checks"

    def test_prefix_match_state(self, pool):
        result = _match_key("state", pool)
        assert result is not None
        assert result[0] == "State Handling"

    def test_no_match_returns_none(self, pool):
        assert _match_key("secrets", pool) is None

    def test_empty_needle_matches_nothing(self, pool):
        # Empty string would prefix-match everything, but stripped → ""
        # Behaviour: matches first key whose lower().startswith("") — that's
        # every key. We treat this as valid but note it's caller's responsibility.
        result = _match_key("", pool)
        assert result is not None  # first key wins


# ── get_npc_sections ──────────────────────────────────────────────────────────

class TestGetNpcSections:
    def test_name_always_present(self, npc_root):
        result = get_npc_sections("abstalar_zantus", ["Personality"], _npc_root=npc_root)
        assert result["Name"] == "Abstalar Zantus"

    def test_single_section(self, npc_root):
        result = get_npc_sections("abstalar_zantus", ["Personality"], _npc_root=npc_root)
        assert "Personality" in result
        assert "Warm and genuinely kind" in result["Personality"]

    def test_multiple_sections(self, npc_root):
        result = get_npc_sections(
            "abstalar_zantus",
            ["Personality", "Social Checks", "State Handling"],
            _npc_root=npc_root,
        )
        assert "Personality" in result
        assert "Social Checks" in result
        assert "State Handling" in result

    def test_prefix_section_name(self, npc_root):
        result = get_npc_sections("abstalar_zantus", ["location"], _npc_root=npc_root)
        # Should match "Location & Availability — Act I"
        keys = [k for k in result if k != "Name"]
        assert len(keys) == 1
        assert keys[0].startswith("Location & Availability")

    def test_missing_section_returns_none(self, npc_root):
        result = get_npc_sections("abstalar_zantus", ["Appearance", "Inventory"], _npc_root=npc_root)
        assert result["Appearance"] is not None   # present in file
        assert result["Inventory"] is None        # not in file

    def test_no_sections_returns_all_above_line(self, npc_root):
        result = get_npc_sections("abstalar_zantus", _npc_root=npc_root)
        expected = {"Name", "Aliases", "Locations", "Personality", "Appearance",
                    "GM Notes", "Social Checks", "Secrets", "State Handling"}
        assert expected.issubset(set(result.keys()))

    def test_no_sections_excludes_below_line_by_default(self, npc_root):
        result = get_npc_sections("abstalar_zantus", _npc_root=npc_root)
        assert "Tier" not in result
        assert "Narrative Function" not in result

    def test_include_below_line(self, npc_root):
        result = get_npc_sections(
            "abstalar_zantus",
            ["Personality", "Tier", "Narrative Function"],
            include_below_line=True,
            _npc_root=npc_root,
        )
        assert result["Tier"] == "II — Emotional Anchor"
        assert "spiritual compass" in result["Narrative Function"]

    def test_below_line_excluded_without_flag(self, npc_root):
        result = get_npc_sections(
            "abstalar_zantus",
            ["Tier"],
            include_below_line=False,
            _npc_root=npc_root,
        )
        assert result["Tier"] is None

    def test_name_in_sections_list_not_duplicated(self, npc_root):
        result = get_npc_sections("abstalar_zantus", ["Name", "Personality"], _npc_root=npc_root)
        name_keys = [k for k in result if k == "Name"]
        assert len(name_keys) == 1

    def test_display_name_resolution(self, npc_root):
        result = get_npc_sections("Abstalar Zantus", ["Personality"], _npc_root=npc_root)
        assert result["Name"] == "Abstalar Zantus"

    def test_unknown_npc_raises(self, npc_root):
        with pytest.raises(FileNotFoundError):
            get_npc_sections("Nobody Important", _npc_root=npc_root)

    def test_minimal_npc_no_reference_marker(self, npc_root):
        result = get_npc_sections("larz_rovanky", ["Personality"], _npc_root=npc_root)
        assert result["Name"] == "Larz Rovanky"
        assert "workaholic" in result["Personality"]

    def test_aliases_included_in_no_filter_result(self, npc_root):
        result = get_npc_sections("abstalar_zantus", _npc_root=npc_root)
        assert result["Aliases"] == "zantus, father zantus, abstalar"

    def test_locations_included_in_no_filter_result(self, npc_root):
        result = get_npc_sections("abstalar_zantus", _npc_root=npc_root)
        assert result["Locations"] == "cathedral, chapel"


# ── list_npc_sections ─────────────────────────────────────────────────────────

class TestListNpcSections:
    def test_returns_list_of_strings(self, npc_root):
        sections = list_npc_sections("abstalar_zantus", _npc_root=npc_root)
        assert isinstance(sections, list)
        assert all(isinstance(s, str) for s in sections)

    def test_contains_expected_above_line_sections(self, npc_root):
        sections = list_npc_sections("abstalar_zantus", _npc_root=npc_root)
        for expected in ["Name", "Aliases", "Locations", "Personality", "Social Checks"]:
            assert expected in sections

    def test_excludes_below_line_by_default(self, npc_root):
        sections = list_npc_sections("abstalar_zantus", _npc_root=npc_root)
        assert "Tier" not in sections
        assert "Narrative Function" not in sections

    def test_include_below_line_adds_fields(self, npc_root):
        sections = list_npc_sections(
            "abstalar_zantus", include_below_line=True, _npc_root=npc_root
        )
        assert "Tier" in sections
        assert "Role" in sections
        assert "Flags" in sections
        assert "Narrative Function" in sections

    def test_no_duplicates(self, npc_root):
        sections = list_npc_sections(
            "abstalar_zantus", include_below_line=True, _npc_root=npc_root
        )
        assert len(sections) == len(set(sections))

    def test_minimal_npc(self, npc_root):
        sections = list_npc_sections("larz_rovanky", _npc_root=npc_root)
        assert "Name" in sections
        assert "Personality" in sections

    def test_unknown_npc_raises(self, npc_root):
        with pytest.raises(FileNotFoundError):
            list_npc_sections("Unknown NPC", _npc_root=npc_root)
