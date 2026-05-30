# Combat in the RotRL GM System

This document describes how combat is tracked, displayed, and ended — from the LLM writing a `%%COMBAT%%` block to the UI panel disappearing when the fight is over.

---

## Overview

The LLM owns combat. It decides when a fight starts, writes all HP values each turn, and signals the end. The server parses the output, stores a `CombatState` object on the session, and pushes a `combat_update` SSE event to the UI after every turn. The frontend renders the `CombatPanel` when state is non-null and hides it when state is cleared.

No dice resolution happens server-side. No initiative is rolled automatically. The LLM tracks all of that in the block it writes.

---

## Starting Combat

Combat begins when the LLM writes a `%%COMBAT%%` block with `round: 1` in its response. This is typically triggered by the `goblin_attack_starts` event (or another combat-starting event) firing.

### What triggers the block

Event files in `adventure_path/08_events/` that start a combat wave include a `### REQUIRED — Combat tracker` section in their injectable content. When the event is active, the system prompt includes explicit text telling the LLM to write `%%COMBAT%%` every turn while the event is active.

Additionally, once `session.combat_state` is set (i.e. the first block has been parsed), `_inject_context` appends a `[COMBAT ONGOING — round N]` block to the system prompt each turn. This reminder fires regardless of whether any event is still active, so combat tracking continues even after the 5-turn event TTL expires.

### The `%%COMBAT%%` block format

```
%%COMBAT%%
round: 1
combatants:
  - name: Goblin Warchanter · hp: 8/8 · ac: 14 · init: 15 · status: active
  - name: Goblin Warrior 1 · hp: 5/5 · ac: 16 · init: 12 · status: active
  - name: Goblin Warrior 2 · hp: 5/5 · ac: 16 · init: 10 · status: active
```

Rules the LLM follows (also stated in the system prompt):

- `round:` starts at 1. Increment each time all combatants have acted.
- Combatants are listed **highest initiative first**.
- Each row uses `·` (middle dot, U+00B7) as the field separator.
- Fields: `name`, `hp` (current/max), `ac`, `init`, `status`.
- Valid statuses: `active`, `unconscious`, `fled`, `dead`.
- **Every combatant appears every turn** — do not drop resolved combatants until `round: 0`.
- HP values are updated each turn to reflect damage taken this turn.

---

## What the server does with it

After the LLM response is received, `_parse_combat_block` reads the `%%COMBAT%%` section:

1. Finds the `round:` line. If missing → **parse failure** → existing `session.combat_state` is left unchanged (malformed turns do not wipe live state).
2. `round: 0` is the **intentional end signal** → `session.combat_state = None`.
3. `round ≥ 1` with at least one valid combatant row → `session.combat_state = CombatState(...)`.

Per-combatant parsing:
- `hp_current` is clamped to `[0, hp_max]`.
- Unrecognised status values default to `"active"`.
- Rows with no `name` field are silently skipped.

After parsing, a `combat_update` SSE event is emitted on **every turn** (not just when state changes):

```json
{ "type": "combat_update", "combat_state": { "round": 1, "combatants": [...] } }
```

or `"combat_state": null` when no combat is active. This is how the frontend knows whether to show or hide the panel.

---

## The Combat Panel

When `combatState` is non-null in `App.tsx`:

- `CombatPanel` renders in the **right column**.
- `DicePanel` shifts to the **left column** (adjacent to `CharacterSidebar`).
- `.main-content` gains the `combat-active` CSS class.

`CombatPanel` renders:
- A header showing the current round number.
- One row per combatant, sorted highest-initiative-first.
- The top combatant (highest init, `active` status) gets the `combatant-current` class — gold glow.
- Inactive combatants (`unconscious`, `fled`, `dead`) get the `combatant-inactive` class — dimmed, with a coloured status badge.
- `HpBar` for each combatant: green (>66%), amber (33–66%), red (<33%), dark grey (0 HP).
- AC value shown as a shield chip.
- An **End Combat** button.

---

## Ending Combat

### LLM signals end — `round: 0`

When the LLM writes `round: 0` in the `%%COMBAT%%` block, the server sets `session.combat_state = None` and emits a `combat_update` with `combat_state: null`. The `CombatPanel` disappears, `DicePanel` returns to the right column.

The `attack_repelled` event file includes a `### REQUIRED — Combat tracker` section telling the LLM to write `round: 0` when all waves are done.

### GM clicks End Combat

`DELETE /api/sessions/{id}/combat` sets `session.combat_state = None` on the backend immediately. The UI sets `combatState` to `null` without waiting for a `combat_update` event. The next turn proceeds normally; the LLM can re-open combat by writing a new `%%COMBAT%%` block.

### Session end

`handleEnd` and `handleKillEnd` both call `setCombatState(null)`. The panel is always cleared when a session ends, regardless of whether combat was in progress.

---

## Wave Transitions

This adventure has three goblin waves, each triggered by a different event:

| Event | Trigger | Wave |
|-------|---------|------|
| `goblin_attack_starts` | Alarm bell / goblins visible | Wave 1 — warriors + warchanter |
| `fire_phase_begins` | Warchanter killed or fled | Wave 2 — rooftop arsonists + alley goblins |
| `cavalry_arrives` | Wave 2 suppressed | Wave 3 — goblin commandos on goblin dogs |
| `attack_repelled` | All waves gone | Aftermath |

Wave transitions do **not** reset the round counter — combat is continuous. The LLM updates the combatant list in the `%%COMBAT%%` block: add new enemies, update existing ones, mark defeated ones as `fled` or `dead`.

Each wave event file's injectable content tells the LLM exactly what combatants to list and instructs it to write `%%COMBAT%%` every turn.

---

## Dev Mode

In dev mode (`Dev Mode ON` in the header), all `%%` markers are visible in the chat stream, including the raw `%%COMBAT%%` block. This lets you verify the LLM is writing the correct format without waiting for the panel to appear.

The `combat_update` SSE event is emitted regardless of dev mode — the panel updates in real time in both modes.

---

## Combat and the API Log

Each turn's LLM call is logged to `outputs/api_log/`. To check whether the LLM wrote a `%%COMBAT%%` block:

1. Open `http://localhost:8000/api/log/api` in the browser.
2. Click the relevant turn file.
3. Look at `raw_response` — the full LLM output is there, including any `%%COMBAT%%` block.
4. `section_format_ok: true` means the LLM used section markers. `false` means it fell through to the flat-block fallback (older pattern).

If combat state parsed correctly, the session log (`outputs/*.log.md`) will contain a line like:

```
> *[Combat state updated: round 1]*
```

or

```
> *[Combat reminder injected: round 2]*
```

for subsequent turns.

---

## Known LLM Behaviour

- **First combat turn compliance**: the model sometimes writes good narrative and fires `%%EVENT%% goblin_attack_starts` but omits `%%COMBAT%%`. This is why event files include an explicit `REQUIRED` block and `_inject_context` injects a reminder on every subsequent turn.
- **Round counter**: models sometimes repeat the same round number instead of incrementing. The UI shows whatever round the LLM writes — there is no server-side round validation.
- **Flat-prose fallback**: if the model doesn't use `%%NARRATIVE%%` markers at all, `section_format_ok` is `false` and the flat-block fallback path is used. `%%COMBAT%%` is still detected in the flat path.
- **Duplicate `%%EVENT%%`**: the model occasionally writes `%%EVENT%% goblin_attack_starts` even when the event is already active. The `_already_active` guard prevents double-counting.

---

## Tier 2 (Not Yet Implemented)

- Automatic attack resolution via `%%ATTACK%%` blocks
- Server-side HP delta computation (currently the LLM writes all HP values)
- Map / grid positioning
- Condition tracking beyond the four status values
- Spell slot consumption tracking
