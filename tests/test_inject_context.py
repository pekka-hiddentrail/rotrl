"""Tests for _inject_context: per-turn system prompt assembly and context metadata."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from api.session_manager import (
    GameSession,
    _inject_context,
    _DEV_MAX_HISTORY,
    _GROQ_MAX_HISTORY,
    _FULL_MAX_HISTORY,
    _GROQ_MAX_SYSTEM_CHARS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(**kwargs) -> GameSession:
    defaults = dict(
        id=str(uuid.uuid4()),
        session_number=1,
        model="qwen3:4b",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=False,
        provider="ollama",
        num_ctx=2048,
        num_gpu=999,
        system_prompt="BASE SYSTEM PROMPT",
        log_path=None,
    )
    defaults.update(kwargs)
    return GameSession(**defaults)


def _no_npc_index():
    idx = MagicMock()
    idx.detect.return_value = None
    idx.detect_by_location.return_value = []
    return idx


def _no_skill_index():
    idx = MagicMock()
    idx.detect.return_value = None
    return idx


def _call(session, npc_idx=None, skill_idx=None):
    with patch("api.session_manager._get_npc_index", return_value=npc_idx or _no_npc_index()), \
         patch("api.session_manager._get_skill_index", return_value=skill_idx or _no_skill_index()):
        return _inject_context(session)


def _user_msgs(n: int) -> list[dict]:
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(n)
    ]


# ── History trimming ──────────────────────────────────────────────────────────

class TestHistoryTrimming:
    def test_dev_trims_to_dev_max(self):
        session = _make_session(dev_mode=True, messages=_user_msgs(20))
        _, ctx = _call(session)
        assert len(ctx["history"]) == _DEV_MAX_HISTORY

    def test_groq_trims_to_groq_max(self):
        session = _make_session(provider="groq", messages=_user_msgs(20))
        _, ctx = _call(session)
        assert len(ctx["history"]) == _GROQ_MAX_HISTORY

    def test_ollama_trims_to_full_max(self):
        session = _make_session(provider="ollama", messages=_user_msgs(40))
        _, ctx = _call(session)
        assert len(ctx["history"]) == _FULL_MAX_HISTORY

    def test_short_history_not_trimmed(self):
        session = _make_session(messages=_user_msgs(4))
        _, ctx = _call(session)
        assert len(ctx["history"]) == 4

    def test_trim_keeps_tail(self):
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        session = _make_session(dev_mode=True, messages=msgs)
        _, ctx = _call(session)
        assert ctx["history"][-1]["content"] == "msg 19"

    def test_empty_history(self):
        session = _make_session(messages=[])
        _, ctx = _call(session)
        assert ctx["history"] == []


# ── Groq truncation ───────────────────────────────────────────────────────────

class TestGroqTruncation:
    def test_long_prompt_truncated_for_groq(self):
        long = "X" * (_GROQ_MAX_SYSTEM_CHARS + 500)
        session = _make_session(provider="groq", system_prompt=long)
        content, _ = _call(session)
        assert "…[later context omitted" in content
        assert len(content) < len(long)

    def test_short_prompt_unchanged_for_groq(self):
        session = _make_session(provider="groq", system_prompt="SHORT")
        content, _ = _call(session)
        assert content.startswith("SHORT")
        assert "omitted" not in content

    def test_long_prompt_not_truncated_for_ollama(self):
        long = "X" * (_GROQ_MAX_SYSTEM_CHARS + 500)
        session = _make_session(provider="ollama", system_prompt=long)
        content, _ = _call(session)
        assert "omitted" not in content
        assert content == long  # no modification without any injected context


# ── NPC detection ─────────────────────────────────────────────────────────────

def _npc_match(name="Abstalar Zantus", alias="zantus"):
    m = MagicMock()
    m.canonical_name = name
    m.matched_alias = alias
    return m


def _npc_idx_with_match(match):
    idx = MagicMock()
    idx.detect.return_value = match
    idx.detect_by_location.return_value = []
    idx.format_context.return_value = f"NPC profile: {match.canonical_name}"
    return idx


class TestNpcDetection:
    def test_npc_sets_context_info_fields(self):
        npc = _npc_match()
        session = _make_session(messages=[{"role": "user", "content": "Talk to Zantus"}])
        _, ctx = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert ctx["npc"] == "Abstalar Zantus"
        assert ctx["npc_trigger"] == "zantus"

    def test_npc_profile_injected_into_system_content(self):
        npc = _npc_match()
        session = _make_session(messages=[{"role": "user", "content": "Talk to Zantus"}])
        content, _ = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert "NPC profile: Abstalar Zantus" in content
        assert "[CONTEXT FOR THIS TURN]" in content

    def test_npc_added_to_scene_npcs(self):
        npc = _npc_match("Kendra Deverin", "deverin")
        session = _make_session(messages=[{"role": "user", "content": "Talk to Deverin"}])
        _call(session, npc_idx=_npc_idx_with_match(npc))
        assert "Kendra Deverin" in session.scene_npcs

    def test_npc_not_duplicated_in_scene_npcs(self):
        npc = _npc_match("Kendra Deverin", "deverin")
        session = _make_session(
            messages=[{"role": "user", "content": "Talk to Deverin"}],
            scene_npcs=["Kendra Deverin"],
        )
        _call(session, npc_idx=_npc_idx_with_match(npc))
        assert session.scene_npcs.count("Kendra Deverin") == 1

    def test_no_npc_match_returns_none_fields(self):
        session = _make_session(messages=[{"role": "user", "content": "We look around"}])
        _, ctx = _call(session)
        assert ctx["npc"] is None
        assert ctx["npc_trigger"] is None


# ── Skill detection ───────────────────────────────────────────────────────────

def _skill_match(skill="Diplomacy", trigger="talk nicely"):
    m = MagicMock()
    m.skill_name = skill
    m.matched_trigger = trigger
    return m


def _skill_idx_with_match(match):
    idx = MagicMock()
    idx.detect.return_value = match
    idx.format_context.return_value = f"Skill rules: {match.skill_name}"
    return idx


class TestSkillDetection:
    def test_skill_sets_context_info_fields(self):
        skill = _skill_match()
        session = _make_session(messages=[{"role": "user", "content": "Ani tries to talk nicely"}])
        _, ctx = _call(session, skill_idx=_skill_idx_with_match(skill))
        assert ctx["skill"] == "Diplomacy"
        assert ctx["skill_trigger"] == "talk nicely"

    def test_skill_rules_injected_into_system_content(self):
        skill = _skill_match()
        session = _make_session(messages=[{"role": "user", "content": "Ani tries to talk nicely"}])
        content, _ = _call(session, skill_idx=_skill_idx_with_match(skill))
        assert "Skill rules: Diplomacy" in content

    def test_no_skill_returns_none_fields(self):
        session = _make_session(messages=[{"role": "user", "content": "We rest"}])
        _, ctx = _call(session)
        assert ctx["skill"] is None
        assert ctx["skill_trigger"] is None


# ── Location detection ────────────────────────────────────────────────────────

def _loc_match(name, location):
    m = MagicMock()
    m.canonical_name = name
    m.matched_location = location
    m.matched_alias = name.lower()
    return m


def _npc_idx_with_location(loc_matches, direct_match=None):
    idx = MagicMock()
    idx.detect.return_value = direct_match
    idx.detect_by_location.return_value = loc_matches
    idx.format_context.side_effect = lambda m: f"Profile: {m.canonical_name}"
    return idx


class TestLocationDetection:
    def test_location_sets_context_info_fields(self):
        lm = _loc_match("Hemlock", "garrison")
        session = _make_session(messages=[{"role": "user", "content": "Go to the garrison"}])
        _, ctx = _call(session, npc_idx=_npc_idx_with_location([lm]))
        assert ctx["location"] == "garrison"
        assert "Hemlock" in ctx["location_npcs"]

    def test_location_npc_added_to_scene_npcs(self):
        lm = _loc_match("Hemlock", "garrison")
        session = _make_session(messages=[{"role": "user", "content": "Go to the garrison"}])
        _call(session, npc_idx=_npc_idx_with_location([lm]))
        assert "Hemlock" in session.scene_npcs

    def test_npc_matched_by_name_excluded_from_location_list(self):
        """An NPC already injected by direct name match is not re-injected via location."""
        npc = _loc_match("Hemlock", "garrison")
        npc.matched_alias = "hemlock"

        idx = MagicMock()
        idx.detect.return_value = npc
        idx.detect_by_location.return_value = [npc]
        idx.format_context.return_value = "Profile: Hemlock"

        session = _make_session(messages=[{"role": "user", "content": "Talk to Hemlock at garrison"}])
        content, ctx = _call(session, npc_idx=idx)

        assert ctx["location_npcs"] == []
        assert content.count("Profile: Hemlock") == 1

    def test_no_location_match_returns_empty(self):
        session = _make_session(messages=[{"role": "user", "content": "We rest"}])
        _, ctx = _call(session)
        assert ctx["location"] is None
        assert ctx["location_npcs"] == []


# ── Delta-reminder path ───────────────────────────────────────────────────────

class TestDeltaReminder:
    def test_reminder_injected_when_scene_npcs_active_but_no_new_context(self):
        session = _make_session(
            messages=[{"role": "user", "content": "We continue"}],
            scene_npcs=["Abstalar Zantus", "Kendra Deverin"],
        )
        content, _ = _call(session)
        assert "%%DELTAS%%" in content
        assert "Abstalar Zantus" in content
        assert "Kendra Deverin" in content
        assert "[GM DIRECTIVE FOR THIS TURN" in content

    def test_no_reminder_when_no_scene_npcs_and_no_context(self):
        session = _make_session(messages=[{"role": "user", "content": "We look around"}])
        content, _ = _call(session)
        assert "[CONTEXT FOR THIS TURN]" not in content
        assert "[GM DIRECTIVE FOR THIS TURN" not in content

    def test_full_directive_used_when_new_context_detected(self):
        """When new NPC is detected the full directive block fires, not bare delta reminder."""
        npc = _npc_match("New Guy", "newguy")
        session = _make_session(
            messages=[{"role": "user", "content": "Talk to New Guy"}],
            scene_npcs=["Old NPC"],
        )
        content, _ = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert "[CONTEXT FOR THIS TURN]" in content
        assert "[GM DIRECTIVE FOR THIS TURN" in content

    def test_scene_npcs_list_preserved_in_reminder(self):
        npcs = ["Alice Smith", "Bob Jones", "Carol White"]
        session = _make_session(
            messages=[{"role": "user", "content": "We sit down"}],
            scene_npcs=npcs,
        )
        content, _ = _call(session)
        for name in npcs:
            assert name in content


# ── context_info structure ────────────────────────────────────────────────────

class TestContextInfoStructure:
    def test_all_expected_keys_present(self):
        session = _make_session(messages=[{"role": "user", "content": "Hello"}])
        _, ctx = _call(session)
        for key in ("npc", "npc_trigger", "skill", "skill_trigger", "location", "location_npcs", "history"):
            assert key in ctx, f"Missing key: {key}"

    def test_location_npcs_is_list(self):
        session = _make_session(messages=[{"role": "user", "content": "Hello"}])
        _, ctx = _call(session)
        assert isinstance(ctx["location_npcs"], list)

    def test_history_matches_trimmed_messages(self):
        msgs = _user_msgs(4)
        session = _make_session(messages=msgs)
        _, ctx = _call(session)
        assert ctx["history"] == msgs

    def test_detection_uses_last_user_message(self):
        """Keyword detection runs on the most recent user message only."""
        msgs = [
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "response"},
            {"role": "user", "content": "second message"},
        ]
        session = _make_session(messages=msgs)
        detected = []

        def _spy_detect(text):
            detected.append(text)
            return None

        idx = MagicMock()
        idx.detect.side_effect = _spy_detect
        idx.detect_by_location.return_value = []

        _call(session, npc_idx=idx)

        assert "second message" in detected
        assert "first message" not in detected

    def test_return_type(self):
        session = _make_session(messages=[{"role": "user", "content": "Hello"}])
        result = _call(session)
        assert isinstance(result, tuple)
        assert len(result) == 2
        content, ctx = result
        assert isinstance(content, str)
        assert isinstance(ctx, dict)
