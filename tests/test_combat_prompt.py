"""Tests for Tier 1.6 — Dedicated Combat System Prompt.

Covers: _build_combat_system_prompt, _COMBAT_SECTION_SPECS, and the combat
branch of _inject_context (AC-001 through AC-014 in combat-system-prompt.feature).
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from api.session_manager import (
    ActiveEvent,
    Combatant,
    CombatState,
    GameSession,
    _COMBAT_SECTION_SPECS,
    _COMBAT_SPEC_ONGOING,
    _DELTAS_SPEC,
    _FORMAT_EXAMPLE,
    _GENERATE_SPEC,
    _NARRATIVE_SPEC,
    _ROLL_SPEC,
    _build_combat_system_prompt,
    _build_slim_system_prompt,
    _inject_context,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

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


def _make_pc_profiles() -> dict:
    return {
        "thaelion": {
            "narrative": "## PC — Thaelion (Half-Elf Fighter)",
            "mechanical": "## PC Stats — Thaelion\nHP: 22  AC: 16  Init: +3\nStr +2  Dex +1",
            "combat_stats": {"name": "Thaelion", "hp_max": 22, "ac": 16, "initiative": "+3"},
        },
        "yanyeeku": {
            "narrative": "## PC — Yanyeeku (Human Cleric)",
            "mechanical": "## PC Stats — Yanyeeku\nHP: 18  AC: 14  Init: +1\nWis +3",
            "combat_stats": {"name": "Yanyeeku", "hp_max": 18, "ac": 14, "initiative": "+1"},
        },
    }


def _make_combat_state(round_num: int = 2) -> CombatState:
    return CombatState(
        round=round_num,
        combatants=[
            Combatant(name="Shalelu",  hp_current=18, hp_max=24, ac=17, initiative=14),
            Combatant(name="Thaelion", hp_current=22, hp_max=22, ac=16, initiative=10),
            Combatant(name="Goblin 1", hp_current=3,  hp_max=5,  ac=13, initiative=5),
        ],
    )


def _no_index():
    idx = MagicMock()
    idx.detect.return_value = None
    idx.detect_by_location.return_value = []
    return idx


def _call(session, npc_idx=None, skill_idx=None, loc_idx=None, crules_idx=None):
    """Call _inject_context with all external indexes mocked out."""
    with (
        patch("api.session_manager._get_npc_index",          return_value=npc_idx     or _no_index()),
        patch("api.session_manager._get_skill_index",         return_value=skill_idx   or _no_index()),
        patch("api.session_manager._get_location_index",      return_value=loc_idx     or _no_index()),
        patch("api.session_manager._get_combat_rules_index",  return_value=crules_idx  or _no_index()),
        patch("api.session_manager._get_event_index",         return_value=_no_index()),
    ):
        return _inject_context(session)


# ── _COMBAT_SECTION_SPECS constant (AC-014) ───────────────────────────────────

class TestCombatSectionSpecs:
    def test_contains_combat_mode_label(self):
        assert "COMBAT MODE" in _COMBAT_SECTION_SPECS

    def test_contains_narrative_marker(self):
        assert "%%NARRATIVE%%" in _COMBAT_SECTION_SPECS

    def test_contains_combat_marker(self):
        assert "%%COMBAT%%" in _COMBAT_SECTION_SPECS

    def test_contains_attack_marker(self):
        assert "%%ATTACK%%" in _COMBAT_SECTION_SPECS

    def test_no_hp_marker(self):
        # CB1.9-4: %%HP%% removed from spec — LLM no longer instructed to write it
        assert "%%HP%%" not in _COMBAT_SECTION_SPECS

    def test_no_generate_marker(self):
        assert "%%GENERATE%%" not in _COMBAT_SECTION_SPECS

    def test_no_deltas_marker(self):
        assert "%%DELTAS%%" not in _COMBAT_SECTION_SPECS

    def test_no_roll_marker(self):
        assert "%%ROLL%%" not in _COMBAT_SECTION_SPECS


# ── _build_combat_system_prompt (AC-001, AC-002) ──────────────────────────────

class TestBuildCombatSystemPrompt:
    def _prompt(self, **kwargs):
        session = _make_session(pc_profiles=_make_pc_profiles(), **kwargs)
        return _build_combat_system_prompt(session)

    # AC-001 — forbidden sections absent
    def test_no_generate_spec(self):
        assert "%%GENERATE%%" not in self._prompt()

    def test_no_deltas_spec(self):
        assert "%%DELTAS%%" not in self._prompt()

    def test_no_roll_spec(self):
        assert "%%ROLL%%" not in self._prompt()

    def test_no_event_spec(self):
        # %%EVENT%% should never appear in the combat base prompt
        assert "%%EVENT%%" not in self._prompt()

    # AC-001 — allowed sections present
    def test_has_narrative_marker(self):
        assert "%%NARRATIVE%%" in self._prompt()

    def test_has_combat_marker(self):
        assert "%%COMBAT%%" in self._prompt()

    def test_has_attack_marker(self):
        assert "%%ATTACK%%" in self._prompt()

    def test_no_hp_marker(self):
        # CB1.9-4: %%HP%% removed from combat system prompt
        assert "%%HP%%" not in self._prompt()

    def test_has_forbidden_prohibition(self):
        prompt = self._prompt()
        assert "FORBIDDEN" in prompt or "do NOT write" in prompt.upper() or "DO NOT" in prompt

    # PC names appear in party block
    def test_has_pc_names(self):
        prompt = self._prompt()
        assert "Thaelion" in prompt
        assert "Yanyeeku" in prompt

    # AC-002 — significantly shorter than narrative prompt
    def test_shorter_than_slim_prompt(self):
        session = _make_session(pc_profiles=_make_pc_profiles())
        combat_len = len(_build_combat_system_prompt(session))
        slim_len   = len(_build_slim_system_prompt(session.session_number))
        assert combat_len <= 0.60 * slim_len, (
            f"Combat prompt ({combat_len} chars) not ≤ 60% of slim prompt ({slim_len} chars)"
        )


# ── _inject_context combat branch (AC-003 through AC-013) ────────────────────

class TestInjectContextCombatBranch:
    """Tests for the combat path in _inject_context."""

    def _session_in_combat(self, messages=None, active_events=None, combat_state=None, **kwargs):
        session = _make_session(
            pc_profiles=_make_pc_profiles(),
            combat_state=combat_state if combat_state is not None else _make_combat_state(),
            messages=messages or [{"role": "user", "content": "I attack Goblin 1."}],
            active_events=active_events or [],
            **kwargs,
        )
        return session

    # AC-003 — combat prompt as base, not session.system_prompt
    def test_does_not_start_with_session_system_prompt(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert not system_content.startswith("BASE SYSTEM PROMPT")

    def test_does_not_contain_format_example(self):
        session = self._session_in_combat()
        # Even on turn 1 (messages == 1 entry), format example should be absent
        system_content, _ = _call(session)
        assert _FORMAT_EXAMPLE[:40] not in system_content

    # AC-004 — NPC/skill/location detection skipped
    def test_npc_index_detect_not_called(self):
        session = self._session_in_combat()
        npc_idx = _no_index()
        _call(session, npc_idx=npc_idx)
        npc_idx.detect.assert_not_called()

    def test_skill_index_detect_not_called(self):
        session = self._session_in_combat()
        skill_idx = _no_index()
        _call(session, skill_idx=skill_idx)
        skill_idx.detect.assert_not_called()

    def test_location_index_detect_not_called(self):
        session = self._session_in_combat()
        loc_idx = _no_index()
        _call(session, loc_idx=loc_idx)
        loc_idx.detect.assert_not_called()

    def test_context_info_npc_is_none(self):
        session = self._session_in_combat()
        _, ctx = _call(session)
        assert ctx["npc"] is None

    def test_context_info_skill_is_none(self):
        session = self._session_in_combat()
        _, ctx = _call(session)
        assert ctx["skill"] is None

    def test_context_info_location_is_none(self):
        session = self._session_in_combat()
        _, ctx = _call(session)
        assert ctx["location"] is None

    def test_context_info_loc_is_none(self):
        session = self._session_in_combat()
        _, ctx = _call(session)
        assert ctx["loc"] is None

    # AC-005 — [INITIATIVE ORDER] present and sorted descending
    def test_initiative_order_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert "[INITIATIVE ORDER" in system_content

    def test_initiative_order_shalelu_before_thaelion(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        # Locate the initiative order block and check order within it
        order_start = system_content.index("[INITIATIVE ORDER")
        order_text  = system_content[order_start:].split("\n\n")[0]
        idx_shalelu  = order_text.index("Shalelu")
        idx_thaelion = order_text.index("Thaelion")
        assert idx_shalelu < idx_thaelion, "Shalelu (init 14) should appear before Thaelion (init 10)"

    def test_initiative_order_current_actor_marked(self):
        # Shalelu is highest active initiative → marked with →
        session = self._session_in_combat()
        system_content, _ = _call(session)
        lines = system_content.splitlines()
        shalelu_line = next(l for l in lines if "Shalelu" in l and ("14" in l or "init" in l.lower() or "→" in l))
        assert "→" in shalelu_line

    def test_initiative_order_others_not_marked(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        lines = system_content.splitlines()
        # Lines containing Thaelion or Goblin 1 (within the initiative block) should not have →
        order_block_start = system_content.index("[INITIATIVE ORDER")
        order_block_text = system_content[order_block_start:]
        # Grab the block up to the next \n\n section break
        order_section = order_block_text.split("\n\n")[0]
        for line in order_section.splitlines():
            if "Thaelion" in line or "Goblin 1" in line:
                assert "→" not in line, f"Non-current combatant marked with → in: {line!r}"

    # AC-006 — current actor is highest *active* combatant
    def test_unconscious_combatant_not_marked_as_current(self):
        combat = CombatState(
            round=2,
            combatants=[
                Combatant(name="Shalelu",   hp_current=0,  hp_max=24, ac=17, initiative=14, status="unconscious"),
                Combatant(name="Thaelion",  hp_current=22, hp_max=22, ac=16, initiative=10, status="active"),
                Combatant(name="Goblin 1",  hp_current=3,  hp_max=5,  ac=13, initiative=5,  status="active"),
            ],
        )
        # Use a session without pc_profiles so "Thaelion" only appears in the initiative block
        session = _make_session(
            combat_state=combat,
            messages=[{"role": "user", "content": "I attack."}],
            active_events=[],
        )
        system_content, _ = _call(session)
        order_start   = system_content.index("[INITIATIVE ORDER")
        order_section = system_content[order_start:].split("\n\n")[0]
        shalelu_line  = next(l for l in order_section.splitlines() if "Shalelu" in l)
        thaelion_line = next(l for l in order_section.splitlines() if "Thaelion" in l)
        assert "→" not in shalelu_line,  "Unconscious combatant should not be current"
        assert "→" in thaelion_line,     "Highest active combatant should be current"

    # AC-007 — [CURRENT HP] always injected
    def test_current_hp_block_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert "[CURRENT HP]" in system_content

    def test_current_hp_contains_all_combatants(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert "Shalelu" in system_content
        assert "Thaelion" in system_content
        assert "Goblin 1" in system_content

    def test_current_hp_shows_hp_values(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        hp_block_start = system_content.index("[CURRENT HP]")
        hp_section = system_content[hp_block_start:].split("\n\n")[0]
        assert "18/24" in hp_section  # Shalelu

    # AC-008 — [PC COMBAT STATS] for all PCs
    def test_pc_combat_stats_thaelion(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert "PC Stats — Thaelion" in system_content

    def test_pc_combat_stats_yanyeeku(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert "PC Stats — Yanyeeku" in system_content

    # AC-009 — [ACTIVE CONDITIONS] only when non-empty
    def test_no_active_conditions_block_when_empty(self):
        session = self._session_in_combat()  # default combatants have no conditions
        system_content, _ = _call(session)
        assert "[ACTIVE CONDITIONS]" not in system_content

    def test_active_conditions_block_present_when_set(self):
        combat = CombatState(
            round=2,
            combatants=[
                Combatant(name="Shalelu",  hp_current=18, hp_max=24, ac=17, initiative=14),
                Combatant(name="Goblin 1", hp_current=3,  hp_max=5,  ac=13, initiative=5,
                          conditions=["prone", "shaken"]),
            ],
        )
        session = self._session_in_combat(combat_state=combat)
        system_content, _ = _call(session)
        assert "[ACTIVE CONDITIONS]" in system_content
        assert "Goblin 1" in system_content
        assert "prone" in system_content
        assert "shaken" in system_content

    def test_active_conditions_only_lists_affected_combatants(self):
        combat = CombatState(
            round=2,
            combatants=[
                Combatant(name="Shalelu",  hp_current=18, hp_max=24, ac=17, initiative=14),
                Combatant(name="Goblin 1", hp_current=3,  hp_max=5,  ac=13, initiative=5,
                          conditions=["prone"]),
            ],
        )
        session = self._session_in_combat(combat_state=combat)
        system_content, _ = _call(session)
        cond_start = system_content.index("[ACTIVE CONDITIONS]")
        cond_section = system_content[cond_start:].split("\n\n")[0]
        # Shalelu has no conditions — she should not appear in the conditions block
        assert "Shalelu" not in cond_section

    # AC-010 — _COMBAT_SECTION_SPECS used, not narrative specs
    def test_combat_section_specs_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert "COMBAT MODE" in system_content

    def test_narrative_spec_not_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        # _NARRATIVE_SPEC's distinctive phrasing should not appear
        assert "2–4 paragraphs" not in system_content

    def test_generate_spec_not_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert _GENERATE_SPEC[:40] not in system_content

    def test_deltas_spec_not_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert _DELTAS_SPEC[:40] not in system_content

    def test_roll_spec_not_present(self):
        session = self._session_in_combat()
        system_content, _ = _call(session)
        assert _ROLL_SPEC[:40] not in system_content

    # AC-011 — normal narrative path unchanged (regression guard)
    def test_no_combat_blocks_in_narrative_mode(self):
        session = _make_session(
            pc_profiles=_make_pc_profiles(),
            messages=[{"role": "user", "content": "I look around."}],
        )
        system_content, _ = _call(session)
        assert "[INITIATIVE ORDER" not in system_content
        assert "[CURRENT HP]" not in system_content
        assert "[PC COMBAT STATS]" not in system_content
        assert "COMBAT MODE" not in system_content

    def test_narrative_mode_starts_with_system_prompt(self):
        session = _make_session(
            messages=[{"role": "user", "content": "I look around."}],
        )
        system_content, _ = _call(session)
        assert system_content.startswith("BASE SYSTEM PROMPT")

    def test_narrative_mode_npc_detection_called(self):
        session = _make_session(
            messages=[{"role": "user", "content": "I talk to Ameiko."}],
        )
        npc_idx = _no_index()
        _call(session, npc_idx=npc_idx)
        npc_idx.detect.assert_called_once()

    # AC-012 — combat rules lookup still runs
    def test_combat_rules_lookup_called_in_combat(self):
        session = self._session_in_combat(
            messages=[{"role": "user", "content": "I move away — does that trigger attacks of opportunity?"}]
        )
        crules_idx = _no_index()
        _call(session, crules_idx=crules_idx)
        crules_idx.detect.assert_called_once()

    def test_combat_rules_content_injected_when_matched(self):
        session = self._session_in_combat(
            messages=[{"role": "user", "content": "I move away — does that trigger attacks of opportunity?"}]
        )
        crules_idx = MagicMock()
        crules_idx.detect.return_value = MagicMock(rule_name="attacks_of_opportunity", matched_trigger="attacks of opportunity")
        crules_idx.format_context.return_value = "## AoO Rule\nMovement provokes."
        system_content, _ = _call(session, crules_idx=crules_idx)
        assert "AoO Rule" in system_content

    # AC-013 — active events still injected
    def test_active_event_content_in_combat_mode(self):
        event = ActiveEvent(
            event_id="goblin_attack_starts",
            content="## Goblin Raid\nGoblins pour through the gate.",
            turns_remaining=2,
        )
        session = self._session_in_combat(active_events=[event])
        system_content, _ = _call(session)
        assert "goblin_attack_starts" in system_content

    def test_active_event_in_context_info(self):
        event = ActiveEvent(
            event_id="goblin_attack_starts",
            content="## Goblin Raid",
            turns_remaining=2,
        )
        session = self._session_in_combat(active_events=[event])
        _, ctx = _call(session)
        assert "goblin_attack_starts" in ctx["active_events"]


# ── Pre-combat branch (events with %%COMBAT%% requirement) ───────────────────

class TestPreCombatBranch:
    """When active events contain %%COMBAT%% but combat_state is None,
    _inject_context must use the combat base prompt and skip narrative injections."""

    def _pre_combat_session(self, event_content=None, **kwargs):
        content = event_content or (
            "## Goblin Raid — Wave 1\n"
            "### REQUIRED — Combat tracker\n"
            "Write a `%%COMBAT%%` block every turn.\n"
        )
        event = ActiveEvent(
            event_id="goblin_attack_starts",
            content=content,
            turns_remaining=3,
        )
        return _make_session(
            pc_profiles=_make_pc_profiles(),
            combat_state=None,
            active_events=[event],
            messages=[{"role": "user", "content": "What is happening?"}],
            **kwargs,
        )

    def test_uses_combat_base_not_session_system_prompt(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert not system_content.startswith("BASE SYSTEM PROMPT")

    def test_contains_combat_conduct(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "COMBAT CONDUCT" in system_content

    def test_no_gm_style(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "GM STYLE" not in system_content

    def test_no_current_situation(self):
        # Boot context should not appear — base prompt omits the situation block
        session = self._pre_combat_session(system_prompt="BOOT CONTEXT AND STUFF")
        system_content, _ = _call(session)
        assert "BOOT CONTEXT AND STUFF" not in system_content

    def test_no_narrative_section_specs(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "2–4 paragraphs" not in system_content
        assert "REQUIRED for every NEW named character" not in system_content

    def test_no_format_example(self):
        # Even on turn 1, format example must not appear
        session = self._pre_combat_session()
        session.messages = [{"role": "user", "content": "Goblins!"}]
        system_content, _ = _call(session)
        assert _FORMAT_EXAMPLE[:40] not in system_content

    def test_no_npc_detection(self):
        session = self._pre_combat_session()
        npc_idx = _no_index()
        _call(session, npc_idx=npc_idx)
        npc_idx.detect.assert_not_called()

    def test_no_skill_detection(self):
        session = self._pre_combat_session()
        skill_idx = _no_index()
        _call(session, skill_idx=skill_idx)
        skill_idx.detect.assert_not_called()

    def test_no_location_detection(self):
        session = self._pre_combat_session()
        loc_idx = _no_index()
        _call(session, loc_idx=loc_idx)
        loc_idx.detect.assert_not_called()

    def test_event_content_injected(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "goblin_attack_starts" in system_content

    def test_round1_spec_present(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "round: 1" in system_content

    def test_party_roster_present(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "Thaelion" in system_content
        assert "Yanyeeku" in system_content

    def test_pc_combat_stats_present(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "PC Stats — Thaelion" in system_content

    def test_no_initiative_order(self):
        # No combatants yet — initiative block must not appear
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "[INITIATIVE ORDER" not in system_content

    def test_no_current_hp_block(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "[CURRENT HP]" not in system_content

    def test_combat_section_specs_present(self):
        session = self._pre_combat_session()
        system_content, _ = _call(session)
        assert "COMBAT MODE" in system_content

    def test_context_info_npc_is_none(self):
        session = self._pre_combat_session()
        _, ctx = _call(session)
        assert ctx["npc"] is None

    def test_event_id_in_context_info(self):
        session = self._pre_combat_session()
        _, ctx = _call(session)
        assert "goblin_attack_starts" in ctx["active_events"]

    def test_non_combat_event_still_uses_narrative_path(self):
        """An event WITHOUT %%COMBAT%% in its content must not trigger combat mode."""
        pure_narrative_event = ActiveEvent(
            event_id="aldern_approaches",
            content="## Aldern Foxglove\nHe strides across the square.",
            turns_remaining=2,
        )
        session = _make_session(
            pc_profiles=_make_pc_profiles(),
            combat_state=None,
            active_events=[pure_narrative_event],
            messages=[{"role": "user", "content": "I look around."}],
        )
        system_content, _ = _call(session)
        # Narrative path → session.system_prompt used as base
        assert system_content.startswith("BASE SYSTEM PROMPT")
        # Non-combat event still gets round-1 hint appended
        assert "round: 1" in system_content

    def test_combat_rules_lookup_runs_in_pre_combat(self):
        session = self._pre_combat_session()
        session.messages = [{"role": "user", "content": "Does moving provoke attacks of opportunity?"}]
        crules_idx = _no_index()
        _call(session, crules_idx=crules_idx)
        crules_idx.detect.assert_called_once()


# ── Token size comparison (AC-002) ───────────────────────────────────────────
# The key ratio test lives in TestBuildCombatSystemPrompt.test_shorter_than_slim_prompt.
# Here we only verify that the combat branch does not *add* the large narrative
# section blocks (NARRATIVE_SPEC, GENERATE_SPEC, etc.) which would widen the gap.

class TestCombatPromptDoesNotAddNarrativeBlocks:
    """Combat inject_context must not grow by adding narrative-only specs."""

    def test_combat_content_has_no_narrative_spec_text(self):
        session = _make_session(
            pc_profiles=_make_pc_profiles(),
            combat_state=_make_combat_state(),
            messages=[{"role": "user", "content": "I attack."}],
        )
        combat_content, _ = _call(session)
        assert "2–4 paragraphs" not in combat_content, (
            "_NARRATIVE_SPEC '2–4 paragraphs' should not appear in combat system_content"
        )

    def test_combat_content_has_no_generate_spec_text(self):
        session = _make_session(
            pc_profiles=_make_pc_profiles(),
            combat_state=_make_combat_state(),
            messages=[{"role": "user", "content": "I attack."}],
        )
        combat_content, _ = _call(session)
        # _GENERATE_SPEC unique phrase
        assert "REQUIRED for every NEW named character" not in combat_content


# ── B-C03a regression — HP conduct rule must be round-conditional ─────────────

class TestCombatPromptHPConductRule:
    """B-C03a: _build_combat_system_prompt must NOT unconditionally forbid hp: on round 1.

    The old wording 'Never write hp: for existing combatants' caused the LLM to omit
    HP on round 1, leaving every combatant at 0/0. The fix makes the rule conditional:
    MUST include HP on round 1, NEVER on round 2+.
    """

    def _prompt(self):
        session = _make_session(pc_profiles=_make_pc_profiles())
        return _build_combat_system_prompt(session)

    def test_round1_hp_requirement_present(self):
        prompt = self._prompt()
        assert "Round 1" in prompt or "round 1" in prompt.lower(), (
            "Combat prompt must mention round 1 HP requirement"
        )

    def test_must_include_hp_on_round1(self):
        prompt = self._prompt()
        # The prompt must instruct LLM to INCLUDE hp: on round 1
        assert "MUST include hp" in prompt or "must include hp" in prompt.lower(), (
            "Combat prompt must explicitly require hp: on round 1"
        )

    def test_never_write_hp_scoped_to_round2(self):
        prompt = self._prompt()
        # The 'never write hp' prohibition must be qualified to round 2+
        assert "Round 2" in prompt or "round 2" in prompt.lower() or "2+" in prompt, (
            "The hp prohibition must be scoped to round 2+ not all rounds"
        )

    def test_old_unconditional_hp_prohibition_absent(self):
        prompt = self._prompt()
        # This was the exact old wording that caused the bug — must not reappear
        assert "Never write hp: for existing combatants" not in prompt, (
            "Old unconditional HP prohibition must not be present — it suppresses HP on round 1"
        )
