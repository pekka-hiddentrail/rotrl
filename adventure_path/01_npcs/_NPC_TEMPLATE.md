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

<Voice, psychology, core wound or drive. 
Detail level scales with Tier:
  Tier I   — 4 sentences
  Tier II  — 4 sentences
  Tier III — 3 sentences
  Tier IV  — 3 sentences>

## Appearance

<Physical description. Detail level scales with Tier:
  Tier I   — 4 sentences
  Tier II  — 3 sentences
  Tier III — 2 sentences
  Tier IV  — 2 sentences>

## Location & Availability

- <where they are usually found>
- <when they are available or absent>

## GM Notes

- <Initial attitude toward unknown PCs>
- <What warms them — specific triggers or actions>
- <What cools or alienates them>
- <Voice, mannerism, or speech pattern to maintain>
- <What to emphasise or avoid in play>

## Social Checks

- **<Skill> (<context>):** DC <number> — <outcome>
  Checks that unlock a Secret should note it explicitly:
  e.g. DC 18 — unlocks: <secret name> (see Secrets)

## Secrets

<What this NPC knows but will not volunteer. Each secret states its
unlock condition — a check result, a trust threshold, or a specific trigger.
GM-only. Never narrated unprompted.>

- **<Secret name>:** <what they know> — *Unlocked by: <condition>*

## State Handling

- **If Cooperative:** <state change / likely behavior>
- **If Distrustful:** <state change / likely behavior>
- **If Killed:** <downstream world consequence>

<!-- REFERENCE -->

**Tier:** IV — Functional
**Role:** <occupation or social function>
**Flags:** SESSION NPC — auto-generated session_NNN

## Narrative Function

<Why this NPC exists in play: witness, gatekeeper, rumour source, etc.
Also absorbs any edge-case notes that don't fit the sections above.>
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
Came up through the smithing trade and has little patience for people who treat tools as decorations.

## Appearance

Broad-shouldered, with smoke-scented clothes and careful, deliberate hands. Singed sleeves he never
bothers replacing — occupational pride, not neglect.

## Location & Availability

- Usually found at his market stall during daylight.
- Closes early on high-crowd festival evenings.

## GM Notes

- Neutral and businesslike on first contact; does not warm quickly but stays professional.
- Opens up when approached with direct, craft-specific questions — treat him as an expert, not a vendor.
- Becomes cold if he senses he is being manipulated or rushed.
- Speaks in short, practical sentences. Never uses flattery. Respects the same in return.

## Social Checks

- **Diplomacy (ask about festival materials):** DC 10 — shares inventory details and recent unusual orders
- **Bluff (mislead him):** DC 12 — cynical; failure makes him immediately suspicious
- **Intimidate:** DC 14 — complies, then reports to Sheriff Hemlock within the hour
- **Craft (any):** DC 10 — demonstrating genuine craft knowledge unlocks Helpful attitude immediately

## Secrets

- **Suspicious order:** A man he didn't recognise pre-purchased a bulk firework order three days before
  the festival and never collected it. He assumed it was a no-show. — *Unlocked by: Diplomacy DC 14 or
  Knowledge (local) DC 12 establishing PCs are investigating the attack*

## State Handling

- **If Cooperative:** Shares inventory, unusual customer details, and local merchant-district rumours freely.
- **If Distrustful:** Refuses details, refers the party to Sheriff Hemlock, and mentions the encounter to
  his neighbours.
- **If Killed:** Merchant district tension rises sharply; guard inquiry opens immediately and PCs are
  persons of interest.

<!-- REFERENCE -->

**Tier:** IV — Functional
**Role:** Fireworks merchant
**Flags:** SESSION NPC — auto-generated session_001

## Narrative Function

Provides local information and commerce access tied to festival materials and suspicious firework activity.
The uncollected bulk order is a breadcrumb toward pre-planned sabotage if PCs think to ask.
```
