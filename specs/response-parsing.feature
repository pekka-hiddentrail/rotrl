# FEATURE — Response Parsing

**ID:** response-parsing
**Status:** Approved
**Area:** Backend
**Tags:** @parsing @sections @narrative @streaming

---

## Story

> As the **GM engine**,
> I want to parse the LLM response into structured sections,
> so that the narrative is cleanly separated from mechanical instructions (rolls, NPC generation, state deltas).

The LLM uses `%%SECTION%%` markers. The backend filters the stream to show only `%%NARRATIVE%%` content in the chat, then parses the remaining sections out-of-band to drive game mechanics.

---

## Background

- Given a session turn has been submitted
- And the LLM has returned a response containing %%SECTION%% markers

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Only %%NARRATIVE%% content reaches the player
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM response contains all four section types

```gherkin
Given the LLM response contains %%NARRATIVE%%, %%ROLL%%, %%GENERATE%%, %%DELTAS%% sections
When  the response is streamed in normal mode
Then  only tokens between %%NARRATIVE%% and the next section marker are emitted as token events
And   a patch_last event replaces the GM bubble with the final clean narrative
And   the %%ROLL%%, %%GENERATE%%, %%DELTAS%% sections are parsed but never shown
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — %%ROLL%% sets a pending skill check
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM requests a skill check

```gherkin
Given the LLM response contains a %%ROLL%% section with skill, DC, success, failure text
When  the section is parsed
Then  session.pending_roll is set with { skill, dc, success, failure }
And   a roll_request SSE event is emitted with the same values
And   the Dice Tray shows the pending roll banner
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — %%GENERATE%% creates a session NPC stub
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM introduces a new NPC not in the index

```gherkin
Given the LLM response contains a %%GENERATE%% section with a name and role
And   the NPC does not already exist in the index
When  the section is parsed
Then  a dot-prefixed directory adventure_path/01_npcs/.{slug}/ is created
And   base.md is written with the correct canonical format
And   the NPC index is invalidated so the next turn can detect this NPC
```

```gherkin
Given the %%GENERATE%% section names an NPC already in the index
When  the section is parsed
Then  no new directory is created (no duplicates)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — %%DELTAS%% writes NPC state changes
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM records what happened to an NPC this turn

```gherkin
Given the LLM response contains a %%DELTAS%% section with a bracket block for an NPC
When  the section is parsed
Then  session_NNN.md is appended with the turn header, disposition, location, summary
And   any knowledge facts in the block are appended to that NPC's knowledge.md with the correct tag
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Partial markers do not leak into the chat
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A section marker arrives split across token boundaries

```gherkin
Given the LLM streams "%%NARR" in one token and "ATIVE%%" in the next
When  the streaming filter processes these tokens
Then  neither token is emitted to the chat
And   the 16-character holdback buffer absorbs the partial marker
And   the patch_last event sends the correct clean narrative after streaming completes
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Missing %%NARRATIVE%% triggers a buffered retry
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM response contains section markers but omits %%NARRATIVE%%

```gherkin
Given the LLM returns a section-format response (contains %% markers)
And   the response has no %%NARRATIVE%% block, or %%NARRATIVE%% content is empty
When  the turn stream completes server-side
Then  the buffered tokens are discarded
And   the LLM is called again (up to 1 retry, 2 total attempts)
And   each attempt is logged independently via write_api_log
And   if the retry returns a valid %%NARRATIVE%%, its tokens are released to the client
And   if all retries are exhausted without %%NARRATIVE%%, the response is used as-is
```

**Scenario:** LLM response contains no %% markers at all (flat format)

```gherkin
Given the LLM returns a flat-format response with no %% section markers
When  the turn stream completes
Then  the guard is skipped — any non-empty content is accepted without retry
```

**Notes:**
- The client sees only the spinner (no tokens) until a validated response is released.
- A retry notice is appended to the session log via `_log()`.
- LLM API errors (network failures, rate-limit exceptions) propagate immediately; no retry is attempted for hard errors.
- The `%%NARRATIVE%%` presence check uses a direct regex (`^%%NARRATIVE%%`) — NOT `_parse_response_sections`, which applies a graceful NARRATIVE fallback for any non-section-format input.

---

## Out of Scope

- NPC profile content quality (prompt engineering)
- Delta file format details (covered by SPEC-007)

---

## Notes

- See: [INDEX.md §5 — Response Parsing](INDEX.md)
- Fallback flat-block parser handles old-format responses without %%MARKERS%%
- Section regex: `^%%[A-Z]+%%[ \t]*$` (line-anchored)
