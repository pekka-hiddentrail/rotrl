# Festival Encounter — Consolidated Reference

Act 01, Scenes S3–S6. This document summarises the complete goblin raid sequence for the human GM. The LLM receives this content through event file injection, not this document.

---

## Three-Wave Raid Sequence

### Wave 1 — Initial Assault (goblin_attack_starts)

**Trigger:** Cathedral alarm bell / party perception check reveals goblins at the north gate.

**Combatants:**
- 4–6 goblin warriors (AC 16, HP 5, dogslicer +2, shortbow +4)
- 1 goblin warchanter (AC 14, HP 8, shortbow +5, Inspire Courage +1 while singing)

**Priority target:** Warchanter. Silencing her collapses Wave 1 morale.  
**Civilian beat:** Two goblins break off to attack a trapped family at a food cart. A PC who moves to intercept saves them with no roll. See EC-CIV-01.

**Wave ends when:** Warchanter killed or flees.

---

### Wave 2 — Fire Phase (fire_phase_begins)

**Trigger:** Wave 1 ends. Goblin arsonists appear on rooftops.

**Combatants:**
- 3–4 rooftop goblins (AC 20 with cover, HP 5, throwing torches)
- 2–3 alley goblins (AC 16, HP 5, blocking south exit)

**Fire mechanics:** 1d4 structures catch fire round 1. Adjacent creatures take 1 fire damage/round. Scaffolding collapses round 4 (Reflex DC 12 or 1d6). Extinguish at the well (30 ft west, full-round action per hazard).

**Sheriff Hemlock arrives this wave** with 4 militia. He handles civilians and crossbow fire at rooftops; he does not take PC kills.

**Wave ends when:** Rooftop goblins silenced and immediate fire threat addressed.

---

### Wave 3 — Goblin Cavalry (cavalry_arrives)

**Trigger:** Wave 2 ends. Three goblin commandos on goblin dogs burst in from the north gate.

**Combatants:**
- 3 goblin commandos (AC 17, HP 9/11 raging, mwk horsechopper +2/+4, Mounted Combat)
- 3 goblin dogs (AC 13, HP 14, bite +3 plus Goblin Pox Fort DC 12 or 1d3 Dex)

**Tactics:** Charge-and-scatter, grab loot, do not hold ground. Flee if mount killed or 2+ commandos fall.

**Wave ends when:** All commandos routed or killed.

---

## Aldern Foxglove Rescue Moment

Aldern is present during Wave 1 — he is near the food stalls when the goblins arrive, and he freezes rather than fighting. If a PC moves toward the trapped family (EC-CIV-01), Aldern is in the vicinity. He does not fight; he gets out of the way and watches the PC act.

After the attack (attack_repelled event), Aldern approaches the PC who was most visible as a hero. His gratitude is sincere. He offers:
1. Dinner at the Rusty Dragon tonight
2. A hunting trip in the Tickwood the following day

If the rescue beat did not fire (CIVILIAN_RESCUE_BEAT = false), Aldern still approaches but is less personalised — he thanks PCs as a group.

---

## Hemlock Arrival Timing

| Wave | Hemlock State |
|------|--------------|
| Wave 1 | 60 ft away, closing. Engages warriors. Does not target warchanter. |
| Wave 2 | Arrives with 4 militia. Handles crowd control and rooftop crossbow fire. |
| Wave 3 | Present and active. Engages one commando. Leaves killing blow to PCs. |
| Aftermath | Thanks PCs publicly. Plainspoken, brief. Asks if PCs will be in town — implies he may need help with the investigation. |

---

## Aftermath State Changes (attack_repelled)

| State | Change |
|-------|--------|
| Town state | CRISIS → ALERT |
| PC reputation | DEFENDER (or HERO if zero civilian deaths) |
| Civilian deaths | 0 = PCs active; 1–2 = PCs passive; 3+ = PCs disengaged |
| Goblin captive | Mark GOBLIN_CAPTIVE if one was taken alive (see EC-INF-01) |
| Level milestone | PCs reach Level 2 at first rest |

**Ameiko Kaijitsu** offers the PCs free rooms at the Rusty Dragon indefinitely.  
**2–4 townsfolk** approach with thanks or small gifts (1d4 gp each, at GM discretion).  
**Father Zantus** tends wounded at the cathedral steps. He does not have significant dialogue here.

---

## Event File Cross-Reference

| Event ID | File | Content |
|----------|------|---------|
| goblin_attack_starts | `adventure_path/02_events/goblin_attack_starts.md` | Wave 1 stats, civilian rescue beat, warchanter priority |
| fire_phase_begins | `adventure_path/02_events/fire_phase_begins.md` | Wave 2 stats, fire mechanics, Hemlock arrival |
| cavalry_arrives | `adventure_path/02_events/cavalry_arrives.md` | Wave 3 stats, commando tactics, morale |
| attack_repelled | `adventure_path/02_events/attack_repelled.md` | Aftermath beats, Aldern, Ameiko offer, level milestone |

---

## Encounter File Cross-Reference

| ID | Name | Status |
|----|------|--------|
| EC-COM-01 | Wave 1: Initial Goblin Assault | Written |
| EC-COM-02 | Wave 2: Fire Phase | Written |
| EC-COM-03 | Wave 3: Goblin Cavalry | Written |
| EC-CIV-01 | Civilian Rescue Beat | Written |
| EC-INF-01 | Goblin Capture and Interrogation | Written |
| EC-EVT-01 | Release of Swallowtails | Written |
| EC-EVT-02 | Cathedral Consecration and Alarm | Written |
| EC-SOC-01 | Welcoming Speeches | Written |
| EC-SOC-02 | Festival Games and Food | Written |
| EC-SOC-03 | Casual NPC Interaction | Written |
| EC-SOC-04 | Aldern Foxglove Brief Social | Written |
| EC-SUP-01 | Aid the Wounded | Written |
