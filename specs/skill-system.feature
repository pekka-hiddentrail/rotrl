# FEATURE — Skill System

**ID:** skill-system
**Status:** Approved
**Area:** Backend
**Tags:** @skill @detection @injection @dc @roll

---

## Story

> As the **GM engine**,
> I want to detect skill trigger phrases in player input and inject the matching skill rules,
> so that the LLM always has the correct DC tables and adjudication text without hardcoding rules in the base prompt.

Skill detection is zero-cost pure text matching. The injected rules block gives the LLM the DC values it needs to emit a `%%ROLL%%` section.

---

## Background

- Given the `adventure_path/06_rules/skills/` directory contains skill markdown files
- And the SkillIndex has been loaded

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Skill rules are injected when a trigger phrase is detected
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input matches a skill trigger

```gherkin
Given Diplomacy has triggers: "convince", "persuade", "negotiate"
When  the player inputs "I try to persuade the guard to look the other way"
Then  the per-turn prompt includes "## Skill Reference — Diplomacy"
And   the injected text is the rules body from diplomacy.md (above <!-- REFERENCE -->)
And   the context SSE event contains skill="Diplomacy" and skill_trigger="persuade"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Longest trigger wins when multiple match
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input contains both a short and a longer trigger phrase

```gherkin
Given Bluff has trigger "lie" (3 chars) and "tell a lie" (10 chars)
When  the player inputs "I tell a lie to distract the merchant"
Then  the matched skill trigger is "tell a lie"
And   only one Skill Reference block is injected (no duplicates)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Trigger matching is case-insensitive and word-boundary anchored
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player uses different capitalisation or embeds trigger in a longer word

```gherkin
Given Perception has trigger "search"
When  the player inputs "I Search the room carefully"
Then  the Perception skill is detected (case-insensitive match)

When  the player inputs "I researched the topic"
Then  no skill is detected ("search" is not at a word boundary inside "researched")
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Skill file format is enforced
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A skill file is loaded by SkillIndex

```gherkin
Given a skill file at adventure_path/06_rules/skills/diplomacy.md
Then  the first line is "# Diplomacy" (the skill name)
And   a "**Triggers:**" field lists comma-separated trigger phrases
And   the rules body follows the Triggers line
And   content below "<!-- REFERENCE -->" is never injected
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — No skill detected emits null in context event
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player input contains no skill trigger phrase

```gherkin
Given the player inputs "I walk into the tavern"
When  the turn completes
Then  the context SSE event contains skill=null and skill_trigger=null
And   no Skill Reference block is injected into the per-turn prompt
```

---

## Out of Scope

- Adding new skills (requires new file in `06_rules/skills/`)
- DC resolution logic (covered by the resolve_roll endpoint in SPEC-001)

---

## Notes

- See: [INDEX.md §7 — Skill System](INDEX.md)
- Defined skills (13): Bluff · Diplomacy · Intimidate · Perception · Sense Motive · Knowledge (Arcana) · Knowledge (History) · Knowledge (Local) · Knowledge (Nature) · Knowledge (Nobility) · Knowledge (Planes) · Knowledge (Religion) · Stealth
- Trigger matching uses word-boundary regex (`\b`), case-insensitive
- Skill files with underscore prefix are skipped by SkillIndex
