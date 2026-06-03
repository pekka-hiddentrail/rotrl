**Event:** event_name_snake_case
**Type:** social | narrative | aftermath
**Trigger:** One sentence — what causes this event to activate

<!-- INJECT -->

---

<!--
  SOCIAL / NARRATIVE EVENT TEMPLATE
  ==================================
  Use this template for events with no active combat:
    social    — PCs interact with one or more NPCs; player choices shape the outcome
    narrative — GM delivers a scene; players can react but there is no meaningful NPC dialogue tree
    aftermath — post-combat scene with state changes and NPC reactions (may overlap with social)

  Key differences from the combat template:
    - No Zones table (unless zone matters for an NPC or object placement)
    - No Combatants or Tactics sections
    - Scene Setup replaces the zone/combatant block
    - NPCs Present replaces Appearance
    - Branching Outcomes replaces End Conditions (one branch per meaningful player choice)
    - Transitions always name the next %%EVENT%% to fire

  The <!-- INJECT --> comment is the LLM injection point.
  Everything above it is metadata (not injected). Everything below it IS injected.
-->

---

## Scene  [REQUIRED]

<!--
  2–4 sentences. Paint the environment: what the PCs see, hear, smell.
  Establish tone and urgency. Name who is present and where.
  This is the GM's opening narration before any player action.
-->

[Describe the setting, atmosphere, and who is present. Convey mood in concrete sensory detail — don't just state "the mood is tense."]

## Zone Context  [OPTIONAL — include only if zone placement matters]

<!--
  Use only when a specific zone or location is mechanically or narratively relevant
  (e.g., an NPC is in a specific zone; entering their zone triggers their reaction).
  Skip the full adjacency table unless the location has not appeared before.
-->

[NPC or object] is in the **[Zone Name]** zone. Any PC who approaches is also in [Zone Name].

## NPCs Present  [REQUIRED if any NPC has dialogue or a decision tree]

<!--
  One block per NPC. Include:
    - Where they are and what they are doing
    - What they offer or want without being prompted
    - How they react if a PC speaks to them
    - Any mechanical action they can take (healing, skill check, information)
    - One line of characteristic speech if useful
  Keep NPC voices distinct. Do not write full dialogue — write voice and intent.
-->

### [NPC Name] — [Location or Zone]

[One sentence of what the NPC is doing when the PCs arrive.]

**What they offer without being asked:** [Unprompted behavior or statement.]

**If a PC speaks to them:** [How they respond. What they reveal or offer.]

**[Mechanical action if any]:** [Spell cast / item given / skill check result. Include DC and outcome.]

**Their manner:** [One sentence on tone — warm, guarded, distracted, grieving, etc.]

## Player Options  [OPTIONAL — use when the option list is non-obvious]

<!--
  List the main things a PC can do in this scene. Not exhaustive — players can
  always do other things. This primes the GM on what the scene is designed to support.
  Keep each option to one line.
-->

- **[Option]:** [What happens if a PC does this.]
- **[Option]:** [What happens if a PC does this.]
- **[Option]:** [What happens if a PC does this — or what happens if no one does.]

## Branching Outcomes  [REQUIRED]

<!--
  One branch per meaningful player choice. Every branch must end with a transition —
  either %%EVENT%% next_event or a state flag.
  Branches should feel different in tone, not just in mechanics.
  Label them clearly (Branch A, Branch B, etc.).
-->

### Branch A — [Descriptive label, e.g. "PCs engage warmly"]

[What happens. What the NPC does or says in response. What the scene feels like.]

Transition: `%%EVENT%% next_event_name`

### Branch B — [Descriptive label, e.g. "PCs move on without engaging"]

[What happens. What changes in the scene. What the NPC does alone.]

Transition: `%%EVENT%% next_event_name`

### Branch C — [OPTIONAL — third significant outcome]

[As above.]

Transition: `%%EVENT%% next_event_name` or record `FLAG_NAME` in `%%DELTAS%%`

## Scene Constraints (Binding)  [REQUIRED]

<!--
  3–5 hard rules for the LLM.
  Cover: pacing (don't linger), information (don't reveal), tone (don't break).
  Social scenes often need a pacing constraint — name the maximum number of
  exchanges before the scene must end.
-->

- [Pacing rule — e.g. "Do not linger more than 2–3 exchanges; end when PCs disengage."]
- Do NOT [information to withhold].
- [NPC name] [behavioral constraint — e.g. "does not push, argue, or plead."]
- [Tone rule — e.g. "This is a moment of quiet; do not introduce new threats until the event ends."]

## End Condition  [REQUIRED]

<!--
  When does this event close? Be specific.
  Social scenes often end on player disengagement or a time limit.
  Name the next %%EVENT%% explicitly.
-->

Scene ends when [condition]. Write `%%EVENT%% next_event_name` to continue.

## State Changes  [OPTIONAL — use for aftermath-type events]

<!--
  Persistent facts to record in %%DELTAS%%.
  Use SCREAMING_SNAKE_CASE flag names.
-->

Record in `%%DELTAS%%`:

- [FLAG_NAME]: [value]
- [FLAG_NAME]: [value]
