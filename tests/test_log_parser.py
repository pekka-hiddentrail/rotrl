"""Unit tests for _parse_turns_from_log."""
from __future__ import annotations

from api.session_manager import _parse_turns_from_log


def test_extracts_player_and_gm_turns(sample_log):
    turns = _parse_turns_from_log(sample_log)
    roles = [t["role"] for t in turns]
    assert roles == ["PLAYER", "GM", "PLAYER", "GM"]


def test_player_content_correct(sample_log):
    turns = _parse_turns_from_log(sample_log)
    player_turns = [t for t in turns if t["role"] == "PLAYER"]
    assert "Ani wants to talk to father Zantus" in player_turns[0]["content"]
    assert "Ani asks Zantus about Desna" in player_turns[1]["content"]


def test_gm_content_correct(sample_log):
    turns = _parse_turns_from_log(sample_log)
    gm_turns = [t for t in turns if t["role"] == "GM"]
    assert "Father Zantus turns from the altar" in gm_turns[0]["content"]
    assert "goddess of dreams and stars" in gm_turns[1]["content"]


def test_skips_llm_payload_blocks(sample_log):
    turns = _parse_turns_from_log(sample_log)
    all_content = " ".join(t["content"] for t in turns)
    # Content inside <details> blocks must not appear
    assert "system prompt here" not in all_content
    assert "longer system prompt" not in all_content
    assert "<details>" not in all_content


def test_skips_context_injection_notes(sample_log):
    turns = _parse_turns_from_log(sample_log)
    all_content = " ".join(t["content"] for t in turns)
    assert "Context injected" not in all_content


def test_skips_system_prompt_block(sample_log):
    turns = _parse_turns_from_log(sample_log)
    all_content = " ".join(t["content"] for t in turns)
    assert "You are the Game Master" not in all_content


def test_no_turns_returns_empty(tmp_path):
    log = tmp_path / "empty.log.md"
    log.write_text("# Session 001\n\n## System Prompt\n\n---\n\n## Boot complete\n",
                   encoding="utf-8")
    assert _parse_turns_from_log(log) == []


def test_single_turn(tmp_path):
    log = tmp_path / "single.log.md"
    log.write_text(
        "# Session\n\n### [10:00:00] PLAYER\nJust one message.\n\n---\n",
        encoding="utf-8",
    )
    turns = _parse_turns_from_log(log)
    assert len(turns) == 1
    assert turns[0]["role"] == "PLAYER"
    assert "Just one message" in turns[0]["content"]
