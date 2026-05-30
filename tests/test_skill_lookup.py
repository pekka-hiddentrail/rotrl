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
    m = idx.detect("Vanx tries to spot and look around the square.")
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


# ── New skill coverage (Knowledge family + Stealth) ───────────────────────────

@pytest.fixture()
def extended_skill_root(tmp_path):
    """Fixture with all new Knowledge skills, Stealth, and Act I utility skills."""
    _make_skill(tmp_path, "diplomacy.md", "Diplomacy",
                ["persuade", "convince", "talk to", "diplomacy"],
                "DC 15 for basic cooperation.")
    _make_skill(tmp_path, "knowledge_local.md", "Knowledge (Local)",
                ["knowledge local", "know local", "who is", "heard of", "local knowledge"],
                "DC 10 common knowledge; DC 15 town history; DC 20 hidden organisations.")
    _make_skill(tmp_path, "knowledge_religion.md", "Knowledge (Religion)",
                ["knowledge religion", "holy symbol", "identify undead", "who is this god"],
                "Recognize common deity symbol DC 10; common mythology DC 15.")
    _make_skill(tmp_path, "knowledge_arcana.md", "Knowledge (Arcana)",
                ["knowledge arcana", "identify spell", "identify magic", "magical beast"],
                "Identify auras DC 15 + spell level; materials manufactured by magic DC 20.")
    _make_skill(tmp_path, "knowledge_history.md", "Knowledge (History)",
                ["knowledge history", "ancient history", "thassilon", "what happened here"],
                "Significant event DC 10; approximate date DC 15; obscure history DC 20.")
    _make_skill(tmp_path, "knowledge_planes.md", "Knowledge (Planes)",
                ["knowledge planes", "outsider", "identify outsider", "what plane"],
                "Names of planes DC 10; recognize plane DC 15; planar origin DC 20.")
    _make_skill(tmp_path, "knowledge_nature.md", "Knowledge (Nature)",
                ["knowledge nature", "identify animal", "identify plant", "natural hazard"],
                "Common plant/animal DC 10; natural hazard DC 15 + CR.")
    _make_skill(tmp_path, "knowledge_nobility.md", "Knowledge (Nobility)",
                ["knowledge nobility", "noble", "heraldry", "line of succession"],
                "Current rulers DC 10; proper etiquette DC 15; line of succession DC 20.")
    _make_skill(tmp_path, "stealth.md", "Stealth",
                ["stealth", "sneak", "hide", "hiding", "move silently"],
                "Opposed by Perception. Half speed: no penalty; > half speed: -5.")
    _make_skill(tmp_path, "heal.md", "Heal",
                ["heal", "stabilize", "first aid", "treat wounds", "treat poison", "treat disease",
                 "long-term care", "bandage", "revive"],
                "First Aid DC 15; Treat Deadly Wounds DC 20 (1 HP/level).")
    _make_skill(tmp_path, "survival.md", "Survival",
                ["survival", "track", "tracking", "follow tracks", "navigate",
                 "get along in the wild", "predict weather", "find food"],
                "Get along in the wild DC 10; tracking DC by surface type.")
    _make_skill(tmp_path, "acrobatics.md", "Acrobatics",
                ["acrobatics", "balance", "tumble", "tumbling", "jump", "leap", "fall",
                 "move through", "dodge past"],
                "Balance DC by surface width; tumble DC = opponent CMD.")
    _make_skill(tmp_path, "disable_device.md", "Disable Device",
                ["disable device", "disable trap", "disarm trap", "pick lock", "open lock",
                 "disarm", "defuse", "sabotage"],
                "Simple device DC 10; tricky DC 15; difficult DC 20; extreme DC 25.")
    return tmp_path


class TestNewSkillCoverage:
    """Verify each newly added skill and Stealth detects on its primary trigger."""

    def test_knowledge_local_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("Who is Sheriff Hemlock?")
        assert m is not None
        assert m.skill_name == "Knowledge (Local)"

    def test_knowledge_religion_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("Can I identify undead creatures in the crypt?")
        assert m is not None
        assert m.skill_name == "Knowledge (Religion)"

    def test_knowledge_arcana_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I try to identify magic on this amulet.")
        assert m is not None
        assert m.skill_name == "Knowledge (Arcana)"

    def test_knowledge_history_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I know about Thassilon and the ancient empire.")
        assert m is not None
        assert m.skill_name == "Knowledge (History)"

    def test_knowledge_planes_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("Is this creature an outsider?")
        assert m is not None
        assert m.skill_name == "Knowledge (Planes)"

    def test_knowledge_nature_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I try to identify animal tracks near the camp.")
        assert m is not None
        assert m.skill_name == "Knowledge (Nature)"

    def test_knowledge_nobility_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("Does anyone know about the heraldry on that shield?")
        assert m is not None
        assert m.skill_name == "Knowledge (Nobility)"

    def test_stealth_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I try to sneak past the guard.")
        assert m is not None
        assert m.skill_name == "Stealth"

    def test_heal_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("Can I stabilize the dying guard before he bleeds out?")
        assert m is not None
        assert m.skill_name == "Heal"

    def test_survival_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I try to track the goblins through the Nettlewood.")
        assert m is not None
        assert m.skill_name == "Survival"

    def test_acrobatics_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I try to tumble past the goblin without getting hit.")
        assert m is not None
        assert m.skill_name == "Acrobatics"

    def test_disable_device_detects(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("I use disable device to open the chest.")
        assert m is not None
        assert m.skill_name == "Disable Device"

    def test_knowledge_local_vs_religion_no_collision(self, extended_skill_root):
        """Longer trigger wins: 'knowledge local' and 'knowledge religion' must
        each fire only their own skill, not each other's."""
        idx = SkillIndex(_repo_root=extended_skill_root)
        m = idx.detect("knowledge local laws and customs")
        assert m is not None
        assert m.skill_name == "Knowledge (Local)"

        m2 = idx.detect("knowledge religion and its holy symbols")
        assert m2 is not None
        assert m2.skill_name == "Knowledge (Religion)"

    def test_known_skills_includes_all_new(self, extended_skill_root):
        idx = SkillIndex(_repo_root=extended_skill_root)
        skills = set(idx.known_skills)
        new_skills = {
            "Knowledge (Local)", "Knowledge (Religion)", "Knowledge (Arcana)",
            "Knowledge (History)", "Knowledge (Planes)", "Knowledge (Nature)",
            "Knowledge (Nobility)", "Stealth",
            "Heal", "Survival", "Acrobatics", "Disable Device",
        }
        assert new_skills.issubset(skills)


# ── Integration: real skill files ─────────────────────────────────────────────

def test_real_skill_files_all_loaded():
    """Sanity-check that SkillIndex loads all 17 expected skill files from the repo."""
    repo_root = Path(__file__).resolve().parents[1]
    idx = SkillIndex(_repo_root=repo_root)
    skills = set(idx.known_skills)
    expected = {
        "Bluff", "Diplomacy", "Intimidate", "Perception", "Sense Motive",
        "Knowledge (Local)", "Knowledge (Religion)", "Knowledge (History)",
        "Knowledge (Planes)", "Knowledge (Arcana)", "Knowledge (Nature)",
        "Knowledge (Nobility)", "Stealth",
        "Heal", "Survival", "Acrobatics", "Disable Device",
    }
    assert expected.issubset(skills), f"Missing: {expected - skills}"
