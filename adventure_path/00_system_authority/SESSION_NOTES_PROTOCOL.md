# SESSION_NOTES_PROTOCOL.md

This document defines the mandatory rules and format for creating session notes. Session notes are **authoritative canon**. They exist to preserve game state, prevent hallucination, and ensure long-term consistency.

Session notes are not narrative summaries. They are a **verifiable log of facts**.


## 1. Authority and Purpose

Session notes:

* Are the single source of truth for past events.
* Override memory, summaries, and narrative recollection.
* Must be consulted before preparing or running the next session.

If something is not recorded in session notes, it is considered **not to have happened**.

When in doubt, record facts that may affect future decisions, consequences, or world state, even if their importance is not yet clear.


## 2. Fact-Only Rule

Session notes must contain **only facts established in play**.

Allowed:

* Explicit player actions and decisions.
* Mechanical outcomes (damage, death, conditions, success/failure).
* Information spoken aloud or otherwise revealed in-fiction.
* Time passage and resource usage.

Forbidden:

* Interpretation, speculation, or inference.
* NPC motivations unless explicitly stated in dialogue.
* Emotional tone, atmosphere, or thematic commentary.
* Foreshadowing or predictions.

If a fact cannot be verified from play, it must not be recorded.


## 3. Knowledge Separation

All information must be tagged as one of the following:

* **[PC-KNOWN]** – Player characters are aware of this information.
* **[GM-ONLY]** – Information known only to the GM.

Rules:

* GM-only information must never be treated as PC-known unless explicitly revealed later.
* Knowledge tags must not be changed retroactively.


## 4. NPC State Tracking

Every named NPC encountered must have an updated state entry.

NPC state tracking **must comply with** the rules defined in
**NPC Memory and Continuity**.

Each NPC entry may include only the following, and nothing else:

### Required Fields
- **Core State:** Alive / Dead / Missing / Removed
- **Last Confirmed Location**
- **Knowledge Gained During the Session** (facts only)

### Conditional Fields (record only if changed this session)
- **Relationship State:** Allied / Friendly / Neutral / Distrustful / Hostile
- **Psychological / Narrative State:** Obsessed, Corrupted, Traumatized, Resolute, etc.
  *(Only if explicitly demonstrated or stated on-screen)*

### Rules
- NPC state may change **only** as a result of:
  - On-screen actions
  - Explicit dialogue
  - Sustained off-screen pressure authorized by campaign rules
- If no state change occurs, the NPC’s prior state is implicitly preserved.
- Internal intentions, plans, emotional growth, or decay **must not** be inferred or recorded.
- NPCs do not evolve, scheme, or resolve arcs off-screen.

### Logging Requirement
- Any NPC state change recorded here **must** have a corresponding entry in
  **NPC_STATE_LOG_TEMPLATE.md**
- Session notes record **that a change occurred**, not the justification narrative.


## 5. Location and Environment State

Session notes must record:

* Locations entered.
* Rooms or areas explored.
* Objects interacted with.
* Changes to the environment (destroyed, sealed, looted).

Rules:

* Unvisited areas remain unknown.
* Untaken loot remains present.
* Untriggered traps remain armed.
* Cleared locations remain cleared unless repopulation is explicitly triggered later.


## 6. Timeline and Causality

Session notes must include:

* In-world date or relative time marker.
* Travel durations, rests, and downtime.
* Any triggered countdowns, rituals, or timed events.

Rules:

* Time advances only when recorded.
* Off-screen events occur only if authorized by campaign rules.


#TODO Hallucination danger - SESSION_NOTES_PROTOCOL.md is incomplete. Section 7 is cut off and doesn't specify:
- What mechanical state to snapshot (HP, spell slots, resources?)
- Format for snapshots
- How to handle mid-combat saves
- Where snapshots are stored

Must complete this section with explicit snapshot template.

## 7. Mechanical State Snapshot

At session end, record **ALL** character mechanical state:

### Character Status Block (REQUIRED)

For each PC at session end, record:

```
<PC NAME>
  HP: <current> / <max>
  AC: <total>
  Conditions: [list any active OR "None"]
  
  Daily Resources:
    - Spells per day: <used> / <max>
    - Special abilities: <status>
    - Consumable items: <list>
  
  Active Effects:
    - <Name>: <duration remaining>
    [OR "None"]
  
  Special Status:
    - Disease: [Yes/No]
    - Poison: [Yes/No]
    - Curse: [Yes/No]
    - Level drain: [Yes/No]
  
  Location: <specific location>
```

### Rules for Recording

* Record EXACT values, no approximation
* If uncertain, mark **[UNKNOWN]**
* No assumed healing between sessions
* Spell slots do not reset without explicit rest (8 hours uninterrupted)

[UNKNOWN] may be used only when a value is genuinely unresolved in play. UNKNOWN values must be resolved at the earliest possible opportunity and must not be silently replaced.


## 8. Prohibited Content (Anti-Hallucination)

Session notes must not include:

* Predictions or plans.
* Narrative embellishment.
* Thematic analysis.
* Hidden symbolism.
* “What this means” commentary.

Session notes record **what happened**, not what might happen.


## 9. Formatting Rules

* Bullet points only.
* No prose paragraphs.
* No metaphors or evocative language.
* Adjectives allowed only if mechanically relevant.
* Every entry must be falsifiable.


## 10. Handoff and Revision Rules

* Session notes must be completed before the next session begins.
* No retroactive additions are allowed.
* Clerical corrections must be explicitly marked as such.


## 11. File Location

The session note is written to - **.sessions(.sessions/)**
The filename is "[Date-time]-[running number]"


## Session Notes Self-Check Checklist (Silent)

Before finalizing session notes, confirm:

- [ ] Have I recorded all actions, outcomes, and revealed information that occurred in play?
- [ ] Are all entries factual, verifiable, and free of interpretation?
- [ ] Is every informational entry tagged [PC-KNOWN] or [GM-ONLY]?
- [ ] Have I updated the state of every named NPC encountered?
- [ ] Are all visited locations and environmental changes recorded?
- [ ] Have I logged all time passage, rests, and travel explicitly?
- [ ] Is the mechanical snapshot complete for every PC?
- [ ] Are HP, resources, conditions, and effects recorded exactly?
- [ ] Have I avoided assuming healing, resets, or recovery?
- [ ] Does the notes file allow a future GM to resume play without guessing?

If any item cannot be confirmed, pause and correct before saving.


# SESSION NOTES TEMPLATE

```
SESSION: <number>
BOOK / ACT:
IN-WORLD DATE / TIME:
SESSION DURATION:

---

PC STATUS (END OF SESSION)
- <PC Name>: HP <value>, Conditions <list or none>, Resources <notes>

---

TIMELINE
- <Relative or absolute time marker>: <event>

---

LOCATIONS VISITED
- <Location name>
  - Areas explored:
  - Changes:

---

NPCS ENCOUNTERED
- <NPC Name> [PC-KNOWN / GM-ONLY]
  - Status:
  - Location:
  - Knowledge gained:
  - Relationship change (if any):

---

EVENTS (FACTUAL)
- <Action or outcome>

---

COMBAT SUMMARY (IF ANY)
- Encounter location:
- Participants:
- Outcome:
- Deaths:

---

ITEMS AND LOOT
- Gained:
- Lost:
- Left behind:

---

ONGOING EFFECTS / OPEN THREADS
- <Effect, threat, or timer>

---

GM-ONLY NOTES
- <Information not known to PCs>

```
