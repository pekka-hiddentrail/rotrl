# FEATURE — Chat Display

**ID:** chat-display
**Status:** Approved
**Area:** Frontend
**Tags:** @chat @streaming @bubbles @markdown @scroll

---

## Story

> As a **player**,
> I want the chat window to show GM and player messages clearly,
> so that I can follow the narrative and understand what is happening in the game.

Messages are rendered as styled bubbles by role. GM text streams in token by token with an animated cursor. A thinking indicator appears while the GM is composing a response.

---

## Background

- Given a session is active and the chat window is visible

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Player message appears immediately on submit
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player submits an action

```gherkin
Given the session is active and the input bar has text
When  the player presses Enter or clicks Send
Then  the player message appears in the chat immediately (before any backend response)
And   the message is labelled "You" with player styling
And   the input bar is cleared
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Thinking indicator appears while GM is composing
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Backend is processing but no tokens have arrived yet

```gherkin
Given the player message has been sent
And   the backend has not yet emitted any token events
Then  a thinking indicator is visible in the chat
And   it shows three animated dots staggered at 0ms, 160ms, 320ms intervals
And   it disappears as soon as the first GM token arrives
```

```gherkin
Given the backend creates an empty GM bubble before streaming
And   no token has arrived yet
Then  the empty GM bubble shows the same three animated dots
And   the dots are replaced by streamed GM text once the first token arrives
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — GM tokens stream into the bubble with an animated cursor
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM response is streaming

```gherkin
Given the LLM is streaming a response
Then  each token event appends to the GM bubble in real time
And   an animated cursor appears at the end of the bubble text while streaming
And   the cursor disappears when the done event is received
And   the final message is rendered as markdown (bold, italic, headers preserved)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Intro message renders as a styled markdown card
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Session is booted and the intro card loads

```gherkin
Given the intro endpoint returns markdown with h2 headers and italic text
When  the intro message is displayed
Then  h2 and h3 headers render at appropriate sizes
And   horizontal rules (---) render as visual dividers
And   bold and italic text are styled correctly
And   a "Connecting…" indicator is shown while the intro is still loading
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Chat auto-scrolls to the bottom during streaming
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM response is longer than the visible chat area

```gherkin
Given the chat contains several messages
When  new tokens arrive during streaming
Then  the chat window scrolls to the bottom to keep the latest text visible
And   auto-scroll occurs on new message arrival as well as during token streaming
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Session-end status messages display correctly
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** End Session is in progress

```gherkin
Given the player has clicked End Session
Then  an "ending" bubble appears in the chat with animated three-dot indicator
And   the bubble updates as status SSE events arrive (e.g., "Generating recap…", "Writing boot context…")
And   the session clears and the UI returns to the splash screen after completion
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Combat resolution narrative starts a fresh GM message bubble
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** doResumeCombat streams tokens after attack resolution

```gherkin
Given the player has resolved a damage roll (queue_remaining === 0)
And   the previous GM response (attack setup narrative) is the last message in the chat
When  doResumeCombat begins streaming
Then  the combat resolution tokens appear in a NEW GM message bubble
And   the previous GM message text is unchanged
```

**Implementation:** `doResumeCombat` pushes an empty `{ role: 'gm', content: '' }`
message before the streaming loop begins, ensuring `appendToken` appends to the
new bubble rather than the last one from the previous turn.

---

## Out of Scope

- Section marker filtering (covered by SPEC-006)
- Input bar behaviour (covered by SPEC-002)

---

## Notes

- See: [INDEX.md §11 — Frontend: Chat Display](INDEX.md)
- Message roles: `intro` · `player` · `gm` · `ending`
- `patch_last` SSE event replaces the last GM bubble content with the clean narrative
