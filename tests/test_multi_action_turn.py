"""Multi-action PC turn tests.

Spec: specs/action-economy.feature
Covers: AC-013 (backend), AC-014, AC-015, AC-016
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
    _extract_pc_combat_intent,
    stream_pc_turn,
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
            "bonnie": {
                "combat_stats": {"name": "Bonnie", "hp_max": 10, "ac": 15, "initiative": "+2"},
                "weapons": [
                    {"name": "longsword", "atk": "+5", "dmg": "1d8+3", "type": "melee"},
                ],
            },
        },
    )


def _combat(current_actor: str = "Bonnie", zones: bool = True) -> CombatState:
    combatants = [
        Combatant(name="Bonnie",          hp_current=10, hp_max=10, ac=15, initiative=15,
                  zone="center" if zones else ""),
        Combatant(name="Goblin Scout",    hp_current=5,  hp_max=5,  ac=13, initiative=9,
                  zone="north alcove" if zones else ""),
    ]
    return CombatState(round=1, current_actor=current_actor, combatants=combatants)


def _events(chunks) -> list[dict]:
    events = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


# ── AC-015 — action_type_hints priority over action_type_hint ─────────────────

class TestHintsPriority:
    """AC-015"""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat()
        return s

    def test_hints_list_overrides_single_hint_move(self):
        """action_type_hints=["move"] wins over action_type_hint="standard"."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I move behind the pillar",
            s,
            action_type_hint="standard",
            action_type_hints=["move"],
        )
        assert intent["action_type"] == "move"

    def test_hints_list_overrides_single_hint_standard_to_attack(self):
        """action_type_hints=["standard"] maps to attack, overriding move hint."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin",
            s,
            action_type_hint="move",
            action_type_hints=["standard"],
        )
        assert intent["action_type"] == "attack"

    def test_empty_hints_list_falls_back_to_inference(self):
        """Empty action_type_hints list → keyword inference, NOT legacy hint."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin",
            s,
            action_type_hint="move",  # legacy hint present but should be ignored
            action_type_hints=[],      # empty list = no multi-action hints
        )
        # Keyword inference sees "attack" → "attack"
        assert intent["action_type"] == "attack"

    def test_none_hints_falls_back_to_single_hint(self):
        """None action_type_hints → legacy action_type_hint is used."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin",
            s,
            action_type_hint="move",
            action_type_hints=None,
        )
        assert intent["action_type"] == "move"

    def test_hints_full_maps_to_attack(self):
        """action_type_hints=["full"] maps to attack via _HINT_TO_ACTION_TYPE."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin",
            s,
            action_type_hints=["full"],
        )
        assert intent["action_type"] == "attack"

    def test_hints_move_overrides_attack_keyword(self):
        """action_type_hints=["move"] forces move even when text says 'attack'."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I swing my sword at the goblin",
            s,
            action_type_hints=["move"],
        )
        assert intent["action_type"] == "move"


# ── AC-014 — Standard+Move combo: attack queued + zone applied ────────────────

class TestStandardMoveCombo:
    """AC-014"""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat()
        return s

    def test_standard_move_extracts_attack_intent_with_move_secondary(self):
        """Standard+Move combo: primary action_type is attack, secondary_actions has move."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin and then move to the north alcove",
            s,
            action_type_hints=["standard", "move"],
        )
        assert intent["action_type"] == "attack"
        secondary = intent.get("secondary_actions", [])
        assert any(a["type"] == "move" for a in secondary)

    def test_standard_move_secondary_carries_destination_zone(self):
        """The secondary move action captures the destination zone from the text."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I hit the goblin and move to north alcove",
            s,
            action_type_hints=["standard", "move"],
        )
        secondary = intent.get("secondary_actions", [])
        move_actions = [a for a in secondary if a["type"] == "move"]
        assert move_actions, "Expected a move secondary action"
        assert move_actions[0].get("destination_zone") == "north alcove"

    def test_standard_move_secondary_missing_zone_is_empty_string(self):
        """If no zone is mentioned, secondary move destination_zone is empty."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I hit the goblin",
            s,
            action_type_hints=["standard", "move"],
        )
        secondary = intent.get("secondary_actions", [])
        move_actions = [a for a in secondary if a["type"] == "move"]
        assert move_actions, "Expected a move secondary action even without zone"
        assert move_actions[0].get("destination_zone") == ""

    def test_stream_standard_move_queues_attack_and_emits_move(self):
        """stream_pc_turn with Standard+Move: attack_request emitted, zone updated,
        combat_update emitted with new zone."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie attacks the Goblin Scout and moves to north alcove",
                action_type_hints=["standard", "move"],
            ))

        events = _events(chunks)
        types = [e["type"] for e in events]

        # Attack is queued → attack_request emitted
        assert "attack_request" in types

        # Zone change → combat_update emitted (may be before or after attack_request)
        combat_updates = [e for e in events if e["type"] == "combat_update"]
        assert combat_updates, "Expected at least one combat_update for zone move"

        # The combat_update should reflect Bonnie's new zone
        bonnie_row = next(
            (c for u in combat_updates for c in (u.get("combat_state") or {}).get("combatants", [])
             if c["name"] == "Bonnie"),
            None,
        )
        assert bonnie_row is not None
        assert bonnie_row["zone"] == "north alcove"

    def test_stream_standard_move_unknown_zone_does_not_block_attack(self):
        """When Standard+Move but zone is unknown, attack still proceeds (no attention event)."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie attacks the Goblin Scout and moves somewhere",
                action_type_hints=["standard", "move"],
            ))

        events = _events(chunks)
        types = [e["type"] for e in events]

        # No blocking attention event
        assert "attention" not in types
        # Attack proceeds normally
        assert "attack_request" in types

    def test_stream_standard_move_zone_applied_to_combatant(self):
        """Zone move in Standard+Move combo updates the combatant's zone directly."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            list(stream_pc_turn(
                s,
                "Bonnie hits the goblin and moves to north alcove",
                action_type_hints=["standard", "move"],
            ))

        bonnie = next(c for c in s.combat_state.combatants if c.name == "Bonnie")  # type: ignore[union-attr]
        assert bonnie.zone == "north alcove"


# ── AC-016 — Swift and Free are informational ─────────────────────────────────

class TestSwiftFreeInformational:
    """AC-016"""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat()
        return s

    def test_standard_swift_queues_single_attack(self):
        """Standard+Swift: exactly one attack_request, no extra events for swift."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie attacks the Goblin Scout",
                action_type_hints=["standard", "swift"],
            ))

        events = _events(chunks)
        attack_reqs = [e for e in events if e["type"] == "attack_request"]
        assert len(attack_reqs) == 1

    def test_full_free_queues_single_attack(self):
        """Full+Free: exactly one attack_request, no extra events for free."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie attacks the Goblin Scout",
                action_type_hints=["full", "free"],
            ))

        events = _events(chunks)
        attack_reqs = [e for e in events if e["type"] == "attack_request"]
        assert len(attack_reqs) == 1

    def test_swift_is_in_intent_secondary_actions(self):
        """Swift/Free appear in intent['secondary_actions'] for LLM briefing context."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin",
            s,
            action_type_hints=["standard", "swift"],
        )
        secondary = intent.get("secondary_actions", [])
        assert any(a["type"] == "swift" for a in secondary)

    def test_free_is_in_intent_secondary_actions(self):
        """Free action appears in intent['secondary_actions']."""
        s = self._s()
        intent = _extract_pc_combat_intent(
            "I attack the goblin",
            s,
            action_type_hints=["full", "free"],
        )
        secondary = intent.get("secondary_actions", [])
        assert any(a["type"] == "free" for a in secondary)


# ── AC-013 (backend side) — action_type_hints field accepted by stream_pc_turn ──

class TestHintsAccepted:
    """AC-013 — stream_pc_turn accepts action_type_hints list."""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat()
        return s

    def test_move_only_hint_processes_as_move(self):
        """action_type_hints=["move"] → zone-only move processed, no attack_request."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie moves to north alcove",
                action_type_hints=["move"],
            ))

        events = _events(chunks)
        types = [e["type"] for e in events]
        assert "attack_request" not in types
        assert "combat_update" in types

    def test_standard_only_hint_processes_as_attack(self):
        """action_type_hints=["standard"] → attack queued normally."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie attacks the goblin",
                action_type_hints=["standard"],
            ))

        events = _events(chunks)
        types = [e["type"] for e in events]
        assert "attack_request" in types

    def test_full_only_hint_processes_as_attack(self):
        """action_type_hints=["full"] → full-round attack queued."""
        s = self._s()

        with patch.object(sm, "advance_combat_turn"):
            chunks = list(stream_pc_turn(
                s,
                "Bonnie attacks the goblin",
                action_type_hints=["full"],
            ))

        events = _events(chunks)
        types = [e["type"] for e in events]
        assert "attack_request" in types
