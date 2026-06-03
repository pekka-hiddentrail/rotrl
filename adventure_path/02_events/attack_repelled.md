**Event:** attack_repelled
**Type:** aftermath
**Trigger:** The goblin commando is killed — all goblin threats in the square are eliminated

<!-- INJECT -->

## Scene

The square is quiet for the first time in what feels like an hour. The market stalls are wrecked, one is still smoking, and the cobblestones are littered with arrows, broken pottery, and scattered festival ribbons. Somewhere a child is crying inside the cathedral. Hemlock's militia move through the square in pairs, kicking goblin weapons into piles and checking the fallen.

The cathedral doors open. Father Zantus descends the steps with a small group of townsfolk behind him, moving toward the wounded.

Aldern Foxglove, if he is alive, has finally let go of Brion's collar.

## NPCs Present

### Father Zantus — Cathedral Stairs

Zantus moves through the aftermath with quiet purpose — kneeling beside the injured, placing hands on shoulders, murmuring prayers. He is not dramatic about it.

**If a PC approaches him:** He straightens and looks at them with open, unhurried attention. He thanks them plainly — not with speeches, but with the particular weight of someone who means it. *"You kept people alive tonight. Desna does not forget that."*

**Healing:** He will offer healing to any PC who needs it and did not receive it earlier. Cure Moderate Wounds (2d8+4). He has enough left for everyone who asks.

**If asked about the attack:** He does not know why the goblins came in force on this day of all days. He says so honestly. He mentions that he will pray for clarity, and that the cathedral is open to anyone who needs rest or sanctuary.

**His manner:** Calm. Grateful. Present in a way that makes people feel seen.

### Sheriff Hemlock — Center

Hemlock is directing the cleanup — he is not available for extended conversation yet. If a PC catches his eye, he crosses to them directly.

**What he says:** Brief and genuine: *"I don't know who you are, but you handled yourselves. Come find me at the garrison tomorrow — I'd like to talk."* He moves on immediately.

**His manner:** Respect delivered efficiently. No ceremony.

### Aldern Foxglove — Well (if alive)

Aldern approaches whichever PC interacted with him most during the cavalry attack, or the PC who appeared to be leading. He is composed now, though his hands aren't quite steady.

He thanks them directly and without embarrassment — *"That was my life. I know it."* He pauses. *"Let me do something about that. Dinner, at least. The Rusty Dragon — Ameiko keeps a good table."*

If the PC responds warmly, he adds: *"I was actually thinking of a hunting trip in the Tickwood while I'm in town. I'd be glad of company."* He does not push if the PC seems disinterested. He masks the disappointment well and withdraws gracefully.

**His manner:** Genuine, slightly too intense, well-concealed. Exactly as pleasant as he is dangerous later.

### Ameiko Kaijitsu — arrives from the direction of the Rusty Dragon

Ameiko appears as the crowd begins to settle — she was helping civilians reach the inn during the attack. She is unhurt, practical, and already thinking about the next problem.

**What she offers:** Rooms at the Rusty Dragon, free, for as long as the PCs need them. She says it matter-of-factly, as if it were obvious: *"You're not sleeping on the street tonight. Come by whenever."*

**Her manner:** Direct, warm without being sentimental. She is sizing the PCs up as she speaks — she likes what she sees but won't say so yet.

## Branching Outcomes

### Branch A — PCs engage with the NPCs

Allow each interaction to breathe — Zantus is reflective, Hemlock is brief, Aldern is grateful, Ameiko is practical. These are not plot revelations; they are the texture of a town that will remember this night.

End when the PCs stop engaging or the scene has run its natural course.

Transition: record state changes below, then end the session or continue into the next act.

### Branch B — PCs disengage quickly

Zantus nods and returns to his work. Hemlock notes their names for later. Aldern watches them go with an expression nobody reads clearly. Ameiko calls after them: *"Offer stands."*

Transition: record state changes below, then end the session or continue.

## Scene Constraints (Binding)

- This is the exhale after sustained tension — let it breathe; do not rush to the next scene
- Do NOT have any NPC reference goblin motives, Thistletop, or coordination behind the attack
- Aldern must not seem significant; his gratitude is pleasant, not weighted
- Hemlock is available tomorrow, not now — do not allow extended debrief tonight

## End Condition

Scene ends when the PCs disengage from all NPC conversations or indicate they are done for the night.

## State Changes

Record in `%%DELTAS%%`:

- `TOWN_STATE`: CRISIS → ALERT
- `PC_REPUTATION`: DEFENDER (upgrade to HERO if zero civilian deaths)
- `CIVILIAN_DEATHS`: 0 / 1–2 / 3+ (note count)
- `ALDERN_GRATITUDE`: set if Aldern was rescued and PC responded warmly — seeds Act II
- `HEMLOCK_RESPECT`: set if PCs demonstrated competence — unlocks garrison cooperation
- `RUSTY_DRAGON_ROOMS`: set — PCs have free lodging

