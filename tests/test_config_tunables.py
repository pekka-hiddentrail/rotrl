"""Tests for F6 — env-var-configurable tunables and R4 — name_exclude_words file loading.

F6: _DEV_MAX_HISTORY, _FULL_MAX_HISTORY, _GROQ_MAX_HISTORY, _ANTHROPIC_MAX_HISTORY,
    _DEV_MAX_TOKENS, _GROQ_MAX_SYSTEM_CHARS, _GROQ_RETRY_BASE are all read from
    ROTRL_* env vars with their original values as defaults.

R4: _NAME_EXCLUDE_WORDS is loaded from
    adventure_path/00_system_authority/name_exclude_words.txt at import time;
    falls back to the hardcoded set when the file is absent or unreadable.
"""
from __future__ import annotations

from pathlib import Path

import api.session_manager as sm


# ── F6 — default values ───────────────────────────────────────────────────────
# Verify the live module has the expected defaults (no ROTRL_* env vars in CI).

def test_f6_dev_max_history_default():
    assert sm._DEV_MAX_HISTORY == 6

def test_f6_full_max_history_default():
    assert sm._FULL_MAX_HISTORY == 30

def test_f6_groq_max_history_default():
    assert sm._GROQ_MAX_HISTORY == 10

def test_f6_anthropic_max_history_default():
    assert sm._ANTHROPIC_MAX_HISTORY == 60

def test_f6_dev_max_tokens_default():
    assert sm._DEV_MAX_TOKENS == 180

def test_f6_groq_max_system_chars_default():
    assert sm._GROQ_MAX_SYSTEM_CHARS == 30_000

def test_f6_groq_retry_base_default():
    assert sm._GROQ_RETRY_BASE == 5.0

def test_f6_constants_are_correct_types():
    """All tunables are int or float — not strings."""
    assert isinstance(sm._DEV_MAX_HISTORY, int)
    assert isinstance(sm._FULL_MAX_HISTORY, int)
    assert isinstance(sm._GROQ_MAX_HISTORY, int)
    assert isinstance(sm._ANTHROPIC_MAX_HISTORY, int)
    assert isinstance(sm._DEV_MAX_TOKENS, int)
    assert isinstance(sm._GROQ_MAX_SYSTEM_CHARS, int)
    assert isinstance(sm._GROQ_RETRY_BASE, float)


# ── R4 — _load_name_exclude_words() ──────────────────────────────────────────

def test_r4_loads_from_file(tmp_path, monkeypatch):
    """Words in the file are loaded into the result set."""
    words_file = tmp_path / "adventure_path" / "00_system_authority" / "name_exclude_words.txt"
    words_file.parent.mkdir(parents=True)
    words_file.write_text("# comment\ndragon\nwizard\n\nbard\n", encoding="utf-8")

    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    result = sm._load_name_exclude_words()
    assert "dragon" in result
    assert "wizard" in result
    assert "bard" in result


def test_r4_ignores_comments_and_blank_lines(tmp_path, monkeypatch):
    words_file = tmp_path / "adventure_path" / "00_system_authority" / "name_exclude_words.txt"
    words_file.parent.mkdir(parents=True)
    words_file.write_text("# this is a comment\n\nonly_word\n", encoding="utf-8")

    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    result = sm._load_name_exclude_words()
    assert "only_word" in result
    assert "" not in result


def test_r4_falls_back_when_file_absent(tmp_path, monkeypatch):
    """When the file doesn't exist the hardcoded fallback set is returned."""
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)  # no words file under tmp_path
    result = sm._load_name_exclude_words()
    assert "mayor" in result
    assert "sheriff" in result
    assert "sandpoint" in result


def test_r4_falls_back_when_file_empty(tmp_path, monkeypatch):
    """A file with only comments (no words) triggers the fallback."""
    words_file = tmp_path / "adventure_path" / "00_system_authority" / "name_exclude_words.txt"
    words_file.parent.mkdir(parents=True)
    words_file.write_text("# only comments\n\n", encoding="utf-8")

    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    result = sm._load_name_exclude_words()
    assert "mayor" in result  # fallback applied


def test_r4_words_are_lowercased(tmp_path, monkeypatch):
    """Words loaded from the file are normalised to lower-case."""
    words_file = tmp_path / "adventure_path" / "00_system_authority" / "name_exclude_words.txt"
    words_file.parent.mkdir(parents=True)
    words_file.write_text("Dragon\nWIZARD\nBard\n", encoding="utf-8")

    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    result = sm._load_name_exclude_words()
    assert "dragon" in result
    assert "wizard" in result
    assert "Dragon" not in result


def test_r4_module_level_constant_contains_expected_words():
    """The live _NAME_EXCLUDE_WORDS (loaded from the real file) contains known words."""
    assert "mayor" in sm._NAME_EXCLUDE_WORDS
    assert "sandpoint" in sm._NAME_EXCLUDE_WORDS
    assert "festival" in sm._NAME_EXCLUDE_WORDS
