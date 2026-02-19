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

| Scene ID | Name                        | Entry Preconditions | Exit Conditions          |
| -------- | --------------------------- | ------------------- | ------------------------ |
| S1       | Welcoming Ceremonies        | Act start           | Swallowtails released    |
| S2       | Festival Social Phase       | S1 complete         | Cathedral alarm          |
| S3       | Cathedral Alarm             | S2 complete         | Goblin attack begins     |
| S4       | Goblin Assault — Square     | Town state = CRISIS | Initial goblins defeated |
| S5       | Escalation — Fire & Cavalry | S4 complete         | No active goblin threats |
| S6       | Aftermath & Brief Social    | S5 complete         | Town stabilized          |


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

**ALLOWED ENCOUNTERS:**

* EC-SOCIAL-01 Welcoming Speeches
* EC-SOCIAL-05 Release of Swallowtails

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

**ALLOWED ENCOUNTERS:**

* EC-SOCIAL-02 Festival Games & Food
* EC-SOCIAL-03 Casual NPC Interaction
* EC-SOCIAL-04 Aldern Foxglove Brief Social

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

**ALLOWED ENCOUNTERS:**

* EC-EVT-02 Cathedral Consecration & Alarm

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

**ALLOWED ENCOUNTERS:**

* EC-COMBAT-01 Goblins in the Square
* EC-SUPPORT-01 Civilian Rescue

**ESCALATION RULES:**

* Successful resistance unlocks Scene S5

**EXIT CONDITIONS:**

* Initial goblin group neutralized

**STATE OUTPUTS:**

* Civilian harm markers set
* Damage markers created


## ENCOUNTER REFERENCES

### SOCIAL ENCOUNTERS

| Encounter ID | Name                           | Scope      | Resolution Outputs                                       |
| ------------ | ------------------------------ | ---------- | -------------------------------------------------------- |
| EC-SOCIAL-01 | Welcoming Speeches             | Public     | PCs publicly visible; civic authority established        |
| EC-SOCIAL-02 | Festival Games & Food          | Public     | NPC goodwill flags; minor rewards possible               |
| EC-SOCIAL-03 | Casual NPC Interaction         | Individual | Relationship flags set                                   |
| EC-SOCIAL-04 | Aldern Foxglove Brief Social   | Individual | Aldern familiarity flag; obsession seed (no explanation) |
| EC-SOCIAL-05 | Release of Swallowtails        | Public     | Festival climax completed                                |
| EC-SOCIAL-06 | Cathedral Consecration & Alarm | Town       | Town state NORMAL → CRISIS                               |


### COMBAT ENCOUNTERS

| Encounter ID | Name                  | Scope | Resolution Outputs                                    |
| ------------ | --------------------- | ----- | ----------------------------------------------------- |
| EC-COMBAT-01 | Goblins in the Square | Local | Initial goblin threat reduced; civilian danger active |
| EC-COMBAT-02 | Goblin Pyros          | Local | Fire hazards created; escalating property damage      |
| EC-COMBAT-03 | Goblin Cavalry        | Local | Final hostile wave resolved                           |

### SUPPORT ENCOUNTERS

| Encounter ID  | Name                           | Scope       | Resolution Outputs               |
| ------------- | ------------------------------ | ----------- | -------------------------------- |
| EC-SUPPORT-01 | Civilian Rescue                | Local       | Casualties prevented or incurred |
| EC-SUPPORT-02 | Goblin Capture & Interrogation | Conditional | Limited factual information only |
| EC-SUPPORT-03 | Aid the Wounded                | Town        | Injury and death ledger updated  |


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
