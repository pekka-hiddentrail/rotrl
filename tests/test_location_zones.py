"""Tests for location-owned zone graphs and session zone loading."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from api.context.event_index import EventEntry
from api.context.location_lookup import LocationIndex
from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _apply_actor_zone_change,
    _build_session_zone_map,
    apply_zone_move,
    get_location_zone_state,
    _load_event_zone_data,
    _write_session_state,
)


def _session(tmp_path: Path) -> GameSession:
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
    )


def _make_location(tmp_path: Path) -> LocationIndex:
    loc_dir = tmp_path / "adventure_path" / "03_locations" / "festival_square"
    loc_dir.mkdir(parents=True)
    (loc_dir / "base.md").write_text(
        """# Festival Square
**Aliases:** festival square

## Description
A plaza.

## Zones

| id | name | description | visible | source | tags |
|----|------|-------------|---------|--------|------|
| center | Center | Open square. | yes | authored | open |
| alleyway | Alleyway | Side lane. | yes | authored | shadowed |

## Access Points

| id | from | to | label | state | bidirectional | requirements | description |
|----|------|----|-------|-------|---------------|--------------|-------------|
| alleyway_center | alleyway | center | Alley mouth | open | yes | - | Exit to square. |

<!-- REFERENCE -->
**District:** Central Sandpoint
""",
        encoding="utf-8",
    )
    return LocationIndex(_repo_root=tmp_path)


def test_load_event_zone_data_prefers_inline_event_table(tmp_path):
    session = _session(tmp_path)
    entry = EventEntry(
        event_id="evt",
        trigger="test",
        event_type="combat",
        location_id="festival_square",
        content="""## Zones - Festival Square

| Zone | Adjacent to | Properties |
|------|-------------|------------|
| Center | Alleyway | open |
| Alleyway | Center | shadowed |
""",
    )

    _load_event_zone_data(session, entry)

    assert session.current_location_id == "festival_square"
    assert session.zone_map["Center"] == {"Alleyway"}
    assert session.zone_properties["Alleyway"] == ["shadowed"]


def test_load_event_zone_data_falls_back_to_location_file(tmp_path):
    session = _session(tmp_path)
    idx = _make_location(tmp_path)
    entry = EventEntry(
        event_id="evt",
        trigger="test",
        event_type="combat",
        location_id="festival_square",
        content="## Combatants\n\n| Name | HP | AC | Init |\n|---|---|---|---|\n",
    )

    with patch("api.session_manager._get_location_index", return_value=idx):
        _load_event_zone_data(session, entry)

    assert session.zone_map["Alleyway"] == {"Center"}
    assert session.zone_map["Center"] == {"Alleyway"}


def test_build_session_zone_map_uses_session_zone_map(tmp_path):
    session = _session(tmp_path)
    session.zone_map = {"Center": {"Alleyway"}, "Alleyway": {"Center"}}
    session.combat_state = CombatState(
        round=1,
        current_actor="Ani",
        combatants=[
            Combatant(name="Ani", hp_current=10, hp_max=10, ac=15, initiative=5, zone="Center"),
        ],
    )

    zone_map = _build_session_zone_map(session)

    assert zone_map["center"] == "Center"
    assert zone_map["alleyway"] == "Alleyway"


def test_session_state_serializes_zone_map(tmp_path):
    session = _session(tmp_path)
    session.zone_map = {"Center": {"Alleyway"}, "Alleyway": {"Center"}}
    session.zone_properties = {"Alleyway": ["shadowed"]}

    with patch("api.session_manager._session_state_path", return_value=tmp_path / "state.json"):
        _write_session_state(session)

    text = (tmp_path / "state.json").read_text(encoding="utf-8")
    assert '"zone_map"' in text
    assert '"Center"' in text
    assert '"zone_properties"' in text


def test_location_zone_state_shape_for_gui(tmp_path):
    session = _session(tmp_path)
    idx = _make_location(tmp_path)
    session.current_location_id = "festival_square"
    session.party_zone_id = "Center"
    session.zone_map = {"Center": {"Alleyway"}, "Alleyway": {"Center"}}

    with patch("api.session_manager._get_location_index", return_value=idx):
        state = get_location_zone_state(session)

    assert state["current_location"]["id"] == "festival_square"
    assert state["current_zone_id"] == "center"
    assert {z["name"] for z in state["zones"]} == {"Center", "Alleyway"}
    assert state["available_moves"][0]["to_zone_id"] == "alleyway"


# ── LZ-005/006 — zone_move ────────────────────────────────────────────────────

def _session_with_graph(tmp_path: Path):
    """Session wired to festival_square with party in Alleyway."""
    session = _session(tmp_path)
    idx = _make_location(tmp_path)
    session.current_location_id = "festival_square"
    session.party_zone_id = "Alleyway"
    session.zone_map = {"Alleyway": {"Center"}, "Center": {"Alleyway"}}
    return session, idx


def test_zone_move_valid_updates_party_zone(tmp_path):
    session, idx = _session_with_graph(tmp_path)
    with patch("api.session_manager._get_location_index", return_value=idx):
        with patch("api.session_manager._write_session_state"):
            result = apply_zone_move(session, "party", "alleyway_center")
    assert session.party_zone_id == "Center"
    assert result["current_zone_id"] == "center"


def test_zone_move_returns_available_moves_from_new_zone(tmp_path):
    session, idx = _session_with_graph(tmp_path)
    with patch("api.session_manager._get_location_index", return_value=idx):
        with patch("api.session_manager._write_session_state"):
            result = apply_zone_move(session, "party", "alleyway_center")
    # From Center the available move goes back to Alleyway
    dest_ids = {m["to_zone_id"] for m in result["available_moves"]}
    assert "alleyway" in dest_ids


def test_zone_move_bidirectional_from_other_end(tmp_path):
    """alleyway_center is bidirectional — party can use it from Center too."""
    session, idx = _session_with_graph(tmp_path)
    session.party_zone_id = "Center"
    with patch("api.session_manager._get_location_index", return_value=idx):
        with patch("api.session_manager._write_session_state"):
            result = apply_zone_move(session, "party", "alleyway_center")
    assert session.party_zone_id == "Alleyway"
    assert result["current_zone_id"] == "alleyway"


def test_zone_move_unknown_access_point_raises(tmp_path):
    session, idx = _session_with_graph(tmp_path)
    with patch("api.session_manager._get_location_index", return_value=idx):
        with patch("api.session_manager._write_session_state"):
            with pytest.raises(ValueError, match="not found"):
                apply_zone_move(session, "party", "nonexistent_ap")


def test_zone_move_wrong_zone_raises(tmp_path):
    """Party is in Center but tries to use an AP that goes alleyway→center."""
    session, idx = _session_with_graph(tmp_path)
    session.party_zone_id = "Center"
    # Create a one-way AP (not bidirectional) pointing alleyway→center
    (tmp_path / "adventure_path" / "03_locations" / "festival_square" / "base.md").write_text(
        """# Festival Square
**Aliases:** festival square

## Zones

| id | name | description | visible | source | tags |
|----|------|-------------|---------|--------|------|
| center | Center | Open square. | yes | authored | open |
| alleyway | Alleyway | Side lane. | yes | authored | shadowed |

## Access Points

| id | from | to | label | state | bidirectional | requirements | description |
|----|------|----|-------|-------|---------------|--------------|-------------|
| alleyway_center | alleyway | center | Alley mouth | open | no | - | One-way exit. |

<!-- REFERENCE -->
""",
        encoding="utf-8",
    )
    idx2 = LocationIndex(_repo_root=tmp_path)
    with patch("api.session_manager._get_location_index", return_value=idx2):
        with patch("api.session_manager._write_session_state"):
            with pytest.raises(ValueError, match="not reachable"):
                apply_zone_move(session, "party", "alleyway_center")


def test_apply_actor_zone_change_updates_combatant(tmp_path):
    session = _session(tmp_path)
    session.combat_state = CombatState(
        round=1,
        current_actor="Goblin",
        combatants=[Combatant(name="Goblin", hp_current=5, hp_max=5, ac=13, initiative=8, zone="alleyway")],
    )
    with patch("api.session_manager._write_session_state"):
        _apply_actor_zone_change(session, "goblin", "center")
    assert session.combat_state.combatants[0].zone == "center"


def test_apply_actor_zone_change_updates_party(tmp_path):
    session = _session(tmp_path)
    session.party_zone_id = "Alleyway"
    with patch("api.session_manager._write_session_state"):
        _apply_actor_zone_change(session, "party", "Center")
    assert session.party_zone_id == "Center"
