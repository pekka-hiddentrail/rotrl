# Magic Spell System — Tier S1 + S2-1

Spec for spell recognition and auto-hit damage spell resolution.
Rules-agnostic: any PC with a `spells` list in their character JSON
gets the full spell system automatically.

Test IDs: SS-001 through SS-014

---

## Tier S1 — Spell Recognition

### SS-001 — Spell profile parsing: auto-hit detection
Given a character JSON with a spell whose effect contains "never misses"
When `_build_pc_profiles` parses the file
Then that spell's `auto_hit` field is `True`

### SS-002 — Spell profile parsing: damage expression extraction
Given a character JSON with a spell effect containing a dice expression (e.g. "1d4+1")
When `_build_pc_profiles` parses the file
Then `damage_expr` equals that dice expression

### SS-003 — Spell profile parsing: non-damage spell
Given a character JSON with a buff spell (e.g. Shield) with no dice in its effect
When `_build_pc_profiles` parses the file
Then `damage_expr` is empty and `auto_hit` is False

### SS-004 — Intent extraction: spell name match
Given a caster PC is the active combatant
When the player types "I cast Force Bolt at the skeleton"
Then `_extract_pc_combat_intent` returns `action_type=cast` and `spell_name=Force Bolt`

### SS-005 — Intent extraction: partial name with cast keyword
Given a caster PC is the active combatant
When the player types "I cast bolt at the goblin"
Then the spell is matched via partial word overlap against the spell list

### SS-006 — Intent extraction: spell name without cast keyword
Given a caster PC is the active combatant
When the player types "Force Bolt the skeleton" (no "cast")
Then the spell is still detected and `action_type=cast`

### SS-007 — Intent extraction: target resolution
Given the player names an active enemy in their input
When `_extract_pc_combat_intent` runs
Then `target` equals that enemy's name

### SS-008 — Intent extraction: spell takes priority over weapon
Given a caster PC whose input contains a spell name
When `_extract_pc_combat_intent` runs
Then `action_type=cast` even if weapon keywords are also present

---

## Tier S2-1 — Auto-hit Damage Spell Resolution

### SS-009 — damage_request emitted, not attack_request
Given a caster PC on their turn with an auto-hit damage spell
When the player declares the cast
Then `stream_pc_turn` emits `damage_request` (not `attack_request`)

### SS-010 — damage_request fields
Given `stream_pc_turn` emits `damage_request`
Then the event contains `spell_name`, `caster`, `target`, `damage_expr`

### SS-011 — PendingAttack pre-hit for auto-hit spells
Given `stream_pc_turn` runs for an auto-hit spell
Then a PendingAttack is queued with `hit=True`, `is_spell=True`, `spell_name` set

### SS-012 — HP delta applied on damage roll
Given a PendingAttack for an auto-hit spell (hit=True pre-set)
When `resolve_damage_roll` is called with rolls and total
Then the target's HP is reduced by `total`

### SS-013 — Damage result carries spell metadata
Given `resolve_damage_roll` resolves a spell attack
Then the result dict has `is_spell=True`, `spell_name`, and `attack_type="spell"`

### SS-014 — Spell briefing in _build_pc_turn_system
Given `action_type=cast` in the intent dict
When `_build_pc_turn_system` runs
Then the system message contains the spell name, "auto-hit", and the damage value
And does NOT contain "1d20" or "vs AC"

---

## Out of scope (future tiers)

- Spell slot tracking (S3)
- Touch spells with touch AC (S4)
- Save-based spells (S5)
- Buff / duration spells (S6)
- Spell resistance checks (S7)
- Spell dictionary files and SpellIndex (S1-1, S1-2)
