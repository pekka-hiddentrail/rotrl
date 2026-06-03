**Event:** event_name_snake_case
**Type:** combat | aftermath | narrative | trigger
**Trigger:** One sentence — what causes this event to activate

<!-- INJECT -->

---

<!--
  TEMPLATE NOTES
  ==============
  Delete sections that don't apply. Sections marked REQUIRED must always be present
  for the given type. Sections marked OPTIONAL can be omitted if not relevant.

  Types:
    combat    — active fight with combatants, zones, tactics
    aftermath — post-combat scene, state changes, NPC reactions
    narrative — no combat; delivers exposition, revelation, or tone shift
    trigger   — fires instantly, sets a flag or chains to another event; no scene content

  The <!-- INJECT --> comment above is the LLM injection point.
  Everything above it is metadata (not injected). Everything below it IS injected.
-->

---

## Zones  [REQUIRED for combat | OMIT for others]

<!--
  Use named in-world zones. Adjacency = melee reach and one-action movement.
  Same zone = melee. Ranged attacks cross any number of zones.
  Center is typically the most connected zone.
-->

The [location name] is divided into [N] zones.

| Zone | Adjacent to |
|------|-------------|
| Zone A | Zone B, Zone C |
| Zone B | Zone A |
| Zone C | Zone A |

At combat start, [describe how combatants and any special objects/NPCs are placed].

---

## Combatants  [REQUIRED for combat]

<!--
  Reference the bestiary file for stat blocks. List only what differs from bestiary here.
  Zone column is (random) if placement varies; otherwise name the zone.
-->

Stats from bestiary (`adventure_path/09_bestiary/creature_name.md`).

| Name | HP | AC | Init | Zone |
|------|----|----|------|------|
| Creature 1 | 0 | 0 | +0 | (random) |
| Creature 2 | 0 | 0 | +0 | (random) |

Attacks: Weapon +N (damage) melee · Weapon +N (damage) ranged

### Appearance  [REQUIRED for combat]

<!--
  One short paragraph per combatant. One distinct visual detail that makes
  each creature memorable and narration-ready.
  Internal tracking names go in parentheses — do NOT narrate them unless
  players assign their own names.
-->

**Creature 1 — "Internal Name"**
[One or two sentences of distinct appearance detail.]

**Creature 2 — "Internal Name"**
[One or two sentences of distinct appearance detail.]

*(Internal names are for GM tracking only — do not use in narration unless players assign them.)*

### Taunts and Shouts  [REQUIRED for combat]

<!--
  Exactly 5 lines. Tied to dramatic moments: entering a zone, scoring a hit,
  being wounded, reacting to the environment, special ability firing.
  Each should sound like this creature specifically, not a generic villain.
  Include a stage direction in parentheses where tone needs clarifying.
-->

Use one per dramatic moment:

1. *"[taunt]"*
2. *"[taunt]"*
3. *"[taunt]"* (optional stage direction — sung, whispered, etc.)
4. *"[taunt]"*
5. *"[taunt]"*

---

## Tactics  [REQUIRED for combat]

<!--
  Binding AI rules. Apply in priority order — first matching condition wins.
  Separate modes (ranged/melee, mounted/dismounted, etc.) with sub-headers.
  State what triggers a mode switch and whether it is reversible.
-->

Apply these in order — first matching condition wins.

### [Mode A — default]

[Describe what weapon/stance combatants start in.]

- **[Condition]:** [Action.]
- **[Condition]:** [Action.]

### [Mode B — triggered by X]

[Once switched, [reversible / never reverts].]

- **[Condition]:** [Action.]
- **[Condition]:** [Action.]

### [Special zone or object rules]  [OPTIONAL]

<!--
  Use for objects, hazards, or NPCs that have their own per-round logic.
  Describe the countdown or trigger clearly.
-->

If [condition], describe [beat 1]. If [condition persists], [consequence].

---

## Special NPCs / Objects  [OPTIONAL]

<!--
  Use for non-combatant actors (civilians, prisoners, animals) or interactive
  objects (fires, siege engines, locks) that have per-round states.
-->

**[NPC/Object name]**

[One sentence description.]

**[Condition for positive outcome]:** [Result. No roll required / Skill check DC N.]

**[Consequence if ignored]:** [What happens after N rounds.]

---

## Scene Constraints (Binding)  [REQUIRED for combat and narrative]

<!--
  Hard rules for the LLM. Use "Do NOT" language. Keep to 3–5 lines.
  Cover information the GM must not reveal, NPCs who must not speak, tonal limits.
-->

- Do NOT [information to withhold].
- Do NOT [NPC who must stay silent / offscreen].
- [Creatures/factions] are [defining trait] — [one behavioral note].

---

## End Conditions  [REQUIRED for combat | OPTIONAL for others]

<!--
  Be specific. "All enemies dead" is fine for simple fights.
  List alternate ends (retreat, objective achieved, timer expired).
  Always end with the %%EVENT%% chain call.
-->

Combat ends when [specific condition]. Write `%%EVENT%% next_event_name` when this fires.

<!--
  For aftermath events: end with the state changes to record.
-->

---

## State Changes  [REQUIRED for aftermath | OPTIONAL for others]

<!--
  Persistent facts the GM must record in %%DELTAS%%.
  Use flag names in SCREAMING_SNAKE_CASE.
-->

Record in `%%DELTAS%%`:

- [FLAG_NAME]: [value or description]
- [FLAG_NAME]: [value or description]
