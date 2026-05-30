# EC-CIV-01 — Civilian Rescue

**Scene:** S4 — Goblin Assault: Festival Square  
**Type:** Opportunity beat (no roll required)  
**Active during:** Wave 1

---

## Situation

A family of three — two parents and a child — is pinned against a food cart at the north edge of the square. Two goblin warriors have broken off from the main assault and are closing in. The crowd surge has cut off their escape route.

The family does not fight back. If the goblins reach them unchallenged, one parent takes 4 HP damage (a dogslicer slash across the arm).

---

## Resolution

**PC intervenes (moves to interpose):** No roll required. The goblins shift to target the PC instead. The family flees during the distraction. Counts as one civilian saved.

**PC uses ranged attack or spell from range:** Kills or drives off one goblin. Remaining goblin continues to close. Family has one round to flee on their own (DC 10 run-out-of-the-way — assume success).

**Nobody acts:** Both goblins reach the family. One parent takes 4 HP damage. Family escapes on their own next round. Counts as one civilian harmed (mark on the casualty ledger).

---

## Aftermath Flag

If a PC intervened, mark: `CIVILIAN_RESCUE_BEAT = true`

This flag is checked by the `attack_repelled` event — if true, Aldern Foxglove seeks out the intervening PC specifically. If false, Aldern still appears but is less personalised in his gratitude.

---

<!-- REFERENCE -->

**Civilian rescue beat is also described in:** `adventure_path/02_events/goblin_attack_starts.md`  
**Aldern follow-up:** `adventure_path/02_events/attack_repelled.md`  
**NPC file:** `adventure_path/01_npcs/aldern_foxglove/base.md`
