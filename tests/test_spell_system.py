"""Spell system tests — Tiers S1 and S2-1 (auto-hit damage spells).

Spec: specs/magic-spell-system.feature
Covers: SS-001 through SS-014

Design note: examples use "Bonnie" as the caster to keep tests
independent of the real character files. Any PC with a spells list
in their JSON gets the same behaviour automatically.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

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
    stream_pc_turn,
    resolve_damage_roll,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_BONNIE_SPELLS = [
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
    {
        "name": "Flame Dart",
        "school": "Evocation [fire]",
        "sr": "Yes",
        "save": "None",
        "perDay": "At will",
        "castTime": "1 standard action",
        "range": "25 ft.",
        "effect": "A dart of fire deals 1d6 fire damage. Never misses.",
    },
    {
        "name": "Detect Magic",
        "school": "Divination",
        "sr": "—",
        "save": "—",
        "perDay": "At will",
        "castTime": "1 standard action",
        "range": "60 ft.",
        "effect": "Detect magical auras in a cone.",
    },
    {
        "name": "Shield",
        "school": "Abjuration",
        "sr": "—",
        "save": "—",
        "perDay": "5/day",
        "castTime": "1 standard action",
        "range": "Personal",
        "effect": "+4 shield bonus to AC. Dismissible.",
    },
]

_BONNIE_PLAYER_JSON = {
    "name": "Bonnie",
    "race": "Human",
    "class": "Sorcerer",
    "archetype": "",
    "hp": {"max": 7, "current": 7},
    "ac": {"total": 12},
    "initiative": "+2",
    "speed": "30 ft.",
    "abilities": [],
    "saves": [],
    "weapons": [
        {"name": "quarterstaff", "atk": "+1", "dmg": "1d6+1", "type": "Melee"},
    ],
    "spells": {"concentration": "+5", "list": _BONNIE_SPELLS},
}


def _write_bonnie(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "characters.json").write_text(json.dumps(["bonnie"]), encoding="utf-8")
    (data_dir / "player_bonnie.json").write_text(
        json.dumps(_BONNIE_PLAYER_JSON), encoding="utf-8"
    )
    return data_dir


def _session_with_bonnie() -> GameSession:
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
                "combat_stats": {"name": "Bonnie", "hp_max": 7, "ac": 12, "initiative": "+2"},
                "weapons": [
                    {"name": "quarterstaff", "atk": "+1", "dmg": "1d6+1", "type": "melee"},
                ],
                "spells": [
                    {
                        "name": "Force Bolt",
                        "school": "Evocation [force]",
                        "sr": True,
                        "save": "None",
                        "auto_hit": True,
                        "damage_expr": "1d4+1",
                        "per_day": "5/day",
                        "cast_time": "1 standard action",
                        "range_raw": "110 ft.",
                    },
                    {
                        "name": "Flame Dart",
                        "school": "Evocation [fire]",
                        "sr": True,
                        "save": "None",
                        "auto_hit": True,
                        "damage_expr": "1d6",
                        "per_day": "At will",
                        "cast_time": "1 standard action",
                        "range_raw": "25 ft.",
                    },
                    {
                        "name": "Detect Magic",
                        "school": "Divination",
                        "sr": False,
                        "save": "",
                        "auto_hit": False,
                        "damage_expr": "",
                        "per_day": "At will",
                        "cast_time": "1 standard action",
                        "range_raw": "60 ft.",
                    },
                    {
                        "name": "Shield",
                        "school": "Abjuration",
                        "sr": False,
                        "save": "",
                        "auto_hit": False,
                        "damage_expr": "",
                        "per_day": "5/day",
                        "cast_time": "1 standard action",
                        "range_raw": "Personal",
                    },
                ],
            },
        },
    )


def _combat(current_actor: str = "Bonnie") -> CombatState:
    return CombatState(
        round=2,
        current_actor=current_actor,
        combatants=[
            Combatant(name="Bonnie",      hp_current=7,  hp_max=7,  ac=12, initiative=14),
            Combatant(name="Skeleton 1",  hp_current=8,  hp_max=8,  ac=13, initiative=10),
            Combatant(name="Goblin Scout",hp_current=5,  hp_max=5,  ac=15, initiative=8),
        ],
    )


def _events(chunks) -> list[dict]:
    events = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


# ── SS-001/002/003: Spell profile parsing ────────────────────────────────────

class TestSpellParsing:
    """SS-001, SS-002, SS-003 — _build_pc_profiles extracts spell mechanics."""

    def test_auto_hit_detected_from_never_misses(self, tmp_path):
        """'Never misses.' in effect text → auto_hit=True."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        force_bolt = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Force Bolt")
        assert force_bolt["auto_hit"] is True

    def test_damage_expr_extracted_from_effect(self, tmp_path):
        """Dice expression extracted from effect text."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        force_bolt = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Force Bolt")
        assert force_bolt["damage_expr"] == "1d4+1"

    def test_non_damage_spell_has_empty_damage_expr(self, tmp_path):
        """Shield (buff) has no dice expression → damage_expr=''."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        shield = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Shield")
        assert shield["damage_expr"] == ""
        assert shield["auto_hit"] is False

    def test_utility_spell_not_auto_hit(self, tmp_path):
        """Detect Magic has no 'never misses' → auto_hit=False."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        dm = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Detect Magic")
        assert dm["auto_hit"] is False
        assert dm["damage_expr"] == ""

    def test_sr_flag_parsed(self, tmp_path):
        """'Yes' SR field → sr=True; '—' → sr=False."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        spells_by_name = {s["name"]: s for s in profiles["bonnie"]["spells"]}
        assert spells_by_name["Force Bolt"]["sr"] is True
        assert spells_by_name["Detect Magic"]["sr"] is False

    def test_per_day_preserved(self, tmp_path):
        """perDay field is stored as-is."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        force_bolt = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Force Bolt")
        assert force_bolt["per_day"] == "5/day"

    def test_character_without_spells_has_empty_list(self, tmp_path):
        """A martial character with no spells key → spells=[]."""
        data_dir = tmp_path / "data2"
        data_dir.mkdir()
        (data_dir / "characters.json").write_text(json.dumps(["warrior"]), encoding="utf-8")
        (data_dir / "player_warrior.json").write_text(json.dumps({
            "name": "Warrior",
            "hp": {"max": 12}, "ac": {"total": 17}, "initiative": "+1",
            "weapons": [{"name": "greatsword", "atk": "+5", "dmg": "2d6+4", "type": "Melee"}],
        }), encoding="utf-8")
        profiles = _build_pc_profiles(data_dir)
        assert profiles["warrior"]["spells"] == []

    def test_real_yanyeeku_magic_missile(self):
        """Integration: real player_01.json parses Magic Missile correctly."""
        real_dir = Path(__file__).resolve().parents[1] / "ui" / "public" / "data"
        if not real_dir.exists():
            pytest.skip("player data not available")
        profiles = _build_pc_profiles(real_dir)
        mm = next(
            (s for s in profiles.get("yanyeeku", {}).get("spells", []) if s["name"] == "Magic Missile"),
            None,
        )
        assert mm is not None, "Magic Missile not found in Yanyeeku's spell list"
        assert mm["auto_hit"] is True
        assert mm["damage_expr"] == "1d4+1"


# ── SS-004/005/006: Spell intent extraction ──────────────────────────────────

class TestSpellIntentExtraction:
    """SS-004, SS-005, SS-006 — _extract_pc_combat_intent detects spell casts."""

    def _s(self) -> GameSession:
        s = _session_with_bonnie()
        s.combat_state = _combat("Bonnie")
        return s

    def test_spell_matched_by_exact_name(self):
        """'I cast Force Bolt at the skeleton' → action_type=cast, spell_name=Force Bolt."""
        intent = _extract_pc_combat_intent("I cast Force Bolt at the skeleton!", self._s())
        assert intent["action_type"] == "cast"
        assert intent["spell_name"] == "Force Bolt"

    def test_spell_matched_by_partial_name_with_cast(self):
        """'cast bolt' → matches Force Bolt via partial word match."""
        intent = _extract_pc_combat_intent("I cast bolt at the goblin", self._s())
        assert intent["action_type"] == "cast"
        assert intent["spell_name"] == "Force Bolt"

    def test_spell_matched_by_name_without_cast_keyword(self):
        """Spell name alone (no 'cast') still triggers spell intent."""
        intent = _extract_pc_combat_intent("Force Bolt the skeleton!", self._s())
        assert intent["action_type"] == "cast"
        assert intent["spell_name"] == "Force Bolt"

    def test_spell_target_resolved_from_text(self):
        """Target name extracted when present in input."""
        intent = _extract_pc_combat_intent("I cast Force Bolt at Goblin Scout", self._s())
        assert intent["target"] == "Goblin Scout"

    def test_spell_target_falls_back_to_random_enemy(self):
        """No target named → first active enemy used as fallback."""
        intent = _extract_pc_combat_intent("I cast Force Bolt!", self._s())
        assert intent["target"] in {"Skeleton 1", "Goblin Scout"}

    def test_spell_data_returned_in_intent(self):
        """spell_data dict includes auto_hit and damage_expr."""
        intent = _extract_pc_combat_intent("I cast Force Bolt at skeleton", self._s())
        assert intent["spell_data"]["auto_hit"] is True
        assert intent["spell_data"]["damage_expr"] == "1d4+1"

    def test_spell_takes_priority_over_weapon_match(self):
        """When a spell name is present, weapon path is not taken."""
        intent = _extract_pc_combat_intent("I cast Force Bolt", self._s())
        assert intent["action_type"] == "cast"
        assert "weapon_name" not in intent

    def test_no_spell_intent_for_non_caster(self):
        """Character with no spells → weapon fallback, not cast."""
        s = _session_with_bonnie()
        s.pc_profiles["bonnie"]["spells"] = []
        s.combat_state = _combat("Bonnie")
        intent = _extract_pc_combat_intent("I attack the goblin", s)
        assert intent["action_type"] == "attack"

    def test_different_spell_on_same_caster(self):
        """Flame Dart also matched for the same caster."""
        intent = _extract_pc_combat_intent("I use Flame Dart on the goblin", self._s())
        assert intent["spell_name"] == "Flame Dart"
        assert intent["spell_data"]["damage_expr"] == "1d6"


# ── SS-007/008/009: stream_pc_turn auto-hit spell path ───────────────────────

class TestStreamPcTurnAutoHit:
    """SS-007, SS-008, SS-009 — stream_pc_turn emits damage_request for auto-hit spells."""

    def _s(self) -> GameSession:
        s = _session_with_bonnie()
        s.combat_state = _combat("Bonnie")
        return s

    def test_damage_request_emitted_not_attack_request(self):
        """Auto-hit spell emits damage_request — no attack roll phase."""
        s = self._s()
        events = _events(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        types = [e["type"] for e in events]
        assert "damage_request" in types
        assert "attack_request" not in types

    def test_damage_request_contains_spell_fields(self):
        """damage_request event carries spell_name, caster, target, damage_expr."""
        s = self._s()
        events = _events(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        dr = next(e for e in events if e["type"] == "damage_request")
        assert dr["spell_name"] == "Force Bolt"
        assert dr["caster"] == "Bonnie"
        assert dr["target"] == "Skeleton 1"
        assert dr["damage_expr"] == "1d4+1"

    def test_pending_attack_has_hit_true(self):
        """PendingAttack.hit is pre-set to True (skips resolve_attack_roll)."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        assert len(s.attack_queue) == 1
        assert s.attack_queue[0].hit is True

    def test_pending_attack_is_spell_flag(self):
        """PendingAttack.is_spell = True and spell_name set."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        atk = s.attack_queue[0]
        assert atk.is_spell is True
        assert atk.spell_name == "Force Bolt"

    def test_pending_narration_flag_set(self):
        """session._pending_pc_narration is populated after stream_pc_turn."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        assert s._pending_pc_narration is not None
        assert s._pending_pc_narration["action_type"] == "cast"

    def test_player_text_appended_to_history(self):
        """Player text added to session.messages."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        user_msgs = [m for m in s.messages if m["role"] == "user"]
        assert any("Force Bolt" in m["content"] for m in user_msgs)

    def test_no_target_yields_error(self):
        """All enemies defeated → error, no damage_request."""
        s = self._s()
        for c in s.combat_state.combatants:
            if c.name != "Bonnie":
                c.status = "dead"
        events = _events(stream_pc_turn(s, "I cast Force Bolt"))
        assert any(e["type"] == "error" for e in events)
        assert not any(e["type"] == "damage_request" for e in events)


# ── SS-010/011: resolve_damage_roll spell variant ────────────────────────────

class TestSpellDamageResolution:
    """SS-010, SS-011 — resolve_damage_roll handles pre-hit spell attacks."""

    def _session_after_cast(self) -> GameSession:
        """Session in the state after stream_pc_turn has queued a spell attack."""
        s = _session_with_bonnie()
        s.combat_state = _combat("Bonnie")
        list(stream_pc_turn(s, "I cast Force Bolt at Skeleton 1"))
        return s

    def test_damage_applied_to_target(self):
        """HP delta applied to target after damage roll."""
        s = self._session_after_cast()
        skeleton = next(c for c in s.combat_state.combatants if c.name == "Skeleton 1")
        resolve_damage_roll(s, [3], 4)  # rolled 3 + 1 = 4
        assert skeleton.hp_current == 8 - 4

    def test_result_is_spell_flag(self):
        """resolve_damage_roll result carries is_spell=True."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [3], 4)
        result = s.attack_results[-1]
        assert result["is_spell"] is True

    def test_result_spell_name(self):
        """resolve_damage_roll result carries spell_name."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [3], 4)
        result = s.attack_results[-1]
        assert result["spell_name"] == "Force Bolt"

    def test_attack_type_is_spell(self):
        """attack_type field is 'spell' for spell damage results."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [3], 4)
        result = s.attack_results[-1]
        assert result["attack_type"] == "spell"

    def test_queue_cleared_after_damage(self):
        """attack_queue is empty after resolve_damage_roll."""
        s = self._session_after_cast()
        resolve_damage_roll(s, [3], 4)
        assert len(s.attack_queue) == 0


# ── SS-012/013: _build_pc_turn_system spell briefing ─────────────────────────

class TestPcTurnSystemSpell:
    """SS-012, SS-013 — _build_pc_turn_system generates spell-specific briefing."""

    def _intent(self) -> dict:
        return {
            "actor": "Bonnie",
            "action_type": "cast",
            "spell_name": "Force Bolt",
            "spell_data": {
                "name": "Force Bolt",
                "school": "Evocation [force]",
                "auto_hit": True,
                "damage_expr": "1d4+1",
            },
            "target": "Skeleton 1",
            "original_text": "I cast Force Bolt at the skeleton",
        }

    def _session_with_combat(self) -> GameSession:
        s = _session_with_bonnie()
        s.combat_state = _combat("Bonnie")
        return s

    def test_system_contains_spell_name(self):
        """Briefing mentions the spell name."""
        system = _build_pc_turn_system(self._session_with_combat(), self._intent(), {"damage_total": 4})
        assert "Force Bolt" in system

    def test_system_contains_auto_hit_label(self):
        """Briefing says 'auto-hit' for spells that never miss."""
        system = _build_pc_turn_system(self._session_with_combat(), self._intent(), {"damage_total": 4})
        assert "auto-hit" in system

    def test_system_contains_damage(self):
        """Briefing includes the rolled damage amount."""
        system = _build_pc_turn_system(self._session_with_combat(), self._intent(), {"damage_total": 4})
        assert "4" in system

    def test_system_no_attack_roll_line(self):
        """Spell briefing does not include 'To hit: 1d20' line."""
        system = _build_pc_turn_system(self._session_with_combat(), self._intent(), {"damage_total": 4})
        assert "1d20" not in system

    def test_system_no_vs_ac_line(self):
        """Spell briefing does not include 'vs AC' (auto-hit has no AC comparison)."""
        system = _build_pc_turn_system(self._session_with_combat(), self._intent(), {"damage_total": 4})
        assert "vs AC" not in system
