"""Tests for the Roll Initiatives feature.

Spec: specs/roll-initiatives.feature  AC-001 through AC-007
Covers: roll_combat_initiatives(), POST /combat/roll_initiatives endpoint.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

import api.session_manager as sm
from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    get_session,
    roll_combat_initiatives,
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


def _combat(*actors: tuple[str, int, str]) -> CombatState:
    """Quick builder — actors = (name, initiative, status)."""
    return CombatState(
        round=2,
        current_actor=actors[0][0] if actors else None,
        combatants=[
            Combatant(name=n, initiative=init, status=st, hp_current=10, hp_max=10, ac=12)
            for n, init, st in actors
        ],
    )


def _pc_profiles(*names_and_modifiers: tuple[str, str]) -> dict:
    """Build minimal pc_profiles for the given (name, initiative_modifier) pairs."""
    return {
        name.lower(): {
            "narrative": "", "mechanical": "",
            "combat_stats": {"name": name, "hp_max": 20, "ac": 14, "initiative": mod},
        }
        for name, mod in names_and_modifiers
    }


# ── AC-001 — fresh d20 roll for every combatant ───────────────────────────────

class TestRollCombatInitiativesBasic:
    def test_all_combatants_get_new_initiative(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(
            ("Goblin A", 5, "active"),
            ("Goblin B", 5, "active"),
            ("Goblin C", 5, "active"),
        )
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            roll_combat_initiatives(session)
        values = [c.initiative for c in session.combat_state.combatants]
        # After rolling, it is overwhelmingly likely (probability 1/20^3 ≈ 0.01%)
        # that NOT all three remain at exactly 5.
        assert not all(v == 5 for v in values), (
            "All combatants still at 5 after roll — very unlikely if dice were actually rolled"
        )

    def test_enemy_initiative_in_valid_range(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(("Goblin 1", 8, "active"))
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            for _ in range(30):
                roll_combat_initiatives(session)
                val = session.combat_state.combatants[0].initiative
                assert 1 <= val <= 20, f"Enemy initiative {val} out of [1, 20]"

    def test_returns_serialised_combat_state(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(("Goblin 1", 8, "active"))
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            result = roll_combat_initiatives(session)
        assert result is not None
        assert "combatants" in result
        assert "round" in result
        assert "current_actor" in result

    def test_returns_none_when_no_combat(self, tmp_path: Path):
        session = _make_session(tmp_path)
        assert session.combat_state is None
        result = roll_combat_initiatives(session)
        assert result is None


# ── AC-002 — PC modifier from pc_profiles ─────────────────────────────────────

class TestPCModifierApplied:
    def test_pc_positive_modifier_shifts_range_up(self, tmp_path: Path):
        """PC with +5 modifier should produce values in [6, 25]."""
        session = _make_session(
            tmp_path,
            pc_profiles=_pc_profiles(("Thaelion", "+5")),
        )
        session.combat_state = _combat(("Thaelion", 10, "active"))
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            results = []
            for _ in range(40):
                roll_combat_initiatives(session)
                results.append(session.combat_state.combatants[0].initiative)
        # With +5 modifier, the minimum possible is 1+5=6
        assert all(v >= 6 for v in results), (
            f"PC with +5 modifier produced value below 6: {min(results)}"
        )
        assert all(v <= 25 for v in results), (
            f"PC with +5 modifier produced value above 25: {max(results)}"
        )

    def test_pc_zero_modifier_same_as_enemy(self, tmp_path: Path):
        """PC with +0 modifier behaves same as flat d20."""
        session = _make_session(
            tmp_path,
            pc_profiles=_pc_profiles(("Yanyeeku", "+0")),
        )
        session.combat_state = _combat(("Yanyeeku", 10, "active"))
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            for _ in range(30):
                roll_combat_initiatives(session)
                val = session.combat_state.combatants[0].initiative
                assert 1 <= val <= 20

    def test_pc_modifier_string_with_plus_prefix(self, tmp_path: Path):
        session = _make_session(
            tmp_path,
            pc_profiles=_pc_profiles(("Vanx", "+3")),
        )
        session.combat_state = _combat(("Vanx", 10, "active"))
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            for _ in range(20):
                roll_combat_initiatives(session)
                val = session.combat_state.combatants[0].initiative
                assert 4 <= val <= 23, f"Vanx (+3) produced {val}, expected [4, 23]"

    def test_malformed_modifier_falls_back_to_zero(self, tmp_path: Path):
        """Garbage initiative modifier is silently treated as +0."""
        session = _make_session(
            tmp_path,
            pc_profiles={"ani": {
                "narrative": "", "mechanical": "",
                "combat_stats": {"name": "Ani", "hp_max": 10, "ac": 14, "initiative": "fast"},
            }},
        )
        session.combat_state = _combat(("Ani", 8, "active"))
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            for _ in range(20):
                roll_combat_initiatives(session)
                val = session.combat_state.combatants[0].initiative
                assert 1 <= val <= 20


# ── AC-004 — current_actor updated ────────────────────────────────────────────

class TestCurrentActorAfterRoll:
    def _roll_many(self, session: GameSession, tmp_path: Path, n: int = 100):
        results = []
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            for _ in range(n):
                roll_combat_initiatives(session)
                results.append(session.combat_state.current_actor)
        return results

    def test_current_actor_is_always_active(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(
            ("Shalelu",  10, "active"),
            ("Goblin 1", 8,  "active"),
            ("Goblin 2", 5,  "unconscious"),
        )
        current_actors = self._roll_many(session, tmp_path)
        for actor in current_actors:
            assert actor in ("Shalelu", "Goblin 1"), (
                f"Unconscious combatant became current_actor: {actor}"
            )

    def test_all_inactive_sets_current_actor_none(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(
            ("Goblin 1", 5, "unconscious"),
            ("Goblin 2", 3, "dead"),
        )
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            roll_combat_initiatives(session)
        assert session.combat_state.current_actor is None

    def test_current_actor_matches_highest_initiative_active(self, tmp_path: Path):
        """After a fixed-seed roll, current_actor must be the highest active combatant."""
        session = _make_session(tmp_path)
        session.combat_state = _combat(
            ("A", 5, "active"),
            ("B", 5, "active"),
            ("C", 5, "active"),
        )
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            roll_combat_initiatives(session)
        cs = session.combat_state
        active = [c for c in cs.combatants if c.status == "active"]
        highest = max(active, key=lambda c: c.initiative)
        assert cs.current_actor == highest.name


# ── AC-005 — inactive combatants still rolled ─────────────────────────────────

class TestInactiveCombatantsRolled:
    def test_unconscious_combatant_gets_new_initiative(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(
            ("Goblin 1", 99, "unconscious"),  # 99 = sentinel; should change
        )
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            # Roll many times; almost certain to produce at least one ≠ 99 result
            for _ in range(30):
                roll_combat_initiatives(session)
                if session.combat_state.combatants[0].initiative != 99:
                    break
        # Stricter check: after 30 rolls the value must have changed at least once
        # (probability of all 30 rolls being exactly 19 with d20 is (1/20)^30 ≈ 10^-39)
        with patch.object(sm, "_session_state_path", return_value=tmp_path / "state.json"):
            seen = set()
            for _ in range(30):
                roll_combat_initiatives(session)
                seen.add(session.combat_state.combatants[0].initiative)
        assert len(seen) > 1, "Unconscious combatant initiative never changed across 30 rolls"


# ── AC-006 — state.json written ───────────────────────────────────────────────

class TestStateJsonWritten:
    def test_state_json_updated_after_roll(self, tmp_path: Path):
        session = _make_session(tmp_path)
        session.combat_state = _combat(
            ("Goblin 1", 5, "active"),
            ("Thaelion", 3, "active"),
        )
        state_path = tmp_path / "state.json"
        with patch.object(sm, "_session_state_path", return_value=state_path):
            roll_combat_initiatives(session)
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert state["active_character"] == session.combat_state.current_actor

    def test_log_entry_written_in_dev_mode(self, tmp_path: Path):
        session = _make_session(tmp_path, dev_mode=True)
        session.combat_state = _combat(("Goblin 1", 5, "active"))
        state_path = tmp_path / "state.json"
        with patch.object(sm, "_session_state_path", return_value=state_path):
            roll_combat_initiatives(session)
        log_text = session.log_path.read_text(encoding="utf-8") if session.log_path.exists() else ""
        assert "Roll initiatives" in log_text or "initiative" in log_text.lower()


# ── AC-007 — endpoint tests ────────────────────────────────────────────────────

class TestRollInitiativesEndpoint:
    def test_200_returns_updated_combat_state(self, booted_session):
        client, session_id = booted_session
        session = get_session(session_id)
        session.combat_state = _combat(
            ("Goblin 1",  5, "active"),
            ("Thaelion", 10, "active"),
        )
        resp = client.post(f"/api/sessions/{session_id}/combat/roll_initiatives")
        assert resp.status_code == 200
        data = resp.json()
        assert "combat_state" in data
        cs = data["combat_state"]
        assert "combatants" in cs
        assert "current_actor" in cs
        assert len(cs["combatants"]) == 2
        # All combatants must have a non-zero initiative after rolling
        for c in cs["combatants"]:
            assert c["initiative"] >= 1

    def test_409_when_no_combat(self, booted_session):
        client, session_id = booted_session
        assert get_session(session_id).combat_state is None
        resp = client.post(f"/api/sessions/{session_id}/combat/roll_initiatives")
        assert resp.status_code == 409

    def test_404_unknown_session(self, booted_session):
        client, _ = booted_session
        resp = client.post("/api/sessions/does-not-exist/combat/roll_initiatives")
        assert resp.status_code == 404

    def test_endpoint_applies_pc_modifier(self, booted_session):
        client, session_id = booted_session
        session = get_session(session_id)
        session.pc_profiles = _pc_profiles(("Thaelion", "+5"))
        session.combat_state = _combat(("Thaelion", 7, "active"))

        results = []
        for _ in range(20):
            resp = client.post(f"/api/sessions/{session_id}/combat/roll_initiatives")
            assert resp.status_code == 200
            cs = resp.json()["combat_state"]
            results.append(cs["combatants"][0]["initiative"])

        assert all(v >= 6 for v in results), (
            f"PC +5 modifier not applied — minimum seen was {min(results)}"
        )
