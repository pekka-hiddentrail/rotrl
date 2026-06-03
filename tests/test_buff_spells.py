"""AC buff tests — Tier S2-3 (typed AC bonus effects, active_effects, _effective_ac).

Spec: specs/ac-buffs.feature
Covers: SB-001 through SB-013

Uses "Bonnie" as the caster to confirm the system is rules-agnostic.
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
    _effective_ac,
    _extract_pc_combat_intent,
    advance_combat_turn,
    resolve_attack_roll,
    stream_pc_turn,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_BONNIE_SPELLS = [
    {
        "name": "Ward",
        "school": "Abjuration",
        "sr": "—",
        "save": "—",
        "perDay": "5/day",
        "castTime": "1 standard action",
        "range": "Personal",
        "effect": "+4 shield bonus to AC. Dismissible.",
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
]

_BONNIE_JSON = {
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
    "weapons": [],
    "spells": {"concentration": "+5", "list": _BONNIE_SPELLS},
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
                "weapons": [],
                "spells": [
                    {
                        "name": "Ward",
                        "school": "Abjuration",
                        "sr": False,
                        "save": "",
                        "auto_hit": False,
                        "damage_expr": "",
                        "buff_ac": 4,
                        "buff_type": "shield",
                        "per_day": "5/day",
                        "cast_time": "1 standard action",
                        "range_raw": "Personal",
                    },
                    {
                        "name": "Force Bolt",
                        "school": "Evocation [force]",
                        "sr": True,
                        "save": "",
                        "auto_hit": True,
                        "damage_expr": "1d4+1",
                        "buff_ac": 0,
                        "buff_type": "",
                        "per_day": "5/day",
                        "cast_time": "1 standard action",
                        "range_raw": "110 ft.",
                    },
                    {
                        "name": "Detect Magic",
                        "school": "Divination",
                        "sr": False,
                        "save": "",
                        "auto_hit": False,
                        "damage_expr": "",
                        "buff_ac": 0,
                        "buff_type": "",
                        "per_day": "At will",
                        "cast_time": "1 standard action",
                        "range_raw": "60 ft.",
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
            Combatant(name="Bonnie",     hp_current=7, hp_max=7,  ac=12, initiative=14),
            Combatant(name="Skeleton 1", hp_current=8, hp_max=8,  ac=13, initiative=10),
        ],
    )


def _events(chunks) -> list[dict]:
    events = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


# ── SB-001/002: Spell profile parsing ────────────────────────────────────────

class TestBuffSpellParsing:
    """SB-001, SB-002 — _build_pc_profiles extracts buff_ac from effect text."""

    def test_shield_bonus_parsed_from_effect(self, tmp_path):
        """'+4 shield bonus to AC' → buff_ac=4, buff_type='shield'."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        ward = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Ward")
        assert ward["buff_ac"] == 4
        assert ward["buff_type"] == "shield"

    def test_deflection_bonus_parsed_from_effect(self, tmp_path):
        """'+2 deflection bonus to AC' → buff_ac=2, buff_type='deflection'."""
        # Write a character with a deflection-bonus spell
        data_dir = tmp_path / "data2"
        data_dir.mkdir()
        (data_dir / "characters.json").write_text('["cleric"]', encoding="utf-8")
        (data_dir / "player_cleric.json").write_text(
            __import__("json").dumps({
                "name": "Cleric",
                "hp": {"max": 8}, "ac": {"total": 14}, "initiative": "+0",
                "weapons": [],
                "spells": {"list": [
                    {"name": "Holy Aura", "school": "Abjuration", "sr": "—", "save": "—",
                     "perDay": "1/day", "castTime": "1 standard action", "range": "Personal",
                     "effect": "+2 deflection bonus to AC against evil creatures."},
                ]}
            }), encoding="utf-8"
        )
        profiles = _build_pc_profiles(data_dir)
        holy_aura = profiles["cleric"]["spells"][0]
        assert holy_aura["buff_ac"] == 2
        assert holy_aura["buff_type"] == "deflection"

    def test_damage_spell_has_zero_buff_ac(self, tmp_path):
        """Damage spell (Force Bolt) has buff_ac=0 and buff_type=''."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        bolt = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Force Bolt")
        assert bolt["buff_ac"] == 0
        assert bolt["buff_type"] == ""

    def test_utility_spell_has_zero_buff_ac(self, tmp_path):
        """Utility spell (Detect Magic) has buff_ac=0."""
        data_dir = _write_bonnie(tmp_path)
        profiles = _build_pc_profiles(data_dir)
        dm = next(s for s in profiles["bonnie"]["spells"] if s["name"] == "Detect Magic")
        assert dm["buff_ac"] == 0

    def test_real_shield_spell(self):
        """Integration: Yanyeeku's Shield → buff_ac=4, buff_type='shield'."""
        real_dir = Path(__file__).resolve().parents[1] / "ui" / "public" / "data"
        if not real_dir.exists():
            pytest.skip("player data not available")
        profiles = _build_pc_profiles(real_dir)
        shield = next(
            (s for s in profiles.get("yanyeeku", {}).get("spells", []) if s["name"] == "Shield"),
            None,
        )
        assert shield is not None, "Shield not found in Yanyeeku's spell list"
        assert shield["buff_ac"] == 4
        assert shield["buff_type"] == "shield"

    def test_real_shield_of_faith(self):
        """Integration: Ani's Shield of Faith → buff_ac=2, buff_type='deflection'."""
        real_dir = Path(__file__).resolve().parents[1] / "ui" / "public" / "data"
        if not real_dir.exists():
            pytest.skip("player data not available")
        profiles = _build_pc_profiles(real_dir)
        sof = next(
            (s for s in profiles.get("ani", {}).get("spells", []) if s["name"] == "Shield of Faith"),
            None,
        )
        assert sof is not None, "Shield of Faith not found in Ani's spell list"
        assert sof["buff_ac"] == 2
        assert sof["buff_type"] == "deflection"

    def test_real_protection_from_evil(self):
        """Integration: Ani's Protection from Evil → buff_ac=2, buff_type='deflection'."""
        real_dir = Path(__file__).resolve().parents[1] / "ui" / "public" / "data"
        if not real_dir.exists():
            pytest.skip("player data not available")
        profiles = _build_pc_profiles(real_dir)
        pfe = next(
            (s for s in profiles.get("ani", {}).get("spells", []) if s["name"] == "Protection from Evil"),
            None,
        )
        assert pfe is not None, "Protection from Evil not found in Ani's spell list"
        assert pfe["buff_ac"] == 2
        assert pfe["buff_type"] == "deflection"


# ── SB-005/006: _effective_ac helper ─────────────────────────────────────────

class TestEffectiveAc:
    """SB-005, SB-006 — _effective_ac sums base ac and active_effects bonuses."""

    def test_effective_ac_with_no_effects(self):
        c = Combatant(name="Bonnie", hp_current=7, hp_max=7, ac=12, initiative=14)
        assert _effective_ac(c) == 12

    def test_effective_ac_with_shield_effect(self):
        c = Combatant(name="Bonnie", hp_current=7, hp_max=7, ac=12, initiative=14)
        c.active_effects = [{"name": "Ward", "bonus_type": "shield", "ac_bonus": 4, "rounds_remaining": 10}]
        assert _effective_ac(c) == 16

    def test_effective_ac_with_multiple_effects(self):
        c = Combatant(name="Bonnie", hp_current=7, hp_max=7, ac=12, initiative=14)
        c.active_effects = [
            {"name": "Ward", "bonus_type": "shield", "ac_bonus": 4, "rounds_remaining": 10},
            {"name": "Bless", "bonus_type": "morale", "ac_bonus": 1, "rounds_remaining": 5},
        ]
        assert _effective_ac(c) == 17


# ── SB-010: Stacking prevention ──────────────────────────────────────────────

class TestStackingPrevention:
    """SB-010 — same bonus_type is replaced, not stacked."""

    def _cast_ward(self, s: GameSession) -> None:
        list(stream_pc_turn(s, "I cast Ward"))

    def test_shield_type_replaced_not_stacked(self):
        """Casting Ward twice doesn't stack — second replaces first."""
        s = _session()
        s.combat_state = _combat("Bonnie")
        bonnie = next(c for c in s.combat_state.combatants if c.name == "Bonnie")
        # Pre-seed an existing shield effect (e.g. from a magic shield item)
        bonnie.active_effects = [
            {"name": "Magic Shield", "bonus_type": "shield", "ac_bonus": 1, "rounds_remaining": 5}
        ]
        self._cast_ward(s)
        shield_effects = [e for e in bonnie.active_effects if e["bonus_type"] == "shield"]
        assert len(shield_effects) == 1
        assert shield_effects[0]["ac_bonus"] == 4  # Ward's bonus wins

    def test_different_bonus_types_stack(self):
        """Effects with different bonus_type DO stack."""
        s = _session()
        s.combat_state = _combat("Bonnie")
        bonnie = next(c for c in s.combat_state.combatants if c.name == "Bonnie")
        bonnie.active_effects = [
            {"name": "Bless", "bonus_type": "morale", "ac_bonus": 1, "rounds_remaining": 5}
        ]
        self._cast_ward(s)
        assert len(bonnie.active_effects) == 2
        assert _effective_ac(bonnie) == 12 + 4 + 1  # base + shield + morale


# ── SB-003/004/007: stream_pc_turn buff path ─────────────────────────────────

class TestStreamPcTurnBuff:
    """SB-003, SB-004, SB-007 — self-buff cast path in stream_pc_turn."""

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        return s

    def test_no_attack_request_for_buff(self):
        """Buff spell emits neither attack_request nor damage_request."""
        s = self._s()
        events = _events(stream_pc_turn(s, "I cast Ward"))
        types = [e["type"] for e in events]
        assert "attack_request" not in types
        assert "damage_request" not in types

    def test_active_effect_added_to_caster(self):
        """After casting Ward, caster's active_effects has the shield entry."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Ward"))
        bonnie = next(c for c in s.combat_state.combatants if c.name == "Bonnie")
        assert any(
            e["name"] == "Ward" and e["bonus_type"] == "shield" and e["ac_bonus"] == 4
            for e in bonnie.active_effects
        )

    def test_rounds_remaining_after_turn(self):
        """Effect starts at 10 rounds; advance_combat_turn at end of cast turn
        ticks it to 9. This is correct PF1e semantics: 10 rounds from cast."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Ward"))
        bonnie = next(c for c in s.combat_state.combatants if c.name == "Bonnie")
        ward = next(e for e in bonnie.active_effects if e["name"] == "Ward")
        assert ward["rounds_remaining"] == 9

    def test_combat_update_emitted(self):
        """combat_update SSE emitted after buff applied."""
        s = self._s()
        events = _events(stream_pc_turn(s, "I cast Ward"))
        assert any(e["type"] == "combat_update" for e in events)

    def test_no_attack_queue_entry(self):
        """Buff spell does not enqueue a PendingAttack."""
        s = self._s()
        list(stream_pc_turn(s, "I cast Ward"))
        assert len(s.attack_queue) == 0


# ── SB-008/009: resolve_attack_roll uses effective AC ────────────────────────

class TestAttackVsBuffedTarget:
    """SB-008, SB-009 — attack resolution uses _effective_ac, not base ac."""

    def _session_with_buffed_target(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        # Give Skeleton a Shield effect so its effective AC = 13+4 = 17
        skeleton = next(c for c in s.combat_state.combatants if c.name == "Skeleton 1")
        skeleton.active_effects = [
            {"name": "Ward", "bonus_type": "shield", "ac_bonus": 4, "rounds_remaining": 5}
        ]
        return s

    def test_resolve_attack_roll_uses_effective_ac_miss(self):
        """Roll that would hit base AC misses effective AC."""
        s = self._session_with_buffed_target()
        # Queue an attack against Skeleton 1 (base ac=13, effective=17)
        s.attack_queue.append(PendingAttack(
            attacker="Bonnie", target="Skeleton 1",
            bonus=0, damage_expr="1d4", attack_type="melee", is_pc=True,
        ))
        result = resolve_attack_roll(s, rolled=15)  # 15+0=15, misses AC 17
        assert result["hit"] is False
        assert result["ac"] == 17  # effective, not base 13

    def test_resolve_attack_roll_uses_effective_ac_hit(self):
        """Roll above effective AC is a hit."""
        s = self._session_with_buffed_target()
        s.attack_queue.append(PendingAttack(
            attacker="Bonnie", target="Skeleton 1",
            bonus=0, damage_expr="1d4", attack_type="melee", is_pc=True,
        ))
        result = resolve_attack_roll(s, rolled=17)  # 17+0=17, hits AC 17
        assert result["hit"] is True
        assert result["ac"] == 17


# ── SB-011/012: Effect expiry via advance_combat_turn ────────────────────────

class TestEffectExpiry:
    """SB-011, SB-012 — advance_combat_turn ticks down and removes effects."""

    def test_rounds_remaining_decremented(self):
        """Each time the actor's turn ends, their effect rounds_remaining drops by 1."""
        s = _session()
        s.combat_state = CombatState(
            round=1,
            current_actor="Bonnie",
            combatants=[
                Combatant(name="Bonnie",     hp_current=7, hp_max=7, ac=12, initiative=14),
                Combatant(name="Skeleton 1", hp_current=8, hp_max=8, ac=13, initiative=10),
            ],
        )
        bonnie = s.combat_state.combatants[0]
        bonnie.active_effects = [
            {"name": "Ward", "bonus_type": "shield", "ac_bonus": 4, "rounds_remaining": 3}
        ]
        advance_combat_turn(s)  # Bonnie's turn ends
        assert bonnie.active_effects[0]["rounds_remaining"] == 2

    def test_effect_removed_at_zero(self):
        """Effect is removed when rounds_remaining reaches 0."""
        s = _session()
        s.combat_state = CombatState(
            round=1,
            current_actor="Bonnie",
            combatants=[
                Combatant(name="Bonnie",     hp_current=7, hp_max=7, ac=12, initiative=14),
                Combatant(name="Skeleton 1", hp_current=8, hp_max=8, ac=13, initiative=10),
            ],
        )
        bonnie = s.combat_state.combatants[0]
        bonnie.active_effects = [
            {"name": "Ward", "bonus_type": "shield", "ac_bonus": 4, "rounds_remaining": 1}
        ]
        advance_combat_turn(s)  # Bonnie's turn ends
        assert len(bonnie.active_effects) == 0

    def test_other_combatants_effects_not_ticked(self):
        """Only the outgoing actor's effects are decremented, not everyone's."""
        s = _session()
        s.combat_state = CombatState(
            round=1,
            current_actor="Bonnie",
            combatants=[
                Combatant(name="Bonnie",     hp_current=7, hp_max=7, ac=12, initiative=14),
                Combatant(name="Skeleton 1", hp_current=8, hp_max=8, ac=13, initiative=10),
            ],
        )
        skeleton = s.combat_state.combatants[1]
        skeleton.active_effects = [
            {"name": "Ward", "bonus_type": "shield", "ac_bonus": 4, "rounds_remaining": 5}
        ]
        advance_combat_turn(s)  # Bonnie's turn ends, Skeleton's effect untouched
        assert skeleton.active_effects[0]["rounds_remaining"] == 5


# ── SB-013: _build_pc_turn_system buff briefing ──────────────────────────────

class TestPcTurnSystemBuff:
    """SB-013 — _build_pc_turn_system generates buff-specific briefing."""

    def _intent(self) -> dict:
        return {
            "actor": "Bonnie",
            "action_type": "cast",
            "spell_name": "Ward",
            "spell_data": {
                "name": "Ward",
                "school": "Abjuration",
                "auto_hit": False,
                "damage_expr": "",
                "buff_ac": 4,
            },
            "target": "Bonnie",  # self-buff targets caster
            "original_text": "I cast Ward",
        }

    def _s(self) -> GameSession:
        s = _session()
        s.combat_state = _combat("Bonnie")
        return s

    def test_system_contains_spell_name(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {})
        assert "Ward" in system

    def test_system_contains_ac_bonus(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {})
        assert "+4" in system or "4" in system

    def test_system_no_auto_hit_label(self):
        """Buff briefing does not say 'auto-hit' (that's for damage spells)."""
        system = _build_pc_turn_system(self._s(), self._intent(), {})
        assert "auto-hit" not in system

    def test_system_no_attack_roll_line(self):
        system = _build_pc_turn_system(self._s(), self._intent(), {})
        assert "1d20" not in system
