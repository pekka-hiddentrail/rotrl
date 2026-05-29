# Session Lifecycle

This document describes what happens from the moment the player clicks **Boot Session** through to **End Session**. It reflects the current code, not any earlier architecture.

---

## Overview

There is no boot LLM call. The system prompt is built deterministically from files on disk. The first GM narration fires on the player's first turn input.

```
Boot Session  →  create context (no LLM)
Player input  →  GM response (LLM streams)
Player input  →  GM response (LLM streams)
...
End Session   →  recap + next-session boot (two blocking LLM calls)
```

---

## Step 1 — Boot Session (`POST /api/sessions`)

`create_session()` runs entirely on disk — no network call to Groq or Ollama.

```text
POST /api/sessions
│
├─ 1. Delete NPC delta files for this session number
│      adventure_path/05_npcs/*/session_NNN.md → deleted
│      (keeps other sessions' delta files intact)
│
├─ 2. Clear NPC knowledge files (session 1 only)
│      adventure_path/05_npcs/*/knowledge.md → truncated to ""
│      (full campaign reset on session 1 boot)
│
├─ 3. Build system prompt — _build_slim_system_prompt(session_number)
│      ├─ Read players/player_*/character_sheet.md → PARTY block
│      ├─ Situation priority:
│      │    a. sessions/session_NNN/boot.md          (GM-facing brief)
│      │    b. sessions/session_NNN-1/recap.md        (prior session recap)
│      │    c. "(No boot context found…)"             (fallback text)
│      └─ Assemble: core behavior + party + situation + response structure
│           + response format example
│
├─ 4. Create GameSession in memory (session_id = 8-char UUID prefix)
│
├─ 5. Open log file: outputs/session_NNN_YYYYMMDD_HHMMSS.log.md
│      Write system prompt into log (inside <details> block)
│
└─ yield SSE event: { "type": "done", "session_id": "..." }
```

The browser receives the `done` event and is ready for player input. Nothing has been sent to an LLM.

---

## Step 2 — Each Turn (`POST /api/sessions/{id}/turn`)

`stream_turn()` → `_stream_chat()` handles every player action.

```text
POST /api/sessions/{id}/turn  { "input": "We approach the mayor." }
│
├─ 1. Validate input (non-empty, ≤ 4000 chars)
│
├─ 2. Log player input
│      → session log: ### [HH:MM:SS] PLAYER\n{input}
│
├─ 3. Build context-augmented system prompt copy
│      ├─ NpcIndex.detect(input)
│      │    → if alias match: prepend NPC profile (base.md up to <!-- REFERENCE -->)
│      │    → add NPC to session.scene_npcs
│      ├─ SkillIndex.detect(input)
│      │    → if trigger match: prepend skill rules (longest trigger wins)
│      ├─ Location NPC profiles
│      │    → for each NPC in scene_npcs: prepend current status from session_NNN.md
│      └─ GM directive (_build_turn_directive)
│           → if scene_npcs present: append %%DELTAS%% reminder + %%GENERATE%% warning
│           → if skill match: append %%ROLL%% instruction with skill name
│
├─ 4. Trim message history to provider limit
│      Groq: last 10 messages  |  Ollama: last 30  |  Dev: last 6
│
├─ 5. Stream LLM response
│      _stream_with_narrative_filter() wraps the raw token stream:
│        Dev mode:    all tokens pass through (%%MARKERS%% visible in UI)
│        Normal mode: only %%NARRATIVE%% section content forwarded as tokens
│                     %%ROLL%%, %%GENERATE%%, %%DELTAS%% content suppressed
│      Groq: per-minute rate-limit headers captured from the HTTP response
│            → stored in usage_out["rate_limits"]
│            → emitted as SSE event { "type": "rate_limits", rpm_remaining, tpm_remaining, … }
│            → displayed in the UI header as a compact badge after each turn
│
├─ 6. Process completed response
│      ├─ _parse_response_sections() → { NARRATIVE, ROLL, GENERATE, DELTAS }
│      │
│      ├─ %%ROLL%% section
│      │    parse: skill, dc, success, failure
│      │    → set session.pending_roll
│      │    → yield SSE event: { "type": "roll_request", ... }
│      │
│      ├─ %%GENERATE%% section (processed before %%DELTAS%% so stubs are findable)
│      │    for each bracket block:
│      │      if type == "location": log and skip
│      │      else: create adventure_path/05_npcs/.<slug>/base.md   ← dot-prefix = session NPC
│      │            invalidate NPC index
│      │            (rename dir to <slug>/ to promote to permanent)
│      │
│      ├─ %%DELTAS%% section
│      │    for each bracket block:
│      │      → write adventure_path/05_npcs/<slug>/session_NNN.md
│      │           ## Turn N — HH:MM:SS
│      │           **Disposition:** ...
│      │           **Location:** ...
│      │           **Summary:** ...
│      │      → append to adventure_path/05_npcs/<slug>/knowledge.md
│      │           - [tag] fact — S001 T003
│      │      → add NPC to session.scene_npcs
│      │
│      ├─ yield patch_last (non-dev only)
│      │    replaces last UI message with clean narrative (markers stripped)
│      │
│      └─ _detect_narrative_npcs(narrative_text)
│           → scan for Title Case two-word names not yet in scene_npcs
│           → add suspects to scene_npcs (stub created on next %%DELTAS%% write)
│
├─ 7. Append to message history (role: "assistant", content: clean narrative)
│
└─ 8. Log GM response
       → session log: ### [HH:MM:SS] GM\n{clean narrative}
```

### Roll resolution (`POST /api/sessions/{id}/resolve_roll`)

After the dice panel sends the player's roll result:

```text
POST /api/sessions/{id}/resolve_roll  { "rolled": 14 }
│
├─ compare: rolled >= session.pending_roll["dc"] → passed / failed
├─ clear session.pending_roll
├─ log outcome to session log
└─ return { "passed": true, "skill": "Diplomacy", "dc": 12, "rolled": 14, "outcome": "..." }
```

> **Note:** The pass/fail result is currently returned to the frontend only. The next GM turn does not automatically receive it as context — this is a known gap (see TODO.md, closed by M5).

---

## Step 3 — End Session (`POST /api/sessions/{id}/end`)

`stream_end_session()` makes two blocking LLM calls and writes two files.

```text
POST /api/sessions/{id}/end
│
├─ 1. Parse session log → list of PLAYER/GM turns
│      _parse_turns_from_log() strips: system prompt, <details> blocks,
│      GM directives (> *[...]*), section separators (---)
│
├─ 2. Blocking LLM call — player-facing recap
│      system: "You are a tabletop RPG chronicler…"
│      user:   full turn transcript
│      → _enforce_recap_header() normalises heading/date structure
│      → write sessions/session_NNN/recap.md
│
├─ 3. Blocking LLM call — GM-facing boot brief
│      system: "You are a GM preparation assistant…"
│      user:   turn transcript
│      → write sessions/session_NNN+1/boot.md
│
├─ yield status events throughout (UI shows progress)
│
└─ save_session() → remove from memory, write outputs/session_NNN_notes.json
```

---

## File paths written during a session

| File | Written by | When |
|------|-----------|------|
| `outputs/*.log.md` | `_log()` | Continuously — every turn |
| `outputs/api_log/*.json` | `write_api_log()` | After each LLM call |
| `adventure_path/05_npcs/.<slug>/base.md` | `_process_generate_block()` | When `%%GENERATE%%` names a new NPC (dot-prefix = session NPC, purgeable) |
| `adventure_path/05_npcs/<slug>/session_NNN.md` | `_write_npc_delta()` | When `%%DELTAS%%` references an NPC |
| `adventure_path/05_npcs/<slug>/knowledge.md` | `_write_npc_delta()` | When `%%DELTAS%%` includes `knowledge:` lines |
| `sessions/session_NNN/recap.md` | `stream_end_session()` | On End Session |
| `sessions/session_NNN+1/boot.md` | `stream_end_session()` | On End Session |
| `outputs/session_NNN_notes.json` | `save_session()` | On End Session or DELETE |

---

## System prompt structure

`_build_slim_system_prompt()` assembles the prompt once at boot. It never changes during a session; context injection prepends to a **copy** each turn.

```
You are the Game Master for a Pathfinder 1st Edition campaign: Rise of the Runelords.
Session number: N

CORE BEHAVIOR
...5 rules about description, player agency, lore fidelity...

GM STYLE
...7 style directives — NPC demeanor, location detail, rules rulings, player drift,
   events, inventory, travel...

PARTY
  - Yanyeeku (Kitsune Sorcerer / Crossblooded)
  - ...

CURRENT SITUATION
...contents of sessions/session_NNN/boot.md (or prior recap, or fallback)...

RESPONSE STRUCTURE (strictly enforced)
%%NARRATIVE%%  — 2–4 paragraphs of prose
%%ROLL%%       — one bracket block when a check is needed
%%GENERATE%%   — one block per new NPC/location introduced
%%DELTAS%%     — one block per active NPC in the scene

SCENE EVENT (optional — not a section header)
%%EVENT%% <event_id>   ← ID on the same line; fires once per event; omit if no trigger applies

...complete format example with all four sections + SCENE EVENT line...

---
EVENT MAP
...one line per event ID from 08_events/ with trigger condition...
```

The total prompt is capped at `_GROQ_MAX_SYSTEM_CHARS = 30,000` characters for Groq.

---

## What was replaced

The previous architecture (documented in the now-obsolete `AGENTS.md`) used:

- `GMAgent` / `GMConfig` classes in `src/agents/gm_boot_agent.py`
- `.agents/GM/SESSION_BOOT_PROMPT.md` with `{{PLACEHOLDER}}` injection
- Two LLM calls at boot: one for opening narration, one for semantic audit
- A `context_queue` for deferred file loading across turns
- Boot verification that raised `RuntimeError` on checklist failures

All of that has been replaced by the deterministic boot described above. There is no `src/agents/` directory and no LLM call at boot.
