**Event:** cavalry_arrives
**Trigger:** When goblin commandos on goblin dogs charge into the square (Wave 3)
**Expires:** 5 turns

<!-- INJECT -->

## Active Event — Goblin Raid: Wave 3 (Cavalry)

Three goblin commandos on goblin dogs have burst into the square. This is the final wave.

### Combatants (Wave 3)
**Goblin commandos (3):** AC 17, HP 9, mwk horsechopper +2 (1d8+1/×3), shortbow +5. Mounted Combat: negate 1 hit/round on mount.
**Goblin dogs (3):** AC 13, HP 14, bite +3 (1d6+2 plus Goblin Pox — Fort DC 12 or 1d3 Dex damage, onset 1 day).

### Tactics
Commandos charge to scatter civilians, not to hold ground. They grab loot from fallen stalls and flee if the fight turns.

### Morale
Flee if: their mount is killed, OR 2+ commandos fall. Dogs flee if their rider dies.

### Wave 3 ends when
Commandos routed or killed. All active goblin threats are gone. Write `%%EVENT%% attack_repelled`.

### REQUIRED — Combat tracker
Write a `%%COMBAT%%` block every turn while this event is active.
Add Wave 3 combatants (stats above) to the existing combatant list.
Increment round each turn; update HP to reflect damage this turn.
