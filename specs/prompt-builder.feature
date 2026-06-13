# FEATURE — Prompt Builder

**ID:** prompt-builder
**Status:** Planned — Phase 1
**Area:** Backend
**Tags:** @prompt @injection @context @builder @scene

---

## Story

> As the **GM engine**,
> I want a declarative, scene-aware context assembler,
> so that each turn's system prompt contains exactly the sections relevant to the
> current scene type — no more, no less — and the assembled prompt is inspectable
> without reading session logs.

The builder sits between the raw data sources (`NpcIndex`, `SkillIndex`,
`LocationIndex`, `npc_extractor`) and the final system prompt string.
Phase 1 ships the backend foundation and a read-only preview endpoint.
Phase 2 adds the frontend panel. Phase 3 wires the builder into live turns.

---

## Background

- Given the `api/context/` directory exists
- And `npc_extractor.get_npc_sections()` is available
- And `SceneClassifier` has classified the current session

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — `SceneClassifier` derives scene type from session state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Scene type is derived from current `GameSession` state

```gherkin
Given a GameSession in various states
When  classify_scene(session) is called
Then  it returns "combat"       when session.combat_state is not None
And   it returns "combat"       when active_event_id has event_type "combat"
And   it returns "social"       when scene_npcs is non-empty and no combat
And   it returns "exploration"  when scene_locations is non-empty, no NPCs, no combat
And   it returns "social"       when session is empty (default fallback)
```

**Notes:**
- Classification is pure Python — no LLM call, < 1 ms
- Priority order: combat_state → active combat event → scene_npcs → scene_locations → default
- An explicit `session.scene_type_override` (future) will outrank all signals

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — `ContextSlot` dataclass captures the contract for one context block
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A ContextSlot is instantiated

```gherkin
Given a ContextSlot is created with required fields
Then  it has: key (str), label (str), source (str), sections (list[str]),
      token_budget (int), scene_types (list[str])
And   parent defaults to None
And   optional defaults to False
And   source is one of: "npc_extractor" | "npc_lookup" | "skill_lookup"
      | "location_lookup" | "event" | "history" | "gm_instructions" | "party"
      | "active_participants" | "deltas"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — `SCENE_SLOTS` defines slots for all non-combat scene types
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** SCENE_SLOTS config is loaded

```gherkin
Given the SCENE_SLOTS module-level dict
Then  it contains keys: "social", "exploration", "dungeon", "skill_challenge"
And   it does NOT contain "combat" (combat uses _build_combat_system_prompt())
And   every scene type includes slots: gm_instructions, party, encounter_spec, history
And   social includes: npc_profiles (parent=event_desc), active_participants, deltas, zones
And   exploration includes: location, npc_profiles (parent=event_desc), zones
And   dungeon includes: location, zones, npc_profiles (parent=location)
And   skill_challenge includes: skill_rules, npc_profiles
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — NPC sections are filtered per scene type
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** NPC profile slot is assembled for different scene types

```gherkin
Given an NPC is in scene_npcs
When  PromptBuilder assembles the npc_profiles slot for each scene type
Then  social       requests: ["Personality", "GM Notes", "Social Checks"]
And   exploration  requests: ["Personality", "Appearance"]
And   dungeon      requests: ["Appearance", "State Handling"]
And   skill_challenge requests: ["Social Checks", "Secrets"]
And   get_npc_sections() is called with exactly those section names
And   sections absent from the NPC file return None and are omitted silently
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — `PromptBuilder.assemble()` returns content string and slot breakdown
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** PromptBuilder assembles a social scene prompt

```gherkin
Given a session classified as "social" with one NPC in scene_npcs
When  PromptBuilder(session).assemble() is called
Then  it returns an AssembledPrompt with:
        - content: str  (the assembled system prompt string)
        - slots: list[BuiltSlot]
And   each BuiltSlot has: key, label, parent, token_count (int), content (str),
      included (bool)
And   included=False for optional slots whose data source returned empty
And   the assembled content contains each included slot's content in order
And   the total length of content equals sum of included slot token_counts (approx)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — `token_budget` is enforced per slot
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A slot's content exceeds its token budget

```gherkin
Given a ContextSlot with token_budget=200
And   the data source returns content of 500 chars
When  PromptBuilder assembles that slot
Then  the slot content in the assembled output is ≤ 200 chars
And   BuiltSlot.token_count reflects the truncated length
And   truncation preserves complete lines (no mid-word or mid-sentence cut)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Slot hierarchy is preserved in the BuiltSlot list
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** BuiltSlot list reflects parent/child relationships

```gherkin
Given a social scene with npc_profiles and zones configured as children of event_desc
When  PromptBuilder.assemble() returns slots
Then  the npc_profiles BuiltSlot has parent="event_desc"
And   the zones BuiltSlot has parent="event_desc"
And   the gm_instructions BuiltSlot has parent=None
And   child slots appear after their parent slot in the list (depth-first order)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Combat scene type is explicitly refused
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** PromptBuilder is called for a combat session

```gherkin
Given a session with session.combat_state is not None
When  PromptBuilder(session).assemble() is called
Then  it raises ValueError
And   the error message references "_build_combat_system_prompt()"
```

**Notes:**
- Combat prompt assembly remains the responsibility of `_build_combat_system_prompt()`
- This keeps the two prompt paths cleanly separated and prevents accidental misuse

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Optional slots are omitted when their data source is empty
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A session has no active NPCs

```gherkin
Given a session with scene_npcs = [] and optional=True on the npc_profiles slot
When  PromptBuilder assembles the prompt
Then  the npc_profiles slot content is not included in the assembled string
And   the BuiltSlot for npc_profiles has included=False
And   no error is raised
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — `GET /api/sessions/{id}/prompt_preview` returns slot breakdown
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer calls the preview endpoint

```gherkin
Given an active session
When  GET /api/sessions/{id}/prompt_preview is called
Then  it returns 200 with JSON:
        {
          "scene_type": "social",
          "total_tokens": <int>,
          "slots": [
            { "key": "gm_instructions", "label": "GM instructions",
              "parent": null, "token_count": <int>, "content": "You are...",
              "included": true },
            ...
          ]
        }
And   scene_type can be overridden via ?scene_type=exploration query param
And   returns 404 on unknown session
And   returns 400 if scene_type override is not a valid type
```

**Notes:**
- This endpoint is read-only — it does NOT affect the live session or inject context
- It is the data source for the Phase 2 `PromptBuilderPanel.tsx` frontend component

---

## Out of Scope (Phase 1)

- `PromptBuilderPanel.tsx` frontend component (Phase 2)
- Wiring `PromptBuilder` into `_inject_context()` live turns (Phase 3)
- History summarization — history slot uses raw trimmed messages (Phase 4)
- Rules library tag index for feats/traits (Phase 4)
- `dungeon` and `skill_challenge` scene types beyond config (Phase 2 content pass)

---

## Notes

- `api/context/prompt_builder.py` — new file; imports `npc_extractor`, `npc_lookup`,
  `skill_lookup`, `location_lookup`
- `tests/test_prompt_builder.py` — new file; ~30 tests using `tmp_path` and mock sessions
- Phase 2 adds `GET /api/sessions/{id}/prompt_preview` and `PromptBuilderPanel.tsx`
- Phase 3 adds `session.use_prompt_builder: bool` flag and migrates `_inject_context()`
  slot-by-slot, keeping old path live behind the flag
- See: [INDEX.md §prompt-builder](INDEX.md), TODO.md Prompt Optimization section
