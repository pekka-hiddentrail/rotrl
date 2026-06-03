# ACT_01 — FESTIVAL AND FIRE

> **Authority Level:** Adventure Act
> This file is an execution script for an AI GM. All constraints herein are binding unless overridden by higher-priority System Authority files.


## ACT IDENTIFICATION

* **Act ID:** BO-ACT-01
* **Adventure:** Rise of the Runelords – Book 1: Burnt Offerings
* **Chronological Position:** Opening Act


## ACT ROLE IN CAMPAIGN

This act establishes Sandpoint as the initial baseline settlement, introduces key civic NPCs as present authorities, and transitions the town from a NORMAL state into a temporary CRISIS state caused by an external attack. The act produces the first permanent town-state changes and PC reputation flags.

Forbidden in this act:

* Any explanation of goblin motives
* Any reference to runelords, Thassilon, or long-term threats
* Any implication that the attack is part of a larger plan


## START STATE (CANONICAL)

* **Location(s):** Sandpoint, Festival Square and adjacent streets
* **Time / Date:** Late morning, Swallowtail Festival
* **Environmental Conditions:** Clear weather, daylight
* **Faction / Town State:** NORMAL
* **PC Status Constraints:** Free movement, no active threats, no time pressure
* **Known Threats:** None

The AI GM MUST treat all above conditions as true until changed by scene outputs.


## SCENE FLOW CONTROL

* **Default Order:** Sequential
* **Reordering Allowed:** No
* **Parallel Scenes:** Forbidden

Scenes define context only. All uncertainty resolution occurs via encounters.


## SCENE INDEX

| Scene ID | Name                        | Entry Preconditions | Exit Conditions          | Event file |
| -------- | --------------------------- | ------------------- | ------------------------ | ---------- |
| S1       | Welcoming Ceremonies        | Act start           | Festival declared open   | `welcoming_speeches` |
| S2       | Festival Social Phase       | S1 complete         | Sun sets                 | `festival_social_phase` |
| S3       | Cathedral Alarm             | S2 complete         | Goblin attack begins     | `cathedral_alarm` |
| S4       | Goblin Assault — Square     | Town state = CRISIS | First wave defeated      | `goblin_attack_starts` → `first_wave_repelled` |
| S5       | Escalation — Fire & Cavalry | S4 complete         | No active goblin threats | `fire_phase_begins` → `second_wave_repelled` → `goblin_cavalry_attack_begins` |
| S6       | Aftermath & Brief Social    | S5 complete         | Town stabilized          | `attack_repelled` |


## SCENE DEFINITIONS

### SCENE S1 — WELCOMING CEREMONIES

**Preconditions:**

* Act start
* Town state = NORMAL

**Purpose:**

* Establish baseline normalcy and civic authority

**AI GM ALLOWED:**

* Sensory description of festival environment
* Formal speeches and ritual actions

**AI GM FORBIDDEN:**

* Foreshadowing danger
* Introducing unnamed officials or visitors

**NPCS PRESENT (EXHAUSTIVE):**

* Kendra Deverin
* Sheriff Hemlock
* Father Zantus

**LOCATIONS ACTIVE:**

* Festival Square

**EVENT FILE:**

* `welcoming_speeches` (02_events)

**ESCALATION RULES:**

* None

**EXIT CONDITIONS:**

* Swallowtails released

**STATE OUTPUTS:**

* PCs publicly identified as present


### SCENE S2 — FESTIVAL SOCIAL PHASE

**Preconditions:**

* Scene S1 exited

**Purpose:**

* Allow social encounters and goodwill accumulation

**AI GM ALLOWED:**

* Casual NPC interaction
* Food, games, informal conversation

**AI GM FORBIDDEN:**

* Introducing threats
* Advancing plot without an encounter trigger

**NPCS PRESENT (EXHAUSTIVE):**

* Kendra Deverin
* Sheriff Hemlock
* Father Zantus
* Aldern Foxglove
* Festival townsfolk (unnamed)

**LOCATIONS ACTIVE:**

* Festival Square
* Adjacent streets

**EVENT FILE:**

* `festival_social_phase` (02_events)

**ESCALATION RULES:**

* Cathedral ritual may begin at a natural lull

**EXIT CONDITIONS:**

* Cathedral consecration begins

**STATE OUTPUTS:**

* NPC attitude flags (if modified)
* Aldern familiarity flag (if encountered)


### SCENE S3 — CATHEDRAL CONSECRATION & ALARM

**Preconditions:**

* Scene S2 exited

**Purpose:**

* Transition from festival to crisis

**AI GM ALLOWED:**

* Ritual narration
* Sudden alarm interruption

**AI GM FORBIDDEN:**

* Explaining causes beyond immediate observation

**NPCS PRESENT (EXHAUSTIVE):**

* Father Zantus
* Festival attendees (unnamed)

**LOCATIONS ACTIVE:**

* Sandpoint Cathedral (interior and steps)

**EVENT FILE:**

* `cathedral_alarm` (02_events)

**ESCALATION RULES:**

* Alarm immediately unlocks Scene S4

**EXIT CONDITIONS:**

* Goblin attack audible or visible

**STATE OUTPUTS:**

* Town state NORMAL → CRISIS


### SCENE S4 — GOBLIN ASSAULT: FESTIVAL SQUARE

**Preconditions:**

* Scene S3 exited
* Town state = CRISIS

**Purpose:**

* Resolve initial goblin incursion and civilian danger

**AI GM ALLOWED:**

* Chaotic sensory narration
* Tactical descriptions limited to observed facts

**AI GM FORBIDDEN:**

* Strategic explanations
* Naming goblin leaders or motives

**NPCS PRESENT (EXHAUSTIVE):**

* Sheriff Hemlock
* Sandpoint guards (unnamed)
* Civilians (unnamed)

**LOCATIONS ACTIVE:**

* Festival Square

**EVENT FILES:**

* `goblin_attack_starts` → `first_wave_repelled` (02_events)

**ESCALATION RULES:**

* Successful resistance unlocks Scene S5

**EXIT CONDITIONS:**

* Initial goblin group neutralized

**STATE OUTPUTS:**

* Civilian harm markers set
* Damage markers created


## EVENT REFERENCES

All events are in `adventure_path/02_events/`. See `INDEX.md` in that folder for the full chain.

### Festival (pre-combat)

| Event file | Type | Resolution Outputs |
| ---------- | ---- | ------------------ |
| `welcoming_speeches` | social | PCs publicly present; NPC attitudes baseline |
| `festival_social_phase` | social | NPC goodwill flags; Aldern familiarity flag; Ameiko contact |
| `cathedral_alarm` | narrative | Town state NORMAL → CRISIS; early Perception check available |

### Goblin Raid

| Event file | Type | Resolution Outputs |
| ---------- | ---- | ------------------ |
| `goblin_attack_starts` | combat | First wave resolved; civilian rescue outcome; CIVILIAN_DEATHS flag |
| `first_wave_repelled` | social | Healing window; Zantus interaction |
| `fire_phase_begins` | combat | Second wave resolved; fire damage to square |
| `second_wave_repelled` | social | Hemlock arrival; Aldern visible at Well |
| `goblin_cavalry_attack_begins` | combat | Final wave resolved; Aldern rescue outcome |
| `attack_repelled` | aftermath | ALDERN_GRATITUDE, HEMLOCK_RESPECT, RUSTY_DRAGON_ROOMS flags; level 2 milestone |

### Conditional Events (still in encounters/)

| File | Trigger | Notes |
| ---- | ------- | ----- |
| `EC-INF-01` | Goblin captured alive | Interrogation scene; Thistletop hint gated behind DC 20 |


## INFORMATION DISCLOSURE RULES

* **Automatic Facts:** Goblins attacked Sandpoint; fire caused damage
* **Conditional Facts:** Extent of damage and casualties
* **Forbidden Knowledge:** Goblin motives, future attacks, named villains


## BRANCH CONSTRAINTS

* If PCs split: resolve encounters sequentially
* If PCs disengage: increase damage outputs
* If PCs flee Sandpoint: S3 resolves without PC intervention


## REQUIRED PERSISTENCE OUTPUTS

At act completion, the AI GM MUST write:

* Sandpoint damage summary
* NPC injury or death list
* PC public reputation flag
* Town state change log (NORMAL → CRISIS → ALERT)


## ACT TERMINATION CONDITIONS

This act ends ONLY when:

* Scene S4 exit conditions met
* No mandatory encounters unresolved
* Town state stabilized

The AI GM MUST NOT describe or imply subsequent acts.
