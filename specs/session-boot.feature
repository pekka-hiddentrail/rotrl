# FEATURE — Session Boot

**ID:** session-boot
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @session @boot @core

---

## Story

> As a **player**,
> I want to boot a game session with my chosen model and provider,
> so that the GM is primed with the correct context and I can start playing immediately.

Boot initialises the session in-memory, loads the system prompt from campaign files, cleans up stale session NPC stubs, and streams an intro card to the UI — all without making an LLM call.

---

## Background

- Given the backend is running on `127.0.0.1:8000`
- And the Vite dev server is proxying `/api` to the backend
- And at least one LLM provider is available (Groq API key set, or Ollama running)

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Successful session boot
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player clicks Boot Session with valid settings

```gherkin
Given the player has selected a provider, model, and session number
When  the player clicks "Boot Session"
Then  the UI shows the session intro card (from sessions/session_NNN/intro.md or fallback)
And   a session_id is returned in the SSE done event
And   the header switches to show the session badge and End Session button
And   the input bar becomes available
And   a log file is created at outputs/session_NNN_YYYYMMDD_HHMMSS.log.md
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Intro card fallback chain
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** No hand-authored intro exists for the requested session

```gherkin
Given sessions/session_002/intro.md does not exist
And   sessions/session_001/recap.md exists
When  the player boots session 2
Then  the intro card shows the content of sessions/session_001/recap.md
```

```gherkin
Given neither sessions/session_002/intro.md nor sessions/session_001/recap.md exist
When  the player boots session 2
Then  the intro card shows the content of sessions/session_001/intro.md
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Session NPC cleanup on boot
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Stale session NPCs from a prior session are cleaned up

```gherkin
Given dot-prefixed NPC directories exist under adventure_path/05_npcs/ (e.g. .gulden/)
And   their base.md contains the SESSION NPC flag
When  a new session is booted
Then  those dot-prefixed directories are deleted
And   their session_NNN.md delta files are deleted
And   the NPC index no longer contains them
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Party roster loaded into system prompt
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Character names and classes appear in every GM turn

```gherkin
Given players/player_01/character_sheet.md contains NAME: and CLASS: lines
When  a session is booted
Then  the fixed system prompt includes each character's name and class
And   the party listing is present for all subsequent turns without re-reading the files
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Boot failure shown in UI
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Backend is unreachable when player clicks Boot Session

```gherkin
Given the backend is not running
When  the player clicks "Boot Session"
Then  the error bar shows "Boot failed (500)" or a connection error message
And   the session state remains null
And   the Boot Session button becomes available again
```

---

## Out of Scope

- LLM response quality during boot (no LLM call is made)
- Character sheet JSON loading (covered by SPEC-012)

---

## Notes

- See: [INDEX.md §2 — Session Lifecycle](INDEX.md)
- Boot context lookup order: `sessions/session_NNN/boot.md` → `sessions/session_N-1/recap.md` → fallback string
- The first LLM call happens on the player's first turn input, not at boot
