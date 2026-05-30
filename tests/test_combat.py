"""Tests for the Tier 1 combat tracker system.

Covers: Combatant / CombatState dataclasses, _parse_combatant_line,
_parse_combat_block, _serialize_combat_state, %%COMBAT%% SSE integration,
narrative filter stripping %%COMBAT%%, and the DELETE /combat endpoint.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from api.session_manager import (
    Combatant,
    CombatState,
    _parse_combatant_line,
    _parse_combat_block,
    _serialize_combat_state,
    _VALID_CONDITIONS,
)
from .conftest import make_stream_response, parse_sse


# ── Combatant dataclass ───────────────────────────────────────────────────────

class TestCombatant:
    def test_valid_combatant(self):
        c = Combatant(name="Shalelu", hp_current=18, hp_max=24, ac=17, initiative=14)
        assert c.name == "Shalelu"
        assert c.hp_current == 18
        assert c.hp_max == 24
        assert c.status == "active"

    def test_hp_clamp_current_exceeds_max(self):
        c = Combatant(name="X", hp_current=30, hp_max=20, ac=10, initiative=0)
        assert c.hp_current == 20

    def test_hp_clamp_negative(self):
        c = Combatant(name="X", hp_current=-5, hp_max=20, ac=10, initiative=0)
        assert c.hp_current == 0

    def test_unknown_status_defaults_to_active(self):
        c = Combatant(name="X", hp_current=5, hp_max=10, ac=10, initiative=0, status="banana")
        assert c.status == "active"

    def test_valid_statuses_preserved(self):
        for s in ("active", "unconscious", "fled", "dead"):
            assert Combatant(name="X", hp_current=5, hp_max=5, ac=10, initiative=0, status=s).status == s


# ── _parse_combatant_line ─────────────────────────────────────────────────────

class TestParseCombatantLine:
    def test_happy_path(self):
        line = "  - name: Shalelu · hp: 18/24 · ac: 17 · init: 14 · status: active"
        c = _parse_combatant_line(line)
        assert c is not None
        assert c.name == "Shalelu"
        assert c.hp_current == 18
        assert c.hp_max == 24
        assert c.ac == 17
        assert c.initiative == 14
        assert c.status == "active"

    def test_missing_name_returns_none(self):
        assert _parse_combatant_line("  - hp: 5/5 · ac: 13 · init: 8") is None

    def test_partial_fields_use_defaults(self):
        c = _parse_combatant_line("  - name: Goblin 1 · hp: 3/5")
        assert c is not None
        assert c.ac == 10
        assert c.initiative == 0
        assert c.status == "active"

    def test_hp_single_value(self):
        # If LLM omits the /max part, treat it as current == max
        c = _parse_combatant_line("  - name: Goblin · hp: 5 · ac: 13 · init: 8 · status: active")
        assert c is not None
        assert c.hp_current == 5
        assert c.hp_max == 5

    def test_bullet_dot_variant(self):
        """Some LLMs may use • (U+2022) instead of · (U+00B7)."""
        c = _parse_combatant_line("- name: Orc • hp: 10/15 • ac: 14 • init: 6 • status: active")
        assert c is not None
        assert c.name == "Orc"

    def test_unconscious_status(self):
        c = _parse_combatant_line("  - name: Goblin 1 · hp: 0/5 · ac: 13 · init: 12 · status: unconscious")
        assert c is not None
        assert c.status == "unconscious"
        assert c.hp_current == 0

    def test_bare_name_format(self):
        """Anthropic-style: 'Goblin Warrior 1 · hp: 5/5 · ac: 16 · ...' (no 'name:' label)."""
        c = _parse_combatant_line("Goblin Warrior 1 · hp: 5/5 · ac: 16 · init: +4 · status: active")
        assert c is not None
        assert c.name == "Goblin Warrior 1"
        assert c.hp_current == 5
        assert c.hp_max == 5
        assert c.ac == 16

    def test_middle_dot_prefix_bare_name(self):
        """Groq-style: '· Vanx · hp: 10/10 · ac: 18 · ...' (middle-dot prefix, no 'name:' label)."""
        c = _parse_combatant_line("· Vanx · hp: 10/10 · ac: 18 · init: +2 · status: active")
        assert c is not None
        assert c.name == "Vanx"
        assert c.hp_current == 10
        assert c.hp_max == 10
        assert c.ac == 18

    def test_init_em_dash_defaults_to_zero(self):
        """'init: —' (em-dash) should not crash — falls back to 0."""
        c = _parse_combatant_line("Goblin Warchanter · hp: 8/8 · ac: 14 · init: — · status: active")
        assert c is not None
        assert c.name == "Goblin Warchanter"
        assert c.initiative == 0

    def test_trailing_extra_field_ignored(self):
        """Extra non-key fields after status (e.g. '· singing') are silently ignored."""
        c = _parse_combatant_line("Goblin Warchanter · hp: 8/8 · ac: 14 · init: — · status: active · singing")
        assert c is not None
        assert c.status == "active"


# ── _parse_combat_block ───────────────────────────────────────────────────────

_VALID_BLOCK = """\
round: 2
combatants:
  - name: Shalelu      · hp: 18/24 · ac: 17 · init: 14 · status: active
  - name: Goblin 1     · hp: 0/5   · ac: 13 · init: 12 · status: unconscious
  - name: Thaelion     · hp: 22/22 · ac: 16 · init:  6 · status: active
"""


class TestParseCombatBlock:
    def test_happy_path(self):
        state = _parse_combat_block(_VALID_BLOCK)
        assert state is not None
        assert state.round == 2
        assert len(state.combatants) == 3
        assert state.combatants[0].name == "Shalelu"

    def test_round_zero_returns_clear_sentinel(self):
        """round: 0 is an intentional clear signal — returns CombatState(round=0), NOT None."""
        block = "round: 0\ncombatants:\n  - name: X · hp: 5/5 · ac: 10 · init: 5\n"
        result = _parse_combat_block(block)
        assert result is not None
        assert result.round == 0
        assert result.combatants == []

    def test_bare_name_format_block(self):
        """Anthropic-style block: name as first unlabeled segment, no leading bullet."""
        block = (
            "round: 1\n"
            "Goblin Warrior 1 · hp: 5/5 · ac: 16 · init: — · status: active\n"
            "Goblin Warrior 2 · hp: 5/5 · ac: 16 · init: — · status: active\n"
            "Goblin Warchanter · hp: 8/8 · ac: 14 · init: — · status: active · singing\n"
        )
        state = _parse_combat_block(block)
        assert state is not None
        assert state.round == 1
        assert len(state.combatants) == 3
        assert state.combatants[0].name == "Goblin Warrior 1"
        assert state.combatants[2].name == "Goblin Warchanter"
        assert state.combatants[2].status == "active"

    def test_groq_middle_dot_prefix_block(self):
        """Groq-style block: middle-dot prefix on each row, name unlabeled."""
        block = (
            "round: 1\n"
            "· Vanx · hp: 10/10 · ac: 18 · init: +2 · status: active\n"
            "· Goblin warrior 1 · hp: 5/5 · ac: 16 · init: +4 · status: active\n"
        )
        state = _parse_combat_block(block)
        assert state is not None
        assert state.round == 1
        assert len(state.combatants) == 2
        assert state.combatants[0].name == "Vanx"
        assert state.combatants[1].name == "Goblin warrior 1"

    def test_no_round_field_returns_none(self):
        """Block with combatants but no round: line is a parse failure → None (preserve state)."""
        block = "combatants:\n  - name: Goblin · hp: 5/5 · ac: 13 · init: 8 · status: active\n"
        assert _parse_combat_block(block) is None

    def test_no_combatants_returns_none(self):
        assert _parse_combat_block("round: 1\ncombatants:\n") is None

    def test_none_input_returns_none(self):
        assert _parse_combat_block(None) is None  # type: ignore[arg-type]

    def test_empty_string_returns_none(self):
        assert _parse_combat_block("") is None

    def test_malformed_combatant_line_skipped(self):
        block = (
            "round: 1\n"
            "combatants:\n"
            "  - not a combatant line\n"
            "  - name: Goblin · hp: 5/5 · ac: 13 · init: 8 · status: active\n"
        )
        state = _parse_combat_block(block)
        assert state is not None
        assert len(state.combatants) == 1

    def test_hp_values_clamped(self):
        block = "round: 1\ncombatants:\n  - name: Hero · hp: 30/20 · ac: 15 · init: 10 · status: active\n"
        state = _parse_combat_block(block)
        assert state is not None
        assert state.combatants[0].hp_current == 20  # clamped to max


# ── _serialize_combat_state ───────────────────────────────────────────────────

class TestSerializeCombatState:
    def test_none_returns_none(self):
        assert _serialize_combat_state(None) is None

    def test_serializes_correctly(self):
        state = CombatState(
            round=3,
            combatants=[
                Combatant(name="A", hp_current=10, hp_max=20, ac=15, initiative=12, status="active"),
                Combatant(name="B", hp_current=0,  hp_max=8,  ac=12, initiative=5,  status="unconscious"),
            ],
        )
        d = _serialize_combat_state(state)
        assert d is not None
        assert d["round"] == 3
        assert len(d["combatants"]) == 2
        first = d["combatants"][0]
        assert first["name"] == "A"
        assert first["hp_current"] == 10
        assert first["hp_max"] == 20
        assert first["ac"] == 15
        assert first["initiative"] == 12
        assert first["status"] == "active"


# ── SSE integration: combat_update event ──────────────────────────────────────

class TestCombatSseIntegration:
    def test_combat_update_null_when_no_block(self, booted_session):
        """Every turn emits combat_update; it is null when no %%COMBAT%% block."""
        client, session_id = booted_session
        tokens = ["%%NARRATIVE%%\n\nAll is quiet.\n\n%%DELTAS%%\n[]\n"]
        mock_resp = make_stream_response(tokens)
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Look around."})
        events = parse_sse(resp)
        combat_events = [e for e in events if e["type"] == "combat_update"]
        assert len(combat_events) == 1
        assert combat_events[0]["combat_state"] is None

    def test_combat_update_populated_when_block_present(self, booted_session):
        """%%COMBAT%% block in response populates combat_update event."""
        client, session_id = booted_session
        combat_block = (
            "%%NARRATIVE%%\n\nGoblins charge!\n\n"
            "%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\n"
            "round: 1\n"
            "combatants:\n"
            "  - name: Goblin 1 · hp: 5/5 · ac: 13 · init: 12 · status: active\n"
            "  - name: Thaelion · hp: 22/22 · ac: 16 · init: 8 · status: active\n"
        )
        mock_resp = make_stream_response([combat_block])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Fight!"})
        events = parse_sse(resp)
        combat_events = [e for e in events if e["type"] == "combat_update"]
        assert len(combat_events) == 1
        state = combat_events[0]["combat_state"]
        assert state is not None
        assert state["round"] == 1
        assert len(state["combatants"]) == 2
        assert state["combatants"][0]["name"] == "Goblin 1"

    def test_combat_state_persists_to_next_turn(self, booted_session):
        """session.combat_state survives between turns; cleared to null by round: 0."""
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)

        # Turn 1: start combat
        block1 = (
            "%%NARRATIVE%%\n\nFight!\n\n%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\nround: 1\ncombatants:\n"
            "  - name: Goblin · hp: 5/5 · ac: 13 · init: 10 · status: active\n"
        )
        mock_resp = make_stream_response([block1])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Attack!"})
        assert session.combat_state is not None
        assert session.combat_state.round == 1

        # Turn 2: end combat (round: 0)
        block2 = "%%NARRATIVE%%\n\nGoblin flees.\n\n%%DELTAS%%\n[]\n\n%%COMBAT%%\nround: 0\ncombatants:\n"
        mock_resp2 = make_stream_response([block2])
        with patch("api.session_manager._requests.post", return_value=mock_resp2):
            resp2 = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Victory?"})
        assert session.combat_state is None
        events2 = parse_sse(resp2)
        combat_events2 = [e for e in events2 if e["type"] == "combat_update"]
        assert combat_events2[0]["combat_state"] is None

    def test_malformed_block_preserves_existing_state(self, booted_session):
        """A malformed %%COMBAT%% block (no round: line) must NOT wipe existing combat state.

        Regression for Bug 2: _parse_combat_block returning None for both intentional clear
        AND parse failure caused valid state to be silently wiped on any bad LLM turn.
        """
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)

        # Establish valid combat state directly
        session.combat_state = CombatState(
            round=1,
            combatants=[Combatant(name="Goblin", hp_current=5, hp_max=5, ac=13, initiative=10)],
        )

        # Turn with a malformed %%COMBAT%% block (missing round: field)
        bad_block = (
            "%%NARRATIVE%%\n\nFighting continues!\n\n%%DELTAS%%\n[]\n\n"
            "%%COMBAT%%\ncombatants:\n"
            "  - name: Goblin · hp: 4/5 · ac: 13 · init: 10 · status: active\n"
        )
        mock_resp = make_stream_response([bad_block])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            client.post(f"/api/sessions/{session_id}/turn", json={"input": "Continue!"})

        # State must be unchanged — parse failure leaves existing state intact
        assert session.combat_state is not None
        assert session.combat_state.round == 1
        assert session.combat_state.combatants[0].name == "Goblin"

    def test_combat_only_response_does_not_leak_markup(self, client):
        """A response with %%COMBAT%% but no %%NARRATIVE%% must NOT show raw markup to the player.

        Regression for Bug 1: adding COMBAT to _HAS_SECTION_MARKERS_RE caused COMBAT-only
        responses to route to the sections path. The NARRATIVE fallback then injected the raw
        %%COMBAT%% block as display_text, leaking markup to the player token stream.
        """
        boot = client.post("/api/sessions", json={
            "session_number": 1, "model": "qwen3:4b",
            "host": "http://localhost:11434", "temperature": 0.3, "dev_mode": False,
        })
        boot_events = parse_sse(boot)
        session_id = next(e["session_id"] for e in boot_events if e["type"] == "done")

        # Response has %%COMBAT%% but NO %%NARRATIVE%% — the flat/fallback path should handle it
        combat_only = (
            "%%COMBAT%%\n"
            "round: 1\n"
            "combatants:\n"
            "  - name: Goblin · hp: 5/5 · ac: 13 · init: 10 · status: active\n"
        )
        mock_resp = make_stream_response([combat_only])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Fight!"})

        events = parse_sse(resp)
        token_content = "".join(e["content"] for e in events if e["type"] == "token")
        assert "%%COMBAT%%" not in token_content
        assert "round:" not in token_content
        assert "combatants:" not in token_content

    def test_combat_block_stripped_from_player_stream(self, client):
        """%%COMBAT%% block is not visible in token stream (same as %%DELTAS%%).

        Uses dev_mode=False so _stream_with_narrative_filter is active.
        """
        # Boot a non-dev session so the narrative filter runs.
        boot = client.post("/api/sessions", json={
            "session_number": 1, "model": "qwen3:4b",
            "host": "http://localhost:11434", "temperature": 0.3, "dev_mode": False,
        })
        boot_events = parse_sse(boot)
        session_id = next(e["session_id"] for e in boot_events if e["type"] == "done")

        combat_block = (
            "%%NARRATIVE%%\n\nBlades clash!\n\n"
            "%%COMBAT%%\n"
            "round: 1\n"
            "combatants:\n"
            "  - name: Goblin · hp: 5/5 · ac: 13 · init: 10 · status: active\n"
        )
        mock_resp = make_stream_response([combat_block])
        with patch("api.session_manager._requests.post", return_value=mock_resp):
            resp = client.post(f"/api/sessions/{session_id}/turn", json={"input": "Draw sword."})
        events = parse_sse(resp)
        token_content = "".join(e["content"] for e in events if e["type"] == "token")
        assert "%%COMBAT%%" not in token_content
        assert "round:" not in token_content
        assert "Blades clash" in token_content


# ── DELETE /combat endpoint ───────────────────────────────────────────────────

class TestEndCombatEndpoint:
    def test_delete_combat_clears_state(self, booted_session):
        """DELETE /api/sessions/{id}/combat clears session.combat_state."""
        import api.session_manager as sm
        client, session_id = booted_session
        session = sm.get_session(session_id)

        # Set combat state directly
        session.combat_state = CombatState(
            round=2,
            combatants=[Combatant(name="X", hp_current=5, hp_max=5, ac=10, initiative=5)],
        )
        assert session.combat_state is not None

        resp = client.delete(f"/api/sessions/{session_id}/combat")
        assert resp.status_code == 200
        assert resp.json()["combat_state"] is None
        assert session.combat_state is None

    def test_delete_combat_missing_session(self, client):
        resp = client.delete("/api/sessions/nonexistent/combat")
        assert resp.status_code == 404


# ── Combatant conditions (Tier 1.5 extension) ────────────────────────────────

class TestCombatantConditions:
    def test_conditions_parsed_from_line(self):
        line = "- name: Shalelu · ac: 17 · init: 14 · status: active · conditions: [prone, shaken]"
        c = _parse_combatant_line(line)
        assert c is not None
        assert "prone" in c.conditions
        assert "shaken" in c.conditions

    def test_unknown_condition_dropped(self):
        line = "- name: X · ac: 10 · init: 5 · status: active · conditions: [prone, banana]"
        c = _parse_combatant_line(line)
        assert "prone" in c.conditions
        assert "banana" not in c.conditions

    def test_no_conditions_field_returns_empty_list(self):
        line = "- name: X · hp: 5/5 · ac: 10 · init: 5 · status: active"
        c = _parse_combatant_line(line)
        assert c.conditions == []

    def test_conditions_in_serialized_state(self):
        state = CombatState(round=1, combatants=[
            Combatant(name="Shalelu", hp_current=18, hp_max=24, ac=17, initiative=14,
                      conditions=["prone"]),
        ])
        d = _serialize_combat_state(state)
        assert d["combatants"][0]["conditions"] == ["prone"]

    def test_all_valid_conditions_accepted(self):
        for cond in _VALID_CONDITIONS:
            c = Combatant(name="X", hp_current=5, hp_max=5, ac=10, initiative=0,
                          conditions=[cond])
            assert cond in c.conditions
