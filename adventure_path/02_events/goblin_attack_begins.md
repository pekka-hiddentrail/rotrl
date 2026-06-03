**Event:** goblin_attack_begins
**Type:** combat
**Trigger:** Father Zantus strikes the thunderstone — a deafening crack silences the crowd, then the screaming begins

<!-- INJECT -->

## Zones — Festival Square

The square is divided into five named zones. Adjacency determines movement and melee reach.

| Zone | Adjacent to |
|------|-------------|
| Cathedral Stairs | Center |
| Alleyway | Center, Well |
| Well | Alleyway, Market Stalls |
| Market Stalls | Well, Center |
| Center | Cathedral Stairs, Alleyway, Market Stalls |

The civilian family of four occupies Center zone. Goblins start in the zones below.

**PC Starting Zone:** Center

## Combatants

Goblin stats from bestiary (`adventure_path/09_bestiary/goblin.md`).

| Name | HP | AC | Init | Zone | Melee | Ranged |
|------|----|----|------|------|-------|--------|
| Goblin Warrior 1 | 5 | 16 | +6 | Center | dogslicer +2 (1d4) | shortbow +4 (1d4) |
| Goblin Warrior 2 | 5 | 16 | +6 | Well | dogslicer +2 (1d4) | shortbow +4 (1d4) |
| Goblin Warrior 3 | 5 | 16 | +6 | Market Stalls | dogslicer +2 (1d4) | shortbow +4 (1d4) |

### Appearance

**Goblin Warrior 1**
Missing its left ear, replaced by a knot of scar tissue. Two lopsided red handprints painted on its leather armour. Slightly fat by goblin standards — its belly wobbles when it runs.

**Goblin Warrior 2**
Unnervingly still one moment, then convulsing with nervous energy the next. Eyes point in slightly different directions. A dead crow tied to its belt swings as it moves.

**Goblin Warrior 3**
Exceptionally thin, almost skeletal, with limbs that seem too long for its body. Crude runes scrawled on its face in charcoal. Wears a stolen child's sun-hat jammed sideways over its enormous ears.


### Taunts and Shouts

Use one per dramatic moment — a goblin entering a zone, scoring a hit, being wounded, spotting the family:

1. *"Longshanks taste like BOOTS! We know! We checked!"*
2. *"Burn it! Burn the dog! Burn the HAT! Burn EVERYTHING!"*
3. *"Goblins, goblins, kill kill kill — stick them with the pointy bill!"* (sung, badly)
4. *"Too slow, tall one! Too slow too slow TOO SLOW!"*
5. *"Their teeth come OUT! We KNOW this! Put them in our pockets!"*

## Goblin Tactics (Binding AI Rules)

Apply these in order — first matching condition wins.

### Ranged mode (default)

Each goblin starts combat with its shortbow equipped.

- **No PC in zone:** Fire shortbow at the nearest PC (fewest zone hops). Ties broken by lowest current HP.
- **PC enters zone:** Spend the full turn switching to melee (equip shield + dogslicer). No attack this turn.

### Melee mode (after switching)

Once switched to melee a goblin never reverts.

- **PC in zone:** Attack with dogslicer.
- **PC in adjacent zone:** Move into that zone (move action); attack if an action remains.
- **No PC in zone or adjacent:** Move one zone toward the nearest PC.

### Family zone

If a goblin ends its turn in the family's zone and no PC is present:

- **First round in zone:** Goblin corners the family — describe panic. No damage yet.
- **Second round in zone:** One family member is killed.

A PC entering the family's zone redirects the goblin to attack the PC and resets the countdown.

## Civilian Family

A mother, a father, and two small children are huddled behind an overturned vegetable cart.

**Rescue condition:** A PC who ends their turn in the family's zone without having made an attack action that turn guides them to safety. No roll required. Reward: gratitude and a minor item (festival trinket, small purse — GM discretion).


### Scene constraints (binding)
- Do NOT reference Thistletop, Nualia, or any larger plan
- Goblins are chaotic and opportunistic — they loot, screech war songs, and bite dogs

### Combat ends when
All three goblins are dead or have fled the square. Write `%%EVENT%% first_wave_repelled` when combat ends.
