"""Tests for CombatRulesIndex — combat rule detection and context formatting."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from api.context.combat_lookup import (
    CombatRulesIndex,
    CombatRuleMatch,
    _parse_combat_rule_file,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_rule_file(tmp_path: Path, filename: str, content: str) -> Path:
    f = tmp_path / filename
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


def _make_index(tmp_path: Path) -> CombatRulesIndex:
    """Build a CombatRulesIndex whose combat dir is tmp_path."""
    # CombatRulesIndex expects _repo_root / "adventure_path" / "04_rules" / "combat"
    combat_dir = tmp_path / "adventure_path" / "04_rules" / "combat"
    combat_dir.mkdir(parents=True)
    return CombatRulesIndex(_repo_root=tmp_path), combat_dir


# ── _parse_combat_rule_file ───────────────────────────────────────────────────

class TestParseCombatRuleFile:
    def test_extracts_name_triggers_body(self, tmp_path):
        f = _make_rule_file(tmp_path, "attack_rolls.md", """\
            # Attack Rolls
            **Triggers:** attack, hit, miss, swing

            Roll d20 + BAB vs AC.
        """)
        name, triggers, body = _parse_combat_rule_file(f)
        assert name == "Attack Rolls"
        assert "attack" in triggers
        assert "hit" in triggers
        assert "Roll d20 + BAB vs AC." in body

    def test_stops_at_reference_separator(self, tmp_path):
        f = _make_rule_file(tmp_path, "hp.md", """\
            # Hit Points
            **Triggers:** hp, damage

            GM-facing rules here.

            <!-- REFERENCE -->

            Reader-only section — never injected.
        """)
        _, _, body = _parse_combat_rule_file(f)
        assert "GM-facing rules here." in body
        assert "Reader-only section" not in body

    def test_missing_file_returns_empty(self, tmp_path):
        name, triggers, body = _parse_combat_rule_file(tmp_path / "nonexistent.md")
        assert name == ""
        assert triggers == []
        assert body == ""

    def test_file_without_heading_returns_empty_name(self, tmp_path):
        f = _make_rule_file(tmp_path, "nohead.md", """\
            **Triggers:** attack
            Some content.
        """)
        name, _, _ = _parse_combat_rule_file(f)
        assert name == ""

    def test_triggers_stripped_and_split(self, tmp_path):
        f = _make_rule_file(tmp_path, "r.md", """\
            # Rule
            **Triggers:**  first trigger ,  second trigger , third
            Body.
        """)
        _, triggers, _ = _parse_combat_rule_file(f)
        assert triggers == ["first trigger", "second trigger", "third"]


# ── CombatRulesIndex ──────────────────────────────────────────────────────────

class TestCombatRulesIndexLoad:
    def test_empty_combat_dir_loads_cleanly(self, tmp_path):
        idx, _ = _make_index(tmp_path)
        assert idx.known_rules == []

    def test_missing_combat_dir_loads_cleanly(self, tmp_path):
        idx = CombatRulesIndex(_repo_root=tmp_path)
        assert idx.known_rules == []

    def test_skips_underscore_prefixed_files(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "_index.md", """\
            # Index
            **Triggers:** index
            Content.
        """)
        idx._ensure_loaded()
        assert "Index" not in idx.known_rules

    def test_loads_rule_files(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "attack_rolls.md", """\
            # Attack Rolls
            **Triggers:** attack, hit
            Roll d20.
        """)
        assert "Attack Rolls" in idx.known_rules

    def test_loads_multiple_rule_files(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "attack_rolls.md", """\
            # Attack Rolls
            **Triggers:** attack
            Body.
        """)
        _make_rule_file(combat_dir, "initiative.md", """\
            # Initiative
            **Triggers:** initiative, who goes first
            Body.
        """)
        assert set(idx.known_rules) == {"Attack Rolls", "Initiative"}


class TestCombatRulesIndexDetect:
    def _idx_with_rules(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "attack_rolls.md", """\
            # Attack Rolls
            **Triggers:** attack, swing, hit, miss
            Roll d20 + BAB.
        """)
        _make_rule_file(combat_dir, "initiative.md", """\
            # Initiative
            **Triggers:** initiative, who goes first, turn order
            Roll d20 + DEX.
        """)
        return idx

    def test_detect_single_word_trigger(self, tmp_path):
        idx = self._idx_with_rules(tmp_path)
        match = idx.detect("I attack the goblin!")
        assert match is not None
        assert match.rule_name == "Attack Rolls"
        assert match.matched_trigger == "attack"

    def test_detect_multi_word_trigger(self, tmp_path):
        idx = self._idx_with_rules(tmp_path)
        match = idx.detect("Who goes first in the fight?")
        assert match is not None
        assert match.rule_name == "Initiative"
        assert match.matched_trigger == "who goes first"

    def test_longest_trigger_wins(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "aoo.md", """\
            # Attacks of Opportunity
            **Triggers:** attack of opportunity, attack
            AoO rules.
        """)
        match = idx.detect("Does moving provoke an attack of opportunity?")
        assert match is not None
        assert match.matched_trigger == "attack of opportunity"

    def test_detect_case_insensitive(self, tmp_path):
        idx = self._idx_with_rules(tmp_path)
        match = idx.detect("INITIATIVE: who rolls first?")
        assert match is not None
        assert match.rule_name == "Initiative"

    def test_detect_no_match_returns_none(self, tmp_path):
        idx = self._idx_with_rules(tmp_path)
        assert idx.detect("I walk into the tavern.") is None

    def test_detect_word_boundary(self, tmp_path):
        idx = self._idx_with_rules(tmp_path)
        # "attacks" should NOT match the trigger "attack" as a whole word... actually
        # "attacks" contains "attack" but not as a word boundary.
        # rg \battack\b won't match "attacks"
        match = idx.detect("She attacks twice.")
        # "attacks" → \battack\b fails; expect no match from "attack" trigger
        # but "swing" etc. not present either → None
        assert match is None

    def test_matched_trigger_recorded(self, tmp_path):
        idx = self._idx_with_rules(tmp_path)
        match = idx.detect("What is the turn order?")
        assert match is not None
        assert match.matched_trigger == "turn order"


class TestCombatRulesIndexLookup:
    def test_lookup_by_exact_name(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "initiative.md", """\
            # Initiative
            **Triggers:** initiative
            Roll d20.
        """)
        result = idx.lookup("Initiative")
        assert result is not None
        assert result.rule_name == "Initiative"

    def test_lookup_case_insensitive(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "initiative.md", """\
            # Initiative
            **Triggers:** initiative
            Roll d20.
        """)
        assert idx.lookup("initiative") is not None
        assert idx.lookup("INITIATIVE") is not None

    def test_lookup_missing_returns_none(self, tmp_path):
        idx, _ = _make_index(tmp_path)
        assert idx.lookup("Nonexistent Rule") is None


class TestFormatContext:
    def test_format_context_structure(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "attack_rolls.md", """\
            # Attack Rolls
            **Triggers:** attack
            Roll d20 + BAB vs AC.
        """)
        match = idx.detect("I attack")
        assert match is not None
        ctx = idx.format_context(match)
        assert ctx.startswith("## Combat Reference — Attack Rolls")
        assert "Roll d20 + BAB vs AC." in ctx

    def test_format_context_excludes_reference_section(self, tmp_path):
        idx, combat_dir = _make_index(tmp_path)
        _make_rule_file(combat_dir, "hp.md", """\
            # Hit Points
            **Triggers:** hp, damage
            GM rules.
            <!-- REFERENCE -->
            Reader-only.
        """)
        match = idx.detect("take damage")
        assert match is not None
        ctx = idx.format_context(match)
        assert "Reader-only" not in ctx
