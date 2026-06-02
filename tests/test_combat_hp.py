"""Tests for Combat Tier 1.1 — HP Authority Shift.

Covers: backend HP preservation, new-combatant initialisation, HP context
injection, %%HP%% delta block parsing and application, player-stream stripping,
and _get_combatant_ac (shared combat-state lookup utility).
Spec: specs/combat-hp.feature
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from api.session_manager import (
    Combatant,
    CombatState,
    _parse_combat_block,
    _parse_hp_deltas,
    _apply_hp_deltas,
    _inject_context,
    _get_combatant_ac,
)
from .conftest import make_stream_response, parse_sse


# ── Helpers ──────────────────────────────────────────────────────────────────

def _state(round_: int, *combatants: Combatant) -> CombatState:
    return CombatState(round=round_, combatants=list(combatants))


def _combatant(name: str, hp_current: int, hp_max: int, ac: int = 13, init: int = 10) -> Combatant:
    return Combatant(name=name, hp_current=hp_current, hp_max=hp_max, ac=ac, initiative=init)


# ── AC-001 / AC-002 / AC-003 — _parse_combat_block with existing_state ───────

class TestHpInheritance:
    """_parse_combat_block(text, existing_state=...) HP authority logic."""

    def test_ac001_hp_initialised_from_llm_on_combat_start(self):
        """Round 1 with no existing state: all HP values come from the LLM block."""
        block = (
            "round: 1\n"
            "combatants:\n"
            "  - name: Shalelu · hp: 18/24 · ac: 17 · init: 14 · status: active\n"
            "  - name: Goblin 1 · hp: 5/5 · ac: 13 · init: 10 · status: active\n"
        )
        result = _parse_combat_block(block, existing_state=None)
        assert result is not None
        assert result.round == 1
        shalelu = next(c for c in result.combatants if c.name == "Shalelu")
        assert shalelu.hp_current == 18
        assert shalelu.hp_max == 24
        goblin = next(c for c in result.combatants if c.name == "Goblin 1")
        assert goblin.hp_current == 5

    def test_ac002_hp_preserved_from_backend_on_subsequent_turns(self):
        """Round 2+: LLM-written HP for known combatants is ignored; backend values kept."""
        existing = _state(1,
            _combatant("Shalelu", hp_current=7, hp_max=24),
            _combatant("Goblin 1", hp_current=3, hp_max=5),
        )
        # LLM "forgets" and writes full HP for Shalelu
        block = (
            "round: 2\n"
            "combatants:\n"
            "  - name: Shalelu · hp: 24/24 · ac: 17 · init: 14 · status: active\n"
            "  - name: Goblin 1 · hp: 5/5 · ac: 13 · init: 10 · status: active\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        shalelu = next(c for c in result.combatants if c.name == "Shalelu")
        assert shalelu.hp_current == 7   # preserved — not 24
        assert shalelu.hp_max == 24
        goblin = next(c for c in result.combatants if c.name == "Goblin 1")
        assert goblin.hp_current == 3    # preserved — not 5

    def test_ac002_status_still_updated_from_llm(self):
        """Status changes from the LLM are applied, but guarded by backend HP.

        If the backend HP is still positive the LLM cannot mark the combatant as
        dead or unconscious — the guard overrides status back to 'active'.  This
        prevents the LLM from speculatively killing a combatant before damage is
        actually applied.
        """
        existing = _state(1, _combatant("Goblin 1", hp_current=1, hp_max=5))
        block = (
            "round: 2\n"
            "combatants:\n"
            "  - name: Goblin 1 · hp: 0/5 · ac: 13 · init: 10 · status: unconscious\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        goblin = result.combatants[0]
        assert goblin.hp_current == 1   # HP preserved from backend
        assert goblin.status == "active"  # guard: hp_current > 0 overrides unconscious

    def test_ac002b_status_unconscious_accepted_at_zero_hp(self):
        """When backend HP reaches 0 the LLM may mark the combatant unconscious."""
        existing = _state(1, _combatant("Goblin 1", hp_current=0, hp_max=5))
        block = (
            "round: 2\n"
            "combatants:\n"
            "  - name: Goblin 1 · hp: 0/5 · ac: 13 · init: 10 · status: unconscious\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        goblin = result.combatants[0]
        assert goblin.hp_current == 0
        assert goblin.status == "unconscious"

    def test_ac002c_status_dead_accepted_at_zero_hp(self):
        """When backend HP is 0 the LLM may mark the combatant dead."""
        existing = _state(1, _combatant("Goblin 1", hp_current=0, hp_max=5))
        block = (
            "round: 2\n"
            "combatants:\n"
            "  - name: Goblin 1 · hp: 0/5 · ac: 13 · init: 10 · status: dead\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        goblin = result.combatants[0]
        assert goblin.hp_current == 0
        assert goblin.status == "dead"

    def test_ac002d_status_dead_blocked_when_hp_positive(self):
        """LLM writing status: dead for a combatant with HP > 0 is overridden to active."""
        existing = _state(1, _combatant("Goblin 1", hp_current=3, hp_max=5))
        block = (
            "round: 2\n"
            "combatants:\n"
            "  - name: Goblin 1 · hp: 0/5 · ac: 13 · init: 10 · status: dead\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        goblin = result.combatants[0]
        assert goblin.hp_current == 3   # backend HP preserved
        assert goblin.status == "active"  # guard: cannot be dead with HP > 0

    def test_ac003_new_combatant_gets_llm_hp(self):
        """A combatant name not in existing_state is initialised with LLM-provided HP."""
        existing = _state(1,
            _combatant("Shalelu", hp_current=18, hp_max=24),
        )
        block = (
            "round: 3\n"
            "combatants:\n"
            "  - name: Shalelu · hp: 24/24 · ac: 17 · init: 14 · status: active\n"
            "  - name: Goblin 2 · hp: 5/5 · ac: 13 · init: 8 · status: active\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        shalelu = next(c for c in result.combatants if c.name == "Shalelu")
        assert shalelu.hp_current == 18     # preserved
        goblin2 = next(c for c in result.combatants if c.name == "Goblin 2")
        assert goblin2.hp_current == 5      # new combatant — from LLM
        assert goblin2.hp_max == 5

    def test_name_matching_is_case_insensitive(self):
        """Case variance in LLM output doesn't break HP inheritance."""
        existing = _state(1, _combatant("Shalelu", hp_current=7, hp_max=24))
        block = (
            "round: 2\n"
            "combatants:\n"
            "  - name: shalelu · hp: 24/24 · ac: 17 · init: 14 · status: active\n"
        )
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        assert result.combatants[0].hp_current == 7  # preserved despite case mismatch

    def test_existing_state_none_uses_all_llm_values(self):
        """Explicit None existing_state = combat start, use all LLM values."""
        block = (
            "round: 1\n"
            "combatants:\n"
            "  - name: Hero · hp: 30/30 · ac: 18 · init: 12 · status: active\n"
        )
        result = _parse_combat_block(block, existing_state=None)
        assert result is not None
        assert result.combatants[0].hp_current == 30

    def test_round_zero_clear_sentinel_unaffected_by_existing_state(self):
        """round: 0 still returns the clear sentinel regardless of existing_state."""
        existing = _state(2, _combatant("Shalelu", 7, 24))
        block = "round: 0\ncombatants:\n"
        result = _parse_combat_block(block, existing_state=existing)
        assert result is not None
        assert result.round == 0
        assert result.combatants == []

    def test_parse_failure_still_returns_none(self):
        """Malformed block still returns None even with existing_state provided."""
        existing = _state(1, _combatant("Shalelu", 7, 24))
        result = _parse_combat_block("combatants:\n  - name: Shalelu\n", existing_state=existing)
        assert result is None  # no round: field → parse failure

    def test_backwards_compatible_no_arg(self):
        """Calling _parse_combat_block without existing_state still works (default None)."""
        block = "round: 1\ncombatants:\n  - name: Hero · hp: 10/10 · ac: 12 · init: 8\n"
        result = _parse_combat_block(block)
        assert result is not None
        assert result.combatants[0].hp_current == 10


# ── _parse_hp_deltas ──────────────────────────────────────────────────────────

class TestParseHpDeltas:
    """Unit tests for the %%HP%% block parser."""

    def test_single_negative_delta(self):
        text = "- name: Shalelu · delta: -8\n"
        deltas = _parse_hp_deltas(text)
        assert deltas == [("Shalelu", -8)]

    def test_single_positive_delta_with_plus(self):
        text = "- name: Thaelion · delta: +6\n"
        deltas = _parse_hp_deltas(text)
        assert deltas == [("Thaelion", 6)]

    def test_positive_delta_without_plus(self):
        text = "- name: Goblin 1 · delta: 3\n"
        deltas = _parse_hp_deltas(text)
        assert deltas == [("Goblin 1", 3)]

    def test_multiple_deltas(self):
        text = (
            "- name: Shalelu · delta: -8\n"
            "- name: Thaelion · delta: +6\n"
            "- name: Goblin 1 · delta: -50\n"
        )
        deltas = _parse_hp_deltas(text)
        assert deltas == [("Shalelu", -8), ("Thaelion", 6), ("Goblin 1", -50)]

    def test_empty_text_returns_empty_list(self):
        assert _parse_hp_deltas("") == []
        assert _parse_hp_deltas(None) == []  # type: ignore[arg-type]

    def test_malformed_line_skipped(self):
        text = (
            "- name: Shalelu · delta: -8\n"
            "this is not a valid line\n"
            "- name: Thaelion · delta: +3\n"
        )
        deltas = _parse_hp_deltas(text)
        assert deltas == [("Shalelu", -8), ("Thaelion", 3)]

    def test_missing_delta_field_skipped(self):
        text = "- name: Shalelu · ac: 17\n"
        assert _parse_hp_deltas(text) == []

    def test_non_integer_delta_skipped(self):
        text = "- name: Shalelu · delta: lots\n"
        assert _parse_hp_deltas(text) == []


# ── _apply_hp_deltas ──────────────────────────────────────────────────────────

class TestApplyHpDeltas:
    """Unit tests for applying %%HP%% deltas to a CombatState."""

    def test_ac005_damage_applied(self):
        """AC-005: negative delta reduces hp_current."""
        state = _state(2, _combatant("Thaelion", 22, 22))
        _apply_hp_deltas(state, [("Thaelion", -8)])
        assert state.combatants[0].hp_current == 14

    def test_ac006_healing_applied_clamped_to_max(self):
        """AC-006: positive delta increases hp_current but clamps at hp_max."""
        state = _state(2, _combatant("Shalelu", 7, 24))
        _apply_hp_deltas(state, [("Shalelu", 20)])
        assert state.combatants[0].hp_current == 24

    def test_ac007_overkill_clamped_to_zero(self):
        """AC-007: damage beyond current HP clamps to 0."""
        state = _state(2, _combatant("Goblin 1", 3, 5))
        _apply_hp_deltas(state, [("Goblin 1", -50)])
        assert state.combatants[0].hp_current == 0

    def test_ac008_unknown_name_silently_ignored(self):
        """AC-008: delta for a name not in combat_state raises no error."""
        state = _state(2, _combatant("Shalelu", 18, 24))
        _apply_hp_deltas(state, [("Ghost", -5)])
        assert state.combatants[0].hp_current == 18  # unchanged

    def test_multiple_deltas_applied_in_order(self):
        state = _state(2,
            _combatant("Shalelu", 20, 24),
            _combatant("Goblin 1", 4, 5),
        )
        _apply_hp_deltas(state, [("Shalelu", -6), ("Goblin 1", -10)])
        assert state.combatants[0].hp_current == 14
        assert state.combatants[1].hp_current == 0  # clamped

    def test_case_insensitive_name_match(self):
        state = _state(2, _combatant("Shalelu", 18, 24))
        _apply_hp_deltas(state, [("shalelu", -3)])
        assert state.combatants[0].hp_current == 15

    def test_none_combat_state_raises_no_error(self):
        """_apply_hp_deltas with None state should not raise (graceful no-op)."""
        _apply_hp_deltas(None, [("Shalelu", -8)])  # type: ignore[arg-type]


# ── AC-004 — HP context injection ─────────────────────────────────────────────

class TestHpContextInjection:
    """AC-004: [CURRENT HP] block appears in system_content when combat is active."""

    def test_hp_block_present_when_combat_active(self, booted_session):
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)

        session.combat_state = _state(2,
            _combatant("Shalelu", 7, 24),
            _combatant("Goblin 1", 0, 5),
        )
        session.combat_state.combatants[1].status = "unconscious"

        system_content, _ = _inject_context(session)
        assert "[CURRENT HP]" in system_content
        assert "Shalelu" in system_content
        assert "7/24" in system_content
        assert "Goblin 1" in system_content
        assert "0/5" in system_content

    def test_hp_block_absent_when_no_combat(self, booted_session):
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)
        session.combat_state = None

        system_content, _ = _inject_context(session)
        assert "[CURRENT HP]" not in system_content


# ── AC-009 — %%HP%% stripped from player stream ───────────────────────────────

class TestHpBlockStrippedFromStream:
    """AC-009: %%HP%% block is hidden from the player token stream."""

    def test_hp_block_not_in_token_stream(self, client):
        """%%HP%% content never reaches the player in non-dev mode."""
        boot = client.post("/api/sessions", json={
            "session_number": 1, "model": "qwen3:4b",
            "host": "http://localhost:11434", "temperature": 0.3, "dev_mode": False,
        })
        session_id = next(e["session_id"] for e in parse_sse(boot) if e["type"] == "done")

        # Set up combat state so %%HP%% will be processed
        import api.session_manager as sm
        session = sm.get_session(session_id)
        session.combat_state = _state(1, _combatant("Shalelu", 20, 24))

        response_text = (
            "%%NARRATIVE%%\n\nThe trap fires!\n\n"
            "%%DELTAS%%\n[]\n\n"
            "%%HP%%\n"
            "- name: Shalelu · delta: -8\n"
            "%%COMBAT%%\n"
            "round: 2\n"
            "combatants:\n"
            "  - name: Shalelu · ac: 17 · init: 14 · status: active\n"
        )
        mock_resp = make_stream_response([response_text])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "We press on."})

        events = parse_sse(resp)
        token_content = "".join(e["content"] for e in events if e["type"] == "token")
        assert "%%HP%%" not in token_content
        assert "delta:" not in token_content
        assert "The trap fires" in token_content


# ── SSE integration — HP deltas update combat_state ───────────────────────────

class TestHpDeltaIntegration:
    """%%HP%% block in a full turn response updates session.combat_state HP."""

    def test_hp_delta_discarded_via_turn(self, booted_session):
        """CB1.9-4: %%HP%% block in LLM response is now silently discarded."""
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)

        # Establish combat state
        session.combat_state = _state(1,
            _combatant("Shalelu", 22, 24),
            _combatant("Goblin 1", 5, 5),
        )

        response_text = (
            "%%NARRATIVE%%\n\nThe trap fires!\n\n"
            "%%DELTAS%%\n[]\n\n"
            "%%HP%%\n"
            "- name: Shalelu · delta: -8\n"
            "- name: Goblin 1 · delta: -50\n"
            "%%COMBAT%%\n"
            "round: 2\n"
            "combatants:\n"
            "  - name: Shalelu · ac: 17 · init: 14 · status: active\n"
            "  - name: Goblin 1 · ac: 13 · init: 10 · status: unconscious\n"
        )
        mock_resp = make_stream_response([response_text])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "We walk in."})

        shalelu = next(c for c in session.combat_state.combatants if c.name == "Shalelu")
        goblin = next(c for c in session.combat_state.combatants if c.name == "Goblin 1")
        # %%HP%% discarded — HP unchanged from what was set before the turn
        assert shalelu.hp_current == 22
        assert goblin.hp_current == 5

    def test_hp_preserved_across_round_update(self, booted_session):
        """Round 2 %%COMBAT%% block does not overwrite backend HP values."""
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)

        session.combat_state = _state(1,
            _combatant("Shalelu", 7, 24),
        )

        response_text = (
            "%%NARRATIVE%%\n\nCombat continues!\n\n"
            "%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\n"
            "round: 2\n"
            "combatants:\n"
            "  - name: Shalelu · hp: 24/24 · ac: 17 · init: 14 · status: active\n"
        )
        mock_resp = make_stream_response([response_text])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "I wait."})

        shalelu = session.combat_state.combatants[0]
        assert shalelu.hp_current == 7   # preserved — LLM wrote 24 but backend wins


# ── _get_combatant_ac ─────────────────────────────────────────────────────────

class TestGetCombatantAc:
    """Shared lookup utility used by both HP authority and attack resolution."""

    def test_found(self):
        state = CombatState(round=1, combatants=[
            Combatant(name="Shalelu", hp_current=18, hp_max=24, ac=17, initiative=14),
        ])
        assert _get_combatant_ac("Shalelu", state) == 17

    def test_case_insensitive(self):
        state = CombatState(round=1, combatants=[
            Combatant(name="Shalelu", hp_current=18, hp_max=24, ac=17, initiative=14),
        ])
        assert _get_combatant_ac("shalelu", state) == 17

    def test_not_found_returns_10(self):
        state = CombatState(round=1, combatants=[
            Combatant(name="Shalelu", hp_current=18, hp_max=24, ac=17, initiative=14),
        ])
        assert _get_combatant_ac("Ghost", state) == 10

    def test_none_state_returns_10(self):
        assert _get_combatant_ac("Anyone", None) == 10
