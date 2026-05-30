# Generated Session NPC File — Format Reference

This document defines the canonical format for NPC `base.md` files.

NPC folders live under:

    adventure_path/01_npcs/<npc_slug>/

Typical contents:

    base.md         # canonical NPC profile (this template)
    session_NNN.md  # per-session status deltas (boot-cleaned)
    knowledge.md    # cumulative tagged knowledge

Session NPC folders (flagged with `SESSION NPC`) are deleted on boot unless manually promoted.

---

## Base Format

Everything above `<!-- REFERENCE -->` is the **GM payload** — injected into every turn where this NPC is active.
Everything below is **reader documentation** — never sent to the model.

```
# <Canonical Name>

**Aliases:** <comma-separated aliases>
**Locations:** <comma-separated location keywords>

## Personality

<how they speak, react, and what drives them>

## Appearance

<short physical description — omit if unknown>

## Location & Availability

- <where they are usually found>
- <when they are available or absent>

## Reaction to PCs

<default stance toward unknown adventurers>

## Social Checks

- **Diplomacy:** DC <number> for cooperation
- **Bluff:** DC <number> to deceive
- **Intimidate:** DC <number> to coerce

## State Handling

- **If Cooperative:** <state change / likely behavior>
- **If Distrustful:** <state change / likely behavior>
- **If Killed:** <downstream world consequence>

<!-- REFERENCE -->

**Tier:** IV — Functional
**Role:** <occupation or social function>
**Flags:** SESSION NPC — auto-generated session_NNN

## Narrative Function

<why this NPC exists in play: witness, gatekeeper, rumour source, etc.>
```

---

## Notes

- `# <Canonical Name>` must match the intended NPC identity exactly; lookup and delta resolution rely on this.
- `**Aliases:**` should include natural player-facing references (first name, surname, title when relevant).
- `**Locations:**` should contain keywords players might actually say in input.
- Everything above `<!-- REFERENCE -->` must be self-contained — the model never sees what is below the line.
- Keep section headers and field labels exact so parser behavior remains stable.
- To promote a session NPC into permanent canon, remove `SESSION NPC` from the `**Flags:**` line below `<!-- REFERENCE -->`.

---

## Example

```
# Gorm Gulthyn

**Aliases:** gorm, gulthyn
**Locations:** market square, south market lane

## Personality

Brisk, practical, and protective of his inventory. Friendly once he believes someone respects his craft.

## Appearance

Broad-shouldered, smoke-scented, with singed sleeves and careful hands.

## Location & Availability

- Usually found at his market stall during daylight.
- Closes early on high-crowd festival evenings.

## Reaction to PCs

Neutral and businesslike at first; becomes cooperative if approached directly and respectfully.

## Social Checks

- **Diplomacy:** DC 10 for cooperation
- **Bluff:** DC 12 to deceive
- **Intimidate:** DC 14 to coerce

## State Handling

- **If Cooperative:** Shares useful inventory and local rumour details without resistance.
- **If Distrustful:** Refuses details and refers the party to Sheriff Hemlock.
- **If Killed:** Merchant district tension rises; guard inquiry opens immediately.

<!-- REFERENCE -->

**Tier:** IV — Functional
**Role:** Fireworks merchant
**Flags:** SESSION NPC — auto-generated session_001

## Narrative Function

Provides local information and commerce access tied to festival materials and suspicious firework activity.
```
