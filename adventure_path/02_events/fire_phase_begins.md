**Event:** fire_phase_begins
**Type:** combat
**Trigger:** When Wave 1 is suppressed and goblin arsonists appear on rooftops or alleys
**Expires:** 5 turns

<!-- INJECT -->

## Combatants

| name | hp | ac | init_mod | attacks |
|------|----|----|----------|---------|
| Goblin Arsonist 1 | 5 | 20 | +2 | torch throw +4 (1d3 fire, 10 ft range) |
| Goblin Arsonist 2 | 5 | 20 | +2 | torch throw +4 (1d3 fire, 10 ft range) |
| Goblin Arsonist 3 | 5 | 20 | +2 | torch throw +4 (1d3 fire, 10 ft range) |
| Alley Goblin 1 | 5 | 16 | +2 | dogslicer +2 (1d4), shortbow +4 (1d4) |
| Alley Goblin 2 | 5 | 16 | +2 | dogslicer +2 (1d4), shortbow +4 (1d4) |
| Alley Goblin 3 | 5 | 16 | +2 | dogslicer +2 (1d4), shortbow +4 (1d4) |

## Active Event — Goblin Raid: Wave 2 (Fire)

Wave 1 is over. Goblin arsonists have appeared on rooftops; alley goblins are cutting off retreat to the south.

### Combatants (Wave 2)
**Rooftop goblins (3–4):** AC 20 (cover +4), HP 5, throwing torches. Can throw OR move, not both. Must be dislodged or killed — ranged attacks, climb checks (DC 12), or spells.
**Alley goblins (2–3):** AC 16, HP 5, standard stats. Morale: flee if 2 fall.

### Fire mechanics
- 1d4 stalls/structures catch fire this round
- Adjacent creatures take 1 fire damage per round unless they move away
- Scaffolding collapses on round 4 if not extinguished: Reflex DC 12 or 1d6 damage
- Extinguishing: full-round action at the well (30 ft west), one hazard per action

### Hemlock arrives
Sheriff Hemlock arrives mid-wave with 4 militia. He organises civilians toward the cathedral and engages rooftops with crossbow fire. He does not take the PCs' kills — he handles crowd control.

### Wave 2 ends when
Rooftop goblins are silenced and immediate fire threat is addressed (or not — casualties apply). Write `%%EVENT%% cavalry_arrives` when Wave 3 starts.

### REQUIRED — Combat tracker
Write a `%%COMBAT%%` block every turn while this event is active.
Replace Wave 1 combatants with Wave 2 combatants (stats above); carry forward any PCs or surviving Wave 1 enemies.
Increment round each turn; update HP to reflect damage this turn.
