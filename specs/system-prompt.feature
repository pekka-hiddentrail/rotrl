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

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Format example injected on first player turn only
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** First player turn of a session

```gherkin
Given a session has been booted
And   session.messages has exactly 1 entry (the current user message)
When  _inject_context assembles the per-turn system prompt
Then  the full format example (Gerhard Pickle / Bottled Solutions) is appended to system_content
And   the example is NOT present in session.system_prompt (the static base prompt)
When  _inject_context is called on any subsequent turn (messages > 1)
Then  the format example is NOT present in system_content
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Full combat spec injected per-turn only when combat is active
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Turn submitted during active combat

```gherkin
Given session.combat_state.round > 0
When  _inject_context assembles the per-turn system prompt
Then  the full combat format spec (_COMBAT_SPEC_ONGOING) is present in system_content
And   [INITIATIVE ORDER — round N] shows the correct round number
And   [CURRENT HP] lists all combatants with their backend-authoritative HP values
When  session.combat_state is None or round == 0
Then  [INITIATIVE ORDER] is NOT present in system_content
And   the static base prompt contains only a compact one-liner %%COMBAT%% reference
```

> **Note (Tier 1.6):** When `session.combat_state is not None`, `_inject_context` uses the
> dedicated combat branch. `_COMBAT_SPEC_ONGOING` is still injected but via `_COMBAT_SECTION_SPECS`
> + combat base prompt, not the old `[COMBAT ONGOING]` header. See `combat-system-prompt.feature`.

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Section specs injected conditionally each turn (narrative mode only)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Per-turn system prompt assembly with no active combat

```gherkin
Given session.combat_state is None
And   _inject_context assembles the per-turn system prompt
Then  a [SECTIONS ACTIVE THIS TURN] block is always appended
And   the block always includes _NARRATIVE_SPEC and _GENERATE_SPEC
When  a skill match is detected in the player input
Then  _ROLL_SPEC is included in the block
When  no skill is detected
Then  _ROLL_SPEC is NOT included in the block
When  session.scene_npcs is non-empty OR an NPC is detected this turn
Then  _DELTAS_SPEC is included in the block
When  scene_npcs is empty AND no NPC is detected
Then  _DELTAS_SPEC is NOT included in the block
And   the static base prompt contains only the marker list, NOT the full section specs

Given session.combat_state is not None
Then  the [SECTIONS ACTIVE THIS TURN] block is replaced by _COMBAT_SECTION_SPECS (COMBAT MODE)
And   _NARRATIVE_SPEC, _GENERATE_SPEC, _ROLL_SPEC, _DELTAS_SPEC are all absent
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — PC slim profile injected when PC is named in player input
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input names a party character

```gherkin
Given session.pc_profiles contains a slim profile for each PC
And   the player input contains a PC's canonical name (case-insensitive)
When  _inject_context assembles the per-turn system prompt
Then  that PC's narrative profile (appearance + personality) is appended to system_content
When  a skill match is also detected in the same turn
Then  that PC's mechanical profile (HP, AC, saves, spells, abilities) is also appended
When  no PC name appears in the player input
Then  no PC profile is injected
When  multiple PC names appear, only the first matched PC's profile is injected
```

---

## Out of Scope

- Campaign content quality (prompt engineering, not a spec concern)
- Facets injection (facets/ files are currently reference-only; see INDEX.md §15)

---

## Notes

- See: [INDEX.md §16 — System Prompt Architecture](INDEX.md)
- Boot context lookup order: `sessions/session_NNN/boot.md` → `sessions/session_N-1/recap.md` → hardcoded fallback text
- `_build_slim_system_prompt()` in `api/session_manager.py` assembles the fixed prompt at boot; static content only
- `_build_combat_system_prompt(session)` — Tier 1.6 — builds the combat-mode base prompt; called fresh each combat turn, not stored; see `combat-system-prompt.feature`
- Dynamic fragments: `_FORMAT_EXAMPLE`, `_COMBAT_SPEC_ONGOING`, `_COMBAT_SPEC_ROUND1`, `_NARRATIVE_SPEC`, `_ROLL_SPEC`, `_GENERATE_SPEC`, `_DELTAS_SPEC`, `_COMBAT_SECTION_SPECS` — all module-level constants injected conditionally by `_inject_context`
- `_build_pc_profiles(players_dir)` builds two-tier PC profiles at session boot; stored on `GameSession.pc_profiles`
- Per-turn copy assembly (AC-002 through AC-010) is the responsibility of `_inject_context(session) -> tuple[str, dict]`
- Target: static base prompt ≤ 900 tokens; turn-1 total ≤ 1300 tokens; turn 2+ social (no combat) ≤ 800 tokens; combat turns ≤ 60% of equivalent narrative turn
