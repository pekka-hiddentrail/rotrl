# Magic System Backlog

All spell and magic-related work lives here. [TODO.md](TODO.md) links here.

**Same markup rules as TODO.md apply.**

- `- [ ] Item text` — open task
- `- [x] Item text` — completed task
- `- ~~[ ] Item text~~` — obsolete / cancelled task
- Sub-bullets use the same `- [ ]` format, indented two spaces
- **Never** use plain `-` bullets for tasks — everything actionable must have a checkbox
- Bold the item title when it has a longer description below it

---

## Party spell inventory (current)

| PC | Class | CL | Spells known |
|----|-------|-----|--------------|
| Yanyeeku | Sorcerer / Nine Tailed Heir | 1 | Disguise Self (2/day), Dancing Lights (3/day), Detect Magic (∞), Disrupt Undead (∞), Message (∞), Read Magic (∞), Magic Missile (5 slots/day), Shield (5 slots/day) |
| Vanx | Barbarian (kitsune racial magic) | 1 | Same racial/cantrip pool as Yanyeeku — innate, not class-based |
| Ani | Warpriest | 1 | Pyrotechnics (racial), Detect Poison (∞), Resistance (∞), Stabilize (∞), Protection from Evil (1st slot), Shield of Faith (1st slot) |

**Spell categories by backend complexity:**

| Category | Examples | AoO? | Complexity |
|----------|----------|------|-----------|
| Auto-hit damage (ranged) | Magic Missile | Yes (cast) | Low — roll damage, no to-hit |
| Auto-hit damage (ranged touch) | Disrupt Undead | Yes (cast) | Low + touch AC check |
| Self-buff | Shield | Yes (cast) | Medium — track AC bonus |
| Other-buff | Protection from Evil | Yes (cast) | Medium — track on target |
| Touch (heal/utility) | Stabilize, Resistance | Yes (cast) | Medium — melee touch attack vs touch AC |
| Utility / narrative | Detect Magic, Message, Read Magic | Yes (cast) | None — LLM narrates |
| Save-based | Pyrotechnics | Yes (cast) | High — save DC, two paths |

---

## Theater of Mind range model

> **Design decision (locked):** No grid, no compass, no distance matrix.
> Zones are named in-world locations. Adjacency is a boolean. See [MOVEMENT-TODO.md](MOVEMENT-TODO.md)
> for the full zone system. This section covers the spell-specific mapping.

### Spell range → zone requirement

| PF1e range | Valid targets |
|-----------|--------------|
| Personal | Caster only |
| Touch | Same zone only (melee reach) |
| Close (25 ft) | Same zone or adjacent zone |
| Medium (100 ft) | Same zone or adjacent zone |
| Long (400 ft) | Any zone |

> **Note:** Close and Medium both resolve to "same or adjacent" in a typical
> encounter (zones are ~30 ft across). Only Long reaches across non-adjacent zones.
> If an encounter has very large zones (e.g. a canyon), the GM adjusts.

### AoE resolution — count-based, not zone-based

| Size tag | Target count | PF1e equivalent |
|----------|-------------|----------------|
| small | 2 | 5–10 ft burst/cone |
| medium | 3 | 15–20 ft burst |
| large | 4 | 30 ft burst |
| huge | 8+ | 40 ft+ or whole area |

The LLM names which targets are in the area; the backend resolves up to `target_count`
of them. The count adjusts ±1 based on clustering (GM judgment). See MOVEMENT-TODO.md
Tier M6 for the full AoE mechanic.

### Zone data

Zone names, adjacency, and starting positions are defined in the event file `## Zones`
section (see MOVEMENT-TODO.md Tier M1). Combatants have `Combatant.zone: str`.
`stream_pc_turn` validates spell range by calling `_in_ranged_range()` or `_in_melee_range()`
from MOVEMENT-TODO.md Tier M2.

---

## Cross-cutting open items

Items that span multiple tiers or require coordination with other systems.

### Spell Dictionary

- [ ] **Create `adventure_path/04_rules/spells/` directory** — each spell gets its own `.md` file in the same format as skill files. The character sheet only lists spell names; the system looks up mechanics from this dictionary. Prevents duplicating stat blocks across multiple character sheets. Format:

  ```
  # Magic Missile

  **Triggers:** magic missile, force missile, cast magic missile

  ## Resolution

  Auto-hit: always deals damage regardless of AC or attack roll.
  Damage: 1d4+1 force per missile. At CL 1: 1 missile.
  Spell resistance: Yes — roll CL check (d20 + CL) vs target SR before resolving.

  <!-- REFERENCE -->

  School: Evocation [Force]  Level: Sorcerer/Wizard 1
  Cast time: 1 standard action  Range: 110 ft
  Components: V, S  Duration: Instantaneous
  SR: Yes  Save: None
  ```

  Spells to create immediately: Magic Missile, Shield, Disrupt Undead, Detect Magic,
  Shield of Faith, Protection from Evil, Stabilize, Resistance, Pyrotechnics,
  Disguise Self, Dancing Lights.

- [ ] **`SpellIndex`** — lazy-loaded singleton (same pattern as `SkillIndex`, `NpcIndex`, `CombatRulesIndex`). Detects spell name mentions in PC input and injects the spell's payload section into `_build_pc_turn_system` instead of using the inline `effect` string from the character sheet JSON. Characters sheets become a name list only.

- [ ] **`pc_profiles["spells"]` — structured list** — parse `player_*.json["spells"]["list"]` into structured dicts: `[{"name": "Magic Missile", "level": "1st", "per_day": 5, "cast_time": "standard", "touch": false, "auto_hit": true, "save": "", "sr": true, "damage_expr": "1d4+1", "buff_ac": 0}]`. Cantrips: `per_day = -1`. Character sheet `effect` text replaced by SpellIndex lookup.

### Spellcasting mechanics (from `04_rules/combat/spellcasting.md`)

- [ ] **Attacks of Opportunity on casting** — casting any spell (except swift-action) provokes an AoO from any threatening enemy. Relevant every time a PC casts in melee range. Backend should: (a) check if any active enemy has a valid melee threat on the caster, (b) if so, warn in the `[PC TURN BRIEFING]` ("⚠ casting in melee — enemy may attack of opportunity"), (c) future: auto-resolve the AoO before spell takes effect. Defensive casting avoids the AoO but requires a Concentration check (DC 15 + double spell level).

- [ ] **Concentration checks** — taking damage while casting forces DC 10 + damage + spell level. On failure the spell is lost. Relevant whenever an enemy resolves an attack against a spellcaster on the caster's turn (e.g. enemy readied action or AoO). Emit a `roll_request` SSE for the Concentration check; if failed, cancel the queued spell and emit an error.

- [ ] **Spell component constraints** — Verbal (V): silenced caster cannot cast. Somatic (S): grappled/bound caster cannot cast. Tracked via `Combatant.conditions`. When a PC attempts to cast and conditions block it, `stream_pc_turn` yields an error instead of queuing the spell. Ties into Tier 1.11 conditions and SA-7.

- [ ] **Non-combat spells route through `/turn`** — out-of-combat spell use ("I cast Detect Magic on the room") routes through the normal turn endpoint. The LLM narrates. Backend does not resolve mechanics. Only in-combat spells with immediate effects need the `/pc_turn` path.

- [ ] **Zone system prerequisite** — spell range validation depends on `Combatant.zone` and the zone adjacency helpers (`_in_melee_range`, `_in_ranged_range`). These are defined in [MOVEMENT-TODO.md](MOVEMENT-TODO.md) Tiers M1 and M2. Implement those first before wiring spell range checks in Tier S2.

- [ ] **Spell slot state persistence** — `session.spell_slots_remaining: dict[str, dict[str, int]]` — e.g. `{"yanyeeku": {"1st": 5}}`. Written to `state.json`. Decremented on cast. Restored on long rest (or `POST /sessions/{id}/long_rest`). Racial/innate tracked separately by spell name (`innate_uses_remaining`).

- [ ] **Spells shown in InputBar hint** — extend the weapon hint (`⚔ morningstar · crossbow`) to also show known spells: `✦ Magic Missile · Shield`. Show slot count when tracking is active. Pull from `character.spells` already in the frontend JSON.

---

## Tier S1 — Spell Recognition

Backend identifies when a PC wants to cast a spell and which one, mirroring weapon-attack intent extraction in `/pc_turn`. No mechanics resolved yet — just recognition and routing.

> **Prerequisite:** SpellIndex + structured `pc_profiles["spells"]` (cross-cutting above).

- [ ] **S1-1 — Spell dictionary files** — create `adventure_path/04_rules/spells/` with one `.md` per spell (see cross-cutting item). Triggers, resolution summary above `<!-- REFERENCE -->`; full stat block below.

- [ ] **S1-2 — `SpellIndex` singleton** — same pattern as `SkillIndex`. Lazy-loads all spell files from `04_rules/spells/`. `get(name)` returns payload text; `detect(text)` matches spell names/triggers against player input.

- [ ] **S1-3 — Spell intent extraction** — extend `_extract_pc_combat_intent` to detect `action_type = "cast"` when "cast", "use my spell", or any spell name is in the player text. Populate `spell_name` and `spell_data` (from profile). Fallback: if player said "cast" but no spell matched, use first available cantrip.

- [ ] **S1-4 — `pc_profiles["spells"]` structured list** — parse JSON spell list into structured dicts. Key: `auto_hit`, `touch`, `cast_time` ("standard"|"full"|"swift"), `save`, `sr`, `damage_expr`, `buff_ac`, `per_day`.

- [ ] **S1-T — Tests** — "I cast Magic Missile" → `action_type=cast`, `spell_name=Magic Missile`; "I use shield" → `spell_name=Shield`; cantrip recognised; non-caster → no spell intent; SpellIndex loads files and detects by trigger.

---

## Tier S2 — Standard-Action Damage & Buff Spells (Combat)

Spells that take a standard action and resolve immediately: auto-hit damage (Magic Missile, Disrupt Undead) and self-buffs (Shield). These are the most common in the current party.

> **Prerequisite:** Tier S1.

- [ ] **S2-1 — Auto-hit damage spell resolution** — when `auto_hit = True` and `cast_time = "standard"`: roll `damage_expr` server-side, apply HP delta to target, store result, emit `action_card` (with `spell_name` field, no `roll`/`bonus`/`ac`), then narrate via `_stream_pc_turn_narration`.

- [ ] **S2-2 — Cantrip / at-will handling** — cantrips (`per_day = -1`) require no slot. At-will innate spells use their own `per_day` counter (Tier S3 tracks these). For S2 treat all as free.

- [ ] **S2-3 — Self-buff resolution (Shield)** — when `cast_time = "standard"` and `buff_ac > 0`: add an entry to caster's `active_effects` list (see Tier S5). No damage roll. Emit `combat_update` with updated AC. Narrate: "A shimmering barrier appears around {caster}."

- [ ] **S2-4 — AoO warning in briefing** — `_build_pc_turn_system` checks if any enemy is in melee range of the caster. If so, adds: `⚠ Casting in melee — enemy may attack of opportunity before spell resolves.` No mechanics yet; just narrative awareness.

- [ ] **S2-5 — Spell action card** — update `action_card` SSE to support spells: `spell_name` field added; `roll`/`bonus`/`ac` become optional (omitted for auto-hit spells). CombatEventCard renders: `✦ Yanyeeku → Goblin Warrior 1 / Magic Missile · force · 5 damage / HIT (auto)`.

- [ ] **S2-6 — `_build_pc_turn_system` spell variant** — briefing says `Spell: {spell_name} ({school}, {damage_expr}, auto-hit)` and injects the SpellIndex payload text rather than the inline effect string.

- [ ] **S2-T — Tests** — Magic Missile: no `attack_request`, `action_card` emitted with damage, HP reduced, no slot consumed. Shield: `active_effects` updated, `combat_update` carries higher AC. AoO warning appears when enemy in melee.

---

## Tier S3 — Spell Slot Tracking

Adds resource management. Yanyeeku has 5 first-level spell slots per day. Each cast of Magic Missile or Shield costs one.

> **Prerequisite:** Tier S1, S2.

- [ ] **S3-1 — `session.spell_slots_remaining`** — `GameSession` field: `dict[str, dict[str, int]]`. Populated at boot from `pc_profiles["spells"]` (aggregate `per_day` by level). Written to `state.json`.

- [ ] **S3-2 — Slot decrement on cast** — `stream_pc_turn`: after resolving a slotted spell, decrement the slot. Racial/innate tracked separately in `session.innate_uses_remaining[spell_name]`.

- [ ] **S3-3 — Exhaustion error** — if player tries to cast with no remaining slots, yield error SSE: `"Yanyeeku has no 1st-level slots remaining."` No attack queued, no narration.

- [ ] **S3-4 — Long rest restores slots** — `POST /sessions/{id}/long_rest` (or session boot) restores `spell_slots_remaining` to full. Writes `state.json`.

- [ ] **S3-5 — Slot count in InputBar hint** — `✦ Magic Missile (4/5) · Shield (5/5)`.

- [ ] **S3-T — Tests** — slot decrements; cantrips never decrement; error on exhaustion; long rest restores.

---

## Tier S4 — Touch Spells

Stabilize (Ani) and Resistance (Ani) require a melee touch attack after casting. The touch uses touch AC (ignores armor, shield, natural armor). If the touch misses, the caster holds the charge to the next turn.

> **Prerequisite:** Tier S1, S2. Also requires `ac_touch` on Combatant (see COMBAT-TODO flat-footed/touch AC item).

- [ ] **S4-1 — Touch intent path** — when `touch = True` and target is another combatant (not self), after casting: emit `attack_request` SSE with `attack_type = "touch"` and `ac = target.ac_touch` (touch AC). Player rolls the touch attack. On hit: apply spell effect. On miss: set `session._holding_charge = {spell_name, caster}` — charge can be discharged on any subsequent touch attempt.

- [ ] **S4-2 — Holding the charge** — `GameSession._holding_charge: Optional[dict]`. If set, the next time the caster makes any melee attack (including unarmed), they discharge the held spell. Backend checks for this before resolving the attack. Casting another spell dissipates the charge.

- [ ] **S4-3 — Stabilize** — touch spell that removes the dying condition (sets `hp_current` to 0 and `status = "unconscious"` — stable). On hit the target stops losing HP per round. On miss, caster holds the charge.

- [ ] **S4-T — Tests** — Stabilize emits `attack_request` with touch AC; hit → dying target stabilised; miss → `_holding_charge` set; casting another spell clears `_holding_charge`.

---

## Tier S5 — Save-Based Spells

Spells that allow a saving throw. Pyrotechnics (Ani's racial): Will save or blinded; Fortitude save or deafened.

> **Prerequisite:** Tier S2.

- [ ] **S5-1 — Save DC** — derived from caster's `concentration` bonus in character JSON (already present). DC = 10 + spell level + ability mod. Compute from `concentration - caster_level` to get the ability modifier.

- [ ] **S5-2 — Save roll request** — for spells with `save != ""`, emit `roll_request` SSE: `skill = "Will save"` (or Fort/Ref), `dc = <calculated>`, outcome strings from the spell dictionary.

- [ ] **S5-3 — Two outcome paths** — `_build_pc_turn_system` briefing includes both outcomes. Resolved by `resolve_roll` → `_pending_pc_narration` carries the correct path.

- [ ] **S5-4 — Partial effect on save** — `save_effect: "negates" | "half"`. Current spells are all "negates"; framework supports "half" for future fireball etc.

- [ ] **S5-T — Tests** — Pyrotechnics emits save roll request; failed save applies condition; passed save has no effect; half-damage path reduces by 50%.

---

## Tier S6 — Buff / Duration Effects

Spells that modify stats for a duration: Shield (+4 AC), Shield of Faith (+deflection AC), Protection from Evil (+2 AC and saves), Resistance (+1 all saves).

> **Prerequisite:** Tier 1.11 (conditions infrastructure), Tier S2.

- [ ] **S6-1 — `Combatant.active_effects` list** — `[{"name": "Shield", "ac_bonus": 4, "save_bonus": 0, "rounds_remaining": 10, "source": "Yanyeeku"}]`. Written to `state.json`. Field already partially conceptualised in SA-7.

- [ ] **S6-2 — AC and save modifiers from effects** — `resolve_attack_roll` and `_resolve_npc_attack` sum `active_effects[*]["ac_bonus"]` for the target. CombatPanel shows a modifier badge.

- [ ] **S6-3 — Effect expiry** — `advance_combat_turn` decrements `rounds_remaining` for the outgoing actor's effects. At 0: removed, log entry written, `combat_update` emitted.

- [ ] **S6-T — Tests** — Shield adds `ac_bonus: 4`; attack against shielded target uses higher AC; effect expires after 10 rounds; serialised in `state.json`.

---

## Tier S7 — Spell Resistance

Some spells are blocked by SR. Magic Missile and Disrupt Undead both have `sr: Yes`.

> **Prerequisite:** Tier S2. Requires SR data on enemy combatants (SA-2 / bestiary).

- [ ] **S7-1 — SR check** — roll `d20 + CL` vs `target.sr`. On failure: spell fizzles, no damage, narrate "The spell dissipates."

- [ ] **S7-2 — SR on combatants** — `Combatant.sr: int` (default 0). Seeded from event file `## Combatants` table (add `sr` column) or bestiary.

- [ ] **S7-T — Tests** — SR check fires for Magic Missile; SR = 0 always passes; failed SR produces fizzle with no HP change.

---

## Future (Post-Tier S7)

- [ ] **Concentration check on damage** — taking damage while casting forces DC 10 + damage + spell level. Emit `roll_request` for Concentration; failure loses the spell and its slot. Required for any enemy with a readied action.
- [ ] **Full-round spells** — begin casting this turn, resolves at start of next turn. Cast defensively (DC 15 + 2×spell level) to avoid AoO. If hit before next turn, Concentration check or spell lost. Affects Yanyeeku's highest-level spells in future levels.
- [ ] **Defensive casting** — player declares before casting; Concentration check (DC 15 + 2×spell level); success: no AoO; failure: AoO still provoked + possible second Concentration check.
- [ ] **Metamagic** — Empower, Maximize, Quicken, etc. Affects slot cost and effect. Defer until 3rd+ level.
- [ ] **Scrolls and wands** — consumable magic items. Require inventory tracking and UMD skill check for non-class users.
- [ ] **Area spells** — multi-target resolution and per-target saves. Not relevant until 2nd+ level.
- [ ] **Counterspell** — requires recognising and countering incoming spells. Far-future.
- [ ] **Component constraints in play** — silenced caster can't cast V spells; grappled can't cast S spells. Check `Combatant.conditions` before queuing. Requires Tier 1.11 conditions.
