"""Enemy-turn action_type field — backend tests.

Spec: specs/enemy-action-type.feature
Covers: AC-001 through AC-007
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest

import api.session_manager as sm
from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _build_enemy_turn_system,
    _parse_action_block,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _session() -> GameSession:
    s = GameSession(
        id="s1",
        session_number=1,
        model="test-model",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=True,
        pc_profiles={
            "ani": {"combat_stats": {"name": "Ani"}},
        },
    )
    s.combat_state = CombatState(
        round=1,
        current_actor="Goblin Warrior 1",
        combatants=[
            Combatant(name="Ani",              hp_current=9, hp_max=9, ac=15, initiative=12),
            Combatant(
                name="Goblin Warrior 1",
                hp_current=5, hp_max=5, ac=16, initiative=10,
                attacks={"melee": ["dogslicer"], "ranged": ["shortbow"]},
            ),
        ],
    )
    return s


def _blk(lines: str) -> str:
    """Wrap a set of key: value lines in an %%ACTION%% marker."""
    return f"%%ACTION%%\n{lines}"


# ── AC-001 — action_type field is extracted when present ──────────────────────

class TestActionTypeExtraction:
    """AC-001: parser reads the action_type field."""

    def test_extracts_standard(self):
        result = _parse_action_block(_blk("action: attack\naction_type: standard\ntarget: Ani"))
        assert result is not None
        assert result["action_type"] == "standard"

    def test_extracts_move(self):
        result = _parse_action_block(_blk("action: move\naction_type: move\nmovement: behind pillar"))
        assert result is not None
        assert result["action_type"] == "move"

    def test_extracts_full(self):
        result = _parse_action_block(_blk("action: attack\naction_type: full\ntarget: Ani"))
        assert result is not None
        assert result["action_type"] == "full"

    def test_extracts_swift(self):
        result = _parse_action_block(_blk("action: use_ability\naction_type: swift\nability: rage"))
        assert result is not None
        assert result["action_type"] == "swift"

    def test_extracts_free(self):
        result = _parse_action_block(_blk("action: use_ability\naction_type: free\nability: shout"))
        assert result is not None
        assert result["action_type"] == "free"

    def test_extracts_five_foot_step(self):
        result = _parse_action_block(_blk("action: move\naction_type: five_foot_step\nmovement: step left"))
        assert result is not None
        assert result["action_type"] == "five_foot_step"


# ── AC-002 — unknown values normalise to "standard" ───────────────────────────

class TestActionTypeNormalisation:
    """AC-002: non-canonical values fall back to 'standard'."""

    def test_unknown_value_becomes_standard(self):
        result = _parse_action_block(
            _blk("action: attack\naction_type: complicated_maneuver\ntarget: Ani")
        )
        assert result is not None
        assert result["action_type"] == "standard"

    def test_empty_value_becomes_standard(self):
        result = _parse_action_block(_blk("action: attack\naction_type: \ntarget: Ani"))
        assert result is not None
        assert result["action_type"] == "standard"


# ── AC-003 — action_type inferred from action when absent ─────────────────────

class TestActionTypeInference:
    """AC-003: sensible default derived from the action field."""

    def test_attack_infers_standard(self):
        result = _parse_action_block(_blk("action: attack\ntarget: Ani\nweapon: dogslicer"))
        assert result is not None
        assert result["action_type"] == "standard"

    def test_move_infers_move(self):
        result = _parse_action_block(_blk("action: move\nmovement: behind pillar"))
        assert result is not None
        assert result["action_type"] == "move"

    def test_delay_infers_delay(self):
        result = _parse_action_block(_blk("action: delay\nreason: waiting"))
        assert result is not None
        assert result["action_type"] == "delay"

    def test_use_ability_infers_standard(self):
        result = _parse_action_block(_blk("action: use_ability\nability: demoralize\ntarget: Ani"))
        assert result is not None
        assert result["action_type"] == "standard"


# ── AC-004 — all canonical values pass through unchanged ──────────────────────

class TestActionTypeCanonicalValues:
    """AC-004: every legal value is preserved exactly."""

    @pytest.mark.parametrize("value", [
        "standard", "move", "full", "swift", "free", "five_foot_step", "delay",
    ])
    def test_canonical_value_preserved(self, value):
        result = _parse_action_block(
            _blk(f"action: attack\naction_type: {value}\ntarget: Ani")
        )
        assert result is not None
        assert result["action_type"] == value, (
            f"Canonical value '{value}' must be returned unchanged"
        )


# ── AC-005 — briefing prompt includes action_type instruction ─────────────────

class TestEnemyTurnBriefingPrompt:
    """AC-005: _build_enemy_turn_system includes action_type field and legal values."""

    def test_prompt_includes_action_type_field(self):
        s = _session()
        prompt = _build_enemy_turn_system(s, "Goblin Warrior 1")
        assert "action_type:" in prompt, (
            "Briefing must contain 'action_type:' so the LLM knows to write the field"
        )

    def test_prompt_includes_legal_values(self):
        s = _session()
        prompt = _build_enemy_turn_system(s, "Goblin Warrior 1")
        for value in ("standard", "move", "full"):
            assert value in prompt, (
                f"Briefing must list legal value '{value}' in the action_type instruction"
            )


# ── AC-006 — action_card SSE event includes action_type ───────────────────────

_MOCK_ATTACK_RESULT = {
    "attacker": "Goblin Warrior 1",
    "target":   "Ani",
    "roll":     12,
    "bonus":    2,
    "total":    14,
    "ac":       15,
    "hit":      True,
    "damage_rolls": [3],
    "damage_total": 3,
    "attack_type": "ranged",
    "is_pc":    False,
}


class TestActionCardIncludesActionType:
    """AC-006: the action_card event emitted by stream_enemy_turn carries action_type."""

    def _events(self, chunks):
        events = []
        for chunk in chunks:
            for line in chunk.splitlines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        return events

    def test_action_card_has_action_type_standard(self):
        s = _session()
        llm_response = (
            "%%NARRATIVE%%\nThe goblin draws its shortbow and looses an arrow.\n\n"
            "%%ACTION%%\n"
            "action: attack\n"
            "action_type: standard\n"
            "target: Ani\n"
            "weapon: shortbow\n"
            "if_hit: The arrow pierces Ani's shoulder.\n"
            "if_miss: The arrow skips off the flagstones.\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            with patch.object(sm, "_resolve_npc_attack", return_value=_MOCK_ATTACK_RESULT):
                events = self._events(list(sm.stream_enemy_turn(s, "Goblin Warrior 1")))

        card_events = [e for e in events if e["type"] == "action_card"]
        assert card_events, "Expected at least one action_card event"
        assert card_events[0].get("action_type") == "standard", (
            "action_card must include action_type from the %%ACTION%% block"
        )

    def test_action_card_has_action_type_full(self):
        s = _session()
        llm_response = (
            "%%NARRATIVE%%\nThe goblin charges!\n\n"
            "%%ACTION%%\n"
            "action: attack\n"
            "action_type: full\n"
            "target: Ani\n"
            "weapon: dogslicer\n"
            "if_hit: The blade bites deep.\n"
            "if_miss: The slash goes wide.\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            with patch.object(sm, "_resolve_npc_attack", return_value=_MOCK_ATTACK_RESULT):
                events = self._events(list(sm.stream_enemy_turn(s, "Goblin Warrior 1")))

        card_events = [e for e in events if e["type"] == "action_card"]
        assert card_events, "Expected at least one action_card event"
        assert card_events[0].get("action_type") == "full"


# ── AC-007 — session log includes action_type ─────────────────────────────────

class TestEnemyMoveZone:
    """Enemy move action: target is a zone name and the combatant's zone is updated."""

    def _events(self, chunks):
        events = []
        for chunk in chunks:
            for line in chunk.splitlines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        return events

    def _session_with_zones(self):
        s = _session()
        s.combat_state.known_zones = ["center", "alleyway", "market stalls"]
        s.combat_state.combatants[1].zone = "alleyway"  # Goblin starts in alleyway
        return s

    def test_move_action_updates_combatant_zone(self):
        s = self._session_with_zones()
        llm_response = (
            "%%NARRATIVE%%\nThe goblin darts toward the market stalls.\n\n"
            "%%ACTION%%\n"
            "action: move\n"
            "action_type: move\n"
            "target: market stalls\n"
            "movement: dashes toward the stall canopies\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            list(sm.stream_enemy_turn(s, "Goblin Warrior 1"))

        goblin = next(c for c in s.combat_state.combatants if c.name == "Goblin Warrior 1")
        assert goblin.zone == "market stalls"

    def test_move_action_combat_update_reflects_new_zone(self):
        s = self._session_with_zones()
        llm_response = (
            "%%NARRATIVE%%\nThe goblin falls back to center.\n\n"
            "%%ACTION%%\n"
            "action: move\n"
            "action_type: move\n"
            "target: center\n"
            "movement: retreats to the open clearing\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            events = self._events(list(sm.stream_enemy_turn(s, "Goblin Warrior 1")))

        combat_updates = [e for e in events if e["type"] == "combat_update"]
        assert combat_updates, "Expected a combat_update event"
        combatants = combat_updates[-1]["combat_state"]["combatants"]
        goblin = next(c for c in combatants if c["name"] == "Goblin Warrior 1")
        assert goblin["zone"] == "center"

    def test_move_to_unknown_zone_is_ignored(self):
        s = self._session_with_zones()
        llm_response = (
            "%%NARRATIVE%%\nThe goblin tries to flee.\n\n"
            "%%ACTION%%\n"
            "action: move\n"
            "action_type: move\n"
            "target: roof\n"
            "movement: scrambles upward\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            list(sm.stream_enemy_turn(s, "Goblin Warrior 1"))

        goblin = next(c for c in s.combat_state.combatants if c.name == "Goblin Warrior 1")
        assert goblin.zone == "alleyway", "Unknown zone must not overwrite existing zone"

    def test_move_no_zone_in_combat_is_ignored_gracefully(self):
        s = _session()  # no known_zones
        llm_response = (
            "%%NARRATIVE%%\nThe goblin sidesteps.\n\n"
            "%%ACTION%%\n"
            "action: move\n"
            "action_type: move\n"
            "target: somewhere\n"
            "movement: steps aside\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            events = self._events(list(sm.stream_enemy_turn(s, "Goblin Warrior 1")))

        assert any(e["type"] == "combat_update" for e in events), "combat_update should still emit"

    def test_zones_listed_in_enemy_briefing(self):
        s = self._session_with_zones()
        system = _build_enemy_turn_system(s, "Goblin Warrior 1")
        assert "market stalls" in system
        assert "alleyway" in system
        assert "center" in system

    def test_target_description_distinguishes_zone_vs_combatant(self):
        s = self._session_with_zones()
        system = _build_enemy_turn_system(s, "Goblin Warrior 1")
        assert "destination zone name if move" in system


class TestActionTypeSessionLog:
    """AC-007: action_type is visible in the session log after the turn."""

    def test_action_type_appears_in_log(self):
        s = _session()
        log_entries: list[str] = []

        def fake_log(_session, text: str) -> None:
            log_entries.append(text)

        llm_response = (
            "%%NARRATIVE%%\nThe goblin fires.\n\n"
            "%%ACTION%%\n"
            "action: attack\n"
            "action_type: standard\n"
            "target: Ani\n"
            "weapon: shortbow\n"
            "if_hit: Hit!\n"
            "if_miss: Miss.\n"
        )
        with patch.object(sm, "_call_blocking", return_value=llm_response):
            with patch.object(sm, "_resolve_npc_attack", return_value=None):
                with patch.object(sm, "_log", side_effect=fake_log):
                    list(sm.stream_enemy_turn(s, "Goblin Warrior 1"))

        all_log = "\n".join(log_entries)
        assert "standard" in all_log, (
            "Session log must record the action_type of each enemy action"
        )
