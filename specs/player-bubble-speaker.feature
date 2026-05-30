# FEATURE — Player Bubble Speaker Identity

**ID:** player-bubble-speaker
**Status:** Approved
**Area:** Frontend
**Tags:** @chat @bubbles @character @speaker @identity

---

## Story

> As a **player**,
> I want player chat bubbles to show who is speaking,
> so that I can see at a glance which character said what — or that the whole party spoke together.

When a character is active (selected in the sidebar), their portrait and name appear as the
bubble label. When no character is selected, a plain "Player" circle acts as the label.
The raw `@Name: "text"` backend prefix is never visible in the chat — the bubble always
shows the clean player input.

---

## Background

- Given a session has been booted
- And the chat window is visible

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — No active speaker → "Player" circle label
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player sends a message with no character selected

```gherkin
Given no character is active in the sidebar
When  the player submits an action
Then  the player bubble label shows a circle containing the word "player"
And   the bubble content shows the raw typed text (no prefix)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Active speaker → portrait + name label
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player sends a message with a character selected

```gherkin
Given character "Yanyeeku" is active in the sidebar
When  the player submits an action
Then  the player bubble label shows a portrait circle with Yanyeeku's color border
And   the label shows the character's name "Yanyeeku" next to the portrait
And   the bubble content shows only the typed text — no "@Yanyeeku:" prefix
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Speaker identity is snapshotted at send time
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Active speaker changes after a message is sent

```gherkin
Given character "Yanyeeku" is active
And   the player sends a message (bubble shows Yanyeeku's portrait)
When  the player switches to character "Ani" in the sidebar
Then  the previously sent bubble still shows Yanyeeku's portrait and name
And   new bubbles sent as Ani show Ani's portrait and name
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Backend payload is unchanged
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The @Name: prefix is still sent to the backend

```gherkin
Given character "Seoni" is active
When  the player types "I cast fireball" and sends
Then  the API receives the string '@Seoni: "I cast fireball"'
And   the chat bubble displays only "I cast fireball"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Portrait fallback when image unavailable
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Character portrait image fails to load

```gherkin
Given character "Yanyeeku" is active
And   the portrait image returns a 404
When  the player sends a message
Then  the bubble label shows the character's rune glyph in their color
And   the character name is still displayed
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — "Player" label is not shown as text in GM bubbles
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM response bubble is unaffected

```gherkin
Given a GM message is in the chat
Then  the GM bubble still shows the plain "GM" text label
And   no portrait or "player" circle appears on the GM bubble
```
