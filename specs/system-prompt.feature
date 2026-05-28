# FEATURE — System Prompt Architecture

**ID:** system-prompt
**Status:** Approved
**Area:** Backend
**Tags:** @prompt @injection @boot @per-turn @groq

---

## Story

> As the **GM engine**,
> I want a deterministic fixed system prompt built once at boot,
> with a per-turn copy that injects only the context relevant to the current action,
> so that the LLM always has the right information without exceeding payload limits.

The fixed prompt is never mutated. A fresh per-turn copy prepends detected NPC profiles, skill rules, and a GM directive before each LLM call.

---

## Background

- Given a session has been booted
- And the fixed system prompt has been assembled

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Fixed system prompt is built once at boot and never modified
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Session is booted

```gherkin
Given a boot request is submitted
When  create_session() runs
Then  the fixed system prompt is assembled once and stored on session.system_prompt
And   the prompt contains: role declaration, core behaviour rules, GM style guidelines
And   the prompt contains: party listing with names and classes from character_sheet.md
And   the prompt contains: current situation from sessions/session_NNN/boot.md (or fallback)
And   the prompt contains: response structure specification with the %%SECTION%% format example
And   session.system_prompt is not modified by any subsequent turn
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Per-turn injection prepends context to a copy of the fixed prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A turn is submitted with NPC and skill detected

```gherkin
Given the fixed system prompt is on session.system_prompt
And   Ameiko Kaijitsu is detected in player input
And   Diplomacy is detected via skill trigger
When  the LLM call is assembled
Then  the messages list starts with a system message that is a copy of the fixed prompt
And   the copy is prepended with a [CONTEXT FOR THIS TURN] block
And   the context block contains the Ameiko NPC Reference section
And   the context block contains the Diplomacy Skill Reference section
And   session.system_prompt itself is unchanged after the call
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — System prompt is capped at 30,000 chars for Groq
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Assembled per-turn prompt exceeds 30,000 characters with Groq provider

```gherkin
Given the provider is Groq
And   the per-turn system prompt (fixed + context injection) is 32,000 characters
When  the LLM call is assembled
Then  the system prompt sent to Groq is truncated to 30,000 characters
And   the turn still completes normally
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — GM directive is appended based on detected intent
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** NPC is detected in player input

```gherkin
Given Ameiko Kaijitsu is detected
When  the per-turn system message is assembled
Then  a [GM DIRECTIVE FOR THIS TURN] block is appended after the context block
And   the directive contains explicit instructions based on the detected NPC and intent
And   the directive does not appear in the fixed base prompt
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Response structure is enforced by the fixed prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM is asked to respond

```gherkin
Given the fixed prompt includes the response structure specification
Then  the specification shows the expected marker order: %%NARRATIVE%% → %%ROLL%% → %%GENERATE%% → %%DELTAS%%
And   the specification clarifies that %%ROLL%%, %%GENERATE%%, %%DELTAS%% are optional
And   the specification includes a format example the LLM can follow
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Party listing is built from character_sheet.md files at boot
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Adventure has three players

```gherkin
Given players/player_01/character_sheet.md contains "NAME: Harsk" and "CLASS: Ranger"
And   players/player_02/character_sheet.md contains "NAME: Seoni" and "CLASS: Sorcerer"
When  the session is booted
Then  the fixed system prompt party section lists "Harsk (Ranger)" and "Seoni (Sorcerer)"
And   characters without a character_sheet.md are silently skipped
```

---

## Out of Scope

- Campaign content quality (prompt engineering, not a spec concern)
- Facets injection (facets/ files are currently reference-only; see INDEX.md §15)

---

## Notes

- See: [INDEX.md §16 — System Prompt Architecture](INDEX.md)
- Boot context lookup order: `sessions/session_NNN/boot.md` → `sessions/session_N-1/recap.md` → hardcoded fallback text
- `_build_slim_system_prompt()` in `api/session_manager.py` assembles the fixed prompt at boot
- Per-turn copy assembly (AC-002, AC-003, AC-004) is the responsibility of `_inject_context(session) -> tuple[str, dict]`; `_stream_chat` calls it and unpacks `(system_content, context_info)` to build the LLM payload
