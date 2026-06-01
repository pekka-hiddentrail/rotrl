"""Combat Tier 1.7 enemy-turn and close-combat tests.

Spec: specs/enemy-turn.feature
Covers: enemy-turn.feature AC-001 through AC-012
Covers: combat-tracker.feature AC-016, AC-017, AC-018
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import api.session_manager as sm
from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _build_combat_close_directive,
    _build_enemy_turn_query,
    _ENEMY_TURN_SYSTEM,
    _parse_action_block,
    get_session,
    stream_close_combat,
    stream_enemy_turn,
)
from .conftest import parse_sse


def _session() -> GameSession:
    return GameSession(
        id="s1",
        session_number=1,
        model="test-model",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=True,
        pc_profiles={
            "vanx": {"combat_stats": {"name": "Vanx"}},
            "ani": {"combat_stats": {"name": "Ani"}},
        },
    )


def _combat() -> CombatState:
    return CombatState(
        round=1,
        current_actor="Goblin Warrior 1",
        combatants=[
            Combatant(name="Vanx", hp_current=10, hp_max=10, ac=18, initiative=14),
            Combatant(name="Ani", hp_current=9, hp_max=9, ac=15, initiative=12),
            Combatant(name="Goblin Warrior 1", hp_current=5, hp_max=5, ac=16, initiative=10),
            Combatant(name="Goblin Warrior 2", hp_current=5, hp_max=5, ac=16, initiative=8),
        ],
    )


def _events(chunks: list[str]) -> list[dict]:
    events: list[dict] = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


class TestActionBlockParser:
    def test_parse_action_block_accepts_attack_use_ability_and_movement(self):
        attack = _parse_action_block(
            "%%ACTION%%\n"
            "action: attack\n"
            "target: Vanx\n"
            "weapon: dogslicer\n"
            "reason: closest threat"
        )
        assert attack == {
            "action": "attack",
            "target": "Vanx",
            "weapon": "dogslicer",
            "bonus": "",
            "damage": "",
            "ability": "",
            "movement": "",
            "reason": "closest threat",
        }

        ability = _parse_action_block("action: use_ability | target: Ani | ability: demoralize")
        assert ability is not None
        assert ability["action"] == "use_ability"
        assert ability["ability"] == "demoralize"

        move = _parse_action_block("action: move; movement: flank Vanx; reason: pack tactics")
        assert move is not None
        assert move["action"] == "move"
        assert move["movement"] == "flank Vanx"

    def test_parse_action_block_rejects_absent_or_missing_action_blocks(self):
        assert _parse_action_block(None) is None
        assert _parse_action_block("") is None
        assert _parse_action_block("%%ACTION%%\ntarget: Vanx") is None

    def test_parse_action_block_defaults_unknown_actions_to_delay(self):
        parsed = _parse_action_block("%%ACTION%%\naction: monologue\nreason: no valid action")
        assert parsed is not None
        assert parsed["action"] == "delay"

    def test_parse_action_block_extracts_bonus_and_damage(self):
        """LLM-provided bonus/damage fields are extracted verbatim."""
        parsed = _parse_action_block(
            "%%ACTION%%\n"
            "action: attack\n"
            "target: Vanx\n"
            "weapon: dogslicer\n"
            "bonus: +2\n"
            "damage: 1d4\n"
            "reason: closest"
        )
        assert parsed is not None
        assert parsed["bonus"] == "+2"
        assert parsed["damage"] == "1d4"

    def test_extract_narrative_strips_action_markup_when_llm_omits_narrative_block(self):
        """Markup must not reach the player when %%NARRATIVE%% is absent."""
        full_response = (
            "%%ACTION%%\n"
            "action: attack\n"
            "target: Vanx\n"
            "weapon: dogslicer\n"
            "reason: closest threat\n"
            "%%END%%"
        )
        result = sm._extract_narrative(full_response)
        assert result == ""

    def test_get_attack_uses_llm_provided_bonus_and_damage(self):
        """_get_attack_for_enemy honours bonus/damage from the parsed %%ACTION%% block."""
        action = {
            "action": "attack",
            "target": "Vanx",
            "weapon": "dogslicer",
            "bonus": "+2",
            "damage": "1d4+1",
            "ability": "",
            "movement": "",
            "reason": "closest",
        }
        result = sm._get_attack_for_enemy(action, "Goblin Warrior 1")
        assert result["bonus"] == 2
        assert result["damage"] == "1d4+1"
        assert result["type"] == "melee"

    def test_get_attack_falls_back_to_defaults_when_bonus_damage_absent(self):
        """Generic defaults are used when the LLM omits bonus/damage fields."""
        action = {
            "action": "attack",
            "target": "Vanx",
            "weapon": "shortbow",
            "bonus": "",
            "damage": "",
            "ability": "",
            "movement": "",
            "reason": "ranged",
        }
        result = sm._get_attack_for_enemy(action, "Goblin Warrior 1")
        assert result["bonus"] == 4   # fallback default
        assert result["damage"] == "1d4"  # fallback default
        assert result["type"] == "ranged"


class TestEnemyTurnQuery:
    def test_enemy_turn_query_lists_actor_allies_pcs_budget_and_action_spec(self):
        session = _session()
        session.combat_state = _combat()
        query = _build_enemy_turn_query(session, "Goblin Warrior 1")

        assert "Actor: * Goblin Warrior 1: hp 5/5, status active" in query
        assert "Goblin Warrior 2: hp 5/5" in query
        assert "Vanx: hp 10/10" in query
        assert "Ani: hp 9/9" in query
        assert "Normal turn" in query
        assert "%%ACTION%%" in query
        assert "action: attack|use_ability|move|delay" in query
        assert "bonus:" in query
        assert "damage:" in query

    def test_enemy_turn_query_adjusts_action_budget_for_restrictive_conditions(self):
        session = _session()
        session.combat_state = _combat()
        goblin = session.combat_state.combatants[2]
        goblin.conditions = ["nauseated"]
        assert "Single move action only" in _build_enemy_turn_query(session, goblin.name)

        goblin.conditions = ["paralyzed"]
        assert "No meaningful actions" in _build_enemy_turn_query(session, goblin.name)

    def test_enemy_turn_query_omits_ac_values(self):
        session = _session()
        session.combat_state = _combat()
        query = _build_enemy_turn_query(session, "Goblin Warrior 1")
        assert "AC 18" not in query
        assert "ac 18" not in query.lower()
        assert "AC 16" not in query
        assert "ac 16" not in query.lower()

    def test_stream_enemy_turn_uses_short_enemy_system_prompt_without_history(self, monkeypatch):
        session = _session()
        session.combat_state = _combat()
        session.messages = [{"role": "user", "content": "old history"}]
        captured: dict[str, str] = {}

        def fake_call(s: GameSession, system: str, user: str) -> str:
            captured["system"] = system
            captured["user"] = user
            return "%%NARRATIVE%%\nThe goblin waits.\n\n%%ACTION%%\naction: delay"

        monkeypatch.setattr(sm, "_call_blocking", fake_call)
        events = _events(list(stream_enemy_turn(session)))

        assert captured["system"] == _ENEMY_TURN_SYSTEM
        assert "old history" not in captured["user"]
        assert events[-1]["type"] == "done"


class TestEnemyTurnStreaming:
    def test_stream_enemy_turn_streams_narrative_tokens_without_action_markup(self, monkeypatch):
        session = _session()
        session.combat_state = _combat()
        monkeypatch.setattr(
            sm,
            "_call_blocking",
            lambda *_: "%%NARRATIVE%%\nThe goblin darts in with a shriek.\n\n%%ACTION%%\naction: delay",
        )

        events = _events(list(stream_enemy_turn(session)))
        token_text = "".join(e["content"] for e in events if e["type"] == "token")

        assert "The goblin darts in" in token_text
        assert "%%ACTION%%" not in token_text
        assert events[-1]["type"] == "done"

    def test_stream_enemy_turn_attack_resolves_with_backend_ac_and_emits_updates(self, monkeypatch):
        session = _session()
        session.combat_state = _combat()
        monkeypatch.setattr(
            sm,
            "_call_blocking",
            lambda *_: "%%NARRATIVE%%\nThe goblin slashes at Vanx.\n\n%%ACTION%%\naction: attack\ntarget: Vanx\nweapon: dogslicer",
        )
        monkeypatch.setattr(sm.random, "randint", lambda _a, _b: 15)
        monkeypatch.setattr(sm, "_roll_dice", lambda _expr: ([3], 3))

        events = _events(list(stream_enemy_turn(session)))
        attack = next(e for e in events if e["type"] == "attack_result")
        combat_update = next(e for e in events if e["type"] == "combat_update")

        assert attack["attacker"] == "Goblin Warrior 1"
        assert attack["target"] == "Vanx"
        assert attack["total"] == 19
        assert attack["ac"] == 18
        assert attack["hit"] is True
        assert next(c for c in session.combat_state.combatants if c.name == "Vanx").hp_current == 7
        assert combat_update["combat_state"]["combatants"][0]["name"] == "Vanx"

    def test_stream_enemy_turn_delay_emits_no_attack_result_but_still_completes(self, monkeypatch):
        session = _session()
        session.combat_state = _combat()
        monkeypatch.setattr(
            sm,
            "_call_blocking",
            lambda *_: "%%NARRATIVE%%\nThe goblin hesitates.\n\n%%ACTION%%\naction: delay",
        )

        events = _events(list(stream_enemy_turn(session)))

        assert not any(e["type"] == "attack_result" for e in events)
        assert any(e["type"] == "combat_update" for e in events)
        assert events[-1]["type"] == "done"
        assert next(c for c in session.combat_state.combatants if c.name == "Vanx").hp_current == 10

    def test_enemy_turn_endpoint_status_codes(self, booted_session, monkeypatch):
        client, session_id = booted_session
        session = get_session(session_id)
        assert session is not None
        session.pc_profiles = _session().pc_profiles
        session.combat_state = _combat()
        monkeypatch.setattr(
            sm,
            "_call_blocking",
            lambda *_: "%%NARRATIVE%%\nThe goblin waits.\n\n%%ACTION%%\naction: delay",
        )

        ok = client.post(f"/api/sessions/{session_id}/enemy_turn")
        assert ok.status_code == 200
        assert parse_sse(ok)[-1]["type"] == "done"

        session.combat_state = None
        assert client.post(f"/api/sessions/{session_id}/enemy_turn").status_code == 409
        assert client.post("/api/sessions/nope/enemy_turn").status_code == 404


class TestCloseCombat:
    def test_close_combat_streams_narrative_then_clears_state_json(self, tmp_path, monkeypatch):
        session = _session()
        session.combat_state = _combat()
        monkeypatch.setattr(
            sm,
            "_call_blocking",
            lambda *_: "%%NARRATIVE%%\nThe last goblin breaks and the square falls quiet.",
        )

        with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
            events = _events(list(stream_close_combat(session)))

        assert events[0]["type"] == "token"
        assert events[-2] == {"type": "combat_update", "combat_state": None}
        assert events[-1]["type"] == "done"
        assert session.combat_state is None
        data = json.loads((tmp_path / "state.json").read_text())
        assert data["mode"] == "social"
        assert data["combatants"] == []

    def test_close_combat_returns_409_without_active_combat(self, booted_session):
        client, session_id = booted_session
        assert client.post(f"/api/sessions/{session_id}/close_combat").status_code == 409

    def test_close_combat_falls_back_to_silent_clear_on_provider_error(self, monkeypatch):
        session = _session()
        session.combat_state = _combat()

        def fail(*_args):
            raise RuntimeError("provider down")

        monkeypatch.setattr(sm, "_call_blocking", fail)
        events = _events(list(stream_close_combat(session)))

        assert not any(e["type"] == "error" for e in events)
        assert events[-2] == {"type": "combat_update", "combat_state": None}
        assert events[-1]["type"] == "done"
        assert session.combat_state is None

    def test_combat_close_directive_contains_snapshot_and_forbids_structured_sections(self):
        session = _session()
        session.combat_state = _combat()
        directive = _build_combat_close_directive(session)

        assert "Round: 1" in directive
        assert "Goblin Warrior 1: hp 5/5" in directive
        assert "Vanx: hp 10/10" in directive
        assert "Do not write %%COMBAT%%, %%ATTACK%%, %%ACTION%%" in directive


# ── B-C07 regression — stale attack_queue cleared on resume ──────────────────

from api.session_manager import (
    PendingAttack,
    stream_resume_combat,
)


class TestResumeCombatClearsStaleQueue:
    """B-C07: stream_resume_combat must clear orphaned attack_queue entries before
    calling the LLM so a subsequent /enemy_turn call does not return 409.
    """

    def _session_with_stale_queue(self) -> GameSession:
        s = _session()
        s.combat_state = _combat()
        # Stale PendingAttack left from a previous turn the frontend already resolved
        s.attack_queue = [
            PendingAttack(
                attacker="Vanx", target="Goblin Warrior 1",
                bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
            )
        ]
        s.attack_results = []
        s.messages = [{"role": "user", "content": "I attacked last turn."}]
        return s

    def test_stale_queue_cleared_before_llm_call(self):
        s = self._session_with_stale_queue()
        assert len(s.attack_queue) == 1

        # Patch _stream_chat so no real LLM call happens
        with patch.object(sm, "_stream_chat", return_value=iter([])):
            list(stream_resume_combat(s))

        assert s.attack_queue == [], (
            "stream_resume_combat must clear the attack_queue before delegating to _stream_chat"
        )

    def test_resume_with_empty_queue_unchanged(self):
        """Empty queue stays empty — no side-effects when queue is already clear."""
        s = self._session_with_stale_queue()
        s.attack_queue = []

        with patch.object(sm, "_stream_chat", return_value=iter([])):
            list(stream_resume_combat(s))

        assert s.attack_queue == []

    def test_stale_queue_log_message_emitted(self):
        """A log entry is written when stale entries are purged (for dev visibility)."""
        s = self._session_with_stale_queue()
        from pathlib import Path
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log.md', delete=False) as f:
            s.log_path = Path(f.name)
        try:
            with patch.object(sm, "_stream_chat", return_value=iter([])):
                list(stream_resume_combat(s))
            log_text = s.log_path.read_text(encoding="utf-8")
            assert "stale" in log_text.lower() or "attack-queue" in log_text.lower()
        finally:
            os.unlink(s.log_path)


# ── B-C07 regression — enemy_turn 409 guard ──────────────────────────────────

class TestEnemyTurnStaleQueue:
    """B-C07: POST /enemy_turn must return 409 when attack_queue is non-empty,
    AND stream_resume_combat must drain that queue so a subsequent enemy_turn works.
    """

    def test_enemy_turn_409_when_queue_nonempty(self, booted_session):
        client, session_id = booted_session
        session = get_session(session_id)
        session.combat_state = _combat()
        session.attack_queue = [
            PendingAttack(
                attacker="Vanx", target="Goblin Warrior 1",
                bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
            )
        ]
        resp = client.post(f"/api/sessions/{session_id}/enemy_turn")
        assert resp.status_code == 409

    def test_enemy_turn_200_after_resume_clears_queue(self, booted_session):
        client, session_id = booted_session
        session = get_session(session_id)
        session.combat_state = _combat()
        # Simulate stale queue + resume
        session.attack_queue = [
            PendingAttack(
                attacker="Vanx", target="Goblin Warrior 1",
                bonus=5, damage_expr="1d8+3", attack_type="melee", is_pc=True,
            )
        ]
        session.attack_results = []
        session.messages = [{"role": "user", "content": "I attacked."}]

        with patch.object(sm, "_stream_chat", return_value=iter([])):
            list(stream_resume_combat(session))

        # Queue must be empty now
        assert session.attack_queue == []
        # Enemy turn must no longer 409
        with patch.object(sm, "_call_blocking", return_value="%%NARRATIVE%%\nThe goblin sneers.\n%%ACTION%%\naction: delay"):
            resp = client.post(f"/api/sessions/{session_id}/enemy_turn")
        assert resp.status_code == 200
