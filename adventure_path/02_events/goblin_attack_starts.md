**Event:** goblin_attack_starts
**Type:** combat
**Trigger:** When the goblin raid begins — alarm sounds, goblins become visible, or a player perception/awareness check reveals the attack
**Expires:** 5 turns

<!-- INJECT -->

## Active Event — Goblin Raid: Wave 1

Town state is now CRISIS. The Swallowtail Festival has been interrupted by a goblin attack.

### Combatants (Wave 1)
**Goblin warriors (4–6):** AC 16, HP 5, dogslicer +2 (1d4), shortbow +4 (1d4). Morale: flee if 3+ fall.
**Goblin warchanter (1, leading):** AC 14, HP 8, shortbow +5 (1d4+1). Inspire Courage +1 to all goblins while singing. Will not engage melee unless cornered. Priority target — silencing her ends Wave 1.

### Civilian rescue beat
A family is trapped near a food cart with two goblins closing in. No roll required — a PC who moves to intercept saves them. If no one acts: one parent takes 4 HP damage.

### Scene constraints (binding)
- Do NOT name goblin leaders or explain their motives
- Do NOT reference Thistletop, Nualia, or any larger plan
- Goblins are chaotic and opportunistic — they loot, set things on fire, and bite dogs

### Wave 1 ends when
Warchanter is killed or flees. Write `%%EVENT%% fire_phase_begins` when Wave 2 starts.

### REQUIRED — Combat tracker
Write a `%%COMBAT%%` block every turn while this event is active.
First combat turn: set `round: 1`. List all Wave 1 combatants with the AC and HP values above.
Subsequent turns: increment round when all combatants have acted; update HP to reflect damage this turn.
