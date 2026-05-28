# FEATURE — Intent Bar

**ID:** intent-bar
**Status:** Approved
**Area:** Frontend
**Tags:** @intent @context @tags @sse

---

## Story

> As a **GM and developer**,
> I want an intent bar below the chat that shows what the engine detected from the player's last input,
> so that I can verify that the correct NPC, skill, and location context was injected into the prompt.

The intent bar is populated by the `context` SSE event. It shows a truncated player input, an arrow, and context tags. It is diagnostic — visible to the GM, not the player persona.

---

## Background

- Given a session is active
- And the player has submitted at least one turn

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Intent bar shows truncated input and context tags
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Turn completes with NPC and skill detected

```gherkin
Given the player inputs "I try to convince Ameiko to tell us about her brother Tsuto"
And   the context event contains npc="Ameiko Kaijitsu", npc_trigger="ameiko", skill="Diplomacy", skill_trigger="convince"
When  the context event is received
Then  the intent bar shows a truncated input (52 chars max)
And   the intent bar shows an NPC tag: "npc — Ameiko Kaijitsu (ameiko)"
And   the intent bar shows a skill tag: "skill — Diplomacy (convince)"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Location tag is shown when a location is detected
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input mentions a location with stationed NPCs

```gherkin
Given the context event contains location="garrison", location_npcs=["Belor Hemlock"]
When  the context event is received
Then  the intent bar shows a location tag: "loc — garrison (Belor Hemlock)"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Null context fields show "no npc" and "no skill" tags
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Turn completes with nothing detected

```gherkin
Given the context event contains npc=null, skill=null, location=null
When  the context event is received
Then  the intent bar shows a "no npc" tag
And   the intent bar shows a "no skill" tag
And   no location tag is shown
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — "detecting…" state shown while streaming
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player has submitted a turn but context event has not yet arrived

```gherkin
Given the player has submitted a turn
And   the LLM is still streaming
Then  the intent bar shows "detecting…"
And   the tags are not yet visible
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — "no event — restart backend?" shown when context never arrives
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Streaming completes but no context event was received

```gherkin
Given streaming has ended (done event received)
And   no context event was received during the turn
When  the done event is processed
Then  the intent bar shows "no event — restart backend?"
And   this is a diagnostic hint indicating the backend may need a restart
```

---

## Out of Scope

- Context detection logic (covered by SPEC-005)
- System prompt injection (covered by SPEC-016)

---

## Notes

- See: [INDEX.md §14 — Frontend: Intent Bar](INDEX.md)
- Input is truncated at 52 characters for display; full input is always sent to backend
- The intent bar is visible at all times during an active session (not hidden after reading)
