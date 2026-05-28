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

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Avatar click shows a two-action menu: Set Active and Open Sheet
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player clicks a character avatar

```gherkin
Given the sidebar shows character avatars
When  the player clicks an avatar
Then  a two-option menu appears: "Set Active" and "Open Sheet"

When  the player picks "Open Sheet"
Then  the CharacterSheet modal opens (as before — see AC-004)
And   the active character is unchanged

When  the player picks "Set Active"
Then  that character becomes the active character
And   the CharacterSheet modal does not open
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Active character has a visible halo in the sidebar
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A character is set as active

```gherkin
Given Yanyeeku is set as the active character
Then  Yanyeeku's avatar in the sidebar shows a halo/ring using the character's colour
And   no other avatar shows a halo
And   clicking "Set Active" on the already-active character clears active state (toggle off)
And   when cleared no avatar has a halo
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Input bar shows active character badge and speaking label
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A character is active and a session is running

```gherkin
Given Yanyeeku is the active character
And   a session is booted
Then  the input bar shows a small Yanyeeku portrait badge
And   a label reads "Speaking as Yanyeeku"

When  no character is active
Then  the input bar shows no badge
And   the placeholder text remains "What do you do?"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Player messages are prefixed with the active speaker tag
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player sends a message while a character is active

```gherkin
Given Yanyeeku is the active character
When  the player types "I would like to see the fireworks" and sends
Then  the message appears in chat as '@Yanyeeku: "I would like to see the fireworks"'
And   the input sent to the backend is '@Yanyeeku: "I would like to see the fireworks"'

When  no character is active
When  the player types "We look around"
Then  the message appears in chat without any speaker prefix
And   the input sent to the backend is "We look around" unchanged
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Active character persists until changed or cleared
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player switches speaker between turns

```gherkin
Given Yanyeeku is the active character
When  the player sets Ani as active
Then  Yanyeeku's halo disappears
And   Ani's halo appears
And   the input badge updates to "Speaking as Ani"

When  the player clears by toggling the active character off
Then  no halo is shown
And   the badge disappears
```

---

## Out of Scope

- Character sheet editing (read-only, data managed in JSON files)
- Backend NPC character data (covered by SPEC-007)
- Per-player authentication or turn-order enforcement
- Persisting active character across browser refresh (post-MVP)

---

## Notes

- See: [INDEX.md §13 — Frontend: Character System](INDEX.md)
- Character data schema fields: identity · vitals · abilities · saves · skills · feats · weapons · spells · inventory
- `useCharacters` hook returns `{ characters, characterMap, loading, error }`
- Character JSON files live in `ui/public/data/` and are served statically by Vite
- AC-007 through AC-011 implemented in: `App.tsx` (`activeSpeaker` = `activeCharacter` state, `sheetCharId` new state for sheet modal), `CharacterSidebar.tsx` (two-action menu + halo ring), `InputBar.tsx` (speaker badge)
- Speaker tag format: `@<Name>: "<message>"` — prefix prepended in `handleSend` before adding to chat and before sending to backend; `lastInput` retains the raw (unprefixed) text for IntentBar display
- `activeSpeakerId` prop on CharacterSidebar drives halo; `sheetCharId` drives the CharacterSheet modal — the two are independent states
