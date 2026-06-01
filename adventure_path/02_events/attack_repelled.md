**Event:** attack_repelled
**Type:** aftermath
**Trigger:** When all three waves are suppressed and no active goblin threats remain in the square
**Expires:** 5 turns

<!-- INJECT -->

## Active Event — Raid Aftermath

The goblin attack is over. Town state transitions: CRISIS → ALERT.

### Immediate scene (same evening)
- Hemlock thanks PCs publicly — brief, plainspoken
- Father Zantus tends wounded at the cathedral steps
- Ameiko Kaijitsu offers the PCs rooms at the Rusty Dragon, free, indefinitely
- 2–4 townsfolk approach PCs with thanks or small gifts

### Aldern Foxglove
If the rescue beat fired during Wave 1, Aldern approaches now (if not already). He is quietly, sincerely grateful. He offers dinner at the Rusty Dragon and, if the PC engages warmly, a hunting trip in the Tickwood the following day.

### State changes to record in %%DELTAS%%
- Town state: CRISIS → ALERT
- PC reputation flag: DEFENDER (or HERO if no civilian deaths)
- Civilian death count (0 = PCs active; 1–2 = PCs passive; 3+ = PCs disengaged)
- If a goblin was captured: note GOBLIN_CAPTIVE — interrogation available

### What remains forbidden
- Goblin motives or coordination
- Thistletop name (only available if a captured goblin is interrogated)
- Any reference to a larger plan

### Level milestone
PCs reach level 2 after this scene. Award at first natural rest.

### REQUIRED — Combat tracker
Combat is over. Write a `%%COMBAT%%` block with `round: 0` to clear the combat panel.
