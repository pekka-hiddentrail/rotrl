"""Tests for Combat Tier 1.5 — Interactive PC Attack Flow.

Covers: _roll_dice, _parse_attack_line/block, _is_pc_attacker,
_resolve_npc_attack, resolve_attack_roll, resolve_damage_roll,
stream_resume_combat, SSE events, stream filter.
Conditions and _get_combatant_ac are tested in test_combat.py and
test_combat_hp.py respectively.
Spec: specs/attack-resolution.feature
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from api.session_manager import (
    Combatant,
    CombatState,
    PendingAttack,
    _build_attack_history_message,
    _parse_attack_line,
    _parse_attack_block,
    _roll_dice,
    _is_pc_attacker,
    _resolve_npc_attack,
    resolve_attack_roll,
    resolve_damage_roll,
)
from .conftest import make_stream_response, parse_sse


# ── Helpers ──────────────────────────────────────────────────────────────────

def _state(round_: int, *combatants):
    return CombatState(round=round_, combatants=list(combatants))


def _combatant(name, hp_current, hp_max, ac=13, init=10):
    return Combatant(name=name, hp_current=hp_current, hp_max=hp_max, ac=ac, initiative=init)


def _fake_session(booted_session):
    """Return a booted session with combat state and pc_profiles pre-loaded."""
    import api.session_manager as sm
    client, session_id = booted_session
    session = sm.get_session(session_id)
    session.combat_state = _state(1,
        _combatant("Shalelu", 18, 24, ac=17, init=14),
        _combatant("Goblin 1", 5, 5, ac=13, init=10),
    )
    # Simulate a PC named Thaelion
    session.pc_profiles = {"thaelion": {"narrative": "", "mechanical": ""}}
    return client, session_id, session


# ── _roll_dice ────────────────────────────────────────────────────────────────

class TestRollDice:  # AC-001
    def test_single_die(self):
        rolls, total = _roll_dice("1d6")
        assert len(rolls) == 1
        assert 1 <= rolls[0] <= 6
        assert total == rolls[0]

    def test_multiple_dice(self):
        rolls, total = _roll_dice("2d4")
        assert len(rolls) == 2
        assert all(1 <= r <= 4 for r in rolls)
        assert total == sum(rolls)

    def test_positive_modifier(self):
        rolls, total = _roll_dice("1d6+3")
        assert total == rolls[0] + 3

    def test_negative_modifier(self):
        rolls, total = _roll_dice("1d8-1")
        assert total == rolls[0] - 1

    def test_invalid_expr_returns_empty(self):
        assert _roll_dice("invalid") == ([], 0)
        assert _roll_dice("") == ([], 0)
        assert _roll_dice(None) == ([], 0)  # type: ignore[arg-type]

    def test_d20(self):
        rolls, total = _roll_dice("1d20")
        assert 1 <= total <= 20


# ── _parse_attack_line ────────────────────────────────────────────────────────

class TestParseAttackLine:  # AC-001
    def test_happy_path(self):
        line = "  - attacker: Thaelion · target: Goblin 1 · bonus: +5 · damage: 1d8+3 · type: melee"
        a = _parse_attack_line(line)
        assert a is not None
        assert a["attacker"] == "Thaelion"
        assert a["target"] == "Goblin 1"
        assert a["bonus"] == 5
        assert a["damage"] == "1d8+3"
        assert a["type"] == "melee"

    def test_negative_bonus(self):
        line = "- attacker: Goblin 1 · target: Shalelu · bonus: -1 · damage: 1d4"
        a = _parse_attack_line(line)
        assert a is not None
        assert a["bonus"] == -1

    def test_bonus_without_sign(self):
        line = "- attacker: X · target: Y · bonus: 4 · damage: 1d6"
        a = _parse_attack_line(line)
        assert a["bonus"] == 4

    def test_missing_attacker_returns_none(self):
        line = "- target: Goblin 1 · bonus: +4 · damage: 1d6"
        assert _parse_attack_line(line) is None

    def test_missing_target_returns_none(self):
        line = "- attacker: Thaelion · bonus: +4 · damage: 1d6"
        assert _parse_attack_line(line) is None

    def test_defaults(self):
        line = "- attacker: X · target: Y"
        a = _parse_attack_line(line)
        assert a is not None
        assert a["bonus"] == 0
        assert a["type"] == "melee"

    def test_bullet_variant(self):
        line = "• attacker: Orc • target: Hero • bonus: +3 • damage: 1d6+1"
        a = _parse_attack_line(line)
        assert a is not None
        assert a["attacker"] == "Orc"


# ── _parse_attack_block ───────────────────────────────────────────────────────

class TestParseAttackBlock:  # AC-001
    def test_two_attacks(self):
        block = (
            "- attacker: Goblin 1 · target: Shalelu · bonus: +4 · damage: 1d4+2\n"
            "- attacker: Thaelion · target: Goblin 2 · bonus: +5 · damage: 1d8+3\n"
        )
        attacks = _parse_attack_block(block)
        assert len(attacks) == 2
        assert attacks[0]["attacker"] == "Goblin 1"
        assert attacks[1]["attacker"] == "Thaelion"

    def test_invalid_line_skipped(self):
        block = (
            "- attacker: Goblin · target: Hero · bonus: +3 · damage: 1d6\n"
            "this is not a valid line\n"
        )
        assert len(_parse_attack_block(block)) == 1

    def test_empty_returns_empty_list(self):
        assert _parse_attack_block("") == []
        assert _parse_attack_block(None) == []  # type: ignore[arg-type]


# ── _is_pc_attacker ───────────────────────────────────────────────────────────

class TestIsPcAttacker:  # AC-002
    def test_pc_found(self, booted_session):
        _, _, session = _fake_session(booted_session)
        assert _is_pc_attacker("Thaelion", session) is True
        assert _is_pc_attacker("thaelion", session) is True

    def test_npc_not_found(self, booted_session):
        _, _, session = _fake_session(booted_session)
        assert _is_pc_attacker("Goblin 1", session) is False


# ── _resolve_npc_attack ───────────────────────────────────────────────────────

class TestResolveNpcAttack:  # AC-002, AC-007
    def test_guaranteed_hit(self, booted_session):
        _, _, session = _fake_session(booted_session)
        attack = {"attacker": "Goblin 1", "target": "Shalelu", "bonus": 100, "damage": "1d6+2", "type": "melee"}
        result = _resolve_npc_attack(attack, session)
        assert result["hit"] is True
        assert result["damage_total"] > 0
        shalelu = next(c for c in session.combat_state.combatants if c.name == "Shalelu")
        assert shalelu.hp_current < 18

    def test_guaranteed_miss(self, booted_session):
        _, _, session = _fake_session(booted_session)
        attack = {"attacker": "Goblin 1", "target": "Shalelu", "bonus": -100, "damage": "1d6", "type": "melee"}
        result = _resolve_npc_attack(attack, session)
        assert result["hit"] is False
        assert result["damage_total"] == 0
        shalelu = next(c for c in session.combat_state.combatants if c.name == "Shalelu")
        assert shalelu.hp_current == 18

    def test_result_shape(self, booted_session):
        _, _, session = _fake_session(booted_session)
        attack = {"attacker": "Goblin 1", "target": "Shalelu", "bonus": 0, "damage": "1d4", "type": "melee"}
        result = _resolve_npc_attack(attack, session)
        for key in ("attacker", "target", "roll", "bonus", "total", "ac", "hit", "damage_rolls", "damage_total", "attack_type", "is_pc"):
            assert key in result
        assert result["is_pc"] is False


# ── resolve_attack_roll ───────────────────────────────────────────────────────

class TestResolveAttackRoll:  # AC-003
    def _queue_pc_attack(self, session):
        session.attack_queue.append(PendingAttack(
            attacker="Thaelion", target="Goblin 1",
            bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
        ))

    def test_hit_path(self, booted_session):
        _, _, session = _fake_session(booted_session)
        self._queue_pc_attack(session)
        result = resolve_attack_roll(session, 15)  # 15+5=20 ≥ AC 13
        assert result["hit"] is True
        assert result["damage_expr"] == "1d8+3"
        assert result["queue_remaining"] == 1   # awaiting damage roll
        assert session.attack_queue[0].hit is True

    def test_miss_path(self, booted_session):
        _, _, session = _fake_session(booted_session)
        self._queue_pc_attack(session)
        result = resolve_attack_roll(session, 1)   # 1+5=6 < AC 13
        assert result["hit"] is False
        assert result["damage_expr"] is None
        assert result["queue_remaining"] == 0
        assert len(session.attack_queue) == 0
        assert len(session.attack_results) == 1

    def test_no_queue_raises(self, booted_session):
        _, _, session = _fake_session(booted_session)
        with pytest.raises(ValueError):
            resolve_attack_roll(session, 10)


# ── resolve_damage_roll ───────────────────────────────────────────────────────

class TestResolveDamageRoll:  # AC-004
    def _setup_hit(self, session):
        session.attack_queue.append(PendingAttack(
            attacker="Thaelion", target="Goblin 1",
            bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
            hit_roll=15, hit_total=20, hit=True,
        ))

    def test_damage_applied_and_hp_reduced(self, booted_session):
        _, _, session = _fake_session(booted_session)
        self._setup_hit(session)
        result = resolve_damage_roll(session, [4], 7)
        assert result["damage_total"] == 7
        assert result["queue_remaining"] == 0
        goblin = next(c for c in session.combat_state.combatants if c.name == "Goblin 1")
        assert goblin.hp_current == 0   # 5-7 clamped to 0

    def test_no_pending_damage_raises(self, booted_session):
        _, _, session = _fake_session(booted_session)
        with pytest.raises(ValueError):
            resolve_damage_roll(session, [3], 3)


# ── resume_combat endpoint ────────────────────────────────────────────────────

class TestResumeCombat:  # AC-005, AC-006
    def test_injects_results_and_calls_llm(self, booted_session):
        client, session_id, session = _fake_session(booted_session)
        session.attack_results = [
            {"attacker": "Goblin 1", "target": "Shalelu", "roll": 12, "bonus": 4,
             "total": 16, "ac": 17, "hit": False, "damage_rolls": [], "damage_total": 0,
             "attack_type": "melee", "is_pc": False},
        ]
        mock_resp = make_stream_response(["%%NARRATIVE%%\n\nThe goblin misses.\n\n%%DELTAS%%\n[]\n"])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/resume_combat")
        assert resp.status_code == 200
        events = parse_sse(resp)
        assert any(e["type"] == "token" for e in events)
        assert session.attack_results == []
        assert any("[ATTACK RESULTS" in m["content"] for m in session.messages if m["role"] == "user")

    def test_rejected_if_queue_not_empty(self, booted_session):
        client, session_id, session = _fake_session(booted_session)
        session.attack_queue.append(PendingAttack("T", "G", 5, "1d8", is_pc=True))
        resp = client.post(f"/api/sessions/{session_id}/resume_combat")
        assert resp.status_code == 409

    def test_missing_session_404(self, client):
        resp = client.post("/api/sessions/nonexistent/resume_combat")
        assert resp.status_code == 404


# ── SSE integration ───────────────────────────────────────────────────────────

class TestAttackSseIntegration:  # AC-002, AC-007, AC-008
    def test_npc_auto_resolved_pc_queued(self, booted_session):
        """NPC attack → attack_result SSE; PC attack → attack_request SSE."""
        client, session_id, session = _fake_session(booted_session)
        response_text = (
            "%%NARRATIVE%%\n\nCombat!\n\n"
            "%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\nround: 2\ncombatants:\n"
            "  - name: Shalelu · ac: 17 · init: 14 · status: active\n"
            "  - name: Goblin 1 · ac: 13 · init: 10 · status: active\n"
            "%%ATTACK%%\n"
            "- attacker: Goblin 1 · target: Shalelu · bonus: +4 · damage: 1d4+2 · type: melee\n"
            "- attacker: Thaelion · target: Goblin 1 · bonus: +5 · damage: 1d8+3 · type: melee\n"
        )
        mock_resp = make_stream_response([response_text])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Attack!"})
        events = parse_sse(resp)
        npc_results = [e for e in events if e["type"] == "attack_result"]
        pc_requests = [e for e in events if e["type"] == "attack_request"]
        assert len(npc_results) == 1
        assert npc_results[0]["attacker"] == "Goblin 1"
        assert npc_results[0]["is_pc"] is False
        assert len(pc_requests) == 1
        assert pc_requests[0]["attacker"] == "Thaelion"
        assert session.attack_queue[0].attacker == "Thaelion"

    def test_npc_hit_reduces_hp(self, booted_session):
        """NPC attack that hits must reduce combat_state HP immediately."""
        client, session_id, session = _fake_session(booted_session)
        response_text = (
            "%%NARRATIVE%%\n\nStrike!\n\n%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\nround: 2\ncombatants:\n"
            "  - name: Shalelu · ac: 17 · init: 14 · status: active\n"
            "  - name: Goblin 1 · ac: 13 · init: 10 · status: active\n"
            "%%ATTACK%%\n"
            "- attacker: Goblin 1 · target: Shalelu · bonus: +999 · damage: 1d4+2 · type: melee\n"
        )
        mock_resp = make_stream_response([response_text])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Fight!"})
        shalelu = next(c for c in session.combat_state.combatants if c.name == "Shalelu")
        assert shalelu.hp_current < 18

    def test_attack_block_stripped_from_player_stream(self, client):
        """%%ATTACK%% block is never visible in player token stream."""
        boot = client.post("/api/sessions", json={
            "session_number": 1, "model": "qwen3:4b",
            "host": "http://localhost:11434", "temperature": 0.3, "dev_mode": False,
        })
        session_id = next(e["session_id"] for e in parse_sse(boot) if e["type"] == "done")
        import api.session_manager as sm
        session = sm.get_session(session_id)
        session.combat_state = _state(1, _combatant("Shalelu", 18, 24, ac=17))
        response_text = (
            "%%NARRATIVE%%\n\nFight!\n\n%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\nround: 2\ncombatants:\n  - name: Shalelu · ac: 17 · init: 14 · status: active\n"
            "%%ATTACK%%\n- attacker: Goblin · target: Shalelu · bonus: +4 · damage: 1d4 · type: melee\n"
        )
        mock_resp = make_stream_response([response_text])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Fight!"})
        token_content = "".join(e["content"] for e in parse_sse(resp) if e["type"] == "token")
        assert "%%ATTACK%%" not in token_content
        assert "attacker:" not in token_content
        assert "Fight!" in token_content


# ── _build_attack_history_message ────────────────────────────────────────────

class TestBuildAttackHistoryMessage:  # AC-005
    def _hit(self, attacker="Thaelion", target="Goblin 1", roll=15, bonus=5,
             total=20, ac=13, damage_rolls=None, damage_total=8):
        return {
            "attacker": attacker, "target": target,
            "roll": roll, "bonus": bonus, "total": total, "ac": ac,
            "hit": True, "damage_rolls": damage_rolls or [6, 2],
            "damage_total": damage_total, "attack_type": "melee", "is_pc": True,
        }

    def _miss(self, attacker="Goblin 1", target="Shalelu", roll=3, bonus=4, total=7, ac=17):
        return {
            "attacker": attacker, "target": target,
            "roll": roll, "bonus": bonus, "total": total, "ac": ac,
            "hit": False, "damage_rolls": [], "damage_total": 0,
            "attack_type": "melee", "is_pc": False,
        }

    def test_hit_entry_format(self):
        msg = _build_attack_history_message([self._hit()], round_num=2)
        assert "ATTACK RESULTS — round 2" in msg
        assert "Thaelion → Goblin 1" in msg
        assert "HIT" in msg
        assert "8 damage" in msg
        assert "vs AC 13" in msg

    def test_miss_entry_format(self):
        msg = _build_attack_history_message([self._miss()], round_num=1)
        assert "Goblin 1 → Shalelu" in msg
        assert "MISS" in msg
        assert "damage" not in msg

    def test_negative_bonus_formatted(self):
        msg = _build_attack_history_message([self._miss(bonus=-2, total=1)], round_num=1)
        assert "-2" in msg

    def test_empty_results_header_only(self):
        msg = _build_attack_history_message([], round_num=3)
        assert "ATTACK RESULTS" in msg
        assert "→" not in msg

    def test_multiple_entries_all_present(self):
        msg = _build_attack_history_message([self._hit(), self._miss()], round_num=2)
        assert "Thaelion → Goblin 1" in msg
        assert "Goblin 1 → Shalelu" in msg
        assert "HIT" in msg
        assert "MISS" in msg


# ── multi-attack queue progression ───────────────────────────────────────────

class TestMultiAttackQueue:  # AC-009
    def _queue_two(self, session):
        session.attack_queue.extend([
            PendingAttack(attacker="Thaelion", target="Goblin 1",
                          bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True),
            PendingAttack(attacker="Thaelion", target="Goblin 1",
                          bonus=0, damage_expr="1d8", attack_type="melee", is_pc=True),
        ])

    def test_miss_exposes_next_attack(self, booted_session):
        """After a miss the first attack is removed; next_attack is the second."""
        _, _, session = _fake_session(booted_session)
        self._queue_two(session)
        result = resolve_attack_roll(session, 1)  # 1+5=6 < AC 13 → miss
        assert result["hit"] is False
        assert result["queue_remaining"] == 1
        assert result["next_attack"] is not None
        assert result["next_attack"]["bonus"] == 0

    def test_hit_blocks_next_until_damage(self, booted_session):
        """After a hit the attack awaits damage; next_attack is None."""
        _, _, session = _fake_session(booted_session)
        self._queue_two(session)
        result = resolve_attack_roll(session, 15)  # 15+5=20 ≥ AC 13 → hit
        assert result["hit"] is True
        assert result["queue_remaining"] == 2
        assert result["next_attack"] is None  # first attack still in damage phase

    def test_damage_resolve_exposes_second_attack(self, booted_session):
        """After damage is rolled, next_attack returns the second queued attack."""
        _, _, session = _fake_session(booted_session)
        self._queue_two(session)
        resolve_attack_roll(session, 15)                  # first attack hits
        result = resolve_damage_roll(session, [4], 7)     # first attack damaged
        assert result["queue_remaining"] == 1
        assert result["next_attack"] is not None
        assert result["next_attack"]["bonus"] == 0        # second attack


# ── resolve_attack_roll guard ─────────────────────────────────────────────────

class TestResolveAttackRollGuard:  # AC-003
    def test_raises_if_already_in_damage_phase(self, booted_session):
        """Calling resolve_attack_roll while hit=True (damage pending) raises."""
        _, _, session = _fake_session(booted_session)
        session.attack_queue.append(PendingAttack(
            attacker="Thaelion", target="Goblin 1",
            bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
        ))
        session.attack_queue[0].hit = True
        with pytest.raises(ValueError, match="damage roll"):
            resolve_attack_roll(session, 10)


# ── NPC attack on 0-HP target ─────────────────────────────────────────────────

class TestNpcAttackOnDeadTarget:  # AC-007
    def test_hp_stays_at_zero(self, booted_session):
        """A guaranteed NPC hit on a 0-HP target does not drive HP negative."""
        _, _, session = _fake_session(booted_session)
        shalelu = next(c for c in session.combat_state.combatants if c.name == "Shalelu")
        shalelu.hp_current = 0
        attack = {"attacker": "Goblin 1", "target": "Shalelu",
                  "bonus": 100, "damage": "4d6+10", "type": "melee"}
        _resolve_npc_attack(attack, session)
        assert shalelu.hp_current == 0


# ── stream_resume_combat with empty attack_results ───────────────────────────

class TestResumeCombatEmptyResults:  # AC-005
    def test_still_calls_llm(self, booted_session):
        """resume_combat with no prior attack results injects a bare header and calls LLM."""
        client, session_id, session = _fake_session(booted_session)
        # attack_results is already [] by default
        mock_resp = make_stream_response(
            ["%%NARRATIVE%%\n\nThe dust settles.\n\n%%DELTAS%%\n[]\n"]
        )
        with patch("api.session_manager._requests.post", return_value=mock_resp) as mock_post:
            resp = client.post(f"/api/sessions/{session_id}/resume_combat")
        assert resp.status_code == 200
        mock_post.assert_called_once()
        events = parse_sse(resp)
        assert any(e["type"] == "token" for e in events)
        # The bare header is still injected into history
        assert any("ATTACK RESULTS" in m["content"]
                   for m in session.messages if m["role"] == "user")


# ── Endpoint HTTP guard paths ─────────────────────────────────────────────────

class TestResolveEndpointGuards:
    """HTTP-layer guards on /resolve_attack_roll and /resolve_damage_roll.

    These exercise the endpoint error-handling in main.py that wraps
    ValueError from the session-manager functions into 409 responses.
    The underlying function-level guards are tested elsewhere; these tests
    verify the correct HTTP status codes are surfaced.
    """

    def test_resolve_attack_roll_409_when_already_in_damage_phase(self, booted_session):
        """Calling /resolve_attack_roll while the front-of-queue attack has hit=True → 409."""
        client, session_id, session = _fake_session(booted_session)
        # Put a hit-pending attack at the front of the queue
        session.attack_queue.append(PendingAttack(
            attacker="Thaelion", target="Goblin 1",
            bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
        ))
        session.attack_queue[0].hit = True

        resp = client.post(
            f"/api/sessions/{session_id}/resolve_attack_roll",
            json={"rolled": 10},
        )
        assert resp.status_code == 409

    def test_resolve_damage_roll_404_on_missing_session(self, client):
        """DELETE /resolve_damage_roll on an unknown session returns 404."""
        resp = client.post(
            "/api/sessions/nonexistent/resolve_damage_roll",
            json={"rolls": [4], "total": 4},
        )
        assert resp.status_code == 404

    def test_resolve_damage_roll_409_when_no_damage_pending(self, booted_session):
        """Calling /resolve_damage_roll when attack_queue is empty → 409."""
        client, session_id, session = _fake_session(booted_session)
        # attack_queue is empty by default after _fake_session

        resp = client.post(
            f"/api/sessions/{session_id}/resolve_damage_roll",
            json={"rolls": [4], "total": 4},
        )
        assert resp.status_code == 409
