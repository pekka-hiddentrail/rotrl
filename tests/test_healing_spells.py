"""Healing spell tests — Tier S2-4 (Cure Light Wounds, positive HP delta).

Spec: specs/healing-spells.feature
Covers: HL-001 through HL-012

Uses "Bonnie" as the healer to keep tests character-agnostic.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

import api.session_manager as sm
from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    PendingAttack,
    _build_pc_profiles,
    _build_pc_turn_system,
    _extract_pc_combat_intent,
    resolve_damage_roll,
    stream_pc_turn,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_BONNIE_SPELLS_JSON = [
    {
        "name": "Mend Wounds",
        "school": "Conjuration (Healing)",
        "sr": "Yes",
        "save": "Will half (harmless)",
        "perDay": "3/day",
        "castTime": "1 standard action",
        "range": "Touch",
        "effect": "Heals 1d8+1 hit points to a living creature. Harms undead.",
    },
    {
        "name": "Force Bolt",
        "school": "Evocation [force]",
        "sr": "Yes",
        "save": "None",
        "perDay": "5/day",
        "castTime": "1 standard action",
        "range": "110 ft.",
        "effect": "1 bolt dealing 1d4+1 force damage. Never misses.",
    },
]

_BONNIE_JSON = {
    "name": "Bonnie",
    "race": "Human", "class": "Cleric", "archetype": "",
    "hp": {"max": 8, "current": 8}, "ac": {"total": 14},
    "initiative": "+0", "speed": "30 ft.",
    "abilities": [], "saves": [], "weapons": [],
    "spells": {"concentration": "+5", "list": _BONNIE_SPELLS_JSON},
}


def _write_bonnie(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "characters.json").write_text(json.dumps(["bonnie"]), encoding="utf-8")
    (data_dir / "player_bonnie.json").write_text(json.dumps(_BONNIE_JSON), encoding="utf-8")
    return data_dir


def _session() -> GameSession:
    return GameSession(
        id=str(uuid.uuid4()),
        session_number=1, model="test-model", host="http://localhost:11434",
        temperature=0.3, dev_mode=False, provider="ollama",
        num_ctx=2048, num_gpu=999, system_prompt="", log_path=None,
        pc_profiles={
            "bonnie": {
                "combat_stats": {"name": "Bonnie", "hp_max": 8, "ac": 14, "initiative": "+0"},
                "weapons": [],
                "spells": [
                    {
                        "name": "Mend Wounds",
                        "school": "Conjuration (Healing)",
                        "sr": True, "save": "Will half (harmless)",
                        "auto_hit": False, "damage_expr": "",
                        "buff_ac": 0, "buff_type": "",
                        "healing_expr": "1d8+1", "is_heal": True,
                        "per_day": "3/day",
                        "cast_time": "1 standard action",
                        "range_raw": "Touch",
                    },
                    {
                        "name": "Force Bolt",
                        "school": "Evocation [force]",
                        "sr": True, "save": "",
                        "auto_hit": True, "damage_expr": "1d4+1",
                        "buff_ac": 0, "buff_type": "",
                        "healing_expr": "", "is_heal": False,
                        "per_day": "5/day",
                        "cast_time": "1 standard action",
                        "range_raw": "110 ft.",
                    },
                ],
            },
            "vanx": {
                "combat_stats": {"name": "Vanx", "hp_max": 10, "ac": 13, "initiative": "+2"},
                "weapons": [],
                "spells": [],
            },
        },
    )


def _combat(current_actor: str = "Bonnie") -> CombatState:
    return CombatState(
        round=2, current_actor=current_actor,
        combatants=[
            Combatant(name="Bonnie",     hp_current=8,  hp_max=8,  ac=14, initiative=14),
            Combatant(name="Vanx",       hp_current=3,  hp_max=10, ac=13, initiative=10),
            Combatant(name="Skeleton 1", hp_current=8,  hp_max=8,  ac=13, initiative=6),
        ],
    )


def _events(chunks) -> list[dict]:
    events = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


# ── HL-001/002: Spell profile parsing ────────────────────────────────────────

class TestHealingParsing:
    """HL-001, HL-002 — _build_pc_profiles detects healing spells."""

    def test_healing_expr_parsed(self, tmp_path):
        """'Heals 1d8+1 hit points' → healing_expr='1d8+1', is_heal=True."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        mend = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Mend Wounds")
        assert mend["healing_expr"] == "1d8+1"
        assert mend["is_heal"] is True

    def test_damage_spell_not_heal(self, tmp_path):
        """Damage spell has empty healing_expr and is_heal=False."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        bolt = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Force Bolt")
        assert bolt["healing_expr"] == ""
        assert bolt["is_heal"] is False

    def test_real_cure_light_wounds(self):
        """Integration: real Cure Light Wounds parses healing_expr correctly."""
        real_dir = Path(__file__).resolve().parents[1] / "ui" / "public" / "data"
        if not real_dir.exists():
            pytest.skip("player data not available")
        profiles = _build_pc_profiles(real_dir)
        clw = next(
            (s for s in profiles.get("ani", {}).get("spells", [])
             if s["name"] == "Cure Light Wounds"),
            None,
        )
        assert clw is not None, "Cure Light Wounds not found in Ani's spell list"
        assert clw["is_heal"] is True
        assert "d8" in clw["healing_expr"]


# ── HL-003/004/005/006/007: Intent extraction and targeting ──────────────────

class TestHealIntentExtraction:
    """HL-003 through HL-007 — spell intent and PC targeting for heal spells."""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        return s

    def test_heal_spell_recognised_by_name(self):
        """'I cast Mend Wounds on Vanx' → action_type=cast, spell=Mend Wounds."""
        intent = _extract_pc_combat_intent("I cast Mend Wounds on Vanx", self._s())
        assert intent["action_type"] == "cast"
        assert intent["spell_name"] == "Mend Wounds"

    def test_heal_targets_pc_ally(self):
        """Named PC ally resolved as target."""
        intent = _extract_pc_combat_intent("I cast Mend Wounds on Vanx", self._s())
        assert intent["target"] == "Vanx"

    def test_heal_targets_unconscious_pc(self):
        """Unconscious PC is a valid heal target."""
        s = self._s()
        vanx = next(c for c in s.combat_state.combatants if c.name == "Vanx")
        vanx.status = "unconscious"
        vanx.hp_current = 0
        intent = _extract_pc_combat_intent("I cast Mend Wounds on Vanx", s)
        assert intent["target"] == "Vanx"

    def test_heal_defaults_to_most_wounded(self):
        """No target named → most wounded PC selected."""
        # Vanx has 3/10 HP (30%) — most wounded PC
        intent = _extract_pc_combat_intent("I cast Mend Wounds", self._s())
        assert intent["target"] == "Vanx"

    def test_heal_does_not_target_enemy(self):
        """Without a PC name, enemy is not chosen as heal target."""
        intent = _extract_pc_combat_intent("I cast Mend Wounds", self._s())
        assert intent["target"] != "Skeleton 1"

    def test_heal_spell_data_is_heal_flag(self):
        """spell_data carries is_heal=True."""
        intent = _extract_pc_combat_intent("I cast Mend Wounds on Vanx", self._s())
        assert intent["spell_data"]["is_heal"] is True
        assert intent["spell_data"]["healing_expr"] == "1d8+1"


# ── HL-004: stream_pc_turn emits heal_request ────────────────────────────────

class TestStreamPcTurnHeal:
    """HL-004 — stream_pc_turn emits heal_request for healing spells."""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        return s

    def test_heal_request_emitted(self):
        """Heal spell emits heal_request SSE."""
        s = self._s()
        events = _events(stream_pc_turn(s, "I cast Mend Wounds on Vanx"))
        types = [e["type"] for e in events]
        assert "heal_request" in types
        assert "attack_request" not in types
        assert "damage_request" not in types

    def test_heal_request_fields(self):
        """heal_request carries spell_name, caster, target, damage_expr."""
        s = self._s()
        events = _events(stream_pc_turn(s, "I cast Mend Wounds on Vanx"))
        hr = next(e for e in events if e["type"] == "heal_request")
        assert hr["spell_name"] == "Mend Wounds"
        assert hr["caster"] == "Bonnie"
        assert hr["target"] == "Vanx"
        assert hr["damage_expr"] == "1d8+1"

    def test_pending_attack_is_heal(self):
        """PendingAttack has is_heal=True and hit=True."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Mend Wounds on Vanx"))
        assert len(s.attack_queue) == 1
        assert s.attack_queue[0].is_heal is True
        assert s.attack_queue[0].hit is True

    def test_pending_narration_set(self):
        """_pending_pc_narration is set after stream_pc_turn."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Mend Wounds on Vanx"))
        assert s._pending_pc_narration is not None


# ── HL-008/009/010/011: resolve_damage_roll heal path ────────────────────────

class TestResolveHeal:
    """HL-008 through HL-011 — resolve_damage_roll applies positive HP delta."""

    def _session_after_cast(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        list(stream_pc_turn(s, "I cast Mend Wounds on Vanx"))
        return s

    def test_positive_hp_delta_applied(self):
        """Healing increases target HP."""
        s = self._session_after_cast()
        vanx = next(c for c in s.combat_state.combatants if c.name == "Vanx")
        assert vanx.hp_current == 3
        resolve_damage_roll(s, [5], 6)  # 1d8 roll 5 + mod 1 = 6
        assert vanx.hp_current == 9

    def test_hp_capped_at_max(self):
        """HP cannot exceed hp_max after healing."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [7], 8)  # would take Vanx to 11, capped at 10
        vanx = next(c for c in s.combat_state.combatants if c.name == "Vanx")
        assert vanx.hp_current == 10

    def test_unconscious_pc_revived(self):
        """Healing an unconscious PC restores active status."""
        s = _session()
        s.combat_state = _combat("Bonnie")
        vanx = next(c for c in s.combat_state.combatants if c.name == "Vanx")
        vanx.hp_current = 0
        vanx.status = "unconscious"
        list(stream_pc_turn(s, "I cast Mend Wounds on Vanx"))
        resolve_damage_roll(s, [5], 6)
        assert vanx.hp_current == 6
        assert vanx.status == "active"

    def test_result_is_heal_flag(self):
        """Result dict carries is_heal=True."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [5], 6)
        result = s.attack_results[-1]
        assert result["is_heal"] is True

    def test_result_damage_total_is_heal_amount(self):
        """damage_total carries the healing amount."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [5], 6)
        result = s.attack_results[-1]
        assert result["damage_total"] == 6

    def test_queue_cleared(self):
        """attack_queue cleared after resolve."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [5], 6)
        assert len(s.attack_queue) == 0


# ── HL-012: _build_pc_turn_system healing briefing ───────────────────────────

class TestPcTurnSystemHeal:
    """HL-012 — _build_pc_turn_system generates heal-specific briefing."""

    def _intent(self) -> dict:
        return {
            "actor": "Bonnie", "action_type": "cast",
            "spell_name": "Mend Wounds",
            "spell_data": {
                "name": "Mend Wounds", "school": "Conjuration (Healing)",
                "auto_hit": False, "damage_expr": "",
                "buff_ac": 0, "is_heal": True, "healing_expr": "1d8+1",
            },
            "target": "Vanx",
            "original_text": "I cast Mend Wounds on Vanx",
        }

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        return s

    def test_system_contains_spell_name(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {"damage_total": 6, "is_heal": True})
        assert "Mend Wounds" in system

    def test_system_contains_heal_amount(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {"damage_total": 6, "is_heal": True})
        assert "6" in system

    def test_system_no_auto_hit(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {"damage_total": 6, "is_heal": True})
        assert "auto-hit" not in system

    def test_system_no_attack_roll(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {"damage_total": 6, "is_heal": True})
        assert "1d20" not in system
