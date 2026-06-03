# Movement & Zone System Backlog

Zone-based combat for Theater of Mind play. No grid, no distance matrix —
zones are named in-world locations connected by adjacency. Moving within a
zone or to an adjacent zone costs one move action. Everything else follows.

Inspired by: Fate Condensed (Evil Hat), Forbidden Rules (Schwalb),
5e Hardcore Mode (Runehammer), and Sly Flourish's zone-based combat guide.

**Same markup rules as TODO.md apply.**

---

## Design decisions (locked)

> **No 5-foot squares. No distance matrix. No compass directions.**
> Zones are named areas. Adjacency is a boolean — zones are either next to each
> other or they are not. Range is "same zone" or "adjacent zone." That's it.

> **A combatant's complete position is two values: `zone` (where they are) and
> whether they are in melee (same zone as an enemy). Nothing else.**

### Core rules

| Rule | Implementation |
|------|---------------|
| Move within a zone OR to one adjacent zone | One move action |
| Fast movers (monk, rogue, dash, over 40ft movement) | Can move 2 zones |
| Same zone = melee range | **Always.** Same zone as an enemy → in melee. Full stop. |
| Ranged attacks | Same zone (disadvantage — in enemy zone) OR any adjacent zone |
| Ranged in melee | Valid, but **disadvantage** (you are in the enemy's zone) |
| AoE size | Small=2 targets, Medium=3, Large=4, Huge=8+ |
| 5-foot step equivalent | Move within current zone only (no zone change); breaks flanked condition |
| Zone properties | Zones can have conditions (higher ground, cover, darkness, difficult terrain) |

### Zone sizing rule

| Space size | Zone count | Example |
|-----------|-----------|---------|
| ≤ 30 ft in any dimension | **1 zone** | 30×10 corridor, small room — everyone in melee range of everyone |
| > 30 ft | Split by **features**, not measurements | 100×50 hall → "entrance · pillars · altar dais" |

Zones are narrative divisions, not metric ones. A featureless 60×80 room may be 2 zones;
a 40×40 room with a pit, pillars, and a throne may be 4. The GM decides when writing the encounter.
No `## Zones` section in the event file = one zone = everyone always in melee range.

### Zone structure in encounter files

Zones are defined in the event file under a `## Zones` section:

```markdown
## Zones

| zone | adjacent | properties |
|------|----------|-----------|
| stairs | stalls | higher_ground |
| stalls | stairs, well | — |
| well | stalls | — |
```

- **adjacent**: comma-separated list of zone names that are directly reachable in one move
- **properties**: zone-level conditions applied to all occupants (see M5)
- If an encounter has only one zone, the section can be omitted (everyone in melee range by default)

### Combatant.zone field

```python
Combatant.zone: str = "default"   # named zone from event file; "default" when no zones defined
```

Single-zone combats use `"default"` for everyone and skip all range checks.

---

## Cross-cutting open items

- [ ] **Conditions belong in COMBAT-TODO.md** — zone properties like `higher_ground` and `cover` apply conditions to combatants in that zone. The actual condition mechanics (attack bonus/penalty, AC modifier) are tracked on `Combatant.conditions` and must be implemented as part of Tier 1.11 (conditions) and SA-7 (condition mechanical effects). MOVEMENT-TODO only defines that zones *grant* conditions; COMBAT-TODO defines what those conditions *do*.

- [ ] **Flanking and zone changes** — flanking (`Combatant.flanked: bool`) is set when two or more enemies are in the same zone as the target and have attacked it from different sides. A 5-foot-step equivalent (moving within zone) breaks flanking by re-positioning without giving up the zone. Full zone movement does not automatically break flanking — the new zone's occupants determine it.

- [ ] **Event file `## Zones` section** — `_parse_event_combatants` currently reads the `## Combatants` table. Add parsing for the optional `## Zones` section into `session.zone_map: dict[str, set[str]]` — a mapping from zone name to its set of adjacent zones. Also parse zone `properties` into `session.zone_properties: dict[str, list[str]]`.

- [ ] **CombatPanel zone display** — show the zone name next to each combatant's name in the CombatPanel. Small badge or parenthetical: `Goblin Warrior 1 (stairs)`. Helps players see the battlefield at a glance.

---

## Tier M1 — Zone Data Model

Define zones in the data layer. No rules enforcement yet — just the data structures and event file parsing.

- [ ] **M1-1 — `Combatant.zone: str`** — add to `Combatant` dataclass; default `"default"`. Serialised in `state.json` and `_serialize_combat_state`.

- [ ] **M1-2 — `GameSession.zone_map`** — `dict[str, set[str]]` adjacency map. Example: `{"stairs": {"stalls"}, "stalls": {"stairs", "well"}, "well": {"stalls"}}`. Populated at combat start from event file. Empty when no `## Zones` section.

- [ ] **M1-3 — `GameSession.zone_properties`** — `dict[str, list[str]]`. Example: `{"stairs": ["higher_ground"]}`. Empty when no properties defined.

- [ ] **M1-4 — `_parse_event_combatants` extension** — parse `## Zones` table if present. Populate `session.zone_map` and `session.zone_properties`. Add `zone` column support to `## Combatants` table so each combatant's starting zone is seeded at round 1.

- [ ] **M1-5 — Update event files** — add `## Zones` section and `zone` column to all three combat event files (`goblin_attack_starts.md`, `fire_phase_begins.md`, `cavalry_arrives.md`). Design the goblin attack zones: `square` (main engagement), `alley` (flanking goblins), `stalls` (civilian area). Warchanter starts in `square`, Warriors start in `square` or `alley`.

- [ ] **M1-T — Tests** — `_parse_event_combatants` reads zone adjacency and properties; combatant zone seeded correctly; `session.zone_map` populated; default zone when section absent.

---

## Tier M2 — Zone Helpers and Range Validation

Utility functions the rest of the system calls. No UI changes.

- [ ] **M2-1 — `_zones_adjacent(session, zone_a, zone_b) → bool`** — returns True if `zone_b` in `session.zone_map.get(zone_a, set())` OR `zone_a == zone_b`. Single-zone encounters always True.

- [ ] **M2-2 — `_in_melee_range(session, attacker, target) → bool`** — True if attacker and target are in the same zone. Used for melee weapon validation.

- [ ] **M2-3 — `_in_ranged_range(session, attacker, target) → bool`** — True if same zone OR adjacent zone. Used for ranged weapon and most spell validation.

- [ ] **M2-4 — `_ranged_in_melee(session, attacker, target) → bool`** — True if attacker is in the same zone as any enemy. Triggers disadvantage on ranged attacks. No per-turn tracking needed — same zone = melee, always.

- [ ] **M2-5 — Weapon range validation in `stream_pc_turn`** — after intent extraction, validate:
  - Melee weapon: error if target not in same zone. Suggest ranged weapon or move action first.
  - Ranged weapon: error if target not in same or adjacent zone. Note disadvantage if in melee with target.
  - Show weapon hint updated: `⚔ dogslicer (melee) · shortbow (ranged, adjacent zone)`.

- [ ] **M2-T — Tests** — adjacent zones return True; non-adjacent return False; single-zone always True; melee validation blocks cross-zone; ranged validation allows same+adjacent; disadvantage flag set correctly.

---

## Tier M3 — Movement on PC Turn

Handling move actions in `stream_pc_turn` when the player declares movement.

- [ ] **M3-1 — Detect move intent** — extend `_extract_pc_combat_intent` to detect movement declarations: "I move to the stairs", "I run to the well", "I close in on the goblin". Extract `destination_zone` from the text by matching against `session.zone_map` keys.

- [ ] **M3-2 — Validate zone reachability** — one move action: can reach current zone or any adjacent zone. Two-zone jump (monk/rogue/dash): check `pc_profiles["movement_bonus"]` or "dash" keyword in input.

- [ ] **M3-3 — Update `Combatant.zone`** — on successful move, set the PC's zone. Emit `combat_update` SSE with updated state. Log the movement.

- [ ] **M3-4 — Entering a zone = possible melee** — when a combatant moves into a zone containing enemies, they are now in melee range of those enemies. The LLM briefing notes this: "Moving to `stairs` puts you in melee range of Goblin Warrior 1."

- [ ] **M3-5 — 5-foot step equivalent** — "I sidestep", "I 5-foot step", "I step aside" → stay in current zone; breaks `flanked` condition if set; does NOT use the move action budget.

- [ ] **M3-T — Tests** — zone change updates Combatant.zone; adjacent move valid; non-adjacent blocked; monk can jump 2 zones; 5ft step stays in zone and clears flanked; entering enemy zone sets appropriate context.

---

## Tier M4 — Movement on Enemy Turn

Enemy zone changes from `%%ACTION%%` move declarations.

- [ ] **M4-1 — Parse movement from `%%ACTION%%`** — `_parse_action_block` already captures `movement` field. Add zone parsing: if `movement` contains a zone name from `session.zone_map`, update the enemy's `Combatant.zone`.

- [ ] **M4-2 — Charge (move + attack)** — enemy in `"stairs"` zone charges a PC in `"square"` zone. Sequence: move to `"square"` zone → now in melee range → attack. Backend handles as: update zone, then resolve attack. `_build_enemy_turn_system` shows the zone change in the briefing.

- [ ] **M4-3 — Retreat** — enemy moves to a non-adjacent zone (two-zone jump, spending full-round action). Validate that the path exists (or allow with narrative note).

- [ ] **M4-T — Tests** — enemy charge updates zone then resolves attack; retreat moves zone correctly; zone shown in `combat_update`.

---

## Tier M5 — Zone Properties (Conditions)

Zones can grant conditions to all occupants. `higher_ground`, `cover`, `darkness`, `difficult_terrain`, `hazard`.

> **Prerequisite:** Tier 1.11 (conditions) and SA-7 (condition mechanical effects) for the *effects*. This tier only defines the *granting* mechanic.

- [ ] **M5-1 — Apply zone conditions on entry** — when a combatant moves into a zone with `properties`, add those properties to `Combatant.conditions`. When they leave, remove zone-granted conditions.

- [ ] **M5-2 — Higher ground** — occupants of a `higher_ground` zone gain +1 to ranged attack rolls against targets in non-higher-ground zones. Attackers in lower zones take −1 to ranged attacks upward. (PF1e: +1 ranged, no bonus melee at level 1.)

- [ ] **M5-3 — Cover** — occupants of a `cover` zone gain +4 AC against ranged attacks from outside the zone (soft cover). Attacker must be in a different zone. (PF1e: standard cover.)

- [ ] **M5-4 — Difficult terrain** — movement into a `difficult_terrain` zone uses the full move action AND the 5-foot step option is unavailable. A second move action (or dash) is required to then move to another zone.

- [ ] **M5-5 — Darkness** — occupants in a `darkness` zone are effectively invisible to attackers in non-darkness zones (concealment: 50% miss chance). Attackers in the same darkness zone fight normally.

- [ ] **M5-T — Tests** — moving into `higher_ground` zone adds condition; leaving removes it; cover AC bonus applied to ranged attacks from different zone; difficult terrain costs extra move.

---

## Tier M6 — AoE Resolution

Area-of-effect spells and abilities use target counts, not zone coverage.

> **Prerequisite:** Tier M1 (zone model), Tier S2 (spells).

- [ ] **M6-1 — AoE size classification** — each AoE spell/ability carries a size tag:

  | Tag | Target count | PF1e equivalent |
  |-----|-------------|----------------|
  | small | 2 | 5–10 ft burst/cone |
  | medium | 3 | 15–20 ft burst/cone |
  | large | 4 | 30 ft burst/cone |
  | huge | 8+ | 40+ ft or full-zone |

  Add `aoe_size` field to spell dictionary entries.

- [ ] **M6-2 — Target selection** — when resolving an AoE, backend determines: targets must be in the caster's zone or an adjacent zone (unless the spell has longer range). The LLM names which targets are in the area based on the scene description. Backend picks up to `target_count` from the named targets and resolves each.

- [ ] **M6-3 — Concentration and AoE balance** — adjust count up or down based on zone context: if all enemies are in one clustered zone, GM can bump count by 1; if enemies are spread across three zones, count may be lower. The LLM declares and the GM adjudicates.

- [ ] **M6-T — Tests** — small AoE resolves 2 targets; large resolves 4; targets must be in valid zone; each target gets independent save/damage roll.

---

## Future

- [ ] **Zone description and features** — zones can carry a `description` (prose injected into the LLM briefing) and a `## Zone Features` table for named interactables within the zone (doors, traps, chests, levers). Features are not zones — you don't move to them, you interact with them. The LLM reads them; the backend ignores them for range purposes.

  Example event file extension:
  ```markdown
  | zone | adjacent | properties | description |
  |------|----------|-----------|-------------|
  | corridor | antechamber, guard_room | darkness | Long stone passage. Left: 5 wooden doors (D1–D5). Right: 3 iron doors (D6–D8). |

  ## Zone Features
  | zone | feature | detail |
  |------|---------|--------|
  | corridor | D7 | trapped — spring-loaded bolt, DC 15 Perception |
  | corridor | D3 | locked — DC 18 Disable Device |
  ```

- [ ] **`Combatant.senses` and darkvision** — `Combatant.senses: list[str]` with values like `darkvision_60`, `low_light_vision`, `blindsight_30`. When a combatant is in a `darkness` zone, check their senses: no darkvision → blinded (50% miss chance, cannot read zone features); darkvision → fights normally within same/adjacent zone; low-light vision → `darkness` still blinds (needs dim light minimum). Read from `player_*.json["senses"]` and monster stat block.

- [ ] **Opportunity attacks** — triggered when a combatant moves out of a zone while in melee (same zone as an enemy). The enemy gets one free attack before movement completes.
- [ ] **Blocking access** — certain combatants can block a zone transition (e.g. two iron golems blocking the throne room). Declared in event file or by GM. Moving through the blocked path triggers an AoO.
- [ ] **Mounted movement** — mounted combatants move 2 zones per action (horse speed). Mounted in melee has special rules. Defer to mounted combat tier.
- [ ] **Vertical zones** — multi-level encounters (rooftop, ship decks, dungeon floors). Zones on different levels have `vertical: true` adjacency — moving between them may cost the full move action.
- [ ] **Hazard zones** — zones with `hazard` property deal damage on entry (fire, acid, spikes). Triggered by `advance_combat_turn` when a combatant's zone is a hazard.
- [ ] **Forced movement** — grapple, shove, pushing effects move a target to an adjacent zone. Requires a new `push_to_zone` mechanic in the attack resolution path.
