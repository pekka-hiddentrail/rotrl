# FEATURE — Player Turn

**ID:** player-turn
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @session @turn @streaming @core

---

## Story

> As a **player**,
> I want to type an action and receive a streamed GM response,
> so that the game feels responsive and I can see the narrative arrive token by token.

Each turn sends player input to the backend, which detects context (NPC, skill, location), injects relevant rules and profiles into the prompt, streams the LLM response, strips section markers, and returns only the narrative to the chat window.

---

## Background

- Given a session has been booted with a valid session_id
- And the LLM provider is available

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — GM response streams token by token
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player submits an action

```gherkin
Given the session is booted and the input bar is active
When  the player types an action and presses Enter
Then  the player message appears immediately in the chat
And   a thinking indicator (three dots) appears
And   GM tokens arrive one by one and append to the GM bubble
And   the animated cursor appears at the end of the GM bubble while streaming
And   the cursor disappears when streaming completes
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Section markers stripped from displayed narrative
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** LLM response contains %%SECTION%% markers (normal mode)

```gherkin
Given dev mode is off
When  the LLM response contains %%NARRATIVE%%, %%ROLL%%, %%DELTAS%% sections
Then  only the content between %%NARRATIVE%% and the next marker is shown in the chat
And   the patch_last event replaces any partially streamed markers with the clean narrative
And   no %%MARKER%% text is visible to the player
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Section markers visible in dev mode
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer is inspecting the raw LLM output

```gherkin
Given dev mode is on
When  the LLM response contains %%NARRATIVE%%, %%ROLL%%, %%DELTAS%% markers
Then  all tokens including the markers are streamed directly to the chat
And   no patch_last event is emitted
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Input rejected when empty or too long
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player submits an empty or oversized input

```gherkin
Given a session is active
When  the player submits an empty string
Then  no turn request is sent to the backend
And   the input bar retains focus

When  the player submits text longer than 4000 characters
Then  the backend returns an error event
And   the error bar displays the validation message
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Input bar disabled while streaming
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player tries to send a second message before the GM responds

```gherkin
Given the GM is currently streaming a response
Then  the input bar is disabled
And   the send button is disabled
And   no second turn request can be submitted
```

---

## Out of Scope

- Context detection logic (covered by SPEC-005)
- Roll request handling (covered by SPEC-008)
- NPC delta writing (covered by SPEC-007)

---

## Notes

- See: [INDEX.md §2 — Session Lifecycle](INDEX.md), [INDEX.md §5 — Response Parsing](INDEX.md)
- History trimming: dev=6 msgs, groq=10 msgs, ollama=30 msgs
- 16-char holdback buffer prevents partial markers leaking into the chat stream
