# Generated Session NPC File — Format Reference

This document defines the canonical format for generated NPC `base.md` files.

Generated NPC folders live under:

    adventure_path/05_npcs/<npc_slug>/

Typical contents:

    base.md         # canonical NPC profile (this template)
    session_NNN.md  # per-session status deltas (boot-cleaned)
    knowledge.md    # cumulative tagged knowledge

Session NPC folders (flagged with `SESSION NPC`) are deleted on boot unless manually promoted.

---

## Required Base Format

```
# <Canonical Name>

**Tier:** IV — Functional
**Role:** <occupation or social function>
**Flags:** SESSION NPC — auto-generated session_NNN
**Aliases:** <comma-separated aliases>
**Locations:** <comma-separated location keywords>

## Personality

<how they speak, react, and what drives them>

## Appearance

<short physical description>

## Narrative Function

<why this NPC exists in play: witness, gatekeeper, rumor source, etc.>

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
```

### Example

```
# Gorm Gulthyn

**Tier:** IV — Functional
**Role:** Fireworks merchant
**Flags:** SESSION NPC — auto-generated session_001
**Aliases:** gorm, gulthyn
**Locations:** market square, south market lane

## Personality

Brisk, practical, and protective of his inventory. Friendly once he believes someone respects his craft.

## Appearance

Broad-shouldered, smoke-scented, with singed sleeves and careful hands.

## Narrative Function

Provides local information and commerce access tied to festival materials and suspicious firework activity.

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

- **If Cooperative:** Shares useful inventory and local rumor details without resistance.
- **If Distrustful:** Refuses details and refers the party to Sheriff Hemlock.
- **If Killed:** Merchant district tension rises; guard inquiry opens immediately.
```

---

## Notes

- `# <Canonical Name>` must match the intended NPC identity; lookup and delta resolution rely on this.
- `**Aliases:**` should include natural player-facing references (first name, surname, title when relevant).
- `**Locations:**` should contain keywords players might actually say in prompts.
- Keep section headers and field labels exact so parser behavior remains stable.
- To promote a session NPC into permanent canon, remove `SESSION NPC` from the `**Flags:**` line.





