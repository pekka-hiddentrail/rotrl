"""Click-to-target feature — backend tests.

Spec: specs/click-to-target.feature
Covers: AC-005 (target_hint in intent extraction), AC-006 (target in LLM briefing)
Frontend ACs (001-004, 007-009) are covered in:
  ui/src/components/__tests__/ClickToTarget.test.tsx
"""
from __future__ import annotations

import uuid

import pytest

from api.session_manager import (
    Combatant,
    CombatState,
    GameSession,
    _build_pc_turn_system,
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
                ],
            },
        },
    )


def _session_in_combat() -> GameSession:
    s = _session()
    s.combat_state = CombatState(
        round=1,
        current_actor="Ani",
        combatants=[
            Combatant(name="Ani",              hp_current=11, hp_max=11, ac=17, initiative=14),
            Combatant(name="Goblin Warrior 1", hp_current=5,  hp_max=5,  ac=16, initiative=9),
            Combatant(name="Goblin Warrior 2", hp_current=5,  hp_max=5,  ac=16, initiative=7),
        ],
    )
    return s


# ── AC-005 — target_hint overrides keyword inference ──────────────────────────

class TestTargetHintInIntentExtraction:
    """AC-005: _extract_pc_combat_intent uses target_hint to set intent['target']."""

    def test_target_hint_sets_target(self):
        s = _session_in_combat()
        intent = _extract_pc_combat_intent(
            "I attack",
            s,
            target_hint="Goblin Warrior 2",
        )
        assert intent.get("target") == "Goblin Warrior 2", (
            "target_hint must override the inferred target"
        )

    def test_target_hint_overrides_text_target(self):
        """Explicit UI selection beats what the player typed in prose."""
        s = _session_in_combat()
        intent = _extract_pc_combat_intent(
            "I attack Goblin Warrior 1",
            s,
            target_hint="Goblin Warrior 2",
        )
        assert intent.get("target") == "Goblin Warrior 2", (
            "target_hint must take precedence over target named in text"
        )

    def test_no_hint_keeps_text_inference(self):
        """Without a hint, keyword inference from text still works."""
        s = _session_in_combat()
        intent = _extract_pc_combat_intent(
            "I attack Goblin Warrior 1",
            s,
            target_hint=None,
        )
        assert intent.get("target") == "Goblin Warrior 1"

    def test_no_hint_no_text_target_uses_fallback(self):
        """Without hint and without a named target, falls back to first living enemy."""
        s = _session_in_combat()
        intent = _extract_pc_combat_intent(
            "I attack",
            s,
            target_hint=None,
        )
        # Should pick some living enemy — not None / empty
        assert intent.get("target"), "Must fall back to a living enemy when no target given"

    def test_none_hint_is_equivalent_to_omitted(self):
        s = _session_in_combat()
        # Use a named target so both calls are deterministic (no random.choice)
        intent_none  = _extract_pc_combat_intent("I attack Goblin Warrior 1", s, target_hint=None)
        intent_omit  = _extract_pc_combat_intent("I attack Goblin Warrior 1", s)
        assert intent_none.get("target") == intent_omit.get("target")


# ── AC-006 — target appears in LLM briefing ───────────────────────────────────

class TestTargetInBriefing:
    """AC-006: _build_pc_turn_system names the target in the briefing (regression guard)."""

    def test_briefing_contains_target_name(self):
        s = _session_in_combat()
        intent = {
            "actor":       "Ani",
            "target":      "Goblin Warrior 2",
            "action_type": "attack",
            "original_text": "I attack Goblin Warrior 2",
        }
        result = {}
        system = _build_pc_turn_system(s, intent, result)
        assert "Goblin Warrior 2" in system, (
            "The LLM briefing must name the intended target so the LLM writes "
            "the correct narrative"
        )

    def test_briefing_target_line_format(self):
        """Target: <name> must appear as a labelled line, not just anywhere in text."""
        s = _session_in_combat()
        intent = {
            "actor":       "Ani",
            "target":      "Goblin Warrior 1",
            "action_type": "attack",
            "original_text": "I attack",
        }
        system = _build_pc_turn_system(s, intent, {})
        assert "Target: Goblin Warrior 1" in system
