# Healing Spells — Tier S2-4

Positive-energy healing spells (Cure Light Wounds, Cure Moderate Wounds, etc.).
Targets PC allies or self. Auto-hit for willing living targets.
Rolls healing dice; applies positive HP delta. Harms undead (future).

Rules-agnostic: any spell with "Heals Xd8+Y" in its effect text is
handled by the heal path automatically.

Test IDs: HL-001 through HL-012

---

## HL-001 — Healing expression parsed from effect text
Given a spell whose effect contains "Heals 1d8+1 hit points"
When `_build_pc_profiles` parses the character file
Then `healing_expr` equals "1d8+1" and `is_heal` is True

## HL-002 — Non-healing spell has empty healing_expr
Given a damage or buff spell with no healing in its effect
When `_build_pc_profiles` parses the file
Then `healing_expr` is "" and `is_heal` is False

## HL-003 — CLW recognised by spell name
Given Ani is the active combatant and has Cure Light Wounds in her spell list
When the player types "I cast cure light wounds on Vanx"
Then `_extract_pc_combat_intent` returns `action_type=cast`, `spell_name=Cure Light Wounds`

## HL-004 — heal_request emitted, not attack_request or damage_request
Given a PC casts a healing spell
When `stream_pc_turn` resolves
Then it emits `heal_request` SSE with `spell_name`, `caster`, `target`, `damage_expr`
And emits neither `attack_request` nor `damage_request`

## HL-005 — PC ally is a valid heal target
Given the player says "I cast cure light wounds on Vanx"
When spell intent is extracted
Then `target` is "Vanx" (a PC, not an enemy)

## HL-006 — Unconscious PC is a valid heal target
Given a PC has status="unconscious"
When a heal spell is cast with that PC's name in the input
Then that PC is the resolved target

## HL-007 — Most wounded PC targeted when no name given
Given multiple PCs with different HP percentages
When a heal spell is cast without naming a target
Then the PC with the lowest HP ratio is selected as target

## HL-008 — resolve_damage_roll applies positive HP delta for heal
Given a PendingAttack with is_heal=True and target with hp=3/11
When resolve_damage_roll is called with total=6
Then target hp_current becomes 9

## HL-009 — HP capped at hp_max after healing
Given a target with hp=10/11
When resolve_damage_roll is called with total=6
Then target hp_current is 11 (not 16)

## HL-010 — Healed combatant status restored to active
Given a target with status="unconscious" (hp=0)
When resolve_damage_roll is called with total=6 and is_heal=True
Then target hp_current becomes 6 and status becomes "active"

## HL-011 — Damage result carries is_heal flag
Given resolve_damage_roll resolves a heal attack
Then result dict has is_heal=True and damage_total=healing_amount

## HL-012 — _build_pc_turn_system healing briefing
Given action_type=cast and a spell with is_heal=True
When _build_pc_turn_system is called with a heal result
Then the system message mentions the spell name and healed amount
And does NOT contain "auto-hit" or "damage" or "1d20"

---

## Out of scope (future tiers)

- Undead take damage from positive energy (requires creature type tagging)
- Channel energy (Warpriest class feature — heals all allies in zone)
- Spontaneous casting (Cleric trading slots for CLW)
- Heal spells during enemy turns (readied actions / out-of-turn healing)
