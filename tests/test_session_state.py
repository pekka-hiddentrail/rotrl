"""Tests for session state file persistence (specs/session-state.feature).

The state file lives at sessions/session_NNN/state.json and is the lightweight
"state of play" snapshot for mode (social/combat), round number, active events,
and the currently active character ("party" when none is selected).

Spec: specs/session-state.feature
Covers: AC-001 through AC-017
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from api.session_manager import (
    ActiveEvent,
    Combatant,
    CombatState,
    GameSession,
    _session_state_path,
    _write_session_state,
    set_active_character,
    write_session_state,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE  = _REPO_ROOT / "sessions" / "state.template.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(session_number: int = 1, tmp_path: Path | None = None, **kwargs) -> GameSession:
    return GameSession(
        id=str(uuid.uuid4()),
        session_number=session_number,
        model="test-model",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=False,
        provider="ollama",
        num_ctx=2048,
        num_gpu=999,
        system_prompt="SYSTEM",
        log_path=None,
        **kwargs,
    )


def _read_state(session: GameSession) -> dict:
    return json.loads(_session_state_path(session).read_text(encoding="utf-8"))


def _patch_state_root(tmp_path: Path):
    """Return a context manager that redirects _session_state_path writes to tmp_path."""
    def _fake_path(session):
        return tmp_path / f"session_{session.session_number:03d}" / "state.json"
    return patch("api.session_manager._session_state_path", side_effect=_fake_path)


# ── AC-001 — Template shape ───────────────────────────────────────────────────

class TestTemplate:
    def test_template_exists(self):
        assert _TEMPLATE.exists(), "sessions/state.template.json not found"

    def test_template_is_valid_json(self):
        data = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_template_has_required_keys(self):
        data = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
        assert "mode"   in data
        assert "round"  in data
        assert "events" in data

    def test_template_defaults(self):
        data = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
        assert data["mode"]   == "social"
        assert data["round"]  == 0
        assert data["events"] == []


# ── AC-002 / AC-003 — Boot initialises state.json ────────────────────────────

class TestBootInit:
    def test_boot_creates_state_file(self, tmp_path):
        session = _make_session(session_number=1)
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        state_path = tmp_path / "session_001" / "state.json"
        assert state_path.exists()

    def test_boot_state_defaults_to_social(self, tmp_path):
        session = _make_session(session_number=1)
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["mode"]   == "social"
        assert data["round"]  == 0
        assert data["events"] == []

    def test_boot_creates_directory_if_missing(self, tmp_path):
        session = _make_session(session_number=99)
        target = tmp_path / "session_099"
        assert not target.exists()
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        assert (target / "state.json").exists()

    def test_boot_uses_session_number_in_path(self, tmp_path):
        for num in (1, 5, 42):
            session = _make_session(session_number=num)
            with _patch_state_root(tmp_path):
                _write_session_state(session)
            assert (tmp_path / f"session_{num:03d}" / "state.json").exists()


# ── AC-004 / AC-005 — Combat state changes ────────────────────────────────────

class TestCombatStateChanges:
    def test_combat_start_sets_mode_combat(self, tmp_path):
        session = _make_session()
        session.combat_state = CombatState(round=1, combatants=[])
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["mode"]  == "combat"
        assert data["round"] == 1

    def test_round_advance_updates_round_field(self, tmp_path):
        session = _make_session()
        session.combat_state = CombatState(round=1, combatants=[])
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        session.combat_state = CombatState(round=2, combatants=[])
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["round"] == 2

    def test_combat_with_combatants_records_round(self, tmp_path):
        session = _make_session()
        session.combat_state = CombatState(
            round=3,
            combatants=[
                Combatant(name="Goblin 1", hp_current=5, hp_max=5, ac=13, initiative=8),
                Combatant(name="Thaelion", hp_current=22, hp_max=22, ac=16, initiative=15),
            ],
        )
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["mode"]  == "combat"
        assert data["round"] == 3


# ── AC-006 / AC-007 — Combat clear ────────────────────────────────────────────

class TestCombatClear:
    def test_clear_resets_mode_to_social(self, tmp_path):
        session = _make_session()
        session.combat_state = CombatState(round=2, combatants=[])
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        session.combat_state = None
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["mode"]  == "social"
        assert data["round"] == 0

    def test_clear_preserves_events_if_any_active(self, tmp_path):
        session = _make_session()
        session.combat_state = CombatState(round=1, combatants=[])
        session.active_events = [ActiveEvent(event_id="evt_a", content="X", turns_remaining=3)]
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        session.combat_state = None
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["mode"]   == "social"
        assert data["events"] == ["evt_a"]

    def test_public_write_session_state_alias(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            write_session_state(session)
        assert (tmp_path / "session_001" / "state.json").exists()


# ── AC-008 / AC-009 / AC-010 — Event tracking ─────────────────────────────────

class TestEventTracking:
    def test_single_event_appears_in_list(self, tmp_path):
        session = _make_session()
        session.active_events = [ActiveEvent(event_id="goblin_raid", content="X", turns_remaining=5)]
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["events"] == ["goblin_raid"]

    def test_multiple_events_all_appear(self, tmp_path):
        session = _make_session()
        session.active_events = [
            ActiveEvent(event_id="evt_a", content="X", turns_remaining=5),
            ActiveEvent(event_id="evt_b", content="Y", turns_remaining=2),
        ]
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert set(data["events"]) == {"evt_a", "evt_b"}

    def test_expired_event_removed_from_list(self, tmp_path):
        session = _make_session()
        session.active_events = [ActiveEvent(event_id="goblin_raid", content="X", turns_remaining=5)]
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        session.active_events = []
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["events"] == []

    def test_no_events_gives_empty_list(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["events"] == []


# ── AC-011 — Output is always valid JSON ──────────────────────────────────────

class TestOutputValidity:
    @pytest.mark.parametrize("combat_state,events", [
        (None, []),
        (CombatState(round=1, combatants=[]), []),
        (CombatState(round=5, combatants=[]), [ActiveEvent("e1", "X", 3)]),
        (None, [ActiveEvent("e2", "Y", 2), ActiveEvent("e3", "Z", 1)]),
    ])
    def test_output_is_valid_json(self, tmp_path, combat_state, events):
        session = _make_session()
        session.combat_state  = combat_state
        session.active_events = events
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        raw = (tmp_path / "session_001" / "state.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert "mode"             in data
        assert "round"            in data
        assert "events"           in data
        assert "active_character" in data

    def test_mode_is_always_string(self, tmp_path):
        for state in (None, CombatState(round=1, combatants=[])):
            session = _make_session()
            session.combat_state = state
            with _patch_state_root(tmp_path):
                _write_session_state(session)
            data = json.loads((tmp_path / "session_001" / "state.json").read_text())
            assert isinstance(data["mode"], str)

    def test_round_is_always_int(self, tmp_path):
        for state in (None, CombatState(round=3, combatants=[])):
            session = _make_session()
            session.combat_state = state
            with _patch_state_root(tmp_path):
                _write_session_state(session)
            data = json.loads((tmp_path / "session_001" / "state.json").read_text())
            assert isinstance(data["round"], int)

    def test_events_is_always_list(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert isinstance(data["events"], list)


# ── AC-012 — Boot overwrites existing state.json ──────────────────────────────

class TestBootOverwrite:
    def test_boot_resets_stale_combat_state(self, tmp_path):
        state_path = tmp_path / "session_001" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"mode": "combat", "round": 4, "events": ["old_event"]}),
            encoding="utf-8",
        )
        session = _make_session(session_number=1)
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["mode"]             == "social"
        assert data["round"]            == 0
        assert data["events"]           == []
        assert data["active_character"] == "party"


# ── AC-013 — Boot defaults active_character ───────────────────────────────────

class TestActiveCharacterDefaults:
    def test_boot_defaults_to_party(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "party"

    def test_default_on_fresh_session(self):
        session = _make_session()
        assert session.active_character == "party"


# ── AC-014 / AC-015 / AC-016 — set_active_character ──────────────────────────

class TestSetActiveCharacter:
    def test_set_pc_name(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            set_active_character(session, "Ani")
        assert session.active_character == "Ani"
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "Ani"

    def test_set_party_deselects(self, tmp_path):
        session = _make_session()
        session.active_character = "Yanyeeku"
        with _patch_state_root(tmp_path):
            set_active_character(session, "party")
        assert session.active_character == "party"
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "party"

    def test_empty_string_falls_back_to_party(self, tmp_path):
        session = _make_session()
        session.active_character = "Vanx"
        with _patch_state_root(tmp_path):
            set_active_character(session, "")
        assert session.active_character == "party"
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "party"

    def test_whitespace_only_falls_back_to_party(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            set_active_character(session, "   ")
        assert session.active_character == "party"

    def test_set_writes_state_file(self, tmp_path):
        session = _make_session()
        with _patch_state_root(tmp_path):
            set_active_character(session, "Thaelion")
        assert (tmp_path / "session_001" / "state.json").exists()

    def test_multiple_characters_in_sequence(self, tmp_path):
        session = _make_session()
        for name in ("Ani", "Yanyeeku", "Vanx", "party"):
            with _patch_state_root(tmp_path):
                set_active_character(session, name)
            data = json.loads((tmp_path / "session_001" / "state.json").read_text())
            assert data["active_character"] == name


# ── AC-017 — active_character survives other state changes ────────────────────

class TestActiveCharacterPersistence:
    def test_persists_across_combat_start(self, tmp_path):
        session = _make_session()
        session.active_character = "Yanyeeku"
        session.combat_state = CombatState(round=1, combatants=[])
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "Yanyeeku"
        assert data["mode"] == "combat"

    def test_persists_across_combat_clear(self, tmp_path):
        session = _make_session()
        session.active_character = "Ani"
        session.combat_state = CombatState(round=2, combatants=[])
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        session.combat_state = None
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "Ani"
        assert data["mode"] == "social"

    def test_persists_across_event_fire(self, tmp_path):
        session = _make_session()
        session.active_character = "Vanx"
        session.active_events = [ActiveEvent(event_id="goblin_raid", content="X", turns_remaining=5)]
        with _patch_state_root(tmp_path):
            _write_session_state(session)
        data = json.loads((tmp_path / "session_001" / "state.json").read_text())
        assert data["active_character"] == "Vanx"
