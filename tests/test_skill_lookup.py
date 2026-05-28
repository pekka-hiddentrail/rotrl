"""Tests for api/context/skill_lookup.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from api.context.skill_lookup import SkillIndex, _parse_skill_file


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_skill(base: Path, filename: str, name: str,
                triggers: list[str], body: str, ref: str = "") -> Path:
    skills_dir = base / "adventure_path" / "06_rules" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    content = f"# {name}\n**Triggers:** {', '.join(triggers)}\n{body}"
    if ref:
        content += f"\n<!-- REFERENCE -->\n{ref}"
    p = skills_dir / filename
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def skill_root(tmp_path):
    _make_skill(tmp_path, "diplomacy.md", "Diplomacy",
                ["persuade", "convince", "talk to", "diplomacy"],
                "DC 15 for basic cooperation.")
    _make_skill(tmp_path, "bluff.md", "Bluff",
                ["lie", "deceive", "bluff"],
                "Opposed by Sense Motive.")
    _make_skill(tmp_path, "perception.md", "Perception",
                ["notice", "spot", "search", "look around"],
                "DC varies by concealment.",
                ref="Reader docs — never injected.")
    return tmp_path


# ── detect() ─────────────────────────────────────────────────────────────────

def test_detect_basic_trigger(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.detect("Yanyeeku tries to persuade the guard.")
    assert m is not None
    assert m.skill_name == "Diplomacy"
    assert m.matched_trigger == "persuade"


def test_detect_multi_word_trigger(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.detect("Ani wants to talk to the mayor.")
    assert m is not None
    assert m.skill_name == "Diplomacy"
    assert m.matched_trigger == "talk to"


def test_detect_longest_trigger_wins(skill_root):
    # "look around" (10) beats "spot" (4) — both in Perception
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.detect("Revemox tries to spot and look around the square.")
    assert m is not None
    assert m.matched_trigger == "look around"


def test_detect_case_insensitive(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    assert idx.detect("Yanyeeku tries to PERSUADE the merchant.") is not None
    assert idx.detect("She tries to Convince him.") is not None


def test_detect_no_match_returns_none(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    assert idx.detect("The party walks toward the cathedral.") is None


def test_detect_word_boundary(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    # "lie" should not match inside "believe" or "relief"
    assert idx.detect("He believed the story.") is None
    assert idx.detect("She told a lie about the map.") is not None


def test_detect_returns_rules_text(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.detect("Yanyeeku tries to persuade the guard.")
    assert "DC 15" in m.rules_text


# ── lookup() ─────────────────────────────────────────────────────────────────

def test_lookup_by_exact_name(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.lookup("Diplomacy")
    assert m is not None
    assert m.skill_name == "Diplomacy"


def test_lookup_case_insensitive(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    assert idx.lookup("diplomacy") is not None
    assert idx.lookup("BLUFF") is not None


def test_lookup_unknown_returns_none(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    assert idx.lookup("Intimidate") is None


# ── known_skills ──────────────────────────────────────────────────────────────

def test_known_skills_lists_all(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    skills = idx.known_skills
    assert "Diplomacy" in skills
    assert "Bluff" in skills
    assert "Perception" in skills


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_skills_dir(tmp_path):
    (tmp_path / "adventure_path" / "06_rules" / "skills").mkdir(parents=True)
    idx = SkillIndex(_repo_root=tmp_path)
    assert idx.detect("persuade") is None
    assert idx.known_skills == []


def test_missing_skills_dir(tmp_path):
    idx = SkillIndex(_repo_root=tmp_path)
    assert idx.detect("persuade") is None


def test_underscore_files_skipped(tmp_path):
    skills_dir = tmp_path / "adventure_path" / "06_rules" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "_README.md").write_text("# README\n**Triggers:** readme\nbody", encoding="utf-8")
    idx = SkillIndex(_repo_root=tmp_path)
    assert idx.detect("readme") is None


def test_reference_separator_stops_injection(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.lookup("Perception")
    assert "Reader docs" not in m.rules_text
    assert "DC varies" in m.rules_text


def test_format_context_structure(skill_root):
    idx = SkillIndex(_repo_root=skill_root)
    m = idx.lookup("Diplomacy")
    ctx = idx.format_context(m)
    assert ctx.startswith("## Skill Reference — Diplomacy")
    assert "DC 15" in ctx


# ── _parse_skill_file ─────────────────────────────────────────────────────────

def test_parse_skill_file_basic(tmp_path):
    p = tmp_path / "test.md"
    p.write_text("# Sense Motive\n**Triggers:** sense, read intent\nBody line.", encoding="utf-8")
    name, triggers, body = _parse_skill_file(p)
    assert name == "Sense Motive"
    assert "sense" in triggers
    assert "read intent" in triggers
    assert "Body line." in body


def test_parse_skill_file_missing_file(tmp_path):
    name, triggers, body = _parse_skill_file(tmp_path / "nonexistent.md")
    assert name == ""
    assert triggers == []
    assert body == ""


def test_parse_skill_file_no_name(tmp_path):
    p = tmp_path / "noname.md"
    p.write_text("**Triggers:** foo\nBody.", encoding="utf-8")
    name, _, _ = _parse_skill_file(p)
    assert name == ""


def test_parse_skill_file_no_triggers(tmp_path):
    p = tmp_path / "notriggers.md"
    p.write_text("# Skill\nBody only.", encoding="utf-8")
    name, triggers, body = _parse_skill_file(p)
    assert name == "Skill"
    assert triggers == []
    assert "Body only." in body


def test_parse_skill_file_reference_separator(tmp_path):
    p = tmp_path / "split.md"
    p.write_text("# Test\n**Triggers:** foo\nGM content.\n<!-- REFERENCE -->\nReader content.", encoding="utf-8")
    _, _, body = _parse_skill_file(p)
    assert "GM content." in body
    assert "Reader content." not in body
