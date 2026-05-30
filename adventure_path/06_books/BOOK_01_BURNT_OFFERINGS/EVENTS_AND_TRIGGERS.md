# Book I – Burnt Offerings

## Events and Triggers

This document defines **time-based, conditional, and consequence-driven events** for Burnt Offerings. These events exist to maintain pressure, ensure world reactivity, and prevent narrative stagnation.

Events listed here are **not scripts**. They are state changes that occur when conditions are met.


## Design Principles

* Events trigger due to **inaction, delay, or consequence**, not arbitrary timing
* Triggers escalate the situation without invalidating player agency
* Events may occur off-screen and be learned through rumor, aftermath, or NPC reaction

If multiple triggers would activate simultaneously, resolve the one with the **greatest impact on Sandpoint** first.


## Global Pressure Track

Burnt Offerings uses a pressure model tied to Sandpoint's stability and **explicit timers**.

### Pressure Sources

* Civilian casualties (each death = +1 Pressure)
* Public panic (from major events)
* Structural damage (buildings destroyed)
* Prolonged PC absence or inaction (tracked by in-game days)

### Pressure Escalation Rules

**Pressure starts at 0 at the beginning of the Festival.**

| Pressure Level | NPC Behavior | Sheriff Action | Public Mood |
|---|---|---|---|
| 0-2 | Cooperative | Supportive | Calm, grateful |
| 3-5 | Cautious, conditional | Independent but coordinated | Nervous, rumors increase |
| 6-8 | Distrustful, withdrawn | Martial law considerations | Fearful, suspicion of strangers |
| 9+ | Hostile or non-cooperative | Declares curfew, militia mobilized | Panic, scapegoating, divisions |

### Pressure Sources (Specific)

Each of the following adds **+1 Pressure per incident**:

* Death of a **named NPC** = +2 Pressure (instead of +1)
* Death of the **Sheriff or Mayor** = +4 Pressure instantly
* Destruction of a **major building** (Glassworks, Temple, Town Hall) = +2 Pressure
* Public attack during daytime/crowded event = +1 Pressure
* Rumor of a child death = +2 Pressure (morale impact)

As pressure increases:

* NPC trust becomes conditional (see NPC_MEMORY_AND_CONTINUITY.md)
* Authority figures act independently
* Rumors distort facts
* Named NPCs consider leaving town if Pressure ≥ 8


## Act I – Swallowtail Festival

### Trigger: Goblins Escape the Festival

**Condition:** Goblin attackers flee the scene

**Event:**

* Future goblin raids show increased coordination
* Survivors report goblins acting "with purpose"


### Trigger: High Civilian Casualties

**Condition:** Multiple named or unnamed civilians are killed

**Event:**

* Public celebration ends abruptly
* Fear becomes the dominant mood in Sandpoint


### Trigger: PCs Disengage

**Condition:** PCs withdraw from the crisis

**Event:**

* Sheriff Hemlock assumes control
* PCs are treated as capable but unreliable


## Act II – Shadows in Sandpoint

### Trigger: Glassworks Investigation Delayed

**Condition:** PCs do not investigate the Glassworks within **3 days** of the festival

**Timeline & Escalation:**

* Day 1-3: Glassworks remains sealed, rumors spread
* Day 4: Lonjiku body discovered; **Pressure +2**. Ameiko increasingly withdrawn
* Day 5-6: Glassworks officially investigated by Sheriff; PCs lose investigative advantage
* Day 7+: Body removed by Sheriff; physical evidence degraded; Ameiko considers leaving town

**Event:**

* Sabotage escalates to additional vandalism (warehouses, roads)
* Economic anxiety spreads: shopkeepers raise prices
* **Pressure +1** for each 2 days of delay after Day 4


### Trigger: Catacombs Ignored

**Condition:** Catacombs are not entered within **10 days** of Swallowtail

**Timeline & Escalation:**

* Days 1-10: Subtle attacks continue
* Day 11: Seismic tremor shakes Sandpoint
* Day 12+: **Pressure +1 per day**; creatures spotted at town edges
* Day 18+: Random townsperson falls ill with unexplained sickness

**Event:**

* Subtle corruption spreads unseen
* NPCs report strange dreams (nightmares of old stone, ancient voices)
* **Named NPCs affected:** Sheriff Hemlock (moody), Father Zantus (paranoid), Ameiko (secretive)
* Pressure increases from unease


### Trigger: Nualia’s Past Uncovered Early

**Condition:** PCs learn 3+ significant facts about Nualia before meeting her

**Event:**

* Confrontation feels less like ambush, more like meeting a hunted woman
* If killed without redemption offer: **Pressure +1**
* If redeemed/spared: **Pressure -1**


## Act III – Thistletop

### Trigger: Reckless Assault

**Condition:** PCs attack Thistletop openly without preparation/scouting

**Event:**

* Goblins **retaliate against Sandpoint within 1d4 days**
* **Pressure +2** from coordinated counterattack
* Defensive resources are strained


### Trigger: Runewell Mishandled

**Condition:** PCs disturb the Runewell carelessly (smash without understanding, fail knowledge check, overexpose to combat)

**Event:**

* Residual magic affects nearby areas (shadows move wrong, voices whisper)
* **Emotional instability in Sandpoint:** +1 Pressure, NPCs act irrationally for 2d4 days
* Magic persists until properly neutralized (not merely destroyed)


### Trigger: Thistletop Abandoned

**Condition:** PCs clear the stronghold but don't eliminate core threats (Runewell, Nualia, goblin leadership)

**Event:**

* Within **14-28 days** (off-screen), goblin coordination returns
* New goblin raids escalate into Book II
* Sandpoint must allocate defensive resources


## Cross-Book Echoes

Certain events create long-term consequences:

* Persistent Runewell disturbance
* Surviving antagonists
* Reduced Sandpoint resilience

These echoes must be reviewed at the end of the book and carried into the next book’s setup.
