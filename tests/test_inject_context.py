"""Tests for _inject_context: per-turn system prompt assembly and context metadata."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from api.session_manager import (
    ActiveEvent,
    GameSession,
    CombatState,
    Combatant,
    _inject_context,
    _build_pc_combat_roster,
    _DEV_MAX_HISTORY,
    _GROQ_MAX_HISTORY,
    _FULL_MAX_HISTORY,
    _GROQ_MAX_SYSTEM_CHARS,
    _FORMAT_EXAMPLE,
    _COMBAT_SPEC_ONGOING,
    _COMBAT_SPEC_ROUND1,
    _NARRATIVE_SPEC,
    _ROLL_SPEC,
    _GENERATE_SPEC,
    _DELTAS_SPEC,
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
        assert content.startswith(long)  # base prompt intact; sections block appended


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
    idx.format_short_context.return_value = f"NPC stub: {match.canonical_name}"
    return idx


class TestNpcDetection:
    def test_npc_sets_context_info_fields(self):
        npc = _npc_match()
        session = _make_session(messages=[{"role": "user", "content": "Talk to Zantus"}])
        _, ctx = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert ctx["npc"] == "Abstalar Zantus"
        assert ctx["npc_trigger"] == "zantus"

    def test_npc_short_context_injected_without_skill(self):
        """No skill match → short NPC stub (format_short_context)."""
        npc = _npc_match()
        session = _make_session(messages=[{"role": "user", "content": "Talk to Zantus"}])
        content, _ = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert "NPC stub: Abstalar Zantus" in content
        assert "[CONTEXT FOR THIS TURN]" in content

    def test_npc_full_context_injected_with_skill(self):
        """Skill match present → full NPC profile (format_context)."""
        npc = _npc_match()
        skill = _skill_match()
        session = _make_session(messages=[{"role": "user", "content": "I talk to Zantus"}])
        content, _ = _call(
            session,
            npc_idx=_npc_idx_with_match(npc),
            skill_idx=_skill_idx_with_match(skill),
        )
        assert "NPC profile: Abstalar Zantus" in content
        assert "NPC stub:" not in content

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
    def test_location_npc_not_injected_via_location_match(self):
        """Location-based NPC injection is disabled; only directly-named NPCs are injected."""
        lm = _loc_match("Hemlock", "garrison")
        session = _make_session(messages=[{"role": "user", "content": "Go to the garrison"}])
        _, ctx = _call(session, npc_idx=_npc_idx_with_location([lm]))
        assert ctx["location"] is None
        assert ctx["location_npcs"] == []

    def test_location_npc_not_added_to_scene_npcs(self):
        """Location-based NPCs are no longer tracked in scene_npcs."""
        lm = _loc_match("Hemlock", "garrison")
        session = _make_session(messages=[{"role": "user", "content": "Go to the garrison"}])
        _call(session, npc_idx=_npc_idx_with_location([lm]))
        assert "Hemlock" not in session.scene_npcs

    def test_directly_named_npc_still_injected(self):
        """An NPC matched by name is injected even when a location is also mentioned."""
        npc = _loc_match("Hemlock", "garrison")
        npc.matched_alias = "hemlock"

        idx = MagicMock()
        idx.detect.return_value = npc
        idx.detect_by_location.return_value = [npc]
        idx.format_context.return_value = "NPC profile: Hemlock"
        idx.format_short_context.return_value = "NPC stub: Hemlock"

        session = _make_session(messages=[{"role": "user", "content": "Talk to Hemlock at garrison"}])
        content, ctx = _call(session, npc_idx=idx)

        assert ctx["location_npcs"] == []
        # Short context used (no skill match); profile injected exactly once
        assert content.count("NPC stub: Hemlock") == 1

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


# ── Combat reminder ───────────────────────────────────────────────────────────

def _goblin_combatant(name="Goblin Warrior", hp=5, ac=16, init=10):
    return Combatant(name=name, hp_current=hp, hp_max=hp, ac=ac, initiative=init)


class TestCombatReminder:
    def test_combat_reminder_injected_when_round_positive(self):
        session = _make_session(
            messages=[{"role": "user", "content": "I swing at the goblin"}],
            combat_state=CombatState(round=1, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session)
        assert "[COMBAT ONGOING" in content
        assert "%%COMBAT%%" in content

    def test_combat_reminder_includes_correct_round_number(self):
        session = _make_session(
            messages=[{"role": "user", "content": "I attack again"}],
            combat_state=CombatState(round=3, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session)
        assert "round 3" in content

    def test_no_combat_reminder_when_combat_state_is_none(self):
        session = _make_session(
            messages=[{"role": "user", "content": "We look around"}],
            combat_state=None,
        )
        content, _ = _call(session)
        assert "[COMBAT ONGOING" not in content

    def test_no_combat_reminder_when_round_is_zero(self):
        # round: 0 is the intentional clear signal — combat has just ended
        session = _make_session(
            messages=[{"role": "user", "content": "The last goblin falls"}],
            combat_state=CombatState(round=0, combatants=[]),
        )
        content, _ = _call(session)
        assert "[COMBAT ONGOING" not in content

    def test_combat_reminder_present_without_other_context(self):
        # No NPC / skill / location match — reminder still fires
        session = _make_session(
            messages=[{"role": "user", "content": "ok"}],
            combat_state=CombatState(round=2, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session)
        assert "[COMBAT ONGOING — round 2]" in content

    def test_combat_reminder_appended_after_existing_directive(self):
        # Reminder must appear even when another directive block is present
        npc = _npc_match()
        session = _make_session(
            messages=[{"role": "user", "content": "I dodge and talk to Zantus"}],
            combat_state=CombatState(round=1, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert "[GM DIRECTIVE FOR THIS TURN" in content
        assert "[COMBAT ONGOING" in content
        # Combat section must come AFTER the directive
        assert content.index("[COMBAT ONGOING") > content.index("[GM DIRECTIVE FOR THIS TURN")


# ── Turn-1 format example injection ──────────────────────────────────────────

class TestFormatExampleInjection:
    def test_example_injected_on_first_player_turn(self):
        """With exactly 1 message (the turn just appended), example must appear."""
        session = _make_session(
            messages=[{"role": "user", "content": "We arrive at the festival."}],
        )
        content, _ = _call(session)
        assert "Gerhard Pickle" in content
        assert _FORMAT_EXAMPLE in content

    def test_example_not_injected_on_second_turn(self):
        """After the first exchange (3 messages), example must NOT appear."""
        session = _make_session(
            messages=[
                {"role": "user", "content": "First turn."},
                {"role": "assistant", "content": "GM response."},
                {"role": "user", "content": "Second turn."},
            ],
        )
        content, _ = _call(session)
        assert "Gerhard Pickle" not in content

    def test_example_not_injected_with_no_messages(self):
        """0 messages means no turn has been submitted yet — no example."""
        session = _make_session(messages=[])
        content, _ = _call(session)
        assert "Gerhard Pickle" not in content

    def test_example_appears_after_base_prompt(self):
        """Example block must be appended, not prepended."""
        session = _make_session(
            messages=[{"role": "user", "content": "Hello."}],
            system_prompt="BASE",
        )
        content, _ = _call(session)
        assert content.startswith("BASE")
        assert content.index("Gerhard Pickle") > content.index("BASE")

    def test_example_present_alongside_npc_context(self):
        """Turn-1 example and NPC context injection must both appear."""
        npc = _npc_match()
        session = _make_session(
            messages=[{"role": "user", "content": "I talk to Ameiko."}],
        )
        content, _ = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert "Gerhard Pickle" in content
        assert "[CONTEXT FOR THIS TURN]" in content


# ── Combat full-spec injection ────────────────────────────────────────────────

class TestCombatFullSpec:
    def test_full_spec_injected_when_combat_active(self):
        """When round > 0 the full combat spec (format + rules) is injected."""
        session = _make_session(
            messages=[{"role": "user", "content": "I attack."}],
            combat_state=CombatState(round=2, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session)
        assert _COMBAT_SPEC_ONGOING in content

    def test_full_spec_not_injected_when_no_combat(self):
        """Without active combat the full spec must NOT appear."""
        session = _make_session(
            messages=[{"role": "user", "content": "We explore."}],
            combat_state=None,
        )
        content, _ = _call(session)
        assert _COMBAT_SPEC_ONGOING not in content

    def test_full_spec_includes_format_and_round_rule(self):
        """Sanity-check: round-1 spec has HP fields; ongoing spec has round-0 rule."""
        assert "hp:" in _COMBAT_SPEC_ROUND1       # round-1 spec supplies HP for init
        assert "round: 0" in _COMBAT_SPEC_ONGOING  # ongoing spec carries the clear rule

    def test_combat_header_still_shows_round_number(self):
        """[COMBAT ONGOING — round N] header must still carry the actual round."""
        session = _make_session(
            messages=[{"role": "user", "content": "I swing again."}],
            combat_state=CombatState(round=5, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session)
        assert "[COMBAT ONGOING — round 5]" in content

    def test_full_spec_injected_on_first_turn_with_combat(self):
        """Turn-1 example AND full combat spec both appear when combat starts
        on the very first player turn (unlikely but must be handled)."""
        session = _make_session(
            messages=[{"role": "user", "content": "Goblins attack!"}],
            combat_state=CombatState(round=1, combatants=[_goblin_combatant()]),
        )
        content, _ = _call(session)
        assert "Gerhard Pickle" in content
        assert _COMBAT_SPEC_ONGOING in content


# ── Conditional section specs ─────────────────────────────────────────────────

class TestConditionalSectionSpecs:
    def test_sections_block_always_injected(self):
        """[SECTIONS ACTIVE THIS TURN] block is present on every turn."""
        session = _make_session(messages=[{"role": "user", "content": "We look around."}])
        content, _ = _call(session)
        assert "[SECTIONS ACTIVE THIS TURN]" in content

    def test_narrative_spec_always_injected(self):
        """%%NARRATIVE%% spec is always included."""
        session = _make_session(messages=[{"role": "user", "content": "We look around."}])
        content, _ = _call(session)
        assert _NARRATIVE_SPEC in content

    def test_generate_spec_always_injected(self):
        """%%GENERATE%% spec is always included."""
        session = _make_session(messages=[{"role": "user", "content": "We explore the square."}])
        content, _ = _call(session)
        assert _GENERATE_SPEC in content

    def test_roll_spec_injected_when_skill_detected(self):
        """%%ROLL%% spec appears when a skill match is detected."""
        skill = _skill_match("Perception", "look around")
        session = _make_session(messages=[{"role": "user", "content": "I try to look around."}])
        content, _ = _call(session, skill_idx=_skill_idx_with_match(skill))
        assert _ROLL_SPEC in content

    def test_roll_spec_not_injected_without_skill(self):
        """%%ROLL%% spec is absent when no skill is detected."""
        session = _make_session(messages=[{"role": "user", "content": "I wave at the mayor."}])
        content, _ = _call(session)
        assert _ROLL_SPEC not in content

    def test_deltas_spec_injected_when_scene_npcs_present(self):
        """%%DELTAS%% spec appears when scene_npcs is non-empty."""
        session = _make_session(
            messages=[{"role": "user", "content": "I look at the crowd."}],
            scene_npcs=["Kendra Deverin"],
        )
        content, _ = _call(session)
        assert _DELTAS_SPEC in content

    def test_deltas_spec_injected_when_npc_detected(self):
        """%%DELTAS%% spec appears when an NPC is detected in input."""
        npc = _npc_match("Abstalar Zantus", "zantus")
        session = _make_session(messages=[{"role": "user", "content": "Talk to Zantus."}])
        content, _ = _call(session, npc_idx=_npc_idx_with_match(npc))
        assert _DELTAS_SPEC in content

    def test_deltas_spec_not_injected_with_no_npcs(self):
        """%%DELTAS%% spec is absent when no NPCs are in scene and none detected."""
        session = _make_session(
            messages=[{"role": "user", "content": "We admire the decorations."}],
            scene_npcs=[],
        )
        content, _ = _call(session)
        assert _DELTAS_SPEC not in content


# ── PC profile injection ──────────────────────────────────────────────────────

_SAMPLE_NARRATIVE = "## PC — Harsk (Dwarf Ranger)\nAppearance: Short and stocky with a red beard.\nPersonality: Grim and taciturn."
_SAMPLE_MECHANICAL = "## PC Stats — Harsk\nHP: 12  AC: 16  Init: +2  Speed: 20 ft\nSaves: Fort +4 / Ref +4 / Will +1"


def _session_with_pc(**kwargs) -> GameSession:
    return _make_session(
        pc_profiles={
            "harsk": {
                "narrative": _SAMPLE_NARRATIVE,
                "mechanical": _SAMPLE_MECHANICAL,
            }
        },
        **kwargs,
    )


class TestPcProfileInjection:
    def test_narrative_profile_injected_when_pc_named(self):
        """Narrative profile is injected when PC's name appears in last_user."""
        session = _session_with_pc(
            messages=[{"role": "user", "content": "Harsk moves towards the stall."}]
        )
        content, _ = _call(session)
        assert _SAMPLE_NARRATIVE in content

    def test_narrative_profile_not_injected_when_pc_not_named(self):
        """Narrative profile is absent when PC's name does not appear in last_user."""
        session = _session_with_pc(
            messages=[{"role": "user", "content": "We look at the cathedral."}]
        )
        content, _ = _call(session)
        assert _SAMPLE_NARRATIVE not in content

    def test_mechanical_profile_injected_when_pc_named_and_skill_detected(self):
        """Mechanical profile is added when PC is named AND a skill is detected."""
        skill = _skill_match("Perception", "look")
        session = _session_with_pc(
            messages=[{"role": "user", "content": "Harsk tries to look for threats."}]
        )
        content, _ = _call(session, skill_idx=_skill_idx_with_match(skill))
        assert _SAMPLE_NARRATIVE in content
        assert _SAMPLE_MECHANICAL in content

    def test_mechanical_profile_not_injected_without_skill(self):
        """Mechanical profile is absent when PC is named but no skill is detected."""
        session = _session_with_pc(
            messages=[{"role": "user", "content": "Harsk waves at the crowd."}]
        )
        content, _ = _call(session)
        assert _SAMPLE_NARRATIVE in content
        assert _SAMPLE_MECHANICAL not in content

    def test_only_first_matched_pc_injected(self):
        """When multiple PCs are named, only the first matched one is injected."""
        profiles = {
            "harsk": {"narrative": "## PC — Harsk\nFirst PC.", "mechanical": "Stats A"},
            "seoni": {"narrative": "## PC — Seoni\nSecond PC.", "mechanical": "Stats B"},
        }
        session = _make_session(
            pc_profiles=profiles,
            messages=[{"role": "user", "content": "Harsk and Seoni both act."}],
        )
        content, _ = _call(session)
        # The first key match wins; exactly one narrative block injected
        assert content.count("## PC —") == 1


# ── PC combat roster injection ────────────────────────────────────────────────

def _pc_profiles_fixture() -> dict:
    """Two minimal PC profiles with combat_stats populated."""
    return {
        "thaelion": {
            "narrative": "## PC — Thaelion",
            "mechanical": "## PC Stats — Thaelion\nHP: 22  AC: 16  Init: +3",
            "combat_stats": {"name": "Thaelion", "hp_max": 22, "ac": 16, "initiative": "+3"},
        },
        "yanyeeku": {
            "narrative": "## PC — Yanyeeku",
            "mechanical": "## PC Stats — Yanyeeku\nHP: 9  AC: 16  Init: +2",
            "combat_stats": {"name": "Yanyeeku", "hp_max": 9, "ac": 16, "initiative": "+2"},
        },
    }


class TestPcCombatRoster:
    """_build_pc_combat_roster and its injection into the combat-start context."""

    def test_roster_contains_all_pc_names(self):
        session = _make_session(pc_profiles=_pc_profiles_fixture())
        roster = _build_pc_combat_roster(session)
        assert "Thaelion" in roster
        assert "Yanyeeku" in roster

    def test_roster_uses_full_hp_on_round_1(self):
        """HP line must be hp_max/hp_max — PCs start combat at full health."""
        session = _make_session(pc_profiles=_pc_profiles_fixture())
        roster = _build_pc_combat_roster(session)
        assert "hp: 22/22" in roster
        assert "hp: 9/9" in roster

    def test_roster_includes_ac_and_initiative(self):
        session = _make_session(pc_profiles=_pc_profiles_fixture())
        roster = _build_pc_combat_roster(session)
        assert "ac: 16" in roster
        assert "init: +3" in roster

    def test_roster_lines_use_combat_format(self):
        """Every PC line must follow the exact %%COMBAT%% combatant format."""
        session = _make_session(pc_profiles=_pc_profiles_fixture())
        roster = _build_pc_combat_roster(session)
        assert "· hp:" in roster
        assert "· ac:" in roster
        assert "· init:" in roster
        assert "· status: active" in roster

    def test_roster_empty_when_no_profiles(self):
        session = _make_session(pc_profiles={})
        assert _build_pc_combat_roster(session) == ""

    def test_roster_injected_with_combat_start_spec(self):
        """When active_events are present and no combat yet, the PC roster is in the system content."""
        session = _make_session(
            pc_profiles=_pc_profiles_fixture(),
            active_events=[ActiveEvent(event_id="goblin_attack_starts", content="Goblins!", turns_remaining=3)],
            messages=[{"role": "user", "content": "The goblins charge!"}],
        )
        content, _ = _call(session)
        assert "PARTY ROSTER" in content
        assert "Thaelion" in content
        assert "Yanyeeku" in content

    def test_roster_not_injected_without_active_events(self):
        """Without active_events the roster must NOT appear — combat hasn't been signalled."""
        session = _make_session(
            pc_profiles=_pc_profiles_fixture(),
            active_events=[],
            messages=[{"role": "user", "content": "We explore the cathedral."}],
        )
        content, _ = _call(session)
        assert "PARTY ROSTER" not in content

    def test_roster_not_injected_during_ongoing_combat(self):
        """Round 2+ uses the ongoing spec, not round-1 spec — roster must not repeat."""
        session = _make_session(
            pc_profiles=_pc_profiles_fixture(),
            combat_state=CombatState(round=2, combatants=[
                Combatant(name="Thaelion", hp_current=22, hp_max=22, ac=16, initiative=3),
            ]),
            messages=[{"role": "user", "content": "I attack again."}],
        )
        content, _ = _call(session)
        assert "PARTY ROSTER" not in content
