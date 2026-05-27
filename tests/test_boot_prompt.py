"""
Tests for boot prompt assembly and session-start context resolution.

Covers:
  - _build_slim_system_prompt structure and required sections
  - Situation block: boot.md > previous recap.md > fallback notice
  - Party block extracted from character_sheet.md files
  - Deferred context queue: correct files loaded, correct turn numbers
  - validate_turn_input
  - validate_generated_text
"""
from __future__ import annotations

from pathlib import Path

import pytest

from api.session_manager import (
    _build_slim_system_prompt,
    validate_turn_input,
    validate_generated_text,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session_dir(base: Path, n: int) -> Path:
    d = base / "sessions" / f"session_{n:03d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_player(base: Path, slot: int, name: str, cls: str) -> None:
    d = base / "players" / f"player_{slot:02d}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "character_sheet.md").write_text(
        f"**Name:** {name}\n**Class / Archetype:** {cls}\n",
        encoding="utf-8",
    )


# ── Boot prompt structure ─────────────────────────────────────────────────────

def test_prompt_contains_core_behavior(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_session_dir(tmp_path, 1)
    prompt = _build_slim_system_prompt.__wrapped__(1) if hasattr(_build_slim_system_prompt, "__wrapped__") else _build_slim_system_prompt(1)
    assert "CORE BEHAVIOR" in prompt


def test_prompt_contains_output_format(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "OUTPUT FORMAT" in prompt
    assert "No markdown headers" in prompt


def test_prompt_contains_party_section(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "PARTY" in prompt


def test_prompt_contains_situation_section(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "CURRENT SITUATION" in prompt


def test_prompt_ends_with_context_notice(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "Additional rules" in prompt


# ── Situation block resolution ────────────────────────────────────────────────

def test_reads_own_boot_md(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = _make_session_dir(tmp_path, 2)
    (d / "boot.md").write_text("Session 2 boot content.", encoding="utf-8")

    prompt = _build_slim_system_prompt(2)
    assert "Session 2 boot content." in prompt


def test_falls_back_to_previous_recap(tmp_path, monkeypatch):
    """Session 2 has no boot.md — should use session_001/recap.md."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_session_dir(tmp_path, 2)
    prev = _make_session_dir(tmp_path, 1)
    (prev / "recap.md").write_text("Recap from session 1.", encoding="utf-8")

    prompt = _build_slim_system_prompt(2)
    assert "Recap from session 1." in prompt


def test_does_not_use_recap_when_own_boot_exists(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = _make_session_dir(tmp_path, 2)
    (d / "boot.md").write_text("Correct boot.", encoding="utf-8")
    prev = _make_session_dir(tmp_path, 1)
    (prev / "recap.md").write_text("Should not appear.", encoding="utf-8")

    prompt = _build_slim_system_prompt(2)
    assert "Correct boot." in prompt
    assert "Should not appear." not in prompt


def test_fallback_notice_when_no_files(tmp_path, monkeypatch):
    """No session files at all — prompt should contain the fallback string."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    prompt = _build_slim_system_prompt(1)
    assert "No boot context found" in prompt


def test_session1_does_not_look_for_session0_recap(tmp_path, monkeypatch):
    """Session 1 should never try to read session_000/recap.md."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    bogus = _make_session_dir(tmp_path, 0)
    (bogus / "recap.md").write_text("Should never load this.", encoding="utf-8")

    prompt = _build_slim_system_prompt(1)
    assert "Should never load this." not in prompt


# ── Party block extraction ────────────────────────────────────────────────────

def test_party_names_appear_in_prompt(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_player(tmp_path, 1, "Aldric", "Fighter / Two-Handed Fighter")
    _make_player(tmp_path, 2, "Sylara", "Wizard / Diviner")

    prompt = _build_slim_system_prompt(1)
    assert "Aldric" in prompt
    assert "Sylara" in prompt
    assert "Fighter" in prompt
    assert "Wizard" in prompt


def test_party_fallback_when_no_players_dir(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    prompt = _build_slim_system_prompt(1)
    assert "no character files found" in prompt


def test_party_sorted_by_slot(tmp_path, monkeypatch):
    """Players should appear in slot order (01, 02, 03)."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_player(tmp_path, 3, "Charlie", "Rogue")
    _make_player(tmp_path, 1, "Alice",   "Paladin")
    _make_player(tmp_path, 2, "Bob",     "Ranger")

    prompt = _build_slim_system_prompt(1)
    alice_pos  = prompt.index("Alice")
    bob_pos    = prompt.index("Bob")
    charlie_pos = prompt.index("Charlie")
    assert alice_pos < bob_pos < charlie_pos


# ── Deferred context queue ────────────────────────────────────────────────────

def test_context_queue_loads_existing_files(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    # Create one of the deferred files
    adv = tmp_path / "adventure_path" / "00_system_authority"
    adv.mkdir(parents=True)
    (adv / "GM_OPERATING_RULES_01_CRITICAL.md").write_text("Critical rules here.", encoding="utf-8")

    session = sm.create_session(1, "qwen3:4b", dev_mode=False)
    labels = [entry[1] for entry in session.context_queue]
    assert "GM Operating Rules — Critical" in labels


def test_context_queue_skips_missing_files(tmp_path, monkeypatch):
    """Files that don't exist on disk must be silently skipped."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    # No adventure_path at all
    session = sm.create_session(1, "qwen3:4b", dev_mode=False)
    assert session.context_queue == []


def test_context_queue_empty_in_dev_mode(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    session = sm.create_session(1, "qwen3:4b", dev_mode=True)
    assert session.context_queue == []


def test_context_queue_turn_numbers_are_increasing(tmp_path, monkeypatch):
    """Each successive entry's inject_after_turn must be >= the previous."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    # Create all deferred files
    for _, label, rel in sm._DEFERRED_CONTEXT_FILES:
        p = tmp_path / "adventure_path" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"Content for {label}.", encoding="utf-8")

    session = sm.create_session(1, "qwen3:4b", dev_mode=False)
    turns = [entry[0] for entry in session.context_queue]
    assert turns == sorted(turns)


# ── Input validation ──────────────────────────────────────────────────────────

def test_validate_empty_input():
    assert validate_turn_input("") is not None
    assert validate_turn_input("   ") is not None


def test_validate_too_long_input():
    assert validate_turn_input("x" * 4001) is not None


def test_validate_normal_input():
    assert validate_turn_input("We look around the square.") is None


def test_validate_max_length_boundary():
    assert validate_turn_input("x" * 4000) is None


# ── Output validation ─────────────────────────────────────────────────────────

def test_validate_empty_output():
    assert validate_generated_text("", "Recap") is not None
    assert validate_generated_text("   ", "Recap") is not None


def test_validate_too_short_output():
    assert validate_generated_text("Short.", "Recap", min_length=80) is not None


def test_validate_acceptable_output():
    text = "A" * 200
    assert validate_generated_text(text, "Recap", min_length=80) is None


def test_validate_uses_stripped_length():
    """Padding with whitespace should not fool the length check."""
    text = "   " + "x" * 10 + "   "
    assert validate_generated_text(text, "Boot", min_length=80) is not None
