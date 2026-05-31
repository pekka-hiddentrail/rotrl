"""Prompt size audits — run with:  pytest -m prompt_audit

These tests assemble real system prompts (via _inject_context with mocked indexes)
and assert that the resulting system content stays within character budgets.

Character counts are used as the proxy for tokens (avoids a tokenizer dependency).
Real-world calibration from api_log files (Groq llama-3.3):
  ~3.9 chars / prompt token
  ~3.5 chars / Anthropic prompt token (Claude tokenizes more finely)

Conservative threshold: 12,000 chars ≈ ~3,000 Groq tokens / ~3,400 Anthropic tokens.
Per-item costs (observed from api_log/system field lengths):
  Base static prompt + event map:  ~2,000 chars
  FORMAT_EXAMPLE (turn 1 only):   ~1,500 chars
  SECTIONS ACTIVE block:           ~  600 chars
  Full NPC profile (base.md):     ~2,000 chars each
  NPC session delta (+1 turn):    ~  300 chars each
  Location profile:               ~  400 chars
  Session-generated location stub:~  300 chars
  Skill reference:                ~  900 chars
  PC narrative profile:           ~  350 chars
  PC mechanical profile:          ~  400 chars
  GM directive:                   ~  300 chars
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from api.session_manager import (
    GameSession,
    _FORMAT_EXAMPLE,
    _inject_context,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(**kwargs) -> GameSession:
    defaults = dict(
        id=str(uuid.uuid4()),
        session_number=1,
        model="qwen3:4b",
        host="http://localhost:11434",
        temperature=0.3,
        dev_mode=False,
        provider="ollama",
        num_ctx=2048,
        num_gpu=999,
        system_prompt="BASE SYSTEM PROMPT",
        log_path=None,
    )
    defaults.update(kwargs)
    return GameSession(**defaults)


def _no_index():
    idx = MagicMock()
    idx.detect.return_value = None
    idx.detect_by_location.return_value = []
    idx.lookup.return_value = None
    idx.format_context.return_value = ""
    idx.known_rules = []
    return idx


def _npc_index_returning(match):
    idx = _no_index()
    idx.detect.return_value = match
    idx.detect_by_location.return_value = []
    idx.format_context.return_value = f"## NPC Reference — {match.canonical_name}\n\n" + "X" * 2000
    return idx


def _skill_index_returning(match):
    idx = _no_index()
    idx.detect.return_value = match
    idx.format_context.return_value = f"## Skill Reference — {match.skill_name}\n\n" + "X" * 900
    return idx


def _call_inject(session):
    with patch("api.session_manager._get_npc_index", return_value=_no_index()), \
         patch("api.session_manager._get_skill_index", return_value=_no_index()), \
         patch("api.session_manager._get_location_index", return_value=_no_index()), \
         patch("api.session_manager._get_event_index", return_value=_no_index()), \
         patch("api.session_manager._get_combat_rules_index", return_value=_no_index()):
        return _inject_context(session)


# ── Thresholds ────────────────────────────────────────────────────────────────
#
# These are HARD LIMITS — failing means a turn is over-budget.
# Adjust upward only with a documented reason in the TODO.

# Turn 1 with no context injections (bare minimum): static + FORMAT_EXAMPLE + SECTIONS.
_BARE_TURN1_MAX = 6_000  # chars

# Turn 1 or 2 with one full NPC profile injected.
_ONE_NPC_MAX = 8_500  # chars

# Turn with one NPC + one skill reference + PC profile (common active-scene turn).
_ACTIVE_SCENE_MAX = 11_000  # chars

# Absolute ceiling: no single turn's system content should exceed this.
# Above this, we risk hitting Groq's 30,000-char limit on long sessions.
_ABSOLUTE_MAX = 14_000  # chars


# ── Audit tests ───────────────────────────────────────────────────────────────

@pytest.mark.prompt_audit
class TestSystemPromptSizeBudgets:

    def test_bare_turn1_no_injections(self):
        """Turn 1, no NPCs detected, no skill, no PC named.

        Budget: base static (~2000) + FORMAT_EXAMPLE (~1500) + sections (~600) + directive (~300) = ~4400.
        Hard limit: 6000 chars.
        """
        session = _make_session(
            messages=[{"role": "user", "content": "We look around."}],
        )
        system_content, _ = _call_inject(session)
        chars = len(system_content)
        assert _FORMAT_EXAMPLE in system_content, "FORMAT_EXAMPLE missing on turn 1"
        assert chars <= _BARE_TURN1_MAX, (
            f"Bare turn 1 system prompt too large: {chars} chars "
            f"(limit {_BARE_TURN1_MAX}). "
            f"Investigate: {_budget_breakdown(system_content)}"
        )

    @pytest.mark.prompt_audit
    def test_bare_turn2_no_injections(self):
        """Turn 2+, no context injections. FORMAT_EXAMPLE should be absent.

        Budget: base static (~2000) + sections (~600) + directive (~300) = ~2900.
        Hard limit: 4500 chars (well below _BARE_TURN1_MAX because no FORMAT_EXAMPLE).
        """
        session = _make_session(
            messages=[
                {"role": "user", "content": "We arrived."},
                {"role": "assistant", "content": "The square is busy."},
                {"role": "user", "content": "We look around."},
            ],
        )
        system_content, _ = _call_inject(session)
        chars = len(system_content)
        assert _FORMAT_EXAMPLE not in system_content, "FORMAT_EXAMPLE should be absent on turn 2+"
        assert chars <= 4_500, (
            f"Bare turn 2 system prompt too large: {chars} chars (limit 4500). "
            f"Investigate: {_budget_breakdown(system_content)}"
        )

    @pytest.mark.prompt_audit
    def test_turn2_lower_than_turn1_by_format_example(self):
        """Turn 2 system content should be smaller than turn 1 by roughly the FORMAT_EXAMPLE size.

        With identical injections, turn 2 - turn 1 ≈ -len(FORMAT_EXAMPLE).
        """
        session1 = _make_session(
            messages=[{"role": "user", "content": "We arrived."}],
        )
        session2 = _make_session(
            messages=[
                {"role": "user", "content": "We arrived."},
                {"role": "assistant", "content": "The square is busy."},
                {"role": "user", "content": "We look around."},
            ],
        )
        content1, _ = _call_inject(session1)
        content2, _ = _call_inject(session2)

        diff = len(content1) - len(content2)
        fmt_size = len(_FORMAT_EXAMPLE)

        assert diff > 0, "Turn 1 should be larger than turn 2 (FORMAT_EXAMPLE absent after turn 1)"
        assert diff >= fmt_size * 0.8, (
            f"Turn 1 is only {diff} chars larger than turn 2, "
            f"but FORMAT_EXAMPLE is {fmt_size} chars. "
            f"Something else may have shrunk unexpectedly."
        )

    @pytest.mark.prompt_audit
    def test_one_npc_injection_within_budget(self):
        """Turn with one NPC mentioned (no skill check) → short NPC stub injected.

        Simulates: player names an NPC, no social check active → short context (~300 chars).
        Hard limit: 8500 chars.
        """
        npc_match = MagicMock()
        npc_match.canonical_name = "Kendra Deverin"
        npc_match.matched_alias = "mayor"

        session = _make_session(
            messages=[
                {"role": "user", "content": "We arrived."},
                {"role": "assistant", "content": "The square is busy."},
                {"role": "user", "content": "We approach the mayor."},
            ],
        )

        npc_idx = _no_index()
        npc_idx.detect.return_value = npc_match
        npc_idx.detect_by_location.return_value = []
        npc_idx.format_context.return_value = "## NPC Reference — Kendra Deverin\n\n" + "X" * 2000
        npc_idx.format_short_context.return_value = "## NPC — Kendra Deverin\nPragmatic mayor. | Diplomacy DC 12 | friendly | cathedral steps"

        with patch("api.session_manager._get_npc_index", return_value=npc_idx), \
             patch("api.session_manager._get_skill_index", return_value=_no_index()), \
             patch("api.session_manager._get_location_index", return_value=_no_index()), \
             patch("api.session_manager._get_event_index", return_value=_no_index()), \
             patch("api.session_manager._get_combat_rules_index", return_value=_no_index()):
            system_content, _ = _inject_context(session)

        chars = len(system_content)
        assert chars <= _ONE_NPC_MAX, (
            f"One-NPC turn system prompt too large: {chars} chars (limit {_ONE_NPC_MAX}). "
            f"Breakdown: {_budget_breakdown(system_content)}"
        )

    @pytest.mark.prompt_audit
    def test_active_scene_npc_plus_skill_within_budget(self):
        """Turn with 1 NPC + 1 skill reference + PC narrative profile.

        Simulates: player names Ani and attempts a skill check → 3 injections.
        Hard limit: 11000 chars.
        """
        npc_match = MagicMock()
        npc_match.canonical_name = "Belor Hemlock"
        npc_match.matched_alias = "hemlock"

        skill_match = MagicMock()
        skill_match.skill_name = "Diplomacy"
        skill_match.matched_trigger = "diplomacy"

        ani_profile = {
            "narrative": "## PC — Ani\nAppearance: " + "X" * 300,
            "mechanical": "## PC Stats — Ani\nHP: 11  AC: 17\n" + "X" * 350,
        }
        session = _make_session(
            messages=[
                {"role": "user", "content": "We arrived."},
                {"role": "assistant", "content": "The square is busy."},
                {"role": "user", "content": "Ani tries to Diplomacy the sheriff."},
            ],
            pc_profiles={"ani": ani_profile},
        )

        npc_idx = _no_index()
        npc_idx.detect.return_value = npc_match
        npc_idx.detect_by_location.return_value = []
        npc_idx.format_context.return_value = "## NPC Reference — Belor Hemlock\n\n" + "X" * 2000

        skill_idx = _no_index()
        skill_idx.detect.return_value = skill_match
        skill_idx.format_context.return_value = "## Skill Reference — Diplomacy\n\n" + "X" * 900

        with patch("api.session_manager._get_npc_index", return_value=npc_idx), \
             patch("api.session_manager._get_skill_index", return_value=skill_idx), \
             patch("api.session_manager._get_location_index", return_value=_no_index()), \
             patch("api.session_manager._get_event_index", return_value=_no_index()), \
             patch("api.session_manager._get_combat_rules_index", return_value=_no_index()):
            system_content, _ = _inject_context(session)

        chars = len(system_content)
        assert chars <= _ACTIVE_SCENE_MAX, (
            f"Active scene turn system prompt too large: {chars} chars (limit {_ACTIVE_SCENE_MAX}). "
            f"Breakdown: {_budget_breakdown(system_content)}"
        )

    @pytest.mark.prompt_audit
    def test_absolute_ceiling_never_exceeded(self):
        """Worst-case turn: FORMAT_EXAMPLE + 2 NPCs + skill + PC profiles + location.

        Hard limit: 14000 chars. If this fails we're at risk of hitting Groq's 30k char cap
        on long sessions with accumulated message history.
        """
        npc1 = MagicMock()
        npc1.canonical_name = "Kendra Deverin"
        npc1.matched_alias = "mayor"
        npc2 = MagicMock()
        npc2.canonical_name = "Belor Hemlock"
        npc2.matched_location = "garrison"

        skill_match = MagicMock()
        skill_match.skill_name = "Diplomacy"
        skill_match.matched_trigger = "diplomacy"

        ani_profile = {
            "narrative": "## PC — Ani\n" + "X" * 300,
            "mechanical": "## PC Stats — Ani\n" + "X" * 350,
        }
        session = _make_session(
            messages=[{"role": "user", "content": "Ani tries to Diplomacy the mayor."}],
            pc_profiles={"ani": ani_profile},
            scene_npcs=["Kendra Deverin", "Belor Hemlock"],
        )

        npc_idx = _no_index()
        npc_idx.detect.return_value = npc1
        npc_idx.detect_by_location.return_value = [npc2]
        def _fmt(m):
            return f"## NPC Reference — {m.canonical_name}\n\n" + "X" * 2000
        npc_idx.format_context.side_effect = _fmt
        npc_idx.format_short_context.side_effect = lambda m: f"## NPC — {m.canonical_name}\nHook. | Diplomacy DC 12"

        skill_idx = _no_index()
        skill_idx.detect.return_value = skill_match
        skill_idx.format_context.return_value = "## Skill Reference — Diplomacy\n\n" + "X" * 900

        loc_idx = _no_index()
        loc_match = MagicMock()
        loc_match.canonical_name = "Festival Grounds"
        loc_match.matched_alias = "festival"
        loc_idx.detect.return_value = loc_match
        loc_idx.format_context.return_value = "## Location Reference — Festival Grounds\n\n" + "X" * 400

        with patch("api.session_manager._get_npc_index", return_value=npc_idx), \
             patch("api.session_manager._get_skill_index", return_value=skill_idx), \
             patch("api.session_manager._get_location_index", return_value=loc_idx), \
             patch("api.session_manager._get_event_index", return_value=_no_index()), \
             patch("api.session_manager._get_combat_rules_index", return_value=_no_index()):
            system_content, _ = _inject_context(session)

        chars = len(system_content)
        assert chars <= _ABSOLUTE_MAX, (
            f"Worst-case turn system prompt too large: {chars} chars (limit {_ABSOLUTE_MAX}). "
            f"This is a serious budget problem. Breakdown: {_budget_breakdown(system_content)}"
        )


# ── Diagnostic helper ─────────────────────────────────────────────────────────

def _budget_breakdown(content: str) -> str:
    """Return a one-line summary of which sections are present and their size."""
    sections = []
    markers = [
        ("FORMAT_EXAMPLE", "Gerhard Pickle"),
        ("SECTIONS_ACTIVE", "[SECTIONS ACTIVE THIS TURN]"),
        ("CONTEXT", "[CONTEXT FOR THIS TURN]"),
        ("COMBAT", "[COMBAT ONGOING"),
        ("COMBAT_START", "[COMBAT START FORMAT"),
        ("PC_NARRATIVE", "## PC —"),
        ("PC_STATS", "## PC Stats —"),
        ("DIRECTIVE", "[GM DIRECTIVE FOR THIS TURN"),
    ]
    for label, probe in markers:
        if probe in content:
            sections.append(label)
    return f"total={len(content)} present=[{', '.join(sections)}]"
