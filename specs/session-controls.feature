# FEATURE — Session Controls

**ID:** session-controls
**Status:** Approved
**Area:** Frontend
**Tags:** @header @boot @provider @controls

---

## Story

> As a **player and GM**,
> I want clear pre-boot and post-boot controls in the header,
> so that I can configure the session before starting and manage it while playing.

The header has two states: pre-boot (configuration inputs visible) and post-boot (session badge and action buttons visible). Switching provider auto-updates the model dropdown.

---

## Background

- Given the UI is loaded at the splash screen or in an active session

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Pre-boot header shows all configuration controls
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** UI is at the splash screen

```gherkin
Given no session is active
Then  the header shows the provider toggle (⚡ Groq / 🖥 Ollama)
And   the header shows the session number input (integer, min 1)
And   the header shows the model dropdown for the selected provider
And   the header shows the dev mode checkbox
And   the header shows the Boot Session button
And   the Boot Session button is enabled (not disabled)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Provider toggle switches model dropdown options
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player toggles provider before boot

```gherkin
Given the provider is set to Groq
And   the selected model is "llama-3.3-70b-versatile"
When  the player switches to Ollama
Then  the model dropdown shows only Ollama models: qwen3:4b, qwen2.5:1.5b
And   the selected model changes to "qwen3:4b"

When  the player switches back to Groq
Then  the model dropdown shows only Groq models
And   the selected model changes to "llama-3.3-70b-versatile"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Boot button is disabled while booting or streaming
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Boot request is in progress

```gherkin
Given the player has clicked Boot Session
When  the boot request is pending
Then  the Boot Session button is disabled
And   no second boot request can be sent
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Post-boot header shows session badge and action buttons
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Session has been successfully booted

```gherkin
Given a session is active with session_number=2 and model="llama-3.3-70b-versatile"
Then  the header shows a session badge: "Session 2 · llama-3.3-70b-versatile"
And   the header shows a "View Log" button
And   the header shows a "Purge NPCs" button
And   the header shows an "End Session" button
And   the pre-boot configuration inputs are hidden
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — View Log opens the log in a new browser tab
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM clicks View Log during a session

```gherkin
Given a session is active
When  the GM clicks "View Log"
Then  the browser opens /api/sessions/{id}/log in a new tab
And   the current session tab remains active
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Purge NPCs requires confirmation and calls the delete endpoint
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM clicks Purge NPCs

```gherkin
Given a session is active and session NPCs exist
When  the GM clicks "Purge NPCs"
Then  a confirmation prompt is shown
When  the GM confirms
Then  DELETE /api/npcs/session is called
And   session NPC stub directories are removed from 05_npcs/

When  the GM cancels the confirmation
Then  no DELETE request is sent
```

---

## Out of Scope

- End Session flow (covered by SPEC-003)
- Booting logic and system prompt assembly (covered by SPEC-001)

---

## Notes

- See: [INDEX.md §10 — Frontend: Session Controls](INDEX.md)
- Groq default model: `llama-3.3-70b-versatile`; Ollama default: `qwen3:4b`
- End Session button also disabled while streaming or while `ending` state is true
