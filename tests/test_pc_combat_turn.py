"""PC combat action system tests.

Spec: specs/pc-combat-turn.feature
Covers: AC-001 through AC-010
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
    _build_pc_turn_system,
    _extract_pc_combat_intent,
    _hp_descriptor,
    _parse_atk_bonus,
    _PC_TURN_SYSTEM,
    _stream_pc_turn_narration,
    stream_pc_turn,
    stream_resume_combat,
)
from tests.conftest import parse_sse


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _session() -> GameSession:
    return GameSession(
        id=str(uuid.uuid4()),
        session_number=1,
        model="test-model",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=False,
        provider="ollama",
        num_ctx=2048,
        num_gpu=999,
        system_prompt="",
        log_path=None,
        pc_profiles={
            "ani": {
                "combat_stats": {"name": "Ani", "hp_max": 11, "ac": 17, "initiative": "+1"},
                "weapons": [
                    {"name": "morningstar", "atk": "+4", "dmg": "1d8+2", "type": "melee"},
                    {"name": "light crossbow", "atk": "+3", "dmg": "1d8", "type": "ranged"},
                ],
            },
            "vanx": {
                "combat_stats": {"name": "Vanx", "hp_max": 7, "ac": 12, "initiative": "+2"},
                "weapons": [
                    {"name": "longsword", "atk": "+4", "dmg": "1d8+2", "type": "melee"},
                ],
            },
        },
    )


def _combat(current_actor: str = "Ani") -> CombatState:
    return CombatState(
        round=2,
        current_actor=current_actor,
        combatants=[
            Combatant(name="Ani",              hp_current=11, hp_max=11, ac=17, initiative=14),
            Combatant(name="Vanx",             hp_current=7,  hp_max=7,  ac=12, initiative=10),
            Combatant(name="Goblin Warchanter",hp_current=8,  hp_max=8,  ac=14, initiative=18),
            Combatant(name="Goblin Warrior 1", hp_current=5,  hp_max=5,  ac=16, initiative=9),
        ],
    )


def _events(chunks):
    events = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


# ── Helpers ───────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_hp_descriptor_healthy(self):
        assert _hp_descriptor(10, 11) == "healthy"

    def test_hp_descriptor_wounded(self):
        assert _hp_descriptor(5, 11) == "wounded"

    def test_hp_descriptor_badly_wounded(self):
        assert _hp_descriptor(2, 11) == "badly wounded"

    def test_hp_descriptor_dying(self):
        assert _hp_descriptor(0, 11) == "dying"

    def test_parse_atk_bonus_positive(self):
        assert _parse_atk_bonus("+4") == 4

    def test_parse_atk_bonus_negative(self):
        assert _parse_atk_bonus("-1") == -1

    def test_parse_atk_bonus_zero(self):
        assert _parse_atk_bonus("+0") == 0

    def test_parse_atk_bonus_invalid(self):
        assert _parse_atk_bonus("") == 0


# ── AC-001/AC-002: Intent extraction ─────────────────────────────────────────

class TestIntentExtraction:
    """AC-001, AC-002, AC-003"""

    def _session_in_combat(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Ani")
        return s

    def test_weapon_match_by_exact_name(self):
        s = self._session_in_combat()
        intent = _extract_pc_combat_intent("I swing my morningstar!", s)
        assert intent["weapon_name"] == "morningstar"
        assert intent["weapon_atk"]  == "+4"
        assert intent["weapon_dmg"]  == "1d8+2"

    def test_weapon_match_by_substring(self):
        s = self._session_in_combat()
        # "sword" matches "longsword" — test with Vanx's profile
        s.combat_state.current_actor = "Vanx"
        intent = _extract_pc_combat_intent("I use my sword!", s)
        assert "sword" in intent["weapon_name"].lower()

    def test_weapon_fallback_when_unknown(self):
        s = self._session_in_combat()
        intent = _extract_pc_combat_intent("I attack with my halberd!", s)
        # Falls back to first (equipped) weapon
        assert intent["weapon_name"] == "morningstar"
        assert intent["action_type"] == "attack"

    def test_target_match_by_exact_name(self):
        s = self._session_in_combat()
        intent = _extract_pc_combat_intent("I attack Goblin Warrior 1", s)
        assert intent["target"] == "Goblin Warrior 1"

    def test_target_match_by_type_keyword(self):
        s = self._session_in_combat()
        intent = _extract_pc_combat_intent("I hit the goblin!", s)
        # Any goblin — both warriors are active
        assert "Goblin" in intent["target"]

    def test_fallback_vague_input(self):
        s = self._session_in_combat()
        intent = _extract_pc_combat_intent("I attack!", s)
        assert intent["action_type"] == "attack"
        assert intent["weapon_name"] == "morningstar"  # first weapon
        assert intent["target"] != ""  # some enemy
        assert intent["original_text"] == "I attack!"

    def test_actor_from_current_combatant(self):
        s = self._session_in_combat()
        intent = _extract_pc_combat_intent("I swing at the warchanter", s)
        assert intent["actor"] == "Ani"


# ── AC-006: PC turn system message ────────────────────────────────────────────

class TestPcTurnSystem:
    """AC-006"""

    def _hit_result(self) -> dict:
        return {
            "attacker": "Ani", "target": "Goblin Warrior 1",
            "roll": 12, "bonus": 4, "total": 16, "ac": 16,
            "hit": True, "damage_rolls": [6], "damage_total": 6,
            "attack_type": "melee", "is_pc": True,
        }

    def _miss_result(self) -> dict:
        return {**self._hit_result(), "roll": 5, "total": 9, "hit": False,
                "damage_rolls": [], "damage_total": 0}

    def _intent(self) -> dict:
        return {
            "actor": "Ani", "target": "Goblin Warrior 1",
            "weapon_name": "morningstar", "weapon_atk": "+4",
            "weapon_dmg": "1d8+2", "weapon_type": "melee",
            "action_type": "attack", "original_text": "I swing!",
        }

    def test_system_contains_identity_header(self):
        s = _session(); s.combat_state = _combat()
        system = _build_pc_turn_system(s, self._intent(), self._hit_result())
        assert "You are the Game Master" in system
        assert "[PC TURN BRIEFING]" in system

    def test_system_contains_actor_and_target(self):
        s = _session(); s.combat_state = _combat()
        system = _build_pc_turn_system(s, self._intent(), self._hit_result())
        assert "Actor: Ani" in system
        assert "Target: Goblin Warrior 1" in system

    def test_system_contains_hit_outcome(self):
        s = _session(); s.combat_state = _combat()
        system = _build_pc_turn_system(s, self._intent(), self._hit_result())
        assert "HIT" in system
        assert "Damage: 6" in system

    def test_system_contains_miss_outcome(self):
        s = _session(); s.combat_state = _combat()
        system = _build_pc_turn_system(s, self._intent(), self._miss_result())
        assert "MISS" in system
        assert "Damage" not in system.split("MISS")[1][:30]

    def test_system_hp_descriptor_badly_wounded(self):
        s = _session(); s.combat_state = _combat()
        # Wound the target so HP < 33%
        for c in s.combat_state.combatants:
            if c.name == "Goblin Warrior 1":
                c.hp_current = 1
        system = _build_pc_turn_system(s, self._intent(), self._hit_result())
        assert "badly wounded" in system

    def test_system_does_not_contain_weapon_stat_string(self):
        s = _session(); s.combat_state = _combat()
        system = _build_pc_turn_system(s, self._intent(), self._hit_result())
        # Raw "+4 (1d8+2)" style strings should NOT appear
        assert "(1d8+2)" not in system


# ── AC-004/AC-005: stream_pc_turn ─────────────────────────────────────────────

class TestStreamPcTurn:
    """AC-004, AC-005"""

    def _session_in_combat(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Ani")
        return s

    def test_attack_request_emitted(self):
        s = self._session_in_combat()
        events = _events(list(stream_pc_turn(s, "I swing my morningstar at Goblin Warrior 1")))
        types = [e["type"] for e in events]
        assert "attack_request" in types
        assert "done" in types

    def test_attack_queued_from_profile_not_llm(self):
        s = self._session_in_combat()
        list(stream_pc_turn(s, "I swing my morningstar at Goblin Warrior 1"))
        assert len(s.attack_queue) == 1
        pa = s.attack_queue[0]
        assert pa.attacker  == "Ani"
        assert pa.target    == "Goblin Warrior 1"
        assert pa.bonus     == 4           # from profile "+4"
        assert pa.damage_expr == "1d8+2"   # from profile
        assert pa.is_pc     is True

    def test_pending_narration_flag_set(self):
        s = self._session_in_combat()
        list(stream_pc_turn(s, "I swing my morningstar at Goblin Warrior 1"))
        assert s._pending_pc_narration is not None
        assert s._pending_pc_narration["actor"] == "Ani"

    def test_player_text_appended_to_history(self):
        s = self._session_in_combat()
        text = "I swing my morningstar at the warchanter"
        list(stream_pc_turn(s, text))
        user_msgs = [m for m in s.messages if m["role"] == "user"]
        assert any(text in m["content"] for m in user_msgs)

    def test_no_llm_call_in_stream_pc_turn(self, monkeypatch):
        s = self._session_in_combat()
        called = []
        monkeypatch.setattr(sm, "_call_blocking", lambda *a: called.append(a) or "")
        list(stream_pc_turn(s, "I attack!"))
        assert len(called) == 0  # no LLM call at this stage


# ── AC-007/AC-008/AC-009: narration ──────────────────────────────────────────

class TestPcTurnNarration:
    """AC-007, AC-008, AC-009"""

    def _session_with_pending(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Ani")
        s._pending_pc_narration = {
            "actor": "Ani", "target": "Goblin Warrior 1",
            "weapon_name": "morningstar", "weapon_atk": "+4",
            "weapon_dmg": "1d8+2", "weapon_type": "melee",
            "action_type": "attack", "original_text": "I swing!",
        }
        s.attack_results = [{
            "attacker": "Ani", "target": "Goblin Warrior 1",
            "roll": 14, "bonus": 4, "total": 18, "ac": 16,
            "hit": True, "damage_rolls": [5], "damage_total": 5,
            "attack_type": "melee", "is_pc": True,
        }]
        return s

    def test_narrative_streamed_after_resolution(self, monkeypatch):
        s = self._session_with_pending()
        monkeypatch.setattr(sm, "_call_blocking",
                            lambda *_: "%%NARRATIVE%%\nAni strikes with deadly precision!\n")
        events = _events(list(_stream_pc_turn_narration(s)))
        tokens = [e for e in events if e["type"] == "token"]
        assert any("Ani strikes" in t["content"] for t in tokens)

    def test_action_card_emitted_before_token(self, monkeypatch):
        s = self._session_with_pending()
        monkeypatch.setattr(sm, "_call_blocking",
                            lambda *_: "%%NARRATIVE%%\nAni strikes!\n")
        events = _events(list(_stream_pc_turn_narration(s)))
        types = [e["type"] for e in events]
        card_idx  = next((i for i, e in enumerate(events) if e["type"] == "action_card"), None)
        token_idx = next((i for i, e in enumerate(events) if e["type"] == "token"), None)
        assert card_idx is not None
        assert token_idx is not None
        assert card_idx < token_idx

    def test_pending_narration_cleared_after_use(self, monkeypatch):
        s = self._session_with_pending()
        monkeypatch.setattr(sm, "_call_blocking", lambda *_: "%%NARRATIVE%%\nAni strikes!\n")
        list(_stream_pc_turn_narration(s))
        assert s._pending_pc_narration is None

    def test_advance_combat_turn_fires_after_narration(self, monkeypatch):
        """AC-009 — advance_combat_turn is called; combat_update SSE emitted."""
        s = self._session_with_pending()
        monkeypatch.setattr(sm, "_call_blocking", lambda *_: "%%NARRATIVE%%\nAni strikes!\n")
        events = _events(list(_stream_pc_turn_narration(s)))
        update_events = [e for e in events if e["type"] == "combat_update"]
        assert len(update_events) == 1, "exactly one combat_update should follow narration"
        combat_state_payload = update_events[0].get("combat_state", {})
        assert "current_actor" in combat_state_payload

    def test_stream_resume_combat_detects_flag(self, monkeypatch):
        s = self._session_with_pending()
        called = []

        def fake_narration(sess):
            called.append(sess)
            sess._pending_pc_narration = None  # simulate real consumption
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        monkeypatch.setattr(sm, "_stream_pc_turn_narration", fake_narration)
        list(stream_resume_combat(s))
        # resume_combat should have delegated to _stream_pc_turn_narration
        assert len(called) == 1
        assert s._pending_pc_narration is None  # consumed by fake


# ── AC-010: Routing (tested via stream_pc_turn existence) ─────────────────────

class TestPcTurnRouting:
    """AC-010 — verify /pc_turn endpoint is wired (integration smoke)"""

    def test_pc_turn_endpoint_exists(self, booted_session):
        client, session_id = booted_session
        session = sm._sessions[session_id]
        session.combat_state = CombatState(
            round=1, current_actor="TestPC",
            combatants=[
                Combatant(name="TestPC",    hp_current=10, hp_max=10, ac=15, initiative=12),
                Combatant(name="Test Enemy",hp_current=5,  hp_max=5,  ac=13, initiative=8),
            ],
        )
        session.pc_profiles["testpc"] = {
            "combat_stats": {"name": "TestPC", "hp_max": 10, "ac": 15, "initiative": "+1"},
            "weapons": [{"name": "sword", "atk": "+3", "dmg": "1d8+1", "type": "melee"}],
        }
        resp = client.post(f"/api/sessions/{session_id}/pc_turn",
                           json={"input": "I swing my sword at the enemy"})
        assert resp.status_code == 200
        events = parse_sse(resp)
        types = {e["type"] for e in events}
        assert "attack_request" in types
        assert "done" in types


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestPcTurnEdgeCases:
    """Critical edge cases identified in code review."""

    def _session_no_enemies(self) -> GameSession:
        s = _session()
        s.combat_state = CombatState(
            round=2, current_actor="Ani",
            combatants=[
                Combatant(name="Ani",  hp_current=11, hp_max=11, ac=17, initiative=14),
                Combatant(name="Vanx", hp_current=7,  hp_max=7,  ac=12, initiative=10),
                # All enemies dead
                Combatant(name="Goblin Warrior 1", hp_current=0, hp_max=5, ac=16, initiative=9, status="dead"),
            ],
        )
        return s

    def _session_no_weapons(self) -> GameSession:
        s = _session()
        s.pc_profiles["ani"]["weapons"] = []  # no weapons
        s.combat_state = _combat("Ani")
        return s

    def test_attack_with_no_active_enemies_emits_error(self):
        s = self._session_no_enemies()
        events = _events(list(stream_pc_turn(s, "I attack!")))
        types = [e["type"] for e in events]
        assert "error" in types
        assert "attack_request" not in types
        assert len(s.attack_queue) == 0

    def test_no_active_enemies_does_not_set_pending_narration(self):
        s = self._session_no_enemies()
        list(stream_pc_turn(s, "I attack!"))
        assert s._pending_pc_narration is None

    def test_pc_with_no_weapons_falls_back_to_unarmed(self):
        s = self._session_no_weapons()
        list(stream_pc_turn(s, "I attack Goblin Warrior 1"))
        assert len(s.attack_queue) == 1
        pa = s.attack_queue[0]
        assert pa.damage_expr == "1d3"  # unarmed fallback
        assert pa.bonus == 0            # unarmed fallback

    def test_non_attack_action_narrates_immediately(self, monkeypatch):
        """Non-attack actions call LLM in-stream, not via resume_combat."""
        s = _session()
        s.combat_state = _combat("Ani")
        s.dev_mode = False
        narration_called = []
        monkeypatch.setattr(sm, "_call_blocking",
                            lambda *_: (narration_called.append(True) or "%%NARRATIVE%%\nAni moves cautiously.\n"))
        events = _events(list(stream_pc_turn(s, "I move closer to the warchanter")))
        assert len(narration_called) == 1  # LLM was called in-stream
        tokens = [e for e in events if e["type"] == "token"]
        assert any("Ani moves" in t["content"] for t in tokens)
        assert s._pending_pc_narration is None  # not deferred to resume_combat

    def test_non_attack_advances_turn(self, monkeypatch):
        s = _session()
        s.combat_state = _combat("Ani")
        s.dev_mode = False
        monkeypatch.setattr(sm, "_call_blocking", lambda *_: "%%NARRATIVE%%\nAni steps back.\n")
        events = _events(list(stream_pc_turn(s, "I move away")))
        combat_events = [e for e in events if e["type"] == "combat_update"]
        assert len(combat_events) == 1

    def test_intent_extraction_returns_empty_when_no_combat(self):
        s = _session()  # no combat_state
        intent = _extract_pc_combat_intent("I attack!", s)
        assert intent == {}

    def test_stream_pc_turn_error_on_no_combat(self):
        s = _session()  # no combat_state
        events = _events(list(stream_pc_turn(s, "I attack!")))
        assert any(e["type"] == "error" for e in events)
