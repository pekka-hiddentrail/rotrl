"""
Prompt Builder — declarative, scene-aware context assembler.

Architecture
------------
The builder sits between the raw data sources (NpcIndex, SkillIndex,
LocationIndex, npc_extractor) and the final system prompt string.

The assembly pipeline is:

    classify_scene(session)                       → scene_type: str
        ↓
    SCENE_SLOTS[scene_type]                       → list[ContextSlot]
        ↓
    PromptBuilder(session).assemble(scene_type)   → AssembledPrompt
        ↓
    AssembledPrompt.content                       → system prompt string
    AssembledPrompt.slots                         → list[BuiltSlot]  (for preview panel)

Phase 1 (this file): dataclasses, SCENE_SLOTS config, classify_scene(), PromptBuilder stub.
Phase 2: GET /api/sessions/{id}/prompt_preview + PromptBuilderPanel.tsx.
Phase 3: session.use_prompt_builder flag wires assemble() into _inject_context().

Combat is explicitly excluded — call _build_combat_system_prompt() instead.
PromptBuilder.assemble() raises ValueError if scene_type is "combat".

See: specs/prompt-builder.feature, TODO.md §Prompt Optimization §Prompt builder
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Avoid circular import — GameSession is only needed for type hints.
    from api.session_manager import GameSession  # noqa: F401

# ---------------------------------------------------------------------------
# Valid source identifiers for ContextSlot.source
# ---------------------------------------------------------------------------
# "npc_extractor"      — get_npc_sections() from api/context/npc_extractor.py
# "npc_lookup"         — NpcIndex full profile from api/context/npc_lookup.py
# "skill_lookup"       — SkillIndex profile from api/context/skill_lookup.py
# "location_lookup"    — LocationIndex profile from api/context/location_lookup.py
# "event"              — active event content from EventIndex
# "history"            — trimmed session.messages (text)
# "gm_instructions"    — static GM authority / style text
# "party"              — PC profiles from session pc_profiles
# "active_participants"— scene_npcs list (names only)
# "deltas"             — per-NPC recent delta summaries

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
        Example: "npc_profiles", "gm_instructions", "history".
    label : str
        Human-readable label shown in the PromptBuilderPanel.
        Example: "NPC Profiles", "GM Instructions".
    source : str
        Which data source provides the raw content.
        Must be one of _VALID_SOURCES.
    sections : list[str]
        For source="npc_extractor": the exact section names to request via
        get_npc_sections().  Pass [] to request all above-line sections.
        For other sources: unused (pass []).
    token_budget : int
        Maximum character count for the assembled slot content.
        PromptBuilder truncates at the last newline within this limit.
    scene_types : list[str]
        The scene types that include this slot.
        ["social", "exploration"] means the slot only appears in social and
        exploration scenes.  Use ["*"] for all non-combat scenes (future).
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
    parent: str | None = None
    optional: bool = False


@dataclass
class BuiltSlot:
    """
    The assembled result for one ContextSlot after PromptBuilder.assemble().

    This is the per-slot payload returned by the preview endpoint and used
    by PromptBuilderPanel.tsx to display the hierarchy, token bars, and
    content previews.

    Fields
    ------
    key : str
        Matches the originating ContextSlot.key.
    label : str
        Matches the originating ContextSlot.label.
    parent : str | None
        Matches the originating ContextSlot.parent.
    token_count : int
        Actual character count of `content` after truncation.
        Always <= the slot's token_budget.
    content : str
        The assembled content string for this slot.
        Empty string when included=False.
    included : bool
        True if the slot content is part of the assembled prompt.
        False when the slot is optional and the data source returned empty.
    """
    key: str
    label: str
    parent: str | None
    token_count: int
    content: str
    included: bool


@dataclass
class AssembledPrompt:
    """
    Full output of PromptBuilder.assemble().

    Fields
    ------
    content : str
        The assembled system prompt string (all included slot contents
        concatenated in order).
    slots : list[BuiltSlot]
        One entry per ContextSlot in the scene's SCENE_SLOTS list,
        in depth-first order (children immediately after their parent).
        This list is used by the preview API and PromptBuilderPanel.
    scene_type : str
        The scene type that was used for assembly.
    """
    content: str
    slots: list[BuiltSlot]
    scene_type: str


# ---------------------------------------------------------------------------
# SCENE_SLOTS — the declarative context specification
# ---------------------------------------------------------------------------
# Each key is a scene type string returned by classify_scene().
# Each value is an ordered list of ContextSlot instances.
# The order determines injection order in the assembled prompt and
# display order in the PromptBuilderPanel.
#
# Token budgets are approximate character counts (1 token ≈ 4 chars).
# The global cap is _GROQ_MAX_SYSTEM_CHARS = 30,000.  The sum of all
# token_budget values per scene type should stay well under that limit.
#
# "combat" is intentionally absent — PromptBuilder raises ValueError for it.

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
# classify_scene
# ---------------------------------------------------------------------------

def classify_scene(session: "GameSession") -> str:
    """
    Derive the current scene type from session state.

    Rules (evaluated in priority order):
    1. session.combat_state is not None  →  "combat"
    2. Active event with event_type "combat"  →  "combat"
    3. session.scene_npcs is non-empty  →  "social"
    4. session.scene_locations is non-empty  →  "exploration"
    5. Default  →  "social"

    Returns
    -------
    str
        One of "combat", "social", "exploration", "dungeon", "skill_challenge".
        Note: "combat" is returned here but PromptBuilder.assemble() will
        raise ValueError for it — the caller must route to
        _build_combat_system_prompt() instead.

    Notes
    -----
    - Pure Python, no LLM call, < 1 ms.
    - Does not consult session.current_location_id for dungeon/skill_challenge
      classification yet — those scene types are manually invoked or will be
      added as a signal in Phase 2.
    """
    raise NotImplementedError(
        "classify_scene() is not yet implemented. "
        "Implementation guide:\n"
        "  1. if session.combat_state is not None: return 'combat'\n"
        "  2. for event in session.active_events:\n"
        "         if getattr(event, 'event_type', None) == 'combat': return 'combat'\n"
        "  3. if session.scene_npcs: return 'social'\n"
        "  4. if session.scene_locations: return 'exploration'\n"
        "  5. return 'social'"
    )


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

def _truncate_at_line_boundary(text: str, max_chars: int) -> str:
    """
    Truncate *text* to at most *max_chars* characters, breaking only at
    a newline boundary so no line is split mid-word.

    If the text is already within budget, it is returned unchanged.
    If no newline exists within the budget window, the whole text is
    returned (never truncate to empty).
    """
    raise NotImplementedError(
        "_truncate_at_line_boundary() is not yet implemented. "
        "Implementation guide:\n"
        "  if len(text) <= max_chars: return text\n"
        "  window = text[:max_chars]\n"
        "  cut = window.rfind('\\n')\n"
        "  return window[:cut] if cut > 0 else text  # never truncate to empty"
    )


class PromptBuilder:
    """
    Assembles a system prompt from declarative slot config + live session state.

    Usage
    -----
    >>> assembled = PromptBuilder(session).assemble()
    >>> system_prompt = assembled.content
    >>> slots_for_panel = assembled.slots

    With an override (for the preview endpoint):
    >>> assembled = PromptBuilder(session).assemble(scene_type_override="exploration")

    Raises
    ------
    ValueError
        If the resolved scene type is "combat".  Combat prompt assembly is
        the responsibility of _build_combat_system_prompt() in session_manager.py.
    """

    def __init__(self, session: "GameSession") -> None:
        """
        Parameters
        ----------
        session : GameSession
            The live session whose state drives classification and data lookup.
        """
        self._session = session

    def assemble(
        self,
        scene_type_override: str | None = None,
    ) -> AssembledPrompt:
        """
        Assemble the system prompt for the current session.

        Parameters
        ----------
        scene_type_override : str | None
            When provided, bypasses classify_scene() and uses this scene type
            directly.  Used by the preview API endpoint
            (GET /api/sessions/{id}/prompt_preview?scene_type=exploration).
            Must be a key in SCENE_SLOTS or "combat" (which still raises).

        Returns
        -------
        AssembledPrompt
            .content  — assembled system prompt string
            .slots    — list[BuiltSlot] in depth-first order
            .scene_type — the scene type that was used

        Raises
        ------
        ValueError
            If scene_type resolves to "combat" (directly or via override).
        ValueError
            If scene_type_override is provided but not a valid type.

        Notes
        -----
        Implementation guide (Phase 1):

        1. Resolve scene_type:
               scene_type = scene_type_override or classify_scene(self._session)
               if scene_type_override and scene_type_override not in SCENE_SLOTS | {"combat"}:
                   raise ValueError(f"Invalid scene_type: {scene_type_override!r}")

        2. Guard against combat:
               if scene_type == "combat":
                   raise ValueError(
                       "Use _build_combat_system_prompt() for combat scenes"
                   )

        3. Iterate slots and build content:
               slots = SCENE_SLOTS[scene_type]
               built: list[BuiltSlot] = []
               content_parts: list[str] = []

               for slot in slots:
                   raw = self._fetch(slot)          # dispatch to data source
                   truncated = _truncate_at_line_boundary(raw, slot.token_budget)
                   included = bool(truncated) or not slot.optional
                   built.append(BuiltSlot(
                       key=slot.key, label=slot.label, parent=slot.parent,
                       token_count=len(truncated), content=truncated,
                       included=included,
                   ))
                   if included and truncated:
                       content_parts.append(truncated)

        4. Return:
               return AssembledPrompt(
                   content="\\n\\n".join(content_parts),
                   slots=built,
                   scene_type=scene_type,
               )
        """
        raise NotImplementedError(
            "PromptBuilder.assemble() is not yet implemented. "
            "See the docstring for the implementation guide."
        )

    def _fetch(self, slot: ContextSlot) -> str:
        """
        Fetch raw content for *slot* from its data source.

        Dispatch table:
        - "gm_instructions"   → static GM authority text from system prompt
        - "party"             → pc_profiles text from session
        - "event"             → active event content from session.active_events
        - "npc_extractor"     → get_npc_sections() for each NPC in scene_npcs,
                                 filtered by slot.sections; concatenated
        - "npc_lookup"        → NpcIndex full profile for each scene NPC
        - "skill_lookup"      → SkillIndex profile for detected skills
        - "location_lookup"   → LocationIndex profile for current_location_id
        - "active_participants"→ "\n".join(session.scene_npcs)
        - "deltas"            → recent delta summaries from session NPC delta files
        - "history"           → trimmed session.messages rendered as text

        Returns "" (empty string) if the source has no content for this session.

        Notes
        -----
        Implementation guide:

            if slot.source == "npc_extractor":
                parts = []
                for npc_name in self._session.scene_npcs:
                    sections = get_npc_sections(npc_name, slot.sections or None)
                    # sections is dict[str, str | None]; skip None values
                    for section_text in sections.values():
                        if section_text:
                            parts.append(section_text)
                return "\\n\\n".join(parts)

            if slot.source == "active_participants":
                return "\\n".join(self._session.scene_npcs)

            ... etc.
        """
        raise NotImplementedError(
            f"PromptBuilder._fetch() not yet implemented for source={slot.source!r}. "
            "See the docstring for the implementation guide."
        )
