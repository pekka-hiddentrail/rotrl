"""Extended tests for api/context/npc_lookup.py — detect_all, npc_dir_for, lookup, edge cases."""
from __future__ import annotations

from pathlib import Path

import pytest

from api.context.npc_lookup import NpcIndex, _parse_base


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_npc(base: Path, slug: str, name: str, aliases: list[str],
              locations: list[str] = None, body: str = "Profile text.",
              ref: str = "") -> Path:
    npc_dir = base / "adventure_path" / "01_npcs" / slug
    npc_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {name}", f"**Aliases:** {', '.join(aliases)}"]
    if locations:
        lines.append(f"**Locations:** {', '.join(locations)}")
    lines.append(body)
    if ref:
        lines.append("<!-- REFERENCE -->")
        lines.append(ref)
    (npc_dir / "base.md").write_text("\n".join(lines), encoding="utf-8")
    return npc_dir


@pytest.fixture()
def npc_root(tmp_path):
    _make_npc(tmp_path, "kendra_deverin", "Kendra Deverin",
              ["kendra", "deverin", "mayor"],
              locations=["town hall", "festival square"],
              body="Mayor of Sandpoint.")
    _make_npc(tmp_path, "belor_hemlock", "Belor Hemlock",
              ["belor", "hemlock", "sheriff"],
              locations=["barracks"],
              body="Sheriff of Sandpoint.")
    _make_npc(tmp_path, "abstalar_zantus", "Abstalar Zantus",
              ["zantus", "father zantus", "abstalar"],
              locations=["cathedral"],
              body="Head priest of Sandpoint.")
    return tmp_path


# ── detect_all() ──────────────────────────────────────────────────────────────

def test_detect_all_finds_multiple(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    results = idx.detect_all("Kendra and Belor are both at the festival.")
    names = {r.canonical_name for r in results}
    assert "Kendra Deverin" in names
    assert "Belor Hemlock" in names


def test_detect_all_returns_empty_when_none(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    assert idx.detect_all("The party wanders through the market.") == []


def test_detect_all_no_duplicates_per_npc(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    # "kendra" and "deverin" both map to Kendra Deverin — should appear once
    results = idx.detect_all("Kendra Deverin greeted them warmly.")
    kendra = [r for r in results if r.canonical_name == "Kendra Deverin"]
    assert len(kendra) == 1


def test_detect_all_uses_longest_alias(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    results = idx.detect_all("Father Zantus spoke at the cathedral.")
    zantus = next(r for r in results if r.canonical_name == "Abstalar Zantus")
    assert zantus.matched_alias == "father zantus"


def test_detect_all_three_npcs(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    results = idx.detect_all("Mayor Kendra, Sheriff Hemlock, and Father Zantus met.")
    names = {r.canonical_name for r in results}
    assert len(names) == 3


# ── npc_dir_for() ─────────────────────────────────────────────────────────────

def test_npc_dir_for_known(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    d = idx.npc_dir_for("Kendra Deverin")
    assert d is not None
    assert d.name == "kendra_deverin"


def test_npc_dir_for_case_insensitive(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    assert idx.npc_dir_for("kendra deverin") is not None
    assert idx.npc_dir_for("KENDRA DEVERIN") is not None


def test_npc_dir_for_unknown_returns_none(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    assert idx.npc_dir_for("Gorvoth") is None


# ── lookup() ──────────────────────────────────────────────────────────────────

def test_lookup_by_canonical_name(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Belor Hemlock")
    assert m is not None
    assert m.canonical_name == "Belor Hemlock"
    assert "Sheriff" in m.profile_text


def test_lookup_case_insensitive(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    assert idx.lookup("belor hemlock") is not None
    assert idx.lookup("BELOR HEMLOCK") is not None


def test_lookup_unknown_returns_none(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    assert idx.lookup("Nobody Important") is None


# ── Status and knowledge fresh reads ─────────────────────────────────────────

def test_fresh_status_returns_only_last_turn_block(npc_root):
    npc_dir = npc_root / "adventure_path" / "01_npcs" / "kendra_deverin"
    (npc_dir / "session_001.md").write_text(
        "## Turn 1 — 10:00:00\n**Disposition:** neutral → friendly\n\n"
        "## Turn 2 — 10:05:00\n**Disposition:** friendly\n",
        encoding="utf-8",
    )
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Kendra Deverin")
    assert "Turn 2" in m.status
    assert "Turn 1" not in m.status


def test_fresh_status_empty_when_no_session_files(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Belor Hemlock")
    assert m.status == ""


def test_fresh_knowledge_included(npc_root):
    npc_dir = npc_root / "adventure_path" / "01_npcs" / "kendra_deverin"
    (npc_dir / "knowledge.md").write_text(
        "- [pcs] Yanyeeku asked about fireworks.\n", encoding="utf-8"
    )
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Kendra Deverin")
    assert "fireworks" in m.knowledge_text


def test_fresh_knowledge_empty_when_no_file(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Abstalar Zantus")
    assert m.knowledge_text == ""


# ── Reference separator ───────────────────────────────────────────────────────

def test_reference_separator_stops_profile_injection(tmp_path):
    _make_npc(tmp_path, "gorm", "Gorm Hysys", ["gorm"],
              body="Merchant profile.",
              ref="Tier: IV — should never appear in profile_text")
    idx = NpcIndex(_repo_root=tmp_path)
    m = idx.lookup("Gorm Hysys")
    assert "Tier" not in m.profile_text
    assert "Merchant profile." in m.profile_text


# ── format_context ────────────────────────────────────────────────────────────

def test_format_context_minimal(npc_root):
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Belor Hemlock")
    ctx = idx.format_context(m)
    assert "## NPC Reference — Belor Hemlock" in ctx
    assert "Sheriff" in ctx


def test_format_context_includes_status_when_present(npc_root):
    npc_dir = npc_root / "adventure_path" / "01_npcs" / "kendra_deverin"
    (npc_dir / "session_001.md").write_text(
        "## Turn 1 — 10:00:00\n**Disposition:** friendly\n", encoding="utf-8"
    )
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Kendra Deverin")
    ctx = idx.format_context(m)
    assert "### Current Status" in ctx
    assert "friendly" in ctx


def test_format_context_includes_knowledge_when_present(npc_root):
    npc_dir = npc_root / "adventure_path" / "01_npcs" / "kendra_deverin"
    (npc_dir / "knowledge.md").write_text("- [pcs] Knows Yanyeeku.\n", encoding="utf-8")
    idx = NpcIndex(_repo_root=npc_root)
    m = idx.lookup("Kendra Deverin")
    ctx = idx.format_context(m)
    assert "### What Kendra Deverin Knows" in ctx
    assert "Yanyeeku" in ctx


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_npc_with_no_base_md_skipped(tmp_path):
    npc_dir = tmp_path / "adventure_path" / "01_npcs" / "ghost"
    npc_dir.mkdir(parents=True, exist_ok=True)
    idx = NpcIndex(_repo_root=tmp_path)
    assert idx.known_npcs == []


def test_underscore_dirs_skipped(tmp_path):
    _make_npc(tmp_path, "_NPC_TEMPLATE", "Template NPC", ["template"])
    idx = NpcIndex(_repo_root=tmp_path)
    assert idx.detect("template") is None


def test_missing_npcs_dir(tmp_path):
    idx = NpcIndex(_repo_root=tmp_path)
    assert idx.known_npcs == []
    assert idx.detect("anyone") is None


# ── _parse_base unit tests ────────────────────────────────────────────────────

def test_parse_base_extracts_all_fields(tmp_path):
    p = tmp_path / "base.md"
    p.write_text(
        "# Ameiko Kaijitsu\n**Aliases:** ameiko, kaijitsu\n"
        "**Locations:** rusty dragon, inn\nProfile text.\n",
        encoding="utf-8",
    )
    name, aliases, locations, profile = _parse_base(p)
    assert name == "Ameiko Kaijitsu"
    assert "ameiko" in aliases
    assert "rusty dragon" in locations
    assert "inn" in locations
    assert "Profile text." in profile


def test_parse_base_missing_file(tmp_path):
    name, aliases, locations, profile = _parse_base(tmp_path / "nonexistent.md")
    assert name == ""
    assert aliases == []
    assert locations == []
    assert profile == ""


def test_parse_base_no_aliases_or_locations(tmp_path):
    p = tmp_path / "base.md"
    p.write_text("# Simple NPC\nJust a profile.\n", encoding="utf-8")
    name, aliases, locations, profile = _parse_base(p)
    assert name == "Simple NPC"
    assert aliases == []
    assert locations == []
    assert "Just a profile." in profile


def test_parse_base_reference_separator(tmp_path):
    p = tmp_path / "base.md"
    p.write_text(
        "# Test NPC\n**Aliases:** test\nGM content.\n<!-- REFERENCE -->\nReader content.\n",
        encoding="utf-8",
    )
    name, _, _, profile = _parse_base(p)
    assert "GM content." in profile
    assert "Reader content." not in profile
