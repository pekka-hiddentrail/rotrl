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

- [x] **Create `adventure_path/10_spells/` directory** — each spell gets its own `.md` file with structured metadata, a backend-facing `## Resolution` block, and a rules summary below `<!-- REFERENCE -->`. The character sheet should eventually list spell names/resources only; mechanics should come from this dictionary. Class index subfolders exist for `wizard/` and `cleric/`.

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

  Created immediately: Magic Missile, Shield, Shield of Faith, Protection from Evil, Cure Light Wounds.
  Remaining first pass: Disrupt Undead, Detect Magic, Stabilize, Resistance, Pyrotechnics,
  Disguise Self, Dancing Lights.

- [ ] **`SpellIndex`** — lazy-loaded singleton (same pattern as `SkillIndex`, `NpcIndex`, `CombatRulesIndex`). Reads canonical spell files from `adventure_path/10_spells/`, detects spell name mentions in PC input, and injects the spell's payload section into `_build_pc_turn_system` instead of using the inline `effect` string from the character sheet JSON. Character sheets become a name/resource list only.

- [ ] **Replace duplicated spell mechanics in character JSON** — everywhere a spell is referenced (`player_*.json`, PC profiles, InputBar hints, spell intent extraction), use the canonical `10_spells/<spell>.md` data for mechanics. Character JSON may keep prepared/known spell names, per-day slots, caster level, and character-specific DC/concentration data, but should not be the source of truth for spell descriptions, damage dice, AC bonuses, saves, SR, or targeting.

- [ ] **`pc_profiles["spells"]` — structured list** — parse `player_*.json["spells"]["list"]` into structured dicts: `[{"name": "Magic Missile", "level": "1st", "per_day": 5, "cast_time": "standard", "touch": false, "auto_hit": true, "save": "", "sr": true, "damage_expr": "1d4+1", "buff_ac": 0}]`. Cantrips: `per_day = -1`. Character sheet `effect` text replaced by SpellIndex lookup.

### Spellcasting mechanics (from `04_rules/combat/spellcasting.md`)

- [ ] **Attacks of Opportunity on casting** — casting any spell (except swift-action) provokes an AoO from any threatening enemy. Relevant every time a PC casts in melee range. Backend should: (a) check if any active enemy has a valid melee threat on the caster, (b) if so, warn in the `[PC TURN BRIEFING]` ("⚠ casting in melee — enemy may attack of opportunity"), (c) future: auto-resolve the AoO before spell takes effect. Defensive casting avoids the AoO but requires a Concentration check (DC 15 + double spell level).

- [ ] **Magical Tail SLA — per-day use tracking (Yanyeeku)** — Yanyeeku's Magical Tail feat grants Disguise Self 2/day as a spell-like ability (CL = Hit Dice, DC Charisma-based, no slot cost). When Tier S3 `innate_uses_remaining` lands, add `"disguise_self_sla": 2` as a separate counter from any slot-based casting. On each use, decrement the counter; if 0, yield an error SSE ("Disguise Self (Magical Tail) already used twice today"). Note: the Nine-Tailed Heir bloodline also grants Disguise Self from a different source — these are tracked independently, they do not share a counter.

- [ ] **Eschew Materials — PC profile context note (Yanyeeku, Vanx)** — Yanyeeku has Eschew Materials, which means she never needs a spell component pouch for spells with components costing 1 gp or less. The `[PC COMBAT STATS]` and `_build_pc_turn_system` briefings for Yanyeeku should include a one-line note ("Eschew Materials — no component pouch required for ≤1 gp components") so the LLM never narrates her losing access to spells because her pouch was lost/stolen/destroyed. No backend enforcement needed — this is purely a prompt-context correctness item.

- [ ] **Fey Bloodline Arcana — +2 DC on compulsion spells** — when save DCs are computed by the backend (rather than delegated to the LLM), spells tagged as `enchantment/compulsion` subschool cast by a Fey bloodline sorcerer receive +2 to their DC. For a Kitsune caster, a further +1 applies to all enchantment spells (compulsion is a subschool of enchantment, so compulsion spells receive both bonuses: +3 total). Implementation: add `dc_modifiers: list[dict]` to `pc_profiles` at boot, e.g. `[{"subschool": "compulsion", "bonus": 2, "source": "Fey Bloodline Arcana"}, {"school": "enchantment", "bonus": 1, "source": "Kitsune racial"}]`. Save/DC resolution reads the caster's `dc_modifiers` and sums matching entries onto the base DC formula (10 + spell_level + CHA_mod). Currently the LLM handles all DC arithmetic ad hoc — this item becomes binding only when a structured save-resolution path exists.

- [ ] **Laughing Touch — intent detection, touch attack, condition, and immunity tracking** — Laughing Touch (Fey Bloodline level-1 power) requires multiple pieces: (a) `innate_uses_remaining["laughing_touch"]` counter seeded at 3 + CHA mod per day; (b) intent detection — "I use Laughing Touch" / "laughing touch" → `action_type = "class_ability", ability_name = "laughing_touch"`; (c) melee touch attack resolution against `target.ac_touch` (prerequisite: Flat-footed and touch AC TODO in COMBAT-TODO); (d) on hit: add `"laughing"` to target's `Combatant.conditions` with `expires_after_round = N` and a note that the target may only take a move action — the enemy-turn briefing must reflect this constraint; (e) mind-affecting immunity: check a `Combatant` flag (bestiary `immune_mind_affecting: bool` or similar) and refuse application if immune — constructs, undead, and many outsiders are immune; (f) per-creature 24-hour immunity: `session.laughing_touch_immune: set[str]` — if the target name is already in this set, yield an explanatory narration instead of resolving the attack; add the name to the set on a successful application. Counter decrements on each use; at 0 yield error SSE: "Laughing Touch already used {max}/day."

- [ ] **Concentration checks** — taking damage while casting forces DC 10 + damage + spell level. On failure the spell is lost. Relevant whenever an enemy resolves an attack against a spellcaster on the caster's turn (e.g. enemy readied action or AoO). Emit a `roll_request` SSE for the Concentration check; if failed, cancel the queued spell and emit an error.

- [ ] **Spell component constraints** — Verbal (V): silenced caster cannot cast. Somatic (S): grappled/bound caster cannot cast. Tracked via `Combatant.conditions`. When a PC attempts to cast and conditions block it, `stream_pc_turn` yields an error instead of queuing the spell. Ties into Tier 1.11 conditions and SA-7.

- [ ] **Non-combat spells route through `/turn`** — out-of-combat spell use ("I cast Detect Magic on the room") routes through the normal turn endpoint. The LLM narrates. Backend does not resolve mechanics. Only in-combat spells with immediate effects need the `/pc_turn` path.

- [ ] **Zone system prerequisite** — spell range validation depends on `Combatant.zone` and the zone adjacency helpers (`_in_melee_range`, `_in_ranged_range`). These are defined in [MOVEMENT-TODO.md](MOVEMENT-TODO.md) Tiers M1 and M2. Implement those first before wiring spell range checks in Tier S2.

- [ ] **Spell slot state persistence** — `session.spell_slots_remaining: dict[str, dict[str, int]]` — e.g. `{"yanyeeku": {"1st": 5}}`. Written to `state.json`. Decremented on cast. Restored on long rest (or `POST /sessions/{id}/long_rest`). Racial/innate tracked separately by spell name (`innate_uses_remaining`).

- [ ] **Blessings pool — per-day use tracking (Warpriest)** — the warpriest's Blessings shared pool is 3 + WIS mod uses per day (e.g. 7/day at WIS 18). Add `session.blessings_remaining: dict[str, int]` alongside `spell_slots_remaining`. Populate at boot from `pc_profiles` for warpriest characters only (check `pc_profiles[name]["class"]`). Decrement on each use of any blessing ability (Powerful Healer, Strength Surge, or any future blessing). Restore on long rest. Both current blessing abilities are swift actions — the player declares them alongside their primary action ("I use Powerful Healer with my Cure Light Wounds", "I surge and Flurry"). `stream_pc_turn` intent extraction detects the blessing keyword in the same pass as the primary action, sets `blessing_active: str | None` on the turn context, gate-checks the pool (yield error SSE at 0: "No blessings remaining today"), then passes the flag into the appropriate resolver: `resolve_damage_roll` applies × 1.5 healing for Powerful Healer (see S3-6); Strength Surge adds an enhancement bonus to attack rolls for the round (see Strength Surge TODO in COMBAT-TODO). Pool count should be shown in the InputBar hint once slot tracking is active: `♦ Blessings: 7`.

- [ ] **Spells shown in InputBar hint** — extend the weapon hint (`⚔ morningstar · crossbow`) to also show known spells: `✦ Magic Missile · Shield`. Show slot count when tracking is active. Pull from `character.spells` already in the frontend JSON.

- [ ] **Active effects in enemy turn briefing** — when a target has active AC effects, inject them into `_build_enemy_turn_system` so the LLM knows the target is buffed. Example: "Yanyeeku: hp 8/11, AC 16 (Shield spell, 8r left)". This lets the LLM write flavour like "the blow glances off a shimmering wall of force" instead of generic hit/miss text. Pass `active_effects` list per combatant into the `[INITIATIVE ORDER]` block.

---

## Tier S1 — Spell Recognition

Backend identifies when a PC wants to cast a spell and which one, mirroring weapon-attack intent extraction in `/pc_turn`. No mechanics resolved yet — just recognition and routing.

> **Prerequisite:** SpellIndex + structured `pc_profiles["spells"]` (cross-cutting above).

- [x] **S1-1 — Initial spell dictionary files** — created `adventure_path/10_spells/` with `SPELL_TEMPLATE.md`, canonical files for Magic Missile, Shield, Shield of Faith, Protection from Evil, Cure Light Wounds, and class indexes under `wizard/` and `cleric/`. Continue adding remaining party spells as needed.

- [ ] **S1-2 — `SpellIndex` singleton** — same pattern as `SkillIndex`. Lazy-loads all spell files from `10_spells/`. `get(name)` returns payload text; `detect(text)` matches spell names/triggers against player input.

- [x] **S1-3 — Spell intent extraction** — extend `_extract_pc_combat_intent` to detect `action_type = "cast"` when "cast", "use my spell", or any spell name is in the player text. Populate `spell_name` and `spell_data` (from profile). Spell detection runs before weapon matching and wins on direct name match regardless of cast keyword. Rules-agnostic: reads from `pc_profiles["spells"]` for any PC.

- [x] **S1-4 — `pc_profiles["spells"]` structured list** — `_build_pc_profiles` parses `player_*.json["spells"]["list"]` into structured dicts with `auto_hit` (detected from "never misses" in effect text), `damage_expr` (dice regex on effect), `school`, `sr`, `save`, `per_day`, `cast_time`, `range_raw`.

- [x] **S1-T — Tests** — `test_spell_system.py` SS-001–SS-008: auto_hit/damage_expr parsing, sr flag, non-caster, Magic Missile real data, spell matched by name/partial/no-cast-keyword, target resolution, spell priority over weapon. 34 tests, all pass.

---

## Tier S2 — Standard-Action Damage & Buff Spells (Combat)

Spells that take a standard action and resolve immediately: auto-hit damage (Magic Missile, Disrupt Undead) and self-buffs (Shield). These are the most common in the current party.

> **Prerequisite:** Tier S1.

- [x] **S2-1 — Auto-hit damage spell resolution** — `stream_pc_turn` cast branch: queues a `PendingAttack` with `hit=True`, `is_spell=True`, `spell_name` pre-set. Emits `damage_request` SSE (not `attack_request`). Player rolls damage. `resolve_damage_roll` applies HP delta and stores `is_spell`/`spell_name` in result. `_stream_pc_turn_narration` narrates with known damage. Non-auto-hit spells fall through to immediate narration without dice.

- [ ] **S2-2 — Cantrip / at-will handling** — cantrips (`per_day = -1`) require no slot. At-will innate spells use their own `per_day` counter (Tier S3 tracks these). For S2 treat all as free.

- [x] **S2-4 — Healing spell resolution (Cure Light Wounds)** — `healing_expr` parsed from "Heals Xd8+Y" in effect text; `is_heal` flag on spell profile. `stream_pc_turn` heal branch queues `PendingAttack(is_heal=True, hit=True)`; emits `heal_request` SSE. Target resolution: all PCs (including unconscious) — most wounded PC default. `resolve_damage_roll`: positive HP delta; unconscious → active when healed above 0. Frontend: `spell_heal` AttackPhase; green DicePanel banner ("Roll Healing"); green MessageBubble heal card; CSS heal colours. 23 tests (test_healing_spells.py). Cure Light Wounds added to Ani's spell list (player_03.json, 2/day, 1d8+1).

- [x] **S2-3 — Self-buff resolution (Shield)** — `buff_ac` extracted from effect text via regex (`+N shield bonus to AC`). `Combatant.active_effects` list added; `_effective_ac()` sums base AC + effect bonuses; `_apply_ac_effect()` enforces no-stack rule (same bonus_type replaces); `_tick_effects()` called from `advance_combat_turn` for the outgoing actor. `stream_pc_turn` buff branch: applies effect, emits `combat_update` immediately, narrates inline, advances turn. `_serialize_combat_state` includes `effective_ac` and `active_effects`. CombatPanel shows effective AC with ✦ indicator + tooltip listing active effects. Rules-agnostic: any spell with `+N shield bonus to AC` in effect text is handled automatically.

- [ ] **S2-4 — AoO warning in briefing** — `_build_pc_turn_system` checks if any enemy is in melee range of the caster. If so, adds: `⚠ Casting in melee — enemy may attack of opportunity before spell resolves.` No mechanics yet; just narrative awareness.

- [x] **S2-5 — Spell action card** — `MessageBubble.tsx` renders spell action cards with `✦` icon, spell name, "auto-hit" label (no roll/AC line). `action_card` SSE carries `is_spell` and `spell_name` fields. `AttackResult` type updated to support nullable `roll`/`total`/`ac` and optional `is_spell`/`spell_name`.

- [x] **S2-6 — `_build_pc_turn_system` spell variant** — `action_type=cast` in intent → briefing says `Spell: {name} ({school}, auto-hit)\nDamage: {total}` instead of the `1d20 +X = Y vs AC Z` line.

- [x] **S2-T — Tests** — `test_spell_system.py` SS-009–SS-014: damage_request emitted (not attack_request), spell fields in event, PendingAttack pre-hit, HP delta applied, result carries is_spell/spell_name, system message spell briefing. 34 tests, all pass.

---

## Tier S3 — Spell Slot Tracking

Adds resource management. Yanyeeku has 5 first-level spell slots per day. Each cast of Magic Missile or Shield costs one.

> **Prerequisite:** Tier S1, S2.

- [ ] **S3-1 — `session.spell_slots_remaining`** — `GameSession` field: `dict[str, dict[str, int]]`. Populated at boot from `pc_profiles["spells"]` (aggregate `per_day` by level). Written to `state.json`.

- [ ] **S3-2 — Slot decrement on cast** — `stream_pc_turn`: after resolving a slotted spell, decrement the slot. Racial/innate tracked separately in `session.innate_uses_remaining[spell_name]`.

- [ ] **S3-3 — Exhaustion error** — if player tries to cast with no remaining slots, yield error SSE: `"Yanyeeku has no 1st-level slots remaining."` No attack queued, no narration.

- [ ] **S3-4 — Long rest restores slots** — `POST /sessions/{id}/long_rest` (or session boot) restores `spell_slots_remaining` to full. Writes `state.json`.

- [ ] **S3-5 — Slot count in InputBar hint** — `✦ Magic Missile (4/5) · Shield (5/5)`.

- [ ] **S3-6 — Warpriest Spontaneous Casting** — Ani (Warpriest, good alignment) can expend *any* prepared 1st-level spell slot to cast any cure spell of equal or lower level instead. This means casting Cure Light Wounds should consume one of her prepared slots (Shield of Faith or Protection from Evil), not a separate CLW counter. The current `per_day: "2/day"` on CLW is a placeholder approximation matching her 2 prepared slots. Proper implementation when S3 lands:
  - `pc_profiles["spontaneous_casting"]`: `{"type": "cure", "level": 1, "source_slots": ["Shield of Faith", "Protection from Evil"]}`
  - When CLW is cast, decrement one of the `source_slots` counters instead of a CLW-specific counter. If all source slots are exhausted, CLW is unavailable.
  - Powerful Healer (Su) class feature: casting any cure spell as a swift action empowers it (+50% healing). Trigger on swift-action cast detection.
  - Affects: Ani. Other Warpriests, Clerics, and Oracles have the same mechanic.

- [ ] **S3-T — Tests** — slot decrements; cantrips never decrement; error on exhaustion; long rest restores; Warpriest spontaneous cast decrements source slot, not CLW counter.

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
