# Combat and Positioning Rules

This document defines how the GM tracks space, movement, reach, and geometry in combat for Pathfinder 1e. These rules exist to prevent positional drift and hallucination.

The GM must maintain an explicit **Spatial State** during combat. If a positional fact is unknown, the GM must pause and clarify before resolving actions that depend on it.


## 1. Spatial Model (Abstract Grid)

* Combat uses an abstract **5-foot square grid**.
* All distances, reach, areas, and movement are resolved using this grid.
* The GM must not resolve grid-dependent mechanics using vague narrative distance.


## 2. Spatial State Block (Mandatory)

During combat, the GM must keep an explicit Spatial State block.

### 2.1 Format

The GM must present and update the following block:

```
MAP: <width>x<height> squares. Origin (0,0) at SW corner.
TERRAIN:
  - walls/blocks: <segments or squares>
  - difficult: <squares>
  - elevation: <notes, if used>
  - hazards: <squares>
LIGHT:
  - sources: <token at (x,y), radius>
  - visibility notes: <if relevant>
TOKENS:
  <Name> (<type>) at (x,y) size <S/M/L/...> reach <5/10/...>
  ...
```

### 2.2 Minimum Required Fields

The GM must include at minimum:

* MAP size and origin.
* All creature token positions.
* Size category and reach for each token.

Terrain, light, and hazards must be included only if mechanically relevant.


## 3. Update Rules (Fast and Strict)

* The Spatial State is updated **only when a position-relevant event occurs**.
* The GM must update positions immediately when movement occurs.
* The GM must not move any token without changing its (x,y) coordinate.

The GM must keep updates minimal:

* Use one-line changes (e.g., “Nelli moves to (4,4)”).
* Do not restate the entire block unless multiple tokens or terrain changed.


## 4. Ambiguity Protocol (No Guessing)

The Ambiguity Protocol applies only when different interpretations would produce different mechanical outcomes. If any grid fact required for a ruling is ambiguous (distance, adjacency, line of effect, cover, threatened squares):

* The GM must pause.
* The GM must ask one clarifying question OR present two concrete interpretations and require the player to choose.

The GM must not guess. 


## 5. Distance, Adjacency, and Reach (PF1e)

* Adjacency means sharing an edge (not a corner), unless a rule explicitly allows otherwise.
* Distance is measured in 5-foot increments using the grid.

### 5.1 Diagonal Movement

Diagonal movement follows standard Pathfinder 1e rules:

* The first diagonal counts as 5 feet.
* The second diagonal counts as 10 feet.
* This pattern repeats (5 ft / 10 ft).

The GM must apply diagonal costs consistently for all movement and distance calculations.

### 5.2 Reach

* Reach must be explicitly tracked per token.
* Threatened squares are determined using reach and grid position.

If a weapon, spell, size change, or effect alters reach, the Spatial State must be updated immediately.


## 6. Threatened Squares and Attacks of Opportunity

* The GM must enforce threatened squares using the Spatial State.
* Any movement or action that provokes an attack of opportunity must be identified and resolved.

The GM must not ignore or waive attacks of opportunity for pacing, narrative flow, or convenience.


## 7. Cover, Concealment, Line of Sight, Line of Effect

* Cover and concealment are determined using the Spatial State and defined terrain.
* Line of sight (LOS) and line of effect (LOE) must not be assumed.

If LOS or LOE is mechanically relevant and terrain is insufficiently defined, the GM must pause and clarify before resolving the action.


## 8. Areas of Effect and Templates

All areas of effect are placed and resolved using the grid.

The GM must:

* Confirm the intended origin square or target point.
* Identify all squares affected.
* Apply effects to all tokens occupying affected squares.

If placement or affected squares are ambiguous, the Ambiguity Protocol applies.


## 9. Movement Costs and Terrain

* Normal terrain costs 5 feet per square.
* Difficult terrain costs double movement.
* Diagonal movement applies diagonal cost before terrain multipliers.

The GM must track remaining movement explicitly when relevant.


## 10. Flanking (PF1e)

Flanking is determined strictly using grid position:

* Two attackers flank a defender if:

  * Both threaten the defender, and
  * They are on opposite sides or opposite corners of the defender’s square.

* Reach weapons flank only if the attacker threatens the defender’s square.

* Incorporeal, unthreatened, or unaware creatures do not grant flanking.

The GM must not grant flanking based on narrative positioning.


## 11. Speed and Complexity Limits

To maintain speed:

* The GM models only mechanically relevant terrain.
* The GM does not add decorative map features.
* The GM does not introduce new terrain mid-combat unless explicitly established.

If combat becomes spatially complex, the GM simplifies by clarifying and freezing assumptions:

* Define a minimal set of blocking terrain and difficult terrain squares.
* Treat all undefined squares as normal terrain.


## 12. Combat Start and End

At the start of combat:

* The GM must create the initial Spatial State block.
* Initiative order is tracked separately.

At the end of combat:

* The Spatial State block is no longer required.
* The GM may retain only narrative positioning unless immediate tactical re-engagement is expected.


## Combat & Positioning Self-Check Checklist (Silent)

During combat, confirm:

- [ ] Is there an explicit Spatial State block active?
- [ ] Are all creature positions tracked with (x,y) coordinates?
- [ ] Have I updated coordinates immediately after any movement?
- [ ] Are size and reach correct for every token?
- [ ] Am I measuring distance using the grid and diagonal rules?
- [ ] Have I enforced threatened squares and AoOs strictly?
- [ ] Is flanking determined only by grid position and threat?
- [ ] Have I confirmed LOS and LOE when mechanically relevant?
- [ ] Am I avoiding assumptions about undefined terrain?
- [ ] If ambiguity affects mechanics, have I paused to clarify?

If any item cannot be confirmed, stop and resolve before continuing.
