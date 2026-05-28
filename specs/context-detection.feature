# FEATURE — Context Detection & Injection

**ID:** context-detection
**Status:** Approved
**Area:** Backend
**Tags:** @context @npc @skill @location @injection

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
### AC-001 — NPC profile injected when alias is mentioned
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player mentions an NPC by alias

```gherkin
Given Ameiko Kaijitsu has aliases: "ameiko", "kaijitsu", "innkeeper"
When  the player inputs "I ask the innkeeper about the goblins"
Then  the per-turn prompt includes the Ameiko NPC Reference block
And   the block contains her profile text, current status, and knowledge facts
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
Given Diplomacy has trigger "convince"
When  the player inputs "I try to convince the guard to let us through"
Then  the per-turn prompt includes the Diplomacy Skill Reference block
And   the context SSE event contains skill="Diplomacy" and skill_trigger="convince"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Location keyword returns NPCs stationed there
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input mentions a location where NPCs are stationed

```gherkin
Given Belor Hemlock has location keyword "garrison"
When  the player inputs "I head to the garrison to report what happened"
Then  the per-turn prompt includes Hemlock's NPC Reference block
And   the context SSE event contains location="garrison" and location_npcs=["Belor Hemlock"]
```

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

## Out of Scope

- NPC file writing (covered by SPEC-007)
- Skill DC resolution (covered by SPEC-008)

---

## Notes

- See: [INDEX.md §4 — Context Detection & Injection](INDEX.md)
- Detection runs zero additional LLM calls — pure regex word-boundary matching
- Scene NPCs accumulate in `session.scene_npcs` across turns so DELTAS reminders persist
- All detection + injection logic lives in `_inject_context(session) -> tuple[str, dict]` in `api/session_manager.py`; `_stream_chat` calls it and unpacks `context_info` for the SSE `context` event
