"""
Prompt Builder — declarative, scene-aware context assembler.

Architecture
------------
The builder sits between the raw data sources (NpcIndex, SkillIndex,
LocationIndex, npc_extractor) and the final system prompt string.

The assembly pipeline is:

    classify_scene(session)                        → scene_type: str
        ↓
    SCENE_SLOTS[scene_type]                        → list[ContextSlot]
        ↓
    PromptBuilder(session).assemble(scene_type)    → AssembledPrompt
        ↓
    AssembledPrompt.content                        → system prompt string
    AssembledPrompt.slots                          → list[BuiltSlot]  (for preview panel)

Phase 1 (this file): dataclasses, SCENE_SLOTS config, classify_scene(), PromptBuilder core.
Phase 2: GET /api/sessions/{id}/prompt_preview + PromptBuilderPanel.tsx.
Phase 3: session.use_prompt_builder flag wires assemble() into _inject_context().

Combat is explicitly excluded — call _build_combat_system_prompt() instead.
PromptBuilder.assemble() raises ValueError if scene_type is "combat".

See: specs/prompt-builder.feature, TODO.md §Prompt Optimization §Prompt builder
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from api.context.npc_extractor import get_npc_sections

if TYPE_CHECKING:
    # Avoid circular import — GameSession is only needed for type hints.
    from api.session_manager import GameSession  # noqa: F401
    from api.context.event_index import EventIndex  # noqa: F401
    from api.context.npc_lookup import NpcIndex  # noqa: F401
    from api.context.skill_lookup import SkillIndex  # noqa: F401
    from api.context.location_lookup import LocationIndex  # noqa: F401

# ---------------------------------------------------------------------------
# Valid source identifiers for ContextSlot.source
# ---------------------------------------------------------------------------
_VALID_SOURCES = frozenset({
    "npc_extractor",
    "npc_lookup",
    "skill_lookup",
    "location_lookup",
    "event",
    "history",
    "gm_instructions",
    "party",
    "active_participants",
    "deltas",
})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ContextSlot:
    """
    Declarative specification for one block of context to inject.

    Fields
    ------
    key : str
        Machine identifier used in BuiltSlot and the preview API response.
    label : str
        Human-readable label shown in PromptBuilderPanel.
    source : str
        Which data source provides the raw content. Must be in _VALID_SOURCES.
    sections : list[str]
        For source="npc_extractor": exact section names to request via
        get_npc_sections().  Pass [] to request all above-line sections.
        For other sources: unused (pass []).
    token_budget : int
        Maximum character count for the assembled slot content.
        PromptBuilder truncates at the last newline within this limit.
    scene_types : list[str]
        Scene types that include this slot.
    parent : str | None
        Key of the parent slot (for hierarchy display in the panel).
        None for top-level slots.
    optional : bool
        When True, the slot is silently omitted if the data source returns
        empty content.  BuiltSlot.included will be False.
        When False (default), an empty data source still produces an empty
        slot (included=True, content="").
    """
    key: str
    label: str
    source: str
    sections: list[str]
    token_budget: int
    scene_types: list[str]
    parent: Optional[str] = None
    optional: bool = False


@dataclass
class BuiltSlot:
    """
    The assembled result for one ContextSlot after PromptBuilder.assemble().

    Fields
    ------
    key : str        — matches the originating ContextSlot.key
    label : str      — matches the originating ContextSlot.label
    parent : str | None  — matches the originating ContextSlot.parent
    token_count : int    — actual character count of `content` after truncation
    content : str        — the assembled text for this slot
    included : bool      — False when optional and data source returned empty
    """
    key: str
    label: str
    parent: Optional[str]
    token_count: int
    content: str
    included: bool


@dataclass
class AssembledPrompt:
    """
    Full output of PromptBuilder.assemble().

    Fields
    ------
    content : str           — assembled system prompt string (included slots joined)
    slots : list[BuiltSlot] — one entry per slot in depth-first order
    scene_type : str        — the scene type used for assembly
    """
    content: str
    slots: list[BuiltSlot]
    scene_type: str


# ---------------------------------------------------------------------------
# SCENE_SLOTS — the declarative context specification
# ---------------------------------------------------------------------------

SCENE_SLOTS: dict[str, list[ContextSlot]] = {

    "social": [
        ContextSlot(
            key="gm_instructions",
            label="GM Instructions",
            source="gm_instructions",
            sections=[],
            token_budget=2_000,
            scene_types=["social"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="party",
            label="Party Profiles",
            source="party",
            sections=[],
            token_budget=1_500,
            scene_types=["social"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="encounter_spec",
            label="Encounter / Event Spec",
            source="event",
            sections=[],
            token_budget=2_000,
            scene_types=["social"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="npc_profiles",
            label="NPC Profiles",
            source="npc_extractor",
            sections=["Personality", "GM Notes", "Social Checks"],
            token_budget=3_000,
            scene_types=["social"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="active_participants",
            label="Active Participants",
            source="active_participants",
            sections=[],
            token_budget=500,
            scene_types=["social"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="zones",
            label="Zones",
            source="location_lookup",
            sections=["Zones"],
            token_budget=800,
            scene_types=["social"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="deltas",
            label="NPC Deltas",
            source="deltas",
            sections=[],
            token_budget=1_000,
            scene_types=["social"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="history",
            label="Session History",
            source="history",
            sections=[],
            token_budget=4_000,
            scene_types=["social"],
            parent=None,
            optional=False,
        ),
    ],

    "exploration": [
        ContextSlot(
            key="gm_instructions",
            label="GM Instructions",
            source="gm_instructions",
            sections=[],
            token_budget=2_000,
            scene_types=["exploration"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="party",
            label="Party Profiles",
            source="party",
            sections=[],
            token_budget=1_500,
            scene_types=["exploration"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="encounter_spec",
            label="Encounter / Event Spec",
            source="event",
            sections=[],
            token_budget=2_000,
            scene_types=["exploration"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="location",
            label="Location Profile",
            source="location_lookup",
            sections=[],
            token_budget=2_000,
            scene_types=["exploration"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="zones",
            label="Zones",
            source="location_lookup",
            sections=["Zones"],
            token_budget=800,
            scene_types=["exploration"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="npc_profiles",
            label="NPC Profiles",
            source="npc_extractor",
            sections=["Personality", "Appearance"],
            token_budget=2_000,
            scene_types=["exploration"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="deltas",
            label="NPC Deltas",
            source="deltas",
            sections=[],
            token_budget=800,
            scene_types=["exploration"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="history",
            label="Session History",
            source="history",
            sections=[],
            token_budget=4_000,
            scene_types=["exploration"],
            parent=None,
            optional=False,
        ),
    ],

    "dungeon": [
        ContextSlot(
            key="gm_instructions",
            label="GM Instructions",
            source="gm_instructions",
            sections=[],
            token_budget=2_000,
            scene_types=["dungeon"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="party",
            label="Party Profiles",
            source="party",
            sections=[],
            token_budget=1_500,
            scene_types=["dungeon"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="encounter_spec",
            label="Encounter / Event Spec",
            source="event",
            sections=[],
            token_budget=2_000,
            scene_types=["dungeon"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="location",
            label="Location Profile",
            source="location_lookup",
            sections=[],
            token_budget=2_000,
            scene_types=["dungeon"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="zones",
            label="Zones",
            source="location_lookup",
            sections=["Zones"],
            token_budget=800,
            scene_types=["dungeon"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="npc_profiles",
            label="NPC Profiles",
            source="npc_extractor",
            sections=["Appearance", "State Handling"],
            token_budget=2_000,
            scene_types=["dungeon"],
            parent="location",
            optional=True,
        ),
        ContextSlot(
            key="history",
            label="Session History",
            source="history",
            sections=[],
            token_budget=4_000,
            scene_types=["dungeon"],
            parent=None,
            optional=False,
        ),
    ],

    "skill_challenge": [
        ContextSlot(
            key="gm_instructions",
            label="GM Instructions",
            source="gm_instructions",
            sections=[],
            token_budget=2_000,
            scene_types=["skill_challenge"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="party",
            label="Party Profiles",
            source="party",
            sections=[],
            token_budget=1_500,
            scene_types=["skill_challenge"],
            parent=None,
            optional=False,
        ),
        ContextSlot(
            key="encounter_spec",
            label="Encounter / Event Spec",
            source="event",
            sections=[],
            token_budget=2_000,
            scene_types=["skill_challenge"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="skill_rules",
            label="Skill Rules",
            source="skill_lookup",
            sections=[],
            token_budget=1_500,
            scene_types=["skill_challenge"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="npc_profiles",
            label="NPC Profiles",
            source="npc_extractor",
            sections=["Social Checks", "Secrets"],
            token_budget=2_000,
            scene_types=["skill_challenge"],
            parent="encounter_spec",
            optional=True,
        ),
        ContextSlot(
            key="deltas",
            label="NPC Deltas",
            source="deltas",
            sections=[],
            token_budget=800,
            scene_types=["skill_challenge"],
            parent=None,
            optional=True,
        ),
        ContextSlot(
            key="history",
            label="Session History",
            source="history",
            sections=[],
            token_budget=4_000,
            scene_types=["skill_challenge"],
            parent=None,
            optional=False,
        ),
    ],
}

# Guard: "combat" must never appear in SCENE_SLOTS.
assert "combat" not in SCENE_SLOTS, (
    "SCENE_SLOTS must not contain 'combat'. "
    "Use _build_combat_system_prompt() for combat scenes."
)

_VALID_SCENE_TYPES = frozenset(SCENE_SLOTS.keys())


# ---------------------------------------------------------------------------
# Token budget helper
# ---------------------------------------------------------------------------

def _truncate_at_line_boundary(text: str, max_chars: int) -> str:
    """
    Truncate *text* to at most *max_chars* characters, breaking only at a
    newline boundary so no line is cut mid-word.

    Rules:
    - If len(text) <= max_chars, return text unchanged.
    - Otherwise, take text[:max_chars] and find the last newline.
    - If a newline exists, truncate there (preserving the last complete line).
    - If no newline exists within the window, return the full text rather than
      truncating to an empty string (never drop non-empty content entirely).
    """
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    cut = window.rfind("\n")
    if cut > 0:
        return window[:cut]
    # No newline in the window — return as-is to avoid losing all content.
    return text


# ---------------------------------------------------------------------------
# classify_scene
# ---------------------------------------------------------------------------

def classify_scene(
    session: "GameSession",
    event_index: Optional["EventIndex"] = None,
) -> str:
    """
    Derive the current scene type from session state.

    Priority order (first match wins):
    1. session.combat_state is not None              →  "combat"
    2. active scheduled event has event_type="combat"→  "combat"
       (requires event_index; skipped when event_index is None)
    3. session.scene_npcs is non-empty               →  "social"
    4. session.scene_locations is non-empty          →  "exploration"
    5. default                                       →  "social"

    Parameters
    ----------
    session : GameSession
        The live session object.
    event_index : EventIndex | None
        Optional event index for checking the active scheduled event type.
        When None, signal #2 is skipped (session.combat_state still catches
        all combat states that have been fully initialised).

    Returns
    -------
    str
        One of: "combat", "social", "exploration".
        Note: PromptBuilder.assemble() raises ValueError for "combat" —
        the caller must route to _build_combat_system_prompt() instead.
    """
    # 1. Active combat tracker
    if session.combat_state is not None:
        return "combat"

    # 2. Active scheduled event is a combat event
    if event_index is not None:
        active_event_id = getattr(
            getattr(session, "event_runtime", None), "active_event_id", None
        )
        if active_event_id:
            entry = event_index.get(active_event_id)
            if entry is not None and getattr(entry, "event_type", "") == "combat":
                return "combat"

    # 3. Named NPCs are in the scene
    if session.scene_npcs:
        return "social"

    # 4. Named locations have been entered
    if session.scene_locations:
        return "exploration"

    # 5. Default
    return "social"


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class PromptBuilder:
    """
    Assembles a system prompt from declarative slot config + live session state.

    Inject optional indexes for testing or for callers that already hold them:

        PromptBuilder(session)                          # uses lazy imports
        PromptBuilder(session, npc_index=mock_idx)      # test-friendly

    Usage
    -----
    >>> assembled = PromptBuilder(session).assemble()
    >>> system_prompt = assembled.content
    >>> slots_for_panel = assembled.slots

    With scene type override (for the preview endpoint):
    >>> assembled = PromptBuilder(session).assemble(scene_type_override="exploration")

    Raises
    ------
    ValueError
        If the resolved scene type is "combat" — use _build_combat_system_prompt().
    ValueError
        If scene_type_override is not a valid type.
    """

    def __init__(
        self,
        session: "GameSession",
        *,
        npc_index: Optional["NpcIndex"] = None,
        skill_index: Optional["SkillIndex"] = None,
        location_index: Optional["LocationIndex"] = None,
        event_index: Optional["EventIndex"] = None,
    ) -> None:
        self._session = session
        self._npc_index = npc_index
        self._skill_index = skill_index
        self._location_index = location_index
        self._event_index = event_index

    # ── Public method ─────────────────────────────────────────────────────────

    def assemble(
        self,
        scene_type_override: Optional[str] = None,
    ) -> AssembledPrompt:
        """
        Assemble the system prompt for the current session.

        Parameters
        ----------
        scene_type_override : str | None
            Bypasses classify_scene() and uses this scene type directly.
            Used by the preview endpoint (?scene_type=exploration).
            Must be a key in SCENE_SLOTS or "combat" (which still raises).

        Returns
        -------
        AssembledPrompt
            .content    — assembled system prompt string
            .slots      — list[BuiltSlot] in depth-first order
            .scene_type — the scene type used

        Raises
        ------
        ValueError
            If scene_type resolves to "combat".
        ValueError
            If scene_type_override is provided but not a recognised type.
        """
        # Resolve scene type
        if scene_type_override is not None:
            all_types = _VALID_SCENE_TYPES | {"combat"}
            if scene_type_override not in all_types:
                raise ValueError(
                    f"Invalid scene_type_override: {scene_type_override!r}. "
                    f"Valid values: {sorted(all_types)}"
                )
            scene_type = scene_type_override
        else:
            scene_type = classify_scene(self._session, self._event_index)

        # Guard: combat is handled elsewhere
        if scene_type == "combat":
            raise ValueError(
                f"PromptBuilder cannot assemble combat scenes. "
                f"Use _build_combat_system_prompt() for combat scenes."
            )

        slots = SCENE_SLOTS[scene_type]
        built: list[BuiltSlot] = []
        content_parts: list[str] = []

        for slot in slots:
            raw = self._fetch(slot)
            truncated = _truncate_at_line_boundary(raw, slot.token_budget)

            if slot.optional and not truncated.strip():
                # Optional + empty → include=False, zero tokens
                built.append(BuiltSlot(
                    key=slot.key,
                    label=slot.label,
                    parent=slot.parent,
                    token_count=0,
                    content="",
                    included=False,
                ))
            else:
                included = bool(truncated.strip()) or not slot.optional
                built.append(BuiltSlot(
                    key=slot.key,
                    label=slot.label,
                    parent=slot.parent,
                    token_count=len(truncated),
                    content=truncated,
                    included=included,
                ))
                if truncated:
                    content_parts.append(truncated)

        return AssembledPrompt(
            content="\n\n".join(content_parts),
            slots=built,
            scene_type=scene_type,
        )

    # ── Private: data source dispatch ────────────────────────────────────────

    def _fetch(self, slot: ContextSlot) -> str:
        """
        Fetch raw content for *slot* from its data source.

        Returns "" when the source has no content for the current session.
        Never raises — missing data is an empty string.
        """
        src = slot.source

        if src == "gm_instructions":
            return self._session.system_prompt or ""

        if src == "party":
            return self._fetch_party()

        if src == "event":
            return self._fetch_event()

        if src == "npc_extractor":
            return self._fetch_npc_extractor(slot.sections)

        if src == "npc_lookup":
            return self._fetch_npc_lookup()

        if src == "active_participants":
            names = list(self._session.scene_npcs)
            return "\n".join(names) if names else ""

        if src == "location_lookup":
            return self._fetch_location(slot.sections)

        if src == "skill_lookup":
            return self._fetch_skill()

        if src == "history":
            return self._fetch_history()

        if src == "deltas":
            # Phase 2+: delta summaries built from NPC session files.
            # Return empty for now so optional delta slots are cleanly omitted.
            return ""

        return ""

    # ── Fetch helpers ─────────────────────────────────────────────────────────

    def _fetch_party(self) -> str:
        """Return PC narrative profiles joined together."""
        profiles = getattr(self._session, "pc_profiles", {})
        if not profiles:
            return ""
        parts = []
        for _name, profile in profiles.items():
            narrative = profile.get("narrative", "")
            if narrative:
                parts.append(narrative)
        return "\n\n".join(parts)

    def _fetch_event(self) -> str:
        """Return active event content blocks joined together."""
        active_events = getattr(self._session, "active_events", [])
        if not active_events:
            return ""
        parts = [ev.content for ev in active_events if getattr(ev, "content", "")]
        return "\n\n".join(parts)

    def _fetch_npc_extractor(self, sections: list[str]) -> str:
        """
        Return section-filtered NPC content for all NPCs in scene_npcs.

        Calls get_npc_sections() for each NPC with the slot's section list.
        Missing sections (returned as None) are silently skipped.
        FileNotFoundError (unknown NPC) is silently swallowed — the NPC may
        be a session stub without a base.md yet.
        """
        scene_npcs = getattr(self._session, "scene_npcs", [])
        if not scene_npcs:
            return ""

        all_parts: list[str] = []
        for npc_name in scene_npcs:
            try:
                result = get_npc_sections(
                    npc_name,
                    sections if sections else None,
                )
            except (FileNotFoundError, OSError):
                continue

            # Collect section values in the order requested; skip None/empty
            canonical_name = result.get("Name", npc_name)
            npc_parts: list[str] = [f"### {canonical_name}"]
            for key, value in result.items():
                if key == "Name":
                    continue
                if value:
                    npc_parts.append(f"**{key}**\n{value}")

            if len(npc_parts) > 1:  # more than just the header
                all_parts.append("\n\n".join(npc_parts))

        return "\n\n---\n\n".join(all_parts)

    def _fetch_npc_lookup(self) -> str:
        """Return full NPC profiles via NpcIndex for NPCs in scene_npcs."""
        idx = self._npc_index
        if idx is None:
            try:
                from api.session_manager import _npc_index as _g  # lazy import
                idx = _g
            except ImportError:
                return ""

        scene_npcs = getattr(self._session, "scene_npcs", [])
        parts = []
        for npc_name in scene_npcs:
            match = idx.lookup(npc_name)
            if match:
                parts.append(idx.format_context(match))
        return "\n\n".join(parts)

    def _fetch_location(self, sections: list[str]) -> str:
        """
        Return location profile for the session's current_location_id.

        When sections is non-empty, it's a hint for which part of the location
        profile to return (e.g. ["Zones"]). For Phase 1 this is treated as a
        full-profile request since LocationIndex profiles are single-block text.
        """
        idx = self._location_index
        if idx is None:
            try:
                from api.session_manager import _location_index as _g
                idx = _g
            except ImportError:
                return ""

        loc_id = getattr(self._session, "current_location_id", "") or ""
        if not loc_id:
            # Fall back to first scene_location if current_location_id not set
            scene_locations = getattr(self._session, "scene_locations", [])
            if scene_locations:
                loc_id = scene_locations[0]

        if not loc_id:
            return ""

        match = idx.lookup(loc_id)  # type: ignore[attr-defined]
        if match is None:
            return ""
        return match.profile_text or ""

    def _fetch_skill(self) -> str:
        """
        Return skill rules for the active skill in the current scene.

        Phase 1: No detected skill is stored on the session yet — skill
        detection happens per-turn in _inject_context() from player input.
        Returns "" until Phase 3 wires a session.detected_skills field.
        """
        # TODO (Phase 3): add session.detected_skills: list[str] and look them up here.
        return ""

    def _fetch_history(self) -> str:
        """
        Return session message history formatted as plain text.

        Formats each message as "PLAYER: ..." or "GM: ..." lines.
        The actual turn-window trimming is the responsibility of _inject_context();
        here we format whatever is currently in session.messages.
        """
        messages = getattr(self._session, "messages", [])
        if not messages:
            return ""

        role_labels = {"user": "PLAYER", "assistant": "GM", "system": "SYSTEM"}
        lines: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                continue  # system prompt is the gm_instructions slot
            label = role_labels.get(role, role.upper())
            lines.append(f"{label}: {content}")

        return "\n".join(lines)
