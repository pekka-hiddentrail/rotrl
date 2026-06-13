"""
tests/test_prompt_builder.py
────────────────────────────
Unit tests for api/context/prompt_builder.py — Phase 1.

Covers:
  AC-001  classify_scene — all 5 priority signals
  AC-002  ContextSlot dataclass fields and defaults
  AC-003  SCENE_SLOTS structure (4 scene types, no combat, required slots)
  AC-004  NPC section filters per scene type
  AC-005  PromptBuilder.assemble() return shape
  AC-006  token_budget enforcement with line-boundary truncation
  AC-007  Slot hierarchy preserved in BuiltSlot list
  AC-008  Combat scene type raises ValueError
  AC-009  Optional slot omitted when data source is empty
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest

from api.context.prompt_builder import (
    SCENE_SLOTS,
    AssembledPrompt,
    BuiltSlot,
    ContextSlot,
    PromptBuilder,
    _truncate_at_line_boundary,
    classify_scene,
)


# ─────────────────────────────────────────────────────────────────────────────
# Minimal session / event stubs for testing (no import of GameSession)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _FakeCombatState:
    round: int = 1
    combatants: list = field(default_factory=list)
    current_actor: Optional[str] = None
    known_zones: list = field(default_factory=list)


@dataclass
class _FakeEventRuntime:
    active_event_id: Optional[str] = None


@dataclass
class _FakeSession:
    """Minimal stand-in for GameSession with the fields classify_scene() and
    PromptBuilder need."""
    combat_state: Optional[_FakeCombatState] = None
    scene_npcs: list = field(default_factory=list)
    scene_locations: list = field(default_factory=list)
    current_location_id: str = ""
    event_runtime: _FakeEventRuntime = field(default_factory=_FakeEventRuntime)
    active_events: list = field(default_factory=list)
    system_prompt: str = "You are a PF1e GM."
    messages: list = field(default_factory=list)
    pc_profiles: dict = field(default_factory=dict)


def _make_event_index_mock(event_type: str = "combat", event_id: str = "goblin_attack"):
    """Return a mock EventIndex that returns an entry with the given event_type."""
    entry = MagicMock()
    entry.event_type = event_type
    idx = MagicMock()
    idx.get.return_value = entry
    return idx, event_id


# ─────────────────────────────────────────────────────────────────────────────
# _truncate_at_line_boundary
# ─────────────────────────────────────────────────────────────────────────────

class TestTruncateAtLineBoundary:
    def test_short_text_unchanged(self):
        text = "line one\nline two\n"
        assert _truncate_at_line_boundary(text, 200) == text

    def test_exact_fit_unchanged(self):
        text = "abc"
        assert _truncate_at_line_boundary(text, 3) == text

    def test_truncates_at_newline(self):
        text = "line one\nline two\nline three"
        result = _truncate_at_line_boundary(text, 10)
        # "line one\n" is 9 chars — window is "line one\n" → cut at last \n = 8
        assert result == "line one"
        assert len(result) <= 10

    def test_no_newline_in_window_returns_full(self):
        # No newline in the first 5 chars — must not truncate to empty
        text = "abcdefghij"
        result = _truncate_at_line_boundary(text, 5)
        assert result == text  # no cut to avoid losing all content

    def test_preserves_content_exactly_at_boundary(self):
        # max_chars=8: window = "aaa\nbbb\n" (8 chars), rfind("\n") = 7 → "aaa\nbbb"
        text = "aaa\nbbb\nccc"
        result = _truncate_at_line_boundary(text, 8)
        assert result == "aaa\nbbb"

    def test_cuts_at_last_newline_in_window(self):
        # max_chars=7: window = "aaa\nbbb" (7 chars), rfind("\n") = 3 → "aaa"
        text = "aaa\nbbb\nccc"
        result = _truncate_at_line_boundary(text, 7)
        assert result == "aaa"
        assert len(result) <= 7


# ─────────────────────────────────────────────────────────────────────────────
# AC-001 — classify_scene
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyScene:
    def test_combat_state_set_returns_combat(self):
        session = _FakeSession(combat_state=_FakeCombatState())
        assert classify_scene(session) == "combat"

    def test_combat_event_type_returns_combat(self):
        session = _FakeSession()
        session.event_runtime.active_event_id = "goblin_attack"
        idx, _ = _make_event_index_mock(event_type="combat", event_id="goblin_attack")
        assert classify_scene(session, event_index=idx) == "combat"

    def test_non_combat_event_not_classified_as_combat(self):
        session = _FakeSession()
        session.event_runtime.active_event_id = "festival_social_phase"
        idx, _ = _make_event_index_mock(event_type="aftermath", event_id="festival_social_phase")
        assert classify_scene(session, event_index=idx) == "social"

    def test_scene_npcs_returns_social(self):
        session = _FakeSession(scene_npcs=["Ameiko Kaijitsu"])
        assert classify_scene(session) == "social"

    def test_scene_locations_no_npcs_returns_exploration(self):
        session = _FakeSession(scene_locations=["The Rusty Dragon"])
        assert classify_scene(session) == "exploration"

    def test_empty_session_returns_social_default(self):
        session = _FakeSession()
        assert classify_scene(session) == "social"

    def test_combat_state_takes_priority_over_npcs(self):
        session = _FakeSession(
            combat_state=_FakeCombatState(),
            scene_npcs=["Ameiko Kaijitsu"],
        )
        assert classify_scene(session) == "combat"

    def test_npcs_take_priority_over_locations(self):
        session = _FakeSession(
            scene_npcs=["Abstalar Zantus"],
            scene_locations=["Cathedral"],
        )
        assert classify_scene(session) == "social"

    def test_no_event_index_skips_event_type_check(self):
        # Without event_index, even an active event_id doesn't yield combat.
        session = _FakeSession()
        session.event_runtime.active_event_id = "goblin_attack"
        assert classify_scene(session, event_index=None) == "social"

    def test_event_index_unknown_id_returns_none_safely(self):
        session = _FakeSession()
        session.event_runtime.active_event_id = "nonexistent"
        idx = MagicMock()
        idx.get.return_value = None
        # Should not raise; falls through to default "social"
        assert classify_scene(session, event_index=idx) == "social"


# ─────────────────────────────────────────────────────────────────────────────
# AC-002 — ContextSlot dataclass
# ─────────────────────────────────────────────────────────────────────────────

class TestContextSlotDataclass:
    def test_required_fields_present(self):
        slot = ContextSlot(
            key="npc_profiles",
            label="NPC Profiles",
            source="npc_extractor",
            sections=["Personality"],
            token_budget=3_000,
            scene_types=["social"],
        )
        assert slot.key == "npc_profiles"
        assert slot.label == "NPC Profiles"
        assert slot.source == "npc_extractor"
        assert slot.sections == ["Personality"]
        assert slot.token_budget == 3_000
        assert slot.scene_types == ["social"]

    def test_parent_defaults_to_none(self):
        slot = ContextSlot(
            key="gm_instructions", label="GM", source="gm_instructions",
            sections=[], token_budget=2000, scene_types=["social"],
        )
        assert slot.parent is None

    def test_optional_defaults_to_false(self):
        slot = ContextSlot(
            key="history", label="History", source="history",
            sections=[], token_budget=4000, scene_types=["social"],
        )
        assert slot.optional is False

    def test_parent_and_optional_set(self):
        slot = ContextSlot(
            key="npc_profiles", label="NPC Profiles", source="npc_extractor",
            sections=[], token_budget=3000, scene_types=["social"],
            parent="encounter_spec", optional=True,
        )
        assert slot.parent == "encounter_spec"
        assert slot.optional is True


# ─────────────────────────────────────────────────────────────────────────────
# AC-003 — SCENE_SLOTS structure
# ─────────────────────────────────────────────────────────────────────────────

class TestSceneSlotsStructure:
    REQUIRED_SCENE_TYPES = {"social", "exploration", "dungeon", "skill_challenge"}
    REQUIRED_SLOT_KEYS = {"gm_instructions", "party", "history"}

    def test_contains_all_required_scene_types(self):
        for st in self.REQUIRED_SCENE_TYPES:
            assert st in SCENE_SLOTS, f"Missing scene type: {st}"

    def test_does_not_contain_combat(self):
        assert "combat" not in SCENE_SLOTS

    def test_every_scene_type_has_required_slots(self):
        for scene_type, slots in SCENE_SLOTS.items():
            slot_keys = {s.key for s in slots}
            for required in self.REQUIRED_SLOT_KEYS:
                assert required in slot_keys, (
                    f"Scene '{scene_type}' missing required slot '{required}'"
                )

    def test_social_has_npc_profiles_slot(self):
        keys = {s.key for s in SCENE_SLOTS["social"]}
        assert "npc_profiles" in keys

    def test_exploration_has_location_slot(self):
        keys = {s.key for s in SCENE_SLOTS["exploration"]}
        assert "location" in keys

    def test_dungeon_has_location_slot(self):
        keys = {s.key for s in SCENE_SLOTS["dungeon"]}
        assert "location" in keys

    def test_skill_challenge_has_skill_rules_slot(self):
        keys = {s.key for s in SCENE_SLOTS["skill_challenge"]}
        assert "skill_rules" in keys

    def test_all_slots_have_non_empty_key_and_label(self):
        for scene_type, slots in SCENE_SLOTS.items():
            for slot in slots:
                assert slot.key, f"Empty key in {scene_type}"
                assert slot.label, f"Empty label for {slot.key} in {scene_type}"

    def test_all_slots_have_positive_token_budget(self):
        for scene_type, slots in SCENE_SLOTS.items():
            for slot in slots:
                assert slot.token_budget > 0, (
                    f"Non-positive token_budget on {slot.key} in {scene_type}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# AC-004 — NPC section filters per scene type
# ─────────────────────────────────────────────────────────────────────────────

class TestNpcSectionFilters:
    def _npc_slot(self, scene_type: str) -> ContextSlot:
        slots = SCENE_SLOTS[scene_type]
        matches = [s for s in slots if s.key == "npc_profiles"]
        assert matches, f"No npc_profiles slot in {scene_type}"
        return matches[0]

    def test_social_sections(self):
        slot = self._npc_slot("social")
        assert slot.sections == ["Personality", "GM Notes", "Social Checks"]

    def test_exploration_sections(self):
        slot = self._npc_slot("exploration")
        assert slot.sections == ["Personality", "Appearance"]

    def test_dungeon_sections(self):
        slot = self._npc_slot("dungeon")
        assert slot.sections == ["Appearance", "State Handling"]

    def test_skill_challenge_sections(self):
        slot = self._npc_slot("skill_challenge")
        assert slot.sections == ["Social Checks", "Secrets"]

    def test_npc_profiles_source_is_npc_extractor(self):
        for scene_type in ("social", "exploration", "dungeon", "skill_challenge"):
            slot = self._npc_slot(scene_type)
            assert slot.source == "npc_extractor"


# ─────────────────────────────────────────────────────────────────────────────
# AC-005 — PromptBuilder.assemble() return shape
# ─────────────────────────────────────────────────────────────────────────────

class TestAssembleReturnShape:
    def test_returns_assembled_prompt(self):
        session = _FakeSession(system_prompt="GM authority text.")
        result = PromptBuilder(session).assemble()
        assert isinstance(result, AssembledPrompt)

    def test_assembled_prompt_has_content_str(self):
        session = _FakeSession(system_prompt="You are a GM.")
        result = PromptBuilder(session).assemble()
        assert isinstance(result.content, str)

    def test_assembled_prompt_has_slots_list(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble()
        assert isinstance(result.slots, list)
        assert all(isinstance(s, BuiltSlot) for s in result.slots)

    def test_scene_type_recorded(self):
        session = _FakeSession(scene_npcs=["Ameiko Kaijitsu"])
        result = PromptBuilder(session).assemble()
        assert result.scene_type == "social"

    def test_scene_type_override_respected(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="exploration")
        assert result.scene_type == "exploration"

    def test_slots_count_matches_scene_slot_config(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="social")
        assert len(result.slots) == len(SCENE_SLOTS["social"])

    def test_built_slot_fields(self):
        session = _FakeSession(system_prompt="GM instructions here.")
        result = PromptBuilder(session).assemble()
        for slot in result.slots:
            assert hasattr(slot, "key")
            assert hasattr(slot, "label")
            assert hasattr(slot, "parent")
            assert hasattr(slot, "token_count")
            assert hasattr(slot, "content")
            assert hasattr(slot, "included")
            assert isinstance(slot.token_count, int)
            assert isinstance(slot.included, bool)

    def test_gm_instructions_content_in_assembled(self):
        session = _FakeSession(system_prompt="You are a PF1e GM. Never invent lore.")
        result = PromptBuilder(session).assemble()
        assert "You are a PF1e GM" in result.content

    def test_included_slot_token_count_matches_content_length(self):
        session = _FakeSession(system_prompt="GM text here.")
        result = PromptBuilder(session).assemble()
        gm_slot = next(s for s in result.slots if s.key == "gm_instructions")
        if gm_slot.included:
            assert gm_slot.token_count == len(gm_slot.content)


# ─────────────────────────────────────────────────────────────────────────────
# AC-006 — token_budget enforced
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenBudgetEnforcement:
    def test_gm_instructions_exceeding_budget_is_truncated(self):
        """Override a slot's token_budget to a small value and verify truncation."""
        # Patch the SCENE_SLOTS social gm_instructions slot temporarily
        from api.context import prompt_builder as pb

        original_slots = pb.SCENE_SLOTS["social"]
        tiny_slot = ContextSlot(
            key="gm_instructions", label="GM", source="gm_instructions",
            sections=[], token_budget=20, scene_types=["social"],
        )
        other_slots = [s for s in original_slots if s.key != "gm_instructions"]
        pb.SCENE_SLOTS["social"] = [tiny_slot] + other_slots

        try:
            long_text = "Line one\nLine two\nLine three\nLine four\n"
            session = _FakeSession(system_prompt=long_text)
            result = PromptBuilder(session).assemble()
            gm_slot = next(s for s in result.slots if s.key == "gm_instructions")
            if gm_slot.included:
                assert gm_slot.token_count <= 20
                assert len(gm_slot.content) <= 20
        finally:
            pb.SCENE_SLOTS["social"] = original_slots

    def test_truncation_at_line_boundary(self):
        """Directly verify _truncate_at_line_boundary in the assembly path."""
        text = "aaa\nbbb\nccc\nddd\neee"
        result = _truncate_at_line_boundary(text, 8)
        # "aaa\nbbb" is 7 chars; window[:8] = "aaa\nbbb\n" → last \n at pos 7 → "aaa\nbbb"
        assert "\n" not in result or result.endswith(
            result.split("\n")[-1]
        ), "Truncation split a line mid-content"
        assert len(result) <= 8

    def test_content_within_budget_not_truncated(self):
        text = "Short."
        assert _truncate_at_line_boundary(text, 1_000) == text


# ─────────────────────────────────────────────────────────────────────────────
# AC-007 — Slot hierarchy preserved in BuiltSlot list
# ─────────────────────────────────────────────────────────────────────────────

class TestSlotHierarchy:
    def test_gm_instructions_has_no_parent(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="social")
        gm_slot = next(s for s in result.slots if s.key == "gm_instructions")
        assert gm_slot.parent is None

    def test_npc_profiles_has_parent_in_social(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="social")
        npc_slot = next(s for s in result.slots if s.key == "npc_profiles")
        assert npc_slot.parent == "encounter_spec"

    def test_npc_profiles_has_parent_in_exploration(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="exploration")
        npc_slot = next(s for s in result.slots if s.key == "npc_profiles")
        assert npc_slot.parent == "encounter_spec"

    def test_zones_has_parent_in_social(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="social")
        zones_slot = next((s for s in result.slots if s.key == "zones"), None)
        if zones_slot is not None:
            assert zones_slot.parent == "encounter_spec"

    def test_child_appears_after_parent_in_slot_list(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="social")
        keys = [s.key for s in result.slots]
        enc_idx = keys.index("encounter_spec")
        npc_idx = keys.index("npc_profiles")
        assert npc_idx > enc_idx, "npc_profiles (child) should appear after encounter_spec (parent)"

    def test_slot_keys_match_scene_slots_order(self):
        session = _FakeSession()
        result = PromptBuilder(session).assemble(scene_type_override="social")
        expected_keys = [s.key for s in SCENE_SLOTS["social"]]
        actual_keys = [s.key for s in result.slots]
        assert actual_keys == expected_keys


# ─────────────────────────────────────────────────────────────────────────────
# AC-008 — Combat scene type raises ValueError
# ─────────────────────────────────────────────────────────────────────────────

class TestCombatRaisesValueError:
    def test_assemble_with_combat_state_raises(self):
        session = _FakeSession(combat_state=_FakeCombatState())
        with pytest.raises(ValueError, match="_build_combat_system_prompt"):
            PromptBuilder(session).assemble()

    def test_assemble_with_scene_type_override_combat_raises(self):
        session = _FakeSession()
        with pytest.raises(ValueError, match="_build_combat_system_prompt"):
            PromptBuilder(session).assemble(scene_type_override="combat")

    def test_invalid_scene_type_override_raises(self):
        session = _FakeSession()
        with pytest.raises(ValueError, match="Invalid scene_type_override"):
            PromptBuilder(session).assemble(scene_type_override="fantasy_combat")

    def test_error_message_references_combat_function(self):
        session = _FakeSession(combat_state=_FakeCombatState())
        with pytest.raises(ValueError) as exc_info:
            PromptBuilder(session).assemble()
        assert "_build_combat_system_prompt" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# AC-009 — Optional slots omitted when data source is empty
# ─────────────────────────────────────────────────────────────────────────────

class TestOptionalSlotOmission:
    def test_npc_profiles_included_false_when_no_scene_npcs(self):
        session = _FakeSession(scene_npcs=[])
        result = PromptBuilder(session).assemble(scene_type_override="social")
        npc_slot = next(s for s in result.slots if s.key == "npc_profiles")
        assert npc_slot.included is False

    def test_npc_profiles_not_in_content_when_no_scene_npcs(self):
        """The NPC header should not appear in the assembled content."""
        session = _FakeSession(system_prompt="GM text.", scene_npcs=[])
        result = PromptBuilder(session).assemble(scene_type_override="social")
        npc_slot = next(s for s in result.slots if s.key == "npc_profiles")
        assert npc_slot.content == ""

    def test_encounter_spec_included_false_when_no_active_events(self):
        session = _FakeSession(active_events=[])
        result = PromptBuilder(session).assemble(scene_type_override="social")
        enc_slot = next(s for s in result.slots if s.key == "encounter_spec")
        assert enc_slot.included is False

    def test_required_slot_included_even_when_empty(self):
        """Non-optional slots are always included even if content is empty."""
        session = _FakeSession(system_prompt="", messages=[])
        result = PromptBuilder(session).assemble(scene_type_override="social")
        history_slot = next(s for s in result.slots if s.key == "history")
        # history is non-optional — included=True even when messages is empty
        assert history_slot.included is True

    def test_included_false_slot_has_zero_token_count(self):
        session = _FakeSession(scene_npcs=[])
        result = PromptBuilder(session).assemble(scene_type_override="social")
        for slot in result.slots:
            if not slot.included:
                assert slot.token_count == 0

    def test_no_error_raised_when_optional_slot_empty(self):
        session = _FakeSession()  # no npcs, no events, no locations
        # Should not raise
        result = PromptBuilder(session).assemble(scene_type_override="social")
        assert isinstance(result, AssembledPrompt)


# ─────────────────────────────────────────────────────────────────────────────
# NPC extractor integration (AC-004 live path — requires real NPC files)
# ─────────────────────────────────────────────────────────────────────────────

class TestNpcExtractorFetch:
    """Tests that use tmp_path to create minimal NPC base.md files."""

    def _write_npc(self, npc_root: Path, name: str, sections: dict[str, str]) -> None:
        slug = name.lower().replace(" ", "_")
        npc_dir = npc_root / slug
        npc_dir.mkdir(parents=True)
        lines = [f"# {name}", ""]
        for section_name, body in sections.items():
            lines += [f"## {section_name}", body, ""]
        lines += ["<!-- REFERENCE -->", "**Tier:** Test"]
        (npc_dir / "base.md").write_text("\n".join(lines), encoding="utf-8")

    def test_social_sections_fetched(self, tmp_path):
        from api.context import prompt_builder as pb
        from api.context import npc_extractor as ne

        npc_root = tmp_path / "01_npcs"
        self._write_npc(npc_root, "Test Npc", {
            "Personality": "Test personality text.",
            "GM Notes": "GM note text.",
            "Social Checks": "Diplomacy DC 15.",
            "Appearance": "Tall and thin.",
        })

        # Monkey-patch _NPC_ROOT for this test
        original_root = ne._NPC_ROOT
        ne._NPC_ROOT = npc_root
        try:
            session = _FakeSession(scene_npcs=["Test Npc"])
            builder = PromptBuilder(session)
            slot = next(s for s in SCENE_SLOTS["social"] if s.key == "npc_profiles")
            content = builder._fetch(slot)
            assert "Test personality text." in content
            assert "GM note text." in content
            assert "Diplomacy DC 15." in content
            # Appearance should NOT be in social fetch
            assert "Tall and thin." not in content
        finally:
            ne._NPC_ROOT = original_root

    def test_exploration_sections_fetched(self, tmp_path):
        from api.context import npc_extractor as ne

        npc_root = tmp_path / "01_npcs"
        self._write_npc(npc_root, "Explorer Npc", {
            "Personality": "Wandering explorer.",
            "Appearance": "Weathered face.",
            "GM Notes": "Never reveal this.",
        })

        original_root = ne._NPC_ROOT
        ne._NPC_ROOT = npc_root
        try:
            session = _FakeSession(scene_npcs=["Explorer Npc"])
            builder = PromptBuilder(session)
            slot = next(s for s in SCENE_SLOTS["exploration"] if s.key == "npc_profiles")
            content = builder._fetch(slot)
            assert "Wandering explorer." in content
            assert "Weathered face." in content
            # GM Notes should NOT be in exploration fetch
            assert "Never reveal this." not in content
        finally:
            ne._NPC_ROOT = original_root

    def test_unknown_npc_silently_skipped(self):
        """FileNotFoundError for an unknown NPC should not raise."""
        session = _FakeSession(scene_npcs=["Nonexistent McFakename"])
        builder = PromptBuilder(session)
        slot = next(s for s in SCENE_SLOTS["social"] if s.key == "npc_profiles")
        content = builder._fetch(slot)
        assert content == ""

    def test_multiple_npcs_combined(self, tmp_path):
        from api.context import npc_extractor as ne

        npc_root = tmp_path / "01_npcs"
        self._write_npc(npc_root, "Alice", {"Personality": "Friendly."})
        self._write_npc(npc_root, "Bob", {"Personality": "Grumpy."})

        original_root = ne._NPC_ROOT
        ne._NPC_ROOT = npc_root
        try:
            session = _FakeSession(scene_npcs=["Alice", "Bob"])
            builder = PromptBuilder(session)
            slot = next(s for s in SCENE_SLOTS["social"] if s.key == "npc_profiles")
            content = builder._fetch(slot)
            assert "Friendly." in content
            assert "Grumpy." in content
        finally:
            ne._NPC_ROOT = original_root


# ─────────────────────────────────────────────────────────────────────────────
# Party and history fetch
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchHelpers:
    def test_party_profiles_included_in_assembled(self):
        session = _FakeSession(pc_profiles={
            "ani": {"narrative": "## PC — Ani\nWarpriest.", "mechanical": ""},
        })
        result = PromptBuilder(session).assemble()
        party_slot = next(s for s in result.slots if s.key == "party")
        assert "Warpriest." in party_slot.content

    def test_history_messages_in_assembled(self):
        session = _FakeSession(messages=[
            {"role": "user", "content": "I look around the room."},
            {"role": "assistant", "content": "You see dusty shelves."},
        ])
        result = PromptBuilder(session).assemble()
        hist_slot = next(s for s in result.slots if s.key == "history")
        assert "look around" in hist_slot.content
        assert "dusty shelves" in hist_slot.content

    def test_system_messages_excluded_from_history(self):
        session = _FakeSession(messages=[
            {"role": "system", "content": "You are a GM."},
            {"role": "user", "content": "Hello."},
        ])
        result = PromptBuilder(session).assemble()
        hist_slot = next(s for s in result.slots if s.key == "history")
        assert "You are a GM." not in hist_slot.content
        assert "Hello." in hist_slot.content

    def test_active_participants_slot(self):
        session = _FakeSession(scene_npcs=["Ameiko Kaijitsu", "Belor Hemlock"])
        result = PromptBuilder(session).assemble()
        ap_slot = next(
            (s for s in result.slots if s.key == "active_participants"), None
        )
        if ap_slot and ap_slot.included:
            assert "Ameiko Kaijitsu" in ap_slot.content
            assert "Belor Hemlock" in ap_slot.content
