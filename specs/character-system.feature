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
- And character JSON files exist in `ui/public/data/`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Characters are loaded from the API on startup
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** UI initialises

```gherkin
Given character JSON files exist in ui/public/data/
When  the UI loads
Then  GET /api/characters is fetched (served by the FastAPI backend)
And   the response is a JSON array containing all character data objects
And   all characters appear in the sidebar once loaded
And   if the fetch fails an error bar shows "Character data: <reason>"
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
### AC-010 — Player messages show speaker identity in chat; backend receives prefixed payload
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player sends a message while a character is active

```gherkin
Given Yanyeeku is the active character
When  the player types "I would like to see the fireworks" and sends
Then  the chat bubble shows the clean text "I would like to see the fireworks"
And   the bubble has a speaker label with Yanyeeku's portrait and name (see player-bubble-speaker.feature)
And   the input sent to the backend is '@Yanyeeku: "I would like to see the fireworks"'

When  no character is active
When  the player types "We look around"
Then  the chat bubble shows "We look around" with a generic "player" party label
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

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Action menu opens to the right of the avatar, not below
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player opens the action menu

```gherkin
Given the sidebar is on the left edge of the screen
When  the player clicks a character avatar
Then  the action menu appears to the right of the avatar wrap
And   the menu does not overlap the avatar
And   the menu is positioned using data-placement="right" for test and accessibility purposes
```

**Notes:**
- Implemented via `ReactDOM.createPortal` — menu is rendered into `document.body` with `position: fixed` and coordinates from `getBoundingClientRect()` on the wrap element. This is necessary because `.char-sidebar` has `overflow-y: auto`, which creates a clipping context that would hide an absolutely-positioned menu extending beyond the sidebar width.
- `z-index: 1000` on `.char-action-menu` ensures it floats above all other panels (combat, chat, dice).
- Position is computed once when `menuId` is set; `top = wrap.rect.top`, `left = wrap.rect.right + 8px`.
- The click-outside handler checks both the original wrap AND the portaled menu ref so clicking menu items does not trigger an outside-click close.
- `data-placement="right"` attribute on the menu div makes the placement verifiable without relying on CSS layout in tests.

---

## Out of Scope

- Character sheet editing (read-only, data managed in JSON files)
- Backend NPC character data (covered by SPEC-007)
- Per-player authentication or turn-order enforcement
- Persisting active character across browser refresh (post-MVP)

---

## Notes

- See: [INDEX.md §13 — Frontend: Character System](INDEX.md)
- Character data schema fields: identity (`id`, `name`, `race`, `subrace`, `class`, `archetype`, `alignment`, `deity`, `level`, `appearance`) · vitals (`hp`, `ac`, `initiative`, `speed`, `bab`) · abilities · saves · skills · feats · weapons · spells · inventory
- `useCharacters` hook returns `{ characters, characterMap, loading, error }`
- Character JSON files live in `ui/public/data/` and are read by the FastAPI backend at `GET /api/characters`. Each request reads the files fresh — edits to JSON reflect on next page load without a frontend rebuild.
- `race` holds the base race name only (e.g. `"Aasimar"`). Sub-race detail goes in `subrace` (e.g. `"Peri-Blooded (Emberkin)"`).
- AC-007 through AC-011 implemented in: `App.tsx` (`activeSpeaker` = `activeCharacter` state, `sheetCharId` new state for sheet modal), `CharacterSidebar.tsx` (two-action menu + halo ring), `InputBar.tsx` (speaker badge)
- Speaker tag format: `@<Name>: "<message>"` — prefix prepended in `handleSend` before adding to chat and before sending to backend; `lastInput` retains the raw (unprefixed) text for IntentBar display
- `activeSpeakerId` prop on CharacterSidebar drives halo; `sheetCharId` drives the CharacterSheet modal — the two are independent states
