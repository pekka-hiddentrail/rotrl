"""Tests for LocationIndex and _parse_location_base.

Coverage:
- AC-001: loads canonical locations, skips _ dirs, skips dirs without base.md
- AC-002: base.md format — aliases, REFERENCE boundary, profile_body
- AC-003: alias match injects profile
- AC-004: longest alias wins
- AC-005: location + NPC-at-location both detected (integration with inject_context)
- AC-006: loc / loc_trigger in context_info; null when no match
- AC-007: scene_locations persistence across turns
- AC-008 / AC-009: %%GENERATE%% location stub creation + index invalidation
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api.context.location_lookup import LocationIndex, LocationMatch, _parse_location_base


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_base_md(
    name: str = "Test Location",
    aliases: str = "test, test location",
    body: str = "## Description\n\nA test place.",
    reference: str = "**District:** Sandpoint",
) -> str:
    return (
        f"# {name}\n"
        f"**Aliases:** {aliases}\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"<!-- REFERENCE -->\n"
        f"{reference}\n"
    )


def _make_index(tmp_path: Path, locations: dict[str, str]) -> LocationIndex:
    """Create a LocationIndex pointing at tmp_path with given {slug: base_md_content} entries."""
    locs_root = tmp_path / "adventure_path" / "03_locations"
    locs_root.mkdir(parents=True)
    for slug, content in locations.items():
        loc_dir = locs_root / slug
        loc_dir.mkdir()
        (loc_dir / "base.md").write_text(content, encoding="utf-8")
    return LocationIndex(_repo_root=tmp_path)


# ── AC-001: index loading ─────────────────────────────────────────────────────

class TestIndexLoading:
    def test_loads_canonical_locations(self, tmp_path):
        idx = _make_index(tmp_path, {
            "rusty_dragon": _make_base_md("The Rusty Dragon", "rusty dragon, inn"),
            "garrison":     _make_base_md("Sandpoint Garrison", "garrison"),
        })
        known = idx.known_locations
        assert "The Rusty Dragon" in known
        assert "Sandpoint Garrison" in known

    def test_skips_underscore_prefixed_dirs(self, tmp_path):
        locs_root = tmp_path / "adventure_path" / "03_locations"
        locs_root.mkdir(parents=True)
        tmpl_dir = locs_root / "_LOCATION_TEMPLATE"
        tmpl_dir.mkdir()
        (tmpl_dir / "base.md").write_text(_make_base_md("Template"), encoding="utf-8")
        idx = LocationIndex(_repo_root=tmp_path)
        assert "Template" not in idx.known_locations

    def test_skips_dirs_missing_base_md(self, tmp_path):
        locs_root = tmp_path / "adventure_path" / "03_locations"
        locs_root.mkdir(parents=True)
        empty_dir = locs_root / "no_base"
        empty_dir.mkdir()
        idx = LocationIndex(_repo_root=tmp_path)
        assert idx.known_locations == []

    def test_missing_03_locations_dir_is_safe(self, tmp_path):
        idx = LocationIndex(_repo_root=tmp_path)
        assert idx.known_locations == []
        assert idx.detect("garrison") is None

    def test_loaded_flag_prevents_double_scan(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Garrison", "garrison")})
        _ = idx.known_locations  # triggers load
        locs_root = tmp_path / "adventure_path" / "03_locations"
        new_dir = locs_root / "cathedral"
        new_dir.mkdir()
        (new_dir / "base.md").write_text(_make_base_md("Cathedral", "cathedral"), encoding="utf-8")
        # Should NOT pick up the new file — already loaded
        assert "Cathedral" not in idx.known_locations


# ── AC-002: base.md format / parser ──────────────────────────────────────────

class TestParseLocationBase:
    def test_extracts_canonical_name(self, tmp_path):
        p = tmp_path / "base.md"
        p.write_text(_make_base_md("Sandpoint Cathedral", "cathedral"), encoding="utf-8")
        canonical, _, _ = _parse_location_base(p)
        assert canonical == "Sandpoint Cathedral"

    def test_extracts_aliases(self, tmp_path):
        p = tmp_path / "base.md"
        p.write_text(_make_base_md("Garrison", "garrison, guard post, barracks"), encoding="utf-8")
        _, aliases, _ = _parse_location_base(p)
        assert "garrison" in aliases
        assert "guard post" in aliases
        assert "barracks" in aliases

    def test_profile_body_excludes_header_and_aliases(self, tmp_path):
        p = tmp_path / "base.md"
        p.write_text(_make_base_md("Garrison", "garrison", "## Description\n\nA stone fort."), encoding="utf-8")
        _, _, profile = _parse_location_base(p)
        assert "Garrison" not in profile
        assert "garrison" not in profile
        assert "A stone fort." in profile

    def test_reference_section_excluded(self, tmp_path):
        p = tmp_path / "base.md"
        p.write_text(_make_base_md(reference="**District:** Hidden"), encoding="utf-8")
        _, _, profile = _parse_location_base(p)
        assert "Hidden" not in profile

    def test_missing_file_returns_empty(self, tmp_path):
        canonical, aliases, profile = _parse_location_base(tmp_path / "nonexistent.md")
        assert canonical == ""
        assert aliases == []
        assert profile == ""

    def test_aliases_stripped_of_whitespace(self, tmp_path):
        p = tmp_path / "base.md"
        p.write_text(_make_base_md("X", "  foo , bar  , baz  "), encoding="utf-8")
        _, aliases, _ = _parse_location_base(p)
        assert aliases == ["foo", "bar", "baz"]


# ── AC-003: alias detection ───────────────────────────────────────────────────

class TestDetect:
    def test_detects_single_word_alias(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        m = idx.detect("We head to the garrison")
        assert m is not None
        assert m.canonical_name == "Sandpoint Garrison"
        assert m.matched_alias == "garrison"

    def test_detects_multi_word_alias(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison, guard post")})
        m = idx.detect("we go to the guard post")
        assert m is not None
        assert m.canonical_name == "Sandpoint Garrison"
        assert m.matched_alias == "guard post"

    def test_no_match_returns_none(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Garrison", "garrison")})
        assert idx.detect("we look around the market") is None

    def test_case_insensitive(self, tmp_path):
        idx = _make_index(tmp_path, {"cat": _make_base_md("Cathedral", "Cathedral")})
        assert idx.detect("We enter the CATHEDRAL") is not None

    def test_matched_profile_text_present(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Garrison", "garrison", "## Description\n\nStone walls.")})
        m = idx.detect("go to garrison")
        assert m is not None
        assert "Stone walls." in m.profile_text

    def test_alias_boundary_word_match(self, tmp_path):
        idx = _make_index(tmp_path, {"inn": _make_base_md("The Inn", "inn")})
        # "inning" should NOT match "inn"
        assert idx.detect("we went inning") is None
        assert idx.detect("we go to the inn") is not None


# ── AC-004: longest alias wins ────────────────────────────────────────────────

class TestLongestAliasWins:
    def test_longer_alias_beats_shorter(self, tmp_path):
        idx = _make_index(tmp_path, {
            "cathedral": _make_base_md("Sandpoint Cathedral", "cathedral, desna cathedral")
        })
        m = idx.detect("We enter the Desna Cathedral")
        assert m is not None
        assert m.matched_alias == "desna cathedral"

    def test_different_locations_longest_wins(self, tmp_path):
        idx = _make_index(tmp_path, {
            "inn":   _make_base_md("Inn", "inn"),
            "rusty": _make_base_md("Rusty Dragon", "rusty dragon, inn"),
        })
        m = idx.detect("we go to the rusty dragon")
        assert m is not None
        assert m.canonical_name == "Rusty Dragon"
        assert m.matched_alias == "rusty dragon"

    def test_same_location_exact_alias_length_tie(self, tmp_path):
        idx = _make_index(tmp_path, {
            "loc": _make_base_md("Loc", "foo, bar")  # same length — either is fine
        })
        m = idx.detect("there is foo and bar")
        assert m is not None
        assert m.canonical_name == "Loc"


# ── format_context ────────────────────────────────────────────────────────────

class TestFormatContext:
    def test_header_format(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        m = idx.detect("go to garrison")
        block = idx.format_context(m)
        assert block.startswith("## Location Reference — Sandpoint Garrison")

    def test_body_included(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Garrison", "garrison", "## Description\n\nA stone fort.")})
        m = idx.detect("garrison")
        block = idx.format_context(m)
        assert "A stone fort." in block


# ── lookup ────────────────────────────────────────────────────────────────────

class TestLookup:
    def test_lookup_by_canonical_name(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        m = idx.lookup("Sandpoint Garrison")
        assert m is not None
        assert m.canonical_name == "Sandpoint Garrison"

    def test_lookup_case_insensitive(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        assert idx.lookup("sandpoint garrison") is not None
        assert idx.lookup("SANDPOINT GARRISON") is not None

    def test_lookup_missing_returns_none(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Garrison", "garrison")})
        assert idx.lookup("Cathedral") is None


# ── AC-006: context_info loc / loc_trigger ────────────────────────────────────

class TestInjectContextLocFields:
    """Integration tests for _inject_context location detection path."""

    def _make_session(self, **kwargs):
        from api.session_manager import GameSession
        defaults = dict(
            id="s1", session_number=1, model="m", host="h",
            temperature=0.3, provider="ollama",
            messages=[{"role": "user", "content": "test"}],
            system_prompt="SYS",
        )
        defaults.update(kwargs)
        return GameSession(**defaults)

    def _call_inject(self, session, loc_idx):
        """Call _inject_context with real NPC/skill indexes but a given location index."""
        from api.context.npc_lookup import NpcIndex
        from api.context.skill_lookup import SkillIndex

        npc_mock = MagicMock(spec=NpcIndex)
        npc_mock.detect.return_value = None
        npc_mock.detect_by_location.return_value = []

        skill_mock = MagicMock(spec=SkillIndex)
        skill_mock.detect.return_value = None

        with patch("api.session_manager._get_npc_index", return_value=npc_mock), \
             patch("api.session_manager._get_skill_index", return_value=skill_mock), \
             patch("api.session_manager._get_location_index", return_value=loc_idx):
            from api.session_manager import _inject_context
            return _inject_context(session)

    def test_loc_and_trigger_set_on_match(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        session = self._make_session(messages=[{"role": "user", "content": "we go to the garrison"}])
        _, info = self._call_inject(session, idx)
        assert info["loc"] == "Sandpoint Garrison"
        assert info["loc_trigger"] == "garrison"

    def test_loc_null_when_no_match(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        session = self._make_session(messages=[{"role": "user", "content": "we look around"}])
        _, info = self._call_inject(session, idx)
        assert info["loc"] is None
        assert info["loc_trigger"] is None

    def test_profile_injected_into_system_content(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison", "## Description\n\nStone walls.")})
        session = self._make_session(messages=[{"role": "user", "content": "go to garrison"}])
        system_content, _ = self._call_inject(session, idx)
        assert "Location Reference — Sandpoint Garrison" in system_content
        assert "Stone walls." in system_content


# ── AC-007: scene_locations persistence ──────────────────────────────────────

class TestSceneLocationsPersistence:
    def _make_session(self, **kwargs):
        from api.session_manager import GameSession
        defaults = dict(
            id="s1", session_number=1, model="m", host="h",
            temperature=0.3, provider="ollama",
            messages=[{"role": "user", "content": "test"}],
            system_prompt="SYS",
        )
        defaults.update(kwargs)
        return GameSession(**defaults)

    def _call_inject(self, session, loc_idx):
        from api.context.npc_lookup import NpcIndex
        from api.context.skill_lookup import SkillIndex

        npc_mock = MagicMock(spec=NpcIndex)
        npc_mock.detect.return_value = None
        npc_mock.detect_by_location.return_value = []

        skill_mock = MagicMock(spec=SkillIndex)
        skill_mock.detect.return_value = None

        with patch("api.session_manager._get_npc_index", return_value=npc_mock), \
             patch("api.session_manager._get_skill_index", return_value=skill_mock), \
             patch("api.session_manager._get_location_index", return_value=loc_idx):
            from api.session_manager import _inject_context
            return _inject_context(session)

    def test_location_accumulated_to_scene_locations(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        session = self._make_session(messages=[{"role": "user", "content": "go to garrison"}])
        self._call_inject(session, idx)
        assert "Sandpoint Garrison" in session.scene_locations

    def test_no_duplicate_in_scene_locations(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        session = self._make_session(messages=[{"role": "user", "content": "go to garrison"}])
        self._call_inject(session, idx)
        self._call_inject(session, idx)
        assert session.scene_locations.count("Sandpoint Garrison") == 1

    def test_location_reinjected_on_subsequent_turn_no_match(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison", "## Description\n\nStone walls.")})
        session = self._make_session(messages=[{"role": "user", "content": "go to garrison"}])
        # Turn 1 — location detected
        self._call_inject(session, idx)
        # Turn 2 — no location keyword
        session.messages = [{"role": "user", "content": "we look around"}]
        system_content, info = self._call_inject(session, idx)
        assert "Stone walls." in system_content
        assert info["loc"] == "Sandpoint Garrison"
        assert info["loc_trigger"] is None  # no fresh trigger on re-injection

    def test_scene_locations_not_populated_when_no_match(self, tmp_path):
        idx = _make_index(tmp_path, {"garrison": _make_base_md("Sandpoint Garrison", "garrison")})
        session = self._make_session(messages=[{"role": "user", "content": "we look around"}])
        self._call_inject(session, idx)
        assert session.scene_locations == []


# ── AC-008 / AC-009: generate_location_base_md ───────────────────────────────

class TestGenerateLocationBaseMd:
    def test_starts_with_name(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("Bottled Solutions", role="apothecary shop")
        assert out.startswith("# Bottled Solutions")

    def test_aliases_present(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("Bottled Solutions")
        assert "**Aliases:**" in out
        assert "bottled solutions" in out.lower()

    def test_description_uses_appearance(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("Bottled Solutions", appearance="cluttered shelves")
        assert "cluttered shelves" in out

    def test_summary_in_typical_occupants(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("Bottled Solutions", summary="run by Gerhard Pickle")
        assert "run by Gerhard Pickle" in out

    def test_role_appears(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("X", role="apothecary shop")
        assert "apothecary shop" in out

    def test_reference_section_present(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("X")
        assert "<!-- REFERENCE -->" in out

    def test_flags_session_number(self):
        from api.npc_generator import generate_location_base_md
        out = generate_location_base_md("X", session_number=3)
        assert "session_003" in out


# ── AC-008 / AC-009: _process_generate_block location path ───────────────────

class TestProcessGenerateBlockLocation:
    def _make_session(self, tmp_path):
        from api.session_manager import GameSession
        return GameSession(
            id="s1", session_number=2, model="m", host="h",
            temperature=0.3, provider="ollama",
            messages=[{"role": "user", "content": "test"}],
            system_prompt="SYS",
        )

    def test_creates_location_stub(self, tmp_path, monkeypatch):
        monkeypatch.setattr("api.session_manager._REPO_ROOT", tmp_path)
        (tmp_path / "adventure_path" / "03_locations").mkdir(parents=True)

        from api.session_manager import _process_generate_block
        session = self._make_session(tmp_path)

        body = "type: location\nname: Bottled Solutions\nrole: apothecary\nappearance: cluttered shop\nlocation: main street\nsummary: run by Gerhard"
        _process_generate_block(body, session)

        stub = tmp_path / "adventure_path" / "03_locations" / "bottled_solutions" / "base.md"
        assert stub.exists()
        content = stub.read_text(encoding="utf-8")
        assert content.startswith("# Bottled Solutions")

    def test_skips_if_directory_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("api.session_manager._REPO_ROOT", tmp_path)
        loc_dir = tmp_path / "adventure_path" / "03_locations" / "bottled_solutions"
        loc_dir.mkdir(parents=True)
        existing = loc_dir / "base.md"
        existing.write_text("# Old Content", encoding="utf-8")

        from api.session_manager import _process_generate_block
        session = self._make_session(tmp_path)

        body = "type: location\nname: Bottled Solutions"
        _process_generate_block(body, session)

        assert existing.read_text(encoding="utf-8") == "# Old Content"

    def test_invalidates_location_index_after_creation(self, tmp_path, monkeypatch):
        monkeypatch.setattr("api.session_manager._REPO_ROOT", tmp_path)
        (tmp_path / "adventure_path" / "03_locations").mkdir(parents=True)

        import api.session_manager as sm
        sm._location_index = MagicMock()  # set a dummy to confirm it gets cleared

        from api.session_manager import _process_generate_block
        session = self._make_session(tmp_path)

        body = "type: location\nname: New Place\nrole: shop"
        _process_generate_block(body, session)

        assert sm._location_index is None  # invalidated

    def test_npc_block_still_creates_npc(self, tmp_path, monkeypatch):
        monkeypatch.setattr("api.session_manager._REPO_ROOT", tmp_path)
        (tmp_path / "adventure_path" / "01_npcs").mkdir(parents=True)
        (tmp_path / "adventure_path" / "npc_library").mkdir(parents=True)

        import api.session_manager as sm
        npc_mock = MagicMock()
        npc_mock.npc_dir_for.return_value = None
        with patch("api.session_manager._get_npc_index", return_value=npc_mock):
            from api.session_manager import _process_generate_block
            session = self._make_session(tmp_path)

            body = "name: Gerhard Pickle\nrole: apothecary\nappearance: short and round"
            _process_generate_block(body, session)

        npc_dir = tmp_path / "adventure_path" / "01_npcs" / ".gerhard_pickle"
        assert npc_dir.exists()
