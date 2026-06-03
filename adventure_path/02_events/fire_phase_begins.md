**Event:** fire_phase_begins
**Type:** combat
**Trigger:** After the first wave is repelled, there is a moment to relax and orient.

<!-- INJECT -->

## Zones — Festival Square

Same location as the first wave. Zones and adjacency unchanged.

| Zone | Adjacent to |
|------|-------------|
| Cathedral Stairs | Center |
| Alleyway | Center, Well |
| Well | Alleyway, Market Stalls |
| Market Stalls | Well, Center |
| Center | Cathedral Stairs, Alleyway, Market Stalls |

The Alleyway leads out of the square — it is the goblins' escape route.

**PC Starting Zone:** Based on the actions in the `%%EVENT%% goblin_attack_begins`

## Combatants

Goblin stats from bestiary (`adventure_path/09_bestiary/goblin.md`).
Warchanter stats from bestiary (`adventure_path/09_bestiary/goblin_warchanter.md`).

| Name | HP | AC | Init | Zone | Melee | Ranged |
|------|----|----|------|------|-------|--------|
| Goblin Warrior 4 | 5 | 16 | +6 | Alleyway | dogslicer +2 (1d4) | shortbow +4 (1d4) |
| Goblin Warrior 5 | 5 | 16 | +6 | Alleyway | dogslicer +2 (1d4) | shortbow +4 (1d4) |
| Goblin Warrior 6 | 5 | 16 | +6 | Market Stalls | dogslicer +2 (1d4) | shortbow +4 (1d4) |
| Goblin Warchanter | 8 | 14 | +3 | Market Stalls | whip +2 (1d3), dogslicer +1 (1d4) | shortbow +5 (1d4+1) |
Bardic Music 4/day — Inspire Courage +1 (morale bonus to attack, damage, and saves vs fear/charm for all active goblins while singing)

### Appearance

**Goblin Warrior 4**
Sooty-faced and grinning, with singed eyebrows from one too many torch accidents. Has wrapped a stolen silk festival banner around its waist like a skirt. Carries its torch in its off-hand with unsettling pride.

**Goblin Warrior 5**
Shorter than average, almost comically so, but fast — it darts and twitches like a startled rat. Has painted its teeth black. Wears a necklace of broken pottery shards that clatter as it moves.

**Goblin Warrior 6**
Broad-shouldered by goblin standards, with a wide flat nose that has been broken at least twice. Covered in old bite scars on its forearms — from other goblins. Stares at things a moment too long before reacting.

**Goblin Warchanter**
Wiry and wild-eyed, with elaborate streaks of red mud painted across her face in jagged patterns. Taller than the warriors by half a head. Her mouth never quite closes — even mid-song her teeth are showing.

*(Internal names not assigned — describe by zone or physical trait in narration.)*

### Taunts and Shouts

Use one per dramatic moment — goblin entering a zone, scoring a hit, being wounded, building catching fire, warchanter starting to sing:

1. *"FIRE! Fire fire FIRE! Everything is MORE FIRE!"*
2. *"You're too slow and you SMELL like a horse, we NOTICED!"*
3. *"Sing it, sing it — they're bleeding and they don't even KNOW yet!"* (the warchanter, to herself)
4. *"Run away, tall one! Run away and we stop! …We won't stop."*
5. *"The buildings are OURS now! We're KEEPING them!"*

## Surprise

These goblins arrived while the PCs were occupied with wave 1. They have had time to hide.

**Stealth:** Goblin Warriors +10 · Goblin Warchanter +3

At combat start, each PC makes a Perception check:
- **Beat the goblin's Stealth:** PC acts normally in round 1.
- **Fail:** PC is flat-footed for round 1 (loses Dex bonus to AC, cannot take AoO).

Roll each goblin's Stealth separately. A PC who beats one goblin's check is not surprised by that goblin but may still be surprised by another.

## Goblin Tactics (Binding AI Rules)

### Goblin Warriors — Alleyway

Follow the standard goblin tactics (ranged first, switch to melee when PC enters zone).

**Additionally — arson:**

Each warrior carries a torch. When a warrior is **unengaged** (no PC in its zone at the start of its turn) it spends its action setting fire to the nearest building.

- **Turn 1 of burning:** The building smolders — describe smoke and spreading flame. No damage yet.
- **Turn 2 of burning:** The building catches fire. Any creature that ends its turn in this zone takes 1d6 fire damage. This persists for the rest of the encounter.

A goblin that becomes **engaged** (a PC enters its zone) immediately drops its torch and switches to normal combat tactics. It does not relight the torch.

If a building is burned, make a note (determined later where) that the town is on fire.

### Warchanter — Market Stalls

**Round 1:** The warchanter begins singing Inspire Courage as a standard action. This grants all active goblins +1 morale bonus on attack rolls, weapon damage rolls, and saves vs fear and charm. The bonus persists as long as she sings (she uses a free action each turn to maintain it).

**Subsequent turns — ranged mode (default):**
- **No PC in zone:** Fire shortbow at the nearest PC.
- **PC enters zone:** Use whip trip attempt (CMB –1 vs target's CMD) or dogslicer, whichever is more advantageous. Retreats to an adjacent zone if possible rather than staying in melee.

## Morale and Retreat

When the warchanter is killed:

- **2 or more regular goblins still alive:** Both immediately attempt to flee. Each goblin moves toward the Alleyway by the shortest path. Once a goblin enters the Alleyway zone it escapes — remove it from combat.
- **Only 1 regular goblin alive:** It fights to the death, frenzied.

## Scene Constraints (Binding)

- Do NOT reference Thistletop, Nualia, or any larger plan
- Goblins are chaotic — the arsonists cackle and screech as they set fires; narrate the spreading smoke and crowd panic
- The warchanter's song is audible across the square — describe it as discordant and gleeful

## Combat Ends When

All goblins are dead or have fled through the Alleyway. Write `%%EVENT%% attack_repelled` when combat ends.
