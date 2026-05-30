# FEATURE — NPC System

**ID:** npc-system
**Status:** Approved
**Area:** Backend
**Tags:** @npc @index @generator @knowledge @deltas

---

## Story

> As the **GM engine**,
> I want a structured NPC database with profile, knowledge, and session-state files,
> so that each NPC's personality, current disposition, and accumulated facts are available
> for injection without any extra LLM calls.

NPCs live in `adventure_path/01_npcs/`. Canonical NPCs are git-tracked; session NPCs use a dot-prefix and are purged on boot. The `NpcIndex` singleton loads profiles lazily and re-reads volatile files on every call.

---

## Background

- Given the `adventure_path/01_npcs/` directory contains NPC folders
- And the NpcIndex has been loaded

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — NpcIndex loads all canonical NPCs and skips underscore-prefixed dirs
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** NpcIndex is initialised at startup

```gherkin
Given the 01_npcs/ directory contains folders for ameiko_kaijitsu, belor_hemlock, and _NPC_TEMPLATE
When  the NpcIndex is loaded
Then  ameiko_kaijitsu and belor_hemlock are in the index
And   _NPC_TEMPLATE is not in the index
And   dot-prefixed session NPC folders are included if their base.md exists
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — base.md uses the canonical format
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A new canonical NPC file is authored or generated

```gherkin
Given an NPC base.md file
Then  the file starts with "# Canonical Name"
And   "**Aliases:**" and "**Locations:**" fields appear before "<!-- REFERENCE -->"
And   sections Personality, Appearance, Location & Availability, Reaction to PCs appear before "<!-- REFERENCE -->"
And   Tier, Role, and Flags fields appear after "<!-- REFERENCE -->"
And   content below "<!-- REFERENCE -->" is never injected into any prompt
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — knowledge.md is appended with tagged facts
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A %%DELTAS%% block contains a knowledge fact

```gherkin
Given the %%DELTAS%% section includes a knowledge fact for Ameiko Kaijitsu tagged [pcs]
When  the section is parsed
Then  the fact is appended to adventure_path/01_npcs/ameiko_kaijitsu/knowledge.md
And   the entry is suffixed with "— S001 T003" (session and turn number)
And   the full knowledge.md is injected on the next turn that detects Ameiko
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — session_NNN.md records per-turn NPC state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** An NPC appears in a %%DELTAS%% block

```gherkin
Given the %%DELTAS%% block contains disposition, location, and summary for Belor Hemlock
When  the section is parsed
Then  session_001.md is appended with a "## Turn N — HH:MM:SS" header
And   the block contains Disposition, Location, and Summary lines
And   only the most recent turn block is injected into the next prompt (not the full file)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Session NPCs are purged on boot
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A session NPC was created during the previous session

```gherkin
Given adventure_path/01_npcs/.unnamed_guard/ exists with "SESSION NPC" in its Flags
When  a new session is booted
Then  the .unnamed_guard/ directory is deleted
And   no dot-prefixed session NPC directories remain after boot
And   canonical NPCs (no SESSION NPC flag) are not deleted
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — %%GENERATE%% creates a session NPC stub with library fallbacks
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** GM introduces an NPC not in the index

```gherkin
Given the %%GENERATE%% section provides only name="Shalelu" and role="Elven Ranger"
And   npc_library/ contains appearances.txt, personalities.txt, reactions.txt
When  the section is parsed
Then  adventure_path/01_npcs/.shalelu/base.md is created
And   missing Appearance is filled from a random entry in appearances.txt
And   missing Personality is filled from a random entry in personalities.txt
And   the file matches canonical base.md format
And   the NpcIndex is invalidated so the next turn can detect Shalelu
```

---

## Out of Scope

- NPC profile content quality (prompt engineering)
- Character sheet UI data (covered by SPEC-013)

---

## Notes

- See: [INDEX.md §6 — NPC System](INDEX.md)
- `NpcIndex` is a module-level singleton; backend restart is required to pick up new `base.md` files from hand-authored NPCs
- `knowledge.md` and `session_NNN.md` are re-read on every detect call (no restart needed)
- Tag vocabulary: `[persistent]` · `[pcs]` · `[quest]` · `[world]` · `[npcs]` · `[trivia]`
