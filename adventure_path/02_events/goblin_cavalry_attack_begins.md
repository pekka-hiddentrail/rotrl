**Event:** goblin_cavalry_attack_begins
**Type:** combat
**Trigger:** After the fire phase goblins are dealt with, a single mounted goblin commando charges in from the Alleyway

<!-- INJECT -->

## Zones — Festival Square

Same location as the previous waves.

| Zone | Adjacent to |
|------|-------------|
| Cathedral Stairs | Center |
| Alleyway | Center, Well |
| Well | Alleyway, Market Stalls |
| Market Stalls | Well, Center |
| Center | Cathedral Stairs, Alleyway, Market Stalls |

**Starting positions:**
- Goblin Commando (mounted on Goblin Dog): Alleyway — charges in at the start of round 1
- Aldern Foxglove + his mastiff: Well — hiding, non-combatant

## Combatants

Commando stats from bestiary (`adventure_path/09_bestiary/goblin_commando.md`).
Goblin Dog stats from bestiary (`adventure_path/09_bestiary/goblin_dog.md`).

| Name | HP | AC | Init | Starting Zone |
|------|----|----|------|---------------|
| Goblin Commando | 11 | 15 | +3 | Alleyway |
| Goblin Dog (mount) | 9 | 13 | +2 | Alleyway |

The commando is already raging (potion consumed before arrival — 6 rounds total). Use raging stats throughout.

**Commando attacks (raging, mounted):**
Melee: Mwk horsechopper +4 (1d8+2/×3, reach 10 ft.)
Ranged: Shortbow +1 (1d4/×3) — mounted penalty applies

**Goblin Dog attack:**
Melee: Bite +2 (1d6+3 plus Allergic Reaction — Fort DC 12 or –2 Dex and Cha for 1 day; disease effect, does not stack)

**Mounted Combat:** Once per round the commando can negate one hit against the goblin dog with a Ride check (DC = attack roll that hit).

### Appearance

**Goblin Commando**
Bigger than the warriors and visibly unhinged — eyes wide, tendons standing out in its neck, foam at the corners of its mouth from the rage potion. Wears a battered studded leather vest two sizes too large, belted with a strip of someone's curtain. The horsechopper is immaculate — clearly its one pride.

**Goblin Dog**
Hairless and patchy, with mottled pink-grey skin and a permanent snarl showing too many teeth. A crude saddle made of lashed leather scraps is strapped to its back. It smells terrible.

*(No internal tracking names — there is only one of each. Describe by appearance in narration.)*

### Taunts and Shouts

Use one per dramatic moment — charge entry, horsechopper hit, goblin dog biting, spotting Aldern, taking a wound:

1. *"FASTEST! I am the FASTEST! Look at me GOING!"* (screamed on entry)
2. *"The dog bites and I CHOP — we practiced this, we PRACTICED!"*
3. *"Little hiding man! We SEE you! The dog SMELLS you!"* (if moving toward Aldern)
4. *"You hurt me! YOU HURT ME! Now I'm ANGRIER!"*
5. *"Run, run, run — I will CATCH you, I always CATCH!"*

## Tactics (Binding AI Rules)

Apply in order — first matching condition wins.

### Mounted phase (default)

The commando begins mounted. While mounted it uses Mounted Combat to protect the goblin dog.

- **Target priority:** Always attack the nearest PC. If Aldern Foxglove is closer than any PC, target Aldern instead.
- **Target in same zone:** Attack with horsechopper (+4, 1d8+2). The goblin dog bites the same target as an independent attack.
- **Target in adjacent zone:** Move into that zone; attack with horsechopper if a standard action remains.
- **No target in zone or adjacent:** Move one zone toward the nearest PC or Aldern.

The commando does not use its shortbow while mounted except if forced to remain stationary for a full turn with no melee target in reach — in that case it fires once at the nearest PC (+1, 1d4).

### Dismounted phase (if goblin dog is killed)

The commando dismounts as a free action and continues on foot. Use base (non-raging) stats: AC 17, HP 9, horsechopper +2 (1d8+1). Same target priority applies.

**Fights to death — never flees, never surrenders.**

## Aldern Foxglove and His Mastiff

Aldern and his mastiff Brion are crouched behind the stone lip of the well. Aldern is pale and gripping a decorative dagger he has no idea how to use.

**If the commando enters the Well zone:**
- Round 1: The goblin dog fixates on Brion (Favored Enemy: Animals — +2 applies). Aldern scrambles backward and calls for help. Brion snarls and holds ground.
- Round 2 onward: Brion attacks the goblin dog (bite +4, 1d6+1). Aldern takes 1d4 damage from the commando each round unless a PC is also present.

**Brion the Mastiff** (defends Aldern only — does not leave the Well zone)
HP 13 | AC 13 | Bite +4 (1d6+1)

**If a PC enters the Well zone:** The commando redirects to the PC immediately. Aldern presses himself against the well and stays out of the fight.

**Rescue outcome:** If Aldern is alive when combat ends, he approaches whoever intervened — visibly shaken but composed enough to be gracious. He offers dinner at the Rusty Dragon and, if the PC responds warmly, mentions a hunting trip in the Tickwood. Handle his gratitude as pleasant and slightly over-eager, nothing more. This seeds the Act II hook.

## Scene Constraints (Binding)

- The commando is berserk — describe it as frenzied and barely in control, not tactical or coordinated
- Do NOT reference Thistletop, Nualia, or any larger plan behind the raid
- Aldern must not seem important — he is a frightened bystander who happens to be grateful afterward
- Do NOT kill Aldern unless the PCs take no action and he is attacked undefended for 2+ consecutive rounds

## Combat Ends When

The goblin commando is killed. Write `%%EVENT%% attack_repelled` when combat ends.
