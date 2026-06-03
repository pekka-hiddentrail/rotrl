"""Action economy — action_type_hint backend tests.

Spec: specs/action-economy.feature
Covers: AC-007, AC-008, AC-009
"""
from __future__ import annotations

import uuid

import pytest

from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _extract_pc_combat_intent,
)


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
            "ani": {
                "combat_stats": {"name": "Ani", "hp_max": 11, "ac": 17, "initiative": "+1"},
                "weapons": [
                    {"name": "longsword", "atk": "+4", "dmg": "1d8+2", "type": "melee"},
                    {"name": "dagger",    "atk": "+4", "dmg": "1d4+2", "type": "melee"},
                ],
            },
        },
    )


def _session_in_combat(actor: str = "Ani") -> GameSession:
    s = _session()
    s.combat_state = CombatState(
        round=1,
        current_actor=actor,
        combatants=[
            Combatant(name="Ani",             hp_current=11, hp_max=11, ac=17, initiative=14),
            Combatant(name="Goblin Warrior 1", hp_current=5,  hp_max=5,  ac=16, initiative=9),
        ],
    )
    return s


# ── AC-007 — "standard" and "full" hints map to attack ───────────────────────

class TestHintStandardAndFull:
    """AC-007: standard → attack; full → attack."""

    def test_standard_hint_gives_attack_action(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I run forward", s, action_type_hint="standard")
        assert intent["action_type"] == "attack", (
            '"standard" hint must map to action_type="attack"'
        )

    def test_full_hint_gives_attack_action(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I run forward", s, action_type_hint="full")
        assert intent["action_type"] == "attack", (
            '"full" hint must map to action_type="attack"'
        )

    def test_standard_hint_overrides_non_attack_keywords(self):
        """Even if the text looks like movement, 'standard' forces attack branch."""
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I move to the door", s, action_type_hint="standard")
        assert intent["action_type"] == "attack"

    def test_full_hint_overrides_non_attack_keywords(self):
        """Same for 'full': movement text still yields action_type='attack'."""
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I move to the door", s, action_type_hint="full")
        assert intent["action_type"] == "attack"

    def test_standard_hint_does_not_suppress_use_ability(self):
        """'standard' must not override use_ability — e.g. Barbarian Rage or Bard Inspire."""
        s = _session_in_combat()
        # "rage" is in _ability_words via "bardic" proximity; "channel" triggers directly
        intent = _extract_pc_combat_intent("I channel my energy", s, action_type_hint="standard")
        assert intent["action_type"] == "use_ability", (
            '"standard" hint must not suppress use_ability inference'
        )

    def test_full_hint_does_not_suppress_use_ability(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I inspire my allies", s, action_type_hint="full")
        assert intent["action_type"] == "use_ability"


# ── AC-008 — "move" hint maps to move and overrides attack keywords ───────────

class TestHintMove:
    """AC-008: move → move, even when text contains attack keywords."""

    def test_move_hint_gives_move_action(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I run behind the pillar", s, action_type_hint="move")
        assert intent["action_type"] == "move", (
            '"move" hint must map to action_type="move"'
        )

    def test_move_hint_overrides_attack_keywords(self):
        """'move' hint must win even when the player text has attack keywords."""
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I swing at the goblin", s, action_type_hint="move")
        assert intent["action_type"] == "move", (
            '"move" hint must override keyword-inferred "attack"'
        )

    def test_move_hint_overrides_attack_keywords_variant(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I attack!", s, action_type_hint="move")
        assert intent["action_type"] == "move"


# ── AC-009 — null / unknown hint falls back to keyword inference ──────────────

class TestHintFallback:
    """AC-009: None or unrecognised hint does not override intent detection."""

    def test_no_hint_attack_text_gives_attack(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I attack the goblin", s, action_type_hint=None)
        assert intent["action_type"] == "attack"

    def test_no_hint_move_text_gives_move(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent("I move to the door", s, action_type_hint=None)
        assert intent["action_type"] == "move"

    def test_unknown_hint_does_not_override(self):
        """An unrecognised value like 'sprint' must not suppress keyword inference."""
        s = _session_in_combat()
        # text contains attack keyword → should still be "attack"
        intent = _extract_pc_combat_intent("I attack!", s, action_type_hint="sprint")
        assert intent["action_type"] == "attack", (
            "Unrecognised hint must fall back to keyword inference"
        )

    def test_omitted_hint_behaves_same_as_none(self):
        """Calling without the hint parameter is equivalent to hint=None."""
        s = _session_in_combat()
        intent_with_none    = _extract_pc_combat_intent("I attack!", s, action_type_hint=None)
        intent_without_hint = _extract_pc_combat_intent("I attack!", s)
        assert intent_with_none["action_type"] == intent_without_hint["action_type"]
