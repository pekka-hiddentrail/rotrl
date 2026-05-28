# FEATURE — Character System

**ID:** character-system
**Status:** Approved
**Area:** Frontend
**Tags:** @character @sidebar @sheet @data

---

## Story

> As a **player**,
> I want to see my character's stats in a sidebar and open a full character sheet,
> so that I can reference HP, skills, and spells during play without leaving the game.

Character data is loaded from static JSON files served by Vite. The sidebar shows compact portraits; clicking opens a full modal sheet.

---

## Background

- Given the UI is loaded
- And character JSON files exist at `/data/{id}.json`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Characters are loaded from static JSON on startup
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** UI initialises

```gherkin
Given /data/characters.json contains ["harsk", "seoni"]
When  the UI loads
Then  GET /data/characters.json is fetched to get the list of character IDs
And   GET /data/harsk.json and GET /data/seoni.json are fetched in parallel
And   both characters appear in the sidebar once loaded
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Sidebar shows portrait, HP bar, and hover tooltip
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Characters are loaded and the sidebar is visible

```gherkin
Given character data is loaded for a character with current HP 18, max HP 30
Then  a circular 72px portrait is shown (fallback fox SVG if portrait missing)
And   an HP bar is shown beneath the portrait
And   the HP bar is gold-coloured (25–50% HP)
And   hovering over the portrait shows a tooltip with name, race, class, and level
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — HP bar colour reflects health state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** HP bar colour changes with HP percentage

```gherkin
Given a character has max HP 40
When  current HP is 32 (80%)
Then  the HP bar is green (> 50%)

When  current HP is 16 (40%)
Then  the HP bar is gold (25–50%)

When  current HP is 8 (20%)
Then  the HP bar is red (< 25%)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Clicking portrait opens the character sheet modal
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player opens their character sheet

```gherkin
Given the sidebar shows a character portrait
When  the player clicks the portrait
Then  the CharacterSheet modal opens for that character
And   the modal shows: portrait, identity block, vitals row, ability scores, saves, feats, skills, weapons
And   clicking outside the modal or a close button dismisses it
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Vitals and abilities show breakdown tooltips
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player hovers over a stat in the character sheet

```gherkin
Given the character sheet modal is open
When  the player hovers over the AC value
Then  a tooltip appears after 900ms showing the AC component breakdown
And   the tooltip is repositioned to avoid overflowing the right edge of the viewport

When  the player hovers over a saving throw
Then  a tooltip shows base + ability modifier + magic + misc breakdown
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Spells section groups spells by level with per-spell tooltips
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Character sheet is open for a spellcasting character

```gherkin
Given the character has spells at levels 0, 1, and 2
When  the Spells section is visible
Then  spells are grouped by spell level
And   hovering a spell shows its cast time, duration, range, components, school, effect, and save
```

---

## Out of Scope

- Character sheet editing (read-only, data managed in JSON files)
- Backend NPC character data (covered by SPEC-007)

---

## Notes

- See: [INDEX.md §13 — Frontend: Character System](INDEX.md)
- Character data schema fields: identity · vitals · abilities · saves · skills · feats · weapons · spells · inventory
- `useCharacters` hook returns `{ characters, characterMap, loading, error }`
- Character JSON files live in `ui/public/data/` and are served statically by Vite
