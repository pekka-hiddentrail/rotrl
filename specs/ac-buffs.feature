# AC Buffs — Tier S2-3 and beyond

Typed AC bonus effects from spells, abilities, and items.
Rules-agnostic: any effect with a typed AC bonus is handled by
`active_effects` + `_effective_ac`. No full AC decomposition needed —
`Combatant.ac` stays as the base total; effects layer on top.

Stacking rule (PF1e): bonuses of the same type do NOT stack.
`_apply_ac_effect` enforces this — same `bonus_type` replaces.
Different types always stack (exception: dodge, handled in future).

## Bonus type reference

| bonus_type | Stacks? | Example sources |
|------------|---------|-----------------|
| `shield` | No | Shield spell, physical shield (baked into base ac for items) |
| `deflection` | No | Protection from Evil, Ring of Protection |
| `natural` | No | Barkskin, amulet of natural armor |
| `armor` | No | Mage Armor (physical armor baked into base ac) |
| `dodge` | Yes* | Dodge feat, some spells — *requires stackable flag, defer |
| `luck` | No | Prayer, divine favor |
| `morale` | No | Bless, Heroism (applies to attacks/saves; same stacking rule) |
| `sacred` | No | Some divine spells |
| `profane` | No | Some necromantic spells |

Test IDs: SB-001 through SB-013

---

## Shield-type AC bonus (implemented — Tier S2-3)

### SB-001 — AC bonus parsed from effect text (any type)
Given a spell whose effect contains "+N <type> bonus to AC" (e.g. "+4 shield bonus to AC"
or "+2 deflection bonus to AC")
When `_build_pc_profiles` parses the character file
Then `buff_ac` equals N and `buff_type` equals the type word (e.g. "shield", "deflection")

Examples:
| Spell | Effect text | buff_ac | buff_type |
|-------|------------|---------|-----------|
| Shield (Yanyeeku) | "+4 shield bonus to AC" | 4 | "shield" |
| Shield of Faith (Ani) | "+2 deflection bonus to AC" | 2 | "deflection" |
| Protection from Evil (Ani) | "+2 deflection bonus to AC…" | 2 | "deflection" |

### SB-002 — Non-buff spell has buff_ac = 0
Given a damage or utility spell with no AC bonus in its effect
When `_build_pc_profiles` parses the file
Then `buff_ac` equals 0

### SB-003 — Self-buff path: no attack_request, no damage_request
Given a caster PC on their turn with a buff_ac > 0 spell
When the player declares the cast
Then `stream_pc_turn` emits neither `attack_request` nor `damage_request`

### SB-004 — Active effect added to caster's Combatant
Given a shield-type spell is cast
When `stream_pc_turn` resolves
Then the caster's `Combatant.active_effects` contains an entry with
`bonus_type="shield"`, `ac_bonus=4`, `rounds_remaining` set

### SB-005 — _effective_ac sums base AC and active effect bonuses
Given a Combatant with `ac=12` and one active effect with `ac_bonus=4`
When `_effective_ac` is called
Then the result is 16

### SB-006 — _effective_ac with no effects returns base AC
Given a Combatant with `ac=12` and no active effects
When `_effective_ac` is called
Then the result is 12

### SB-007 — combat_update emitted after buff applied
Given a shield spell is cast
When `stream_pc_turn` resolves
Then a `combat_update` SSE event is emitted carrying the updated state

### SB-008 — resolve_attack_roll uses effective AC (shield type)
Given a target has base `ac=12` and an active shield effect (+4)
When `resolve_attack_roll` is called with a roll of 15
Then the comparison is against effective AC 16, not base 12

### SB-009 — _resolve_npc_attack uses effective AC
Given a target has base `ac=12` and an active shield effect (+4)
When an enemy auto-resolves an attack
Then hit/miss is determined against effective AC 16

---

## Stacking rules (applies to all bonus types)

### SB-010 — Same bonus_type replaces, not stacks
Given a Combatant already has a shield-type effect with `ac_bonus=1`
When a new shield-type effect with `ac_bonus=4` is applied
Then only one shield-type effect remains (new replaces old)

### SB-011 — Different bonus types stack freely
Given a Combatant has a shield-type effect (+4) and a morale-type effect (+1)
When `_effective_ac` is called
Then the result is base + 4 + 1 (both apply)

---

## Effect expiry (applies to all bonus types)

### SB-012 — rounds_remaining decremented each turn
Given a Combatant has an active effect with `rounds_remaining=3`
When `advance_combat_turn` passes that combatant's turn
Then `rounds_remaining` decreases by 1

### SB-013 — _build_pc_turn_system buff briefing
Given `action_type=cast` and a spell with `buff_ac=4`
When `_build_pc_turn_system` is called
Then the system message mentions the spell name and AC bonus
And does NOT contain "auto-hit" or "1d20"

---

## Future — additional bonus types

### Deflection bonus (Tier S6)
Protection from Evil: +2 deflection to AC and +2 to saves.
Same `_apply_ac_effect` call with `bonus_type="deflection"`.
Requires `save_bonus` support alongside `ac_bonus` in the effect dict.

### Luck bonus (Tier S6)
Prayer and similar. `bonus_type="luck"`. No engine changes needed —
any string bonus_type is already supported by `_apply_ac_effect`.

### Natural armor bonus (SA-2)
Barkskin. `bonus_type="natural"`. Same engine. Only relevant once
we have bestiary data — monsters bake natural armor into base `ac`.

### Dodge bonus (Tier S6 / SA-7)
Dodge bonuses DO stack in PF1e — the only non-stacking exception.
`_apply_ac_effect` needs a `stackable: bool` flag per type before
this can be implemented safely. Add when the first dodge source lands.

### Touch AC / flat-footed AC split (S4 prerequisite)
Deflection and dodge apply to touch AC; armor and natural armor do not.
Implementing this correctly requires splitting `Combatant.ac` into
`ac_total`, `ac_touch`, `ac_flat_footed`. Needed before touch spells.

### Effect removal on dispel / dismiss (S6)
Dismissible spells (Shield, Protection from Evil) should be removable
by the caster as a move action. Add `dismissible: bool` to the effect
dict and a `POST /pc_action/dismiss` endpoint.
