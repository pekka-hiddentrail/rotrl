"""Tests for combat-active-character.feature — AC-001 through AC-007 + endpoint.

Covers: CombatState.current_actor field, _parse_combat_block seeding, serialization,
advance_combat_turn logic, _write_session_state, and the advance_turn endpoint.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _parse_combat_block,
    _serialize_combat_state,
    _write_session_state,
    advance_combat_turn,
    get_session,
)
from tests.conftest import parse_sse


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_session(tmp_path: Path, **kwargs) -> GameSession:
    defaults = dict(
        id=str(uuid.uuid4()),
        session_number=1,
        model="test",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=False,
        provider="ollama",
        num_ctx=2048,
        num_gpu=999,
        system_prompt="",
        log_path=tmp_path / "test.log.md",
    )
    defaults.update(kwargs)
    return GameSession(**defaults)


def _combat(round_num: int, actors: list[tuple[str, int, str, int, int]]) -> CombatState:
    """Quick builder: actors = [(name, initiative, status, hp, ac), ...]"""
    combatants = [
        Combatant(name=n, initiative=init, status=st, hp_current=hp, hp_max=hp, ac=ac)
        for n, init, st, hp, ac in actors
    ]
    return CombatState(round=round_num, combatants=combatants)


# ── AC-001 — CombatState has current_actor field ──────────────────────────────

class TestCombatStateCurrentActorField:
    def test_field_exists_and_defaults_to_none(self):
        cs = CombatState(round=1, combatants=[])
        assert hasattr(cs, "current_actor")
        assert cs.current_actor is None

    def test_can_be_set_at_construction(self):
        cs = CombatState(round=2, combatants=[], current_actor="Thaelion")
        assert cs.current_actor == "Thaelion"

    def test_serialize_includes_current_actor_none(self):
        cs = CombatState(round=1, combatants=[])
        d = _serialize_combat_state(cs)
        assert "current_actor" in d
        assert d["current_actor"] is None

    def test_serialize_includes_current_actor_name(self):
        cs = CombatState(round=2, combatants=[], current_actor="Goblin 1")
        d = _serialize_combat_state(cs)
        assert d["current_actor"] == "Goblin 1"

    def test_serialize_none_state_returns_none(self):
        assert _serialize_combat_state(None) is None


# ── AC-002 — _parse_combat_block seeds current_actor on round 1 ───────────────

class TestParseBlockSeedsCurrentActor:
    _BLOCK_R1 = """\
round: 1
combatants:
  - name: Shalelu · hp: 24/24 · ac: 17 · init: 14 · status: active
  - name: Thaelion · hp: 22/22 · ac: 16 · init: 10 · status: active
  - name: Goblin 1 · hp: 5/5 · ac: 13 · init: 5 · status: active"""

    def test_seeds_highest_initiative_active(self):
        cs = _parse_combat_block(self._BLOCK_R1, existing_state=None)
        assert cs is not None
        assert cs.current_actor == "Shalelu"  # init 14, highest

    def test_skips_unconscious_for_current(self):
        block = """\
round: 1
combatants:
  - name: Shalelu · hp: 0/24 · ac: 17 · init: 14 · status: unconscious
  - name: Thaelion · hp: 22/22 · ac: 16 · init: 10 · status: active"""
        cs = _parse_combat_block(block, existing_state=None)
        assert cs is not None
        assert cs.current_actor == "Thaelion"

    def test_skips_dead_for_current(self):
        block = """\
round: 1
combatants:
  - name: Shalelu · hp: 0/24 · ac: 17 · init: 14 · status: dead
  - name: Goblin · hp: 5/5 · ac: 13 · init: 8 · status: active"""
        cs = _parse_combat_block(block, existing_state=None)
        assert cs is not None
        assert cs.current_actor == "Goblin"

    def test_none_when_all_inactive(self):
        block = """\
round: 1
combatants:
  - name: Shalelu · hp: 0/24 · ac: 17 · init: 14 · status: unconscious
  - name: Goblin · hp: 0/5 · ac: 13 · init: 8 · status: dead"""
        cs = _parse_combat_block(block, existing_state=None)
        assert cs is not None
        assert cs.current_actor is None

    def test_single_combatant_is_current(self):
        block = "round: 1\ncombatants:\n  - name: Solo · hp: 10/10 · ac: 12 · init: 7 · status: active"
        cs = _parse_combat_block(block, existing_state=None)
        assert cs is not None
        assert cs.current_actor == "Solo"


# ── AC-003 — current_actor preserved on round 2+ ─────────────────────────────

class TestParseBlockPreservesCurrentActor:
    def test_existing_current_actor_carried_over(self):
        existing = _combat(1, [
            ("Shalelu", 14, "active", 20, 17),
            ("Thaelion", 10, "active", 22, 16),
        ])
        existing.current_actor = "Thaelion"

        block = """\
round: 2
combatants:
  - name: Shalelu · ac: 17 · init: 14 · status: active
  - name: Thaelion · ac: 16 · init: 10 · status: active"""
        cs = _parse_combat_block(block, existing_state=existing)
        assert cs is not None
        assert cs.current_actor == "Thaelion"

    def test_none_current_actor_preserved_on_round2(self):
        existing = _combat(1, [("Goblin", 8, "active", 5, 13)])
        existing.current_actor = None

        block = "round: 2\ncombatants:\n  - name: Goblin · ac: 13 · init: 8 · status: active"
        cs = _parse_combat_block(block, existing_state=existing)
        assert cs is not None
        assert cs.current_actor is None


# ── advance_combat_turn logic ─────────────────────────────────────────────────

class TestAdvanceCombatTurn:
    def _session(self, tmp_path: Path, actors: list[tuple], current: str | None = None) -> GameSession:
        cs = _combat(2, actors)
        cs.current_actor = current
        return _make_session(tmp_path, combat_state=cs)

    # AC-005 — basic advance
    def test_advances_to_next_in_initiative_order(self, tmp_path: Path):
        session = self._session(tmp_path, [
            ("Shalelu", 14, "active", 24, 17),
            ("Thaelion", 10, "active", 22, 16),
            ("Goblin", 5, "active", 5, 13),
        ], current="Shalelu")
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        assert result["current_actor"] == "Thaelion"
        assert result["is_pc"] is False  # no pc_profiles set

    def test_advance_wraps_at_end_back_to_first(self, tmp_path: Path):
        session = self._session(tmp_path, [
            ("Shalelu", 14, "active", 24, 17),
            ("Thaelion", 10, "active", 22, 16),
        ], current="Thaelion")
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        assert result["current_actor"] == "Shalelu"

    # AC-006 — skip dead/unconscious
    def test_skips_unconscious_combatant(self, tmp_path: Path):
        session = self._session(tmp_path, [
            ("Shalelu", 14, "active", 24, 17),
            ("Goblin", 10, "unconscious", 0, 13),
            ("Thaelion", 5, "active", 22, 16),
        ], current="Shalelu")
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        assert result["current_actor"] == "Thaelion"

    def test_skips_dead_combatant(self, tmp_path: Path):
        session = self._session(tmp_path, [
            ("Shalelu", 14, "active", 24, 17),
            ("Goblin", 10, "dead", 0, 13),
            ("Thaelion", 5, "active", 22, 16),
        ], current="Shalelu")
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        assert result["current_actor"] == "Thaelion"

    # AC-005 — is_pc detection
    def test_is_pc_true_when_name_in_pc_profiles(self, tmp_path: Path):
        cs = _combat(2, [
            ("Thaelion", 14, "active", 22, 16),
            ("Goblin", 8, "active", 5, 13),
        ])
        cs.current_actor = "Goblin"
        session = _make_session(tmp_path, combat_state=cs, pc_profiles={
            "thaelion": {"narrative": "", "mechanical": "", "combat_stats": {"name": "Thaelion", "hp_max": 22, "ac": 16, "initiative": "+3"}},
        })
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        assert result["current_actor"] == "Thaelion"
        assert result["is_pc"] is True

    def test_is_pc_false_when_name_not_in_pc_profiles(self, tmp_path: Path):
        cs = _combat(2, [
            ("Goblin", 10, "active", 5, 13),
            ("Thaelion", 5, "active", 22, 16),
        ])
        cs.current_actor = "Goblin"
        session = _make_session(tmp_path, combat_state=cs, pc_profiles={
            "thaelion": {"narrative": "", "mechanical": "", "combat_stats": {"name": "Thaelion", "hp_max": 22, "ac": 16, "initiative": "+3"}},
        })
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        assert result["current_actor"] == "Thaelion"
        assert result["is_pc"] is True

    def test_advance_updates_session_combat_state(self, tmp_path: Path):
        session = self._session(tmp_path, [
            ("A", 14, "active", 10, 12),
            ("B", 8, "active", 10, 12),
        ], current="A")
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            advance_combat_turn(session)
        assert session.combat_state.current_actor == "B"

    def test_advance_when_current_actor_none_picks_first(self, tmp_path: Path):
        session = self._session(tmp_path, [
            ("Shalelu", 14, "active", 24, 17),
            ("Goblin", 5, "active", 5, 13),
        ], current=None)
        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            result = advance_combat_turn(session)
        # Should pick Shalelu (highest active) when no current is set
        assert result["current_actor"] == "Shalelu"


# ── AC-005 — endpoint 409 / 404 ──────────────────────────────────────────────

class TestAdvanceTurnEndpoint:
    def test_advance_turn_200(self, booted_session):
        client, session_id = booted_session
        session = get_session(session_id)
        session.combat_state = _combat(2, [
            ("Shalelu", 14, "active", 24, 17),
            ("Goblin", 5, "active", 5, 13),
        ])
        session.combat_state.current_actor = "Shalelu"
        resp = client.post(f"/api/sessions/{session_id}/combat/advance_turn")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_actor" in data
        assert "is_pc" in data
        assert data["current_actor"] == "Goblin"

    def test_advance_turn_409_no_combat(self, booted_session):
        client, session_id = booted_session
        session = get_session(session_id)
        assert session.combat_state is None
        resp = client.post(f"/api/sessions/{session_id}/combat/advance_turn")
        assert resp.status_code == 409

    def test_advance_turn_404_unknown_session(self, booted_session):
        client, _ = booted_session
        resp = client.post("/api/sessions/does-not-exist/combat/advance_turn")
        assert resp.status_code == 404


# ── AC-007 — _write_session_state writes current_actor ───────────────────────

class TestWriteSessionStateCurrentActor:
    def test_writes_combat_current_actor_as_active_character(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(2, [("Goblin", 8, "active", 5, 13)])
        session.combat_state.current_actor = "Goblin"

        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            _write_session_state(session)

        state = json.loads((tmp_path / "state.json").read_text())
        assert state["active_character"] == "Goblin"

    def test_uses_session_active_character_when_no_combat(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = None
        session.active_character = "Yanyeeku"

        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            _write_session_state(session)

        state = json.loads((tmp_path / "state.json").read_text())
        assert state["active_character"] == "Yanyeeku"

    def test_writes_none_current_actor_as_party(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(2, [("Goblin", 8, "active", 5, 13)])
        session.combat_state.current_actor = None
        session.active_character = "Thaelion"

        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            _write_session_state(session)

        state = json.loads((tmp_path / "state.json").read_text())
        # When combat active but no current_actor, fall back to session.active_character
        assert state["active_character"] == "Thaelion"

    def test_advance_turn_writes_state_json(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(2, [
            ("Shalelu", 14, "active", 24, 17),
            ("Goblin", 5, "active", 5, 13),
        ])
        session.combat_state.current_actor = "Shalelu"

        state_path = tmp_path / "state.json"
        with patch("api.session_manager._session_state_path", return_value=state_path):
            advance_combat_turn(session)

        state = json.loads(state_path.read_text())
        assert state["active_character"] == "Goblin"
