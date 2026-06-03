**Event:** first_wave_repelled
**Type:** social
**Trigger:** All goblins from the first wave are dead or fled

<!-- INJECT -->

## Scene

The square is suddenly quiet except for sobbing, barking dogs, and the distant crackle of a smoldering stall. Festival-goers are streaming toward the Cathedral of Desna. Father Zantus stands at the top of the Cathedral Stairs, arms spread wide, calling civilians by name, pressing them toward the doors. He is the last one outside.

The PCs have a brief window — perhaps a minute — before the next wave arrives.

## Zones

Zone context is unchanged from the first wave. Father Zantus is in the **Cathedral Stairs** zone. Any PC who approaches him is also in Cathedral Stairs.

## NPCs Present

### Father Zantus — Cathedral Stairs

Zantus is composed but moving urgently. His white festival robes have a smear of blood across the sleeve — not his own. He notices the PCs immediately and makes eye contact as he ushers the last civilian through the doors.

**What he offers without being asked:**
- A brief, sincere word of acknowledgment: *"Desna's hand was on you tonight. I saw."*
- He will not leave until the PCs either enter the cathedral or make clear they are staying to fight.

**If a PC speaks to him or approaches:**
Zantus pauses and gives them his full attention. He looks each PC over once, assessing injuries. If any PC is visibly wounded (below half HP), he says: *"You're hurt. Let me help — I have one good prayer left in me tonight."*

**Healing — Cure Moderate Wounds:**
Zantus can cast CMW once per wounded PC who accepts. He will not cast it on a PC who declines or who is not wounded.
- Heals 2d8+4 hp
- Requires the PC to be in Cathedral Stairs zone (already adjacent to him)
- Casting takes one round per PC — this matters for the transition below

**His manner:**
Warm, unhurried even when urgent. He does not demand or plead — he simply makes the offer and waits. He will not argue with a PC who refuses healing and chooses to push forward.

## Branching Outcomes

### Branch A — PCs ask for (or accept) healing

Zantus heals each wounded PC who accepts, one per round. When the last healing is complete:

- He presses his hand briefly to the doorframe, murmurs a quiet prayer, then steps inside and pulls the cathedral doors shut with a heavy thud.
- The square is empty. Then — from the Alleyway — the sound of something moving.

Transition: fire the next combat event (`%%EVENT%% fire_phase_begins`).

### Branch B — PCs do not approach or explicitly decline

Zantus waits a moment longer than necessary, watching the PCs with quiet concern. Then he steps inside and pulls the doors shut. No words — just the sound of the heavy bolt sliding home.

Transition: fire the next combat event immediately (`%%EVENT%% fire_phase_begins`).

## Scene Constraints (Binding)

- This is a breath — 60 seconds of quiet between violence. Narrate the aftermath before any new threats: overturned carts, scattered festival ribbons, a child's shoe in the middle of the square
- Zantus does not know another wave is coming; he is not withholding information
- Do NOT have Zantus comment on the goblins' motives or origin
- Do NOT linger here more than 2–3 exchanges; the scene ends when the PCs stop engaging or healing is done

## End Condition

Scene ends when the PCs are done speaking with Zantus, healing is complete, or the PCs move away. Write `%%EVENT%% fire_phase_begins` to start the next wave.
