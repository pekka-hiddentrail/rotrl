"""Tests for location-owned zone graphs and session zone loading."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

from api.context.event_index import EventEntry
from api.context.location_lookup import LocationIndex
from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _build_session_zone_map,
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
