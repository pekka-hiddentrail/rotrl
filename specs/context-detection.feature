# FEATURE — Context Detection & Injection

**ID:** context-detection
**Status:** Approved
**Area:** Backend
**Tags:** @context @npc @skill @location @injection @token

---

## Story

> As the **GM engine**,
> I want to detect which NPC, skill, and location the player is referencing,
> so that the correct rules and character profile are injected into the prompt without any extra LLM calls.

Detection is pure text matching (alias/trigger/location keyword against player input). Results are prepended to the system prompt as a per-turn copy and emitted to the frontend as a `context` SSE event for the intent bar.

---

## Background

- Given a session is active
- And the NPC index and skill index have been loaded

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Short NPC stub injected when alias is mentioned (no skill active)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player mentions an NPC by alias but no skill trigger fires

```gherkin
Given Ameiko Kaijitsu has aliases: "ameiko", "kaijitsu", "innkeeper"
When  the player inputs "I ask the innkeeper about the goblins"
And   no skill trigger is present in the input
Then  the per-turn prompt includes a short NPC stub for Ameiko (~60 tokens)
And   the stub contains her first Personality sentence, Diplomacy DC, disposition, and location
And   the context SSE event contains npc="Ameiko Kaijitsu" and npc_trigger="innkeeper"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Longest alias wins when multiple match
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input matches both a short and a long alias

```gherkin
Given NPC "Ameiko Kaijitsu" has alias "ameiko kaijitsu" (15 chars) and "ameiko" (6 chars)
When  the player inputs "I talk to Ameiko Kaijitsu"
Then  the matched alias is "ameiko kaijitsu" (the longer match wins)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Skill rules injected when trigger phrase is detected
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input contains a skill trigger phrase

```gherkin
Given Diplomacy has trigger "persuade"
When  the player inputs "I persuade the guard to let us through"
Then  the per-turn prompt includes the Diplomacy Skill Reference block
And   skill detection runs before NPC detection (skill result gates NPC format)
And   the context SSE event contains skill="Diplomacy" and skill_trigger="persuade"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Location keyword injects location profile only; no implicit NPC injection
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input mentions a location without naming any NPC

```gherkin
Given the player inputs "I head to the garrison to report what happened"
And   "Hemlock" or "Belor" does not appear in the input
When  the turn is processed
Then  the per-turn prompt includes the Sandpoint Garrison location block
And   Hemlock's NPC block is NOT injected
And   the context SSE event contains location="Sandpoint Garrison" and location_npcs=[]
```

> **Note:** `detect_by_location` (auto-injecting NPCs tagged to a location) is disabled.
> NPCs are only injected when the player explicitly names them in the input.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — No context detected emits null fields
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input contains no recognisable NPC, skill, or location

```gherkin
Given the player inputs "I look around the room"
When  the turn completes
Then  the context SSE event contains npc=null, skill=null, location=null
And   no context block is injected into the per-turn prompt
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Full NPC profile injected when skill is also active
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player names an NPC and uses an explicit skill trigger in the same input

```gherkin
Given Belor Hemlock is an NPC and Diplomacy has trigger "persuade"
When  the player inputs "I persuade Hemlock to reveal what he knows about Nualia"
Then  skill detection fires first (Diplomacy matched)
And   NPC detection fires next (Hemlock matched)
And   the per-turn prompt includes the full Hemlock NPC Reference block (~500 tokens)
And   the full block contains his complete Personality, Social Checks, and State Handling sections
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Skill detection order precedes NPC detection
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Both NPC and skill are detected on the same turn

```gherkin
Given a turn input that matches both an NPC alias and a skill trigger
When  _inject_context processes the turn
Then  SkillIndex.detect() is called before NpcIndex.detect()
And   the result of the skill detection is used to decide whether to call
        NpcIndex.format_context() (full, ~500 tokens) or
        NpcIndex.format_short_context() (stub, ~60 tokens)
```

---

## Out of Scope

- NPC file writing (covered by SPEC-007)
- Skill DC resolution (covered by SPEC-008)

---

## Notes

- See: [INDEX.md §4 — Context Detection & Injection](INDEX.md)
- Detection runs zero additional LLM calls — pure regex word-boundary matching
- Scene NPCs accumulate in `session.scene_npcs` across turns so DELTAS reminders persist
- All detection + injection logic lives in `_inject_context(session) -> tuple[str, dict]` in `api/session_manager.py`; `_stream_chat` calls it and unpacks `context_info` for the SSE `context` event
