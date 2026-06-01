# Combat System Backlog

All combat-related work lives here. [TODO.md](TODO.md) links here rather than carrying the full tier tree inline.

**Same markup rules as TODO.md apply.**

- `- [ ] Item text` — open task
- `- [x] Item text` — completed task
- `- ~~[ ] Item text~~` — obsolete / cancelled task
- Sub-bullets use the same `- [ ]` format, indented two spaces
- **Never** use plain `-` bullets for tasks — everything actionable must have a checkbox
- Bold the item title when it has a longer description below it

---

## Cross-cutting open items

Items that span multiple combat tiers or require coordination with non-combat layers.

- [ ] **Playwright — attack resolution E2E** — one live flow `attack-resolution-flow` in `live-flows.spec.ts`: boot → trigger combat with mixed NPC+PC attack block → assert `attack_result` SSE updates CombatPanel HP → assert `attack_request` fires and DicePanel shows to-hit banner → roll d20 → hit path: damage banner appears, roll damage, assert `combat_update` reduces HP → assert `POST /resume_combat` called and GM resumes streaming. *(spec: `attack-resolution.feature` AC-002 through AC-005)*
- [ ] **Combat initiative active character state** — when combat is active, the current combatant in initiative order should drive `active_character`. Add an API/update path that writes the current initiative actor into the UI and `sessions/session_NNN/state.json`, including enemy turns. When the active actor is an enemy, the input field should switch to a red-ish hostile state with taunting prompt text, show a skull-style icon instead of the character rune, and label the enemy by name (for example `Goblin Warrior 1`).
- [ ] **Combat turn ownership model** — make the backend, not the LLM, the source of truth for the current combatant and initiative advancement. Store current actor, round, and acted/remaining turn state; emit it to the UI; inject it into the combat prompt as authoritative. The LLM may describe outcomes, but should not be able to drift initiative order or choose whose turn is next.
- [ ] **Backend-hydrated combat encounter start** — when a combat event starts, resolve the encounter from backend-owned event/encounter descriptions plus canonical bestiary data instead of trusting the LLM to invent monster stats. Determine the minimum LLM responsibility: likely narrative framing, enemy intent, and choosing among valid tactics; backend should supply combatants, HP, AC, initiative modifiers, attacks, saves, XP, and encounter metadata wherever the data exists.
- [ ] **Enemy stat authority for combat** — stop relying on model-invented enemy stats after initial setup. Load enemies from canonical NPC/monster stat blocks where possible, persist generated combatants into session state, and validate AC/HP/initiative/attack bonuses against those sources.
- [ ] **Combat prompt: PC vs enemy turn behavior** — clarify and test the combat prompt contract: on a PC turn, the GM should present the immediate situation and wait for/resolve the player's declared action; on an enemy turn, the GM may choose and narrate the enemy action using `%%ATTACK%%`/`%%HP%%` as needed. This should align with the active-character/enemy input-state UI.
- [ ] **Combat action economy rules** — add prompt guidance and backend/test support for PF1e action economy: standard/move/swift/immediate/full-round actions, attacks of opportunity, readied/delayed actions, and limits on how much one combatant can do per turn.
- [ ] **Combat end conditions** — define when combat should emit `round: 0` and clear the tracker: all enemies dead/fled/surrendered, encounter defused, or GM/player explicitly ends combat. Add tests so victory, surrender, fleeing enemies, and manual End Combat behave consistently.
- [ ] **Condition duration tracking** — extend combat state to track condition durations and expiry rules, not just condition labels. Include prompt/backend behavior for one-round effects, save-ends effects, prone/standing, bleed, poison, fear states, and other common PF1e combat conditions.
- [ ] **System prompt — strip non-combat context blocks outside active combat** — when `session.combat_state is None`, suppress from the per-turn injection: `_COMBAT_FULL_SPEC`, `_COMBAT_SPEC_ONGOING`, `[CURRENT HP]` block, `_ENEMY_TURN_DIRECTIVE`, and the attack-resolution section of `_COMBAT_SPEC_ONGOING`. Broader review: audit all per-turn injections for appropriate activity-gating; consider a leaner "exploration mode" base prompt variant separate from a "combat mode" variant that activates only when `combat_state is not None`. Potentially large token savings on every non-combat turn.
- [x] **Vitest — attack resolution UI** — 15 tests in `DicePanelAttack.test.tsx`: to-hit banner (attacker/target/AC/bonus/active-class/onAttackRoll callback); damage banner (HIT line/damage-expr/Roll Damage disabled+enabled); null phase (no banner, no active class); attack log (hit badge+damage, miss badge+no-damage, NPC label, log-before-skill-history DOM order). *(spec: `attack-resolution.feature` AC-002/AC-003/AC-004/AC-008)*
- [x] **Bug: `handleDamageRollClick` passes die sides as roll values** — `pending` stores die *sides* (e.g. `[8]` for a d8), not rolled values. `handleDamageRollClick` passes `pending` directly as `rolls`, so `onDamageRoll([8], 8)` is called instead of the actual d8 result. **Fixed:** `pending.map(rollDie)` replaces `[...pending]`. V8 Vitest test added to cover the fix. *(DicePanel.tsx `handleDamageRollClick`)*

---

- [ ] **Enemy turn auto-advance policy** — decide whether `POST /enemy_turn` should automatically advance initiative after it emits `combat_update`, or whether the GM should click **Next Turn** explicitly. Add tests for whichever policy wins so enemy turns cannot accidentally repeat the same actor forever.

## Adventure Combat Content

- [ ] **Sinspawn stat block** — `adventure_path/05_campaign_setting/bestiary/sinspawn.md` created: AC 14, HP 16, claws+bite, sinful bite (Will DC 12 or wrath compulsion), wrathful strike, GM narrative notes.
- [ ] **Thistletop goblin roster** — `01_npcs/thistletop_roster/base.md` created: Ripnugget (fighter 4, gecko mount, surrender), Bruthazmus (bugbear ranger 4, Ameiko connection, turning), Orik Vancaskerkin (fighter 4, mercenary, turning conditions), Lyrie Akenja (wizard 4, library intelligence, cooperation conditions), Stickfoot.
- [ ] **Additional bestiary entries** — `goblin_dog.md` (CR 1, Goblin Pox disease, morale); `yeth_hound.md` (CR 3, Bay DC 13, flight, DR 5/silver). Warchanter variant already complete.
- [ ] **Create `adventure_path/09_monsters/` folder** — centralise all generic monster stat blocks here. Each file named `<slug>.md` (e.g. `goblin.md`, `sinspawn.md`, `yeth_hound.md`). Minimum fields per entry: AC, HP, speed, attacks (name / to-hit / damage), saves, special abilities, morale threshold, XP value, and short GM combat notes. The campaign-specific bestiary files currently scattered in `05_campaign_setting/bestiary/` should move here; named unique NPCs (Nualia, Tsuto) stay in `01_npcs/`. `LocationIndex`-style lazy loading and alias detection can be added later if the GM needs per-encounter monster context injected automatically.
- [x] **Verify and complete bestiary files** — `goblin.md`, `goblin_commando.md`, and `goblin_warchanter.md` confirmed complete: AC, HP, attacks, combat scripts, morale thresholds, XP values all present.
- [x] **Tsuto Kaijitsu combat stats** — added to `01_npcs/tsuto_kaijitsu/base.md`: monk 7, CR 6, AC 20, HP 42, full attack line, surrender condition, loot (journal).
- [x] **Nualia Tobyn combat stats** — added to `01_npcs/nualia_tobyn/base.md`: cleric 4/barbarian 3, CR 7, AC 20, HP 62, spell list, aura of madness, demon claw, full combat script, redemption condition, loot (journal bridges to Book II).

---

## Combat System

Combat runs through the existing narrative loop — the LLM drives pacing, the system tracks state. Multiple tiers of fidelity, each independently shippable. Tier 1 is complete; Tiers 1.1 and 1.5 establish HP authority and the interactive attack flow. Tier 1.6 replaces the bolted-on combat injections with a purpose-built combat system prompt before Tier 2 adds mechanical depth.

> **Layout note:** when the CombatPanel is visible it occupies the right column. DicePanel moves to the left column (stacked beneath CharacterSidebar), freeing the right for initiative/HP display. Out of combat the layout reverts to current (CharSidebar left · Chat centre · DicePanel right).

---

### Combat Rules Reference

- [x] **Create `adventure_path/04_rules/combat/` folder** — six PF1e combat reference files created: `attack_rolls.md`, `armor_class.md`, `initiative.md`, `hit_points.md`, `actions.md`, `attacks_of_opportunity.md`. Each follows the skill file format with `**Triggers:**` header and `<!-- REFERENCE -->` payload/reader split. Injection wired in when a `CombatRulesIndex` is built (same pattern as `SkillIndex`).
- [x] **Wire `CombatRulesIndex` injection** — `api/context/combat_lookup.py` built (`CombatRulesIndex`, `CombatRuleMatch`, `_parse_combat_rule_file`); singleton wired in `session_manager.py`; trigger detection runs in `_inject_context` when `combat_state.round > 0`; 22 tests in `test_combat_lookup.py`.

---

### Tier 1 — Combat Tracker Panel (MVP)

A right-side panel that appears when `session.combat_state` is set and disappears when it is cleared. The LLM writes a `%%COMBAT%%` block each turn to update the state; the UI is read-only.

#### `%%COMBAT%%` block format

Written by the LLM after `%%DELTAS%%` whenever combat is active or just ended. Uses the same indented key-value style as other blocks:

```
%%COMBAT%%
round: 2
combatants:
  - name: Shalelu      · hp: 18/24 · ac: 17 · init: 14 · status: active
  - name: Goblin 1     · hp: 0/5   · ac: 13 · init: 12 · status: unconscious
  - name: Goblin 2     · hp: 5/5   · ac: 13 · init:  8 · status: active
  - name: Thaelion     · hp: 22/22 · ac: 16 · init:  6 · status: active
```

`round: 0` signals combat ended — backend clears `session.combat_state`. If the block is omitted entirely, existing state is preserved (LLM may omit the block between rounds without wiping the tracker). A malformed block (missing `round:` field) is also treated as a parse failure and leaves state unchanged.

#### Backend

- [x] **CB1 — `CombatState` + `Combatant` dataclasses** — `Combatant(name, hp_current, hp_max, ac, initiative, status)` where `status ∈ {active, unconscious, fled, dead}`. `CombatState(round, combatants)`. `Combatant.__post_init__` clamps HP and validates status. `combat_state: Optional[CombatState] = None` field on `GameSession`.
- [x] **CB2 — `%%COMBAT%%` parser** — `_parse_combat_block(text) -> Optional[CombatState]` + `_parse_combatant_line(line) -> Optional[Combatant]`. Return semantics: `CombatState(round=0, combatants=[])` when `round: 0` is present (intentional clear sentinel); `None` on missing block, missing `round:` field, or parse error (preserve existing state — do not wipe on bad LLM output). `_COMBAT_BLOCK_RE` regex for flat-block fallback path. Processed in both section and fallback response paths. `_HAS_SECTION_MARKERS_RE` does **not** include COMBAT (keeping it out prevents COMBAT-only responses from routing to the sections path and leaking raw markup via the NARRATIVE fallback).
- [x] **CB3 — SSE `combat_update` event** — `_serialize_combat_state()` helper; `{"type": "combat_update", "combat_state": <dict|null>}` emitted every turn after `roll_request`. `SseEvent` union in `api.ts` updated with `combat_update` variant.
- [x] **CB4 — `%%COMBAT%%` in system prompt** — COMBAT TRACKER block added to `_build_slim_system_prompt` with format spec and rules. `"\n%%COMBAT%%"` added to `_END_MARKERS` in `_stream_with_narrative_filter`. `DELETE /api/sessions/{id}/combat` endpoint clears `session.combat_state`.

#### Frontend

- [x] **CB5 — Layout: DicePanel moves left** — `combat-active` CSS class on `.main-content` when `combatState !== null`. CSS flex `order` rules: non-combat: sidebar(1)|chat(2)|dice(3); combat: sidebar(1)|dice(2)|chat(3)|combat(4). DicePanel border swaps sides in combat mode.
- [x] **CB6 — `CombatPanel` component** — `ui/src/components/CombatPanel.tsx`. Right column (220 px), shown only when `combatState !== null`. Shows: "⚔ Combat" title + "Round N" badge; initiative list sorted descending; current actor (top) highlighted with gold glow; inactive combatants dimmed; status badges (KO / fled / dead). "End Combat" button calls `DELETE /combat` + clears client state.
- [x] **CB6.1 — CombatPanel active-turn highlight advances** — `currentCombatantName: string | null` state in `App.tsx` tracks the highlighted combatant by name (not by position). Initialised to the highest-initiative active combatant on the first `combat_update` of a new combat. "Next Turn →" button in `CombatPanel` advances the highlight to the next active combatant in initiative order and wraps at the end of the round. Falls back to the first active combatant when `currentCombatantName` is unset. Resets to `null` on combat clear, end session, and kill-end.
- [x] **CB7 — HP bar component** — `ui/src/components/HpBar.tsx`. Green > 66%, amber 33–66%, red < 33%, dark-grey at 0. CSS `transition` for animated width changes on HP update.
- [x] **CB8 — `combatState` in `App.tsx`** — `useState<CombatState | null>(null)`. Updated from `combat_update` SSE events. Cleared on session end and kill-end. `endCombat()` API call in `api.ts`.

#### Tests

- [x] **CB-T1** — `tests/test_combat.py`: 29 tests. Combatant HP clamp + status validation (5); `_parse_combatant_line` happy path + edge cases (6); `_parse_combat_block` happy path + round-0-clear-sentinel + no-round-field-returns-None + empty + None/empty-string + malformed-line-skipped + HP clamp (8); `_serialize_combat_state` None + full shape (2); SSE null-when-no-block + populated + state-persists-and-clears + malformed-block-preserves-state + combat-only-no-leak + filter (6); DELETE endpoint clears state + 404 (2). 482 total passing.

---

### Tier 1.1 — HP Authority Shift

Move HP ownership from the LLM to the backend. In Tier 1 the LLM writes HP values every turn
and inevitably drifts (arithmetic errors, forgetting damage between rounds). Tier 1.1 makes the
backend the single source of truth so Tier 1.5 attack resolution can update HP reliably.

> **Authority model after Tier 1.1:**
> LLM writes: round number, initiative, status (active/unconscious/fled/dead), conditions, new combatants.
> Backend owns: HP values. LLM never writes HP after round 1 — it reads current HP from injected context.

#### Backend

- [x] **CB1.1-1 — HP stripped from `%%COMBAT%%` format after round 1** — on combat start (first turn `session.combat_state` is None), accept HP values from the LLM to initialise `combat_state`. On subsequent turns, parse and discard HP columns from `%%COMBAT%%` lines; backend retains its own HP values. `_parse_combat_block` gains an `existing_state: Optional[CombatState]` parameter — when provided, it copies HP from matching combatants by name instead of using the LLM-written values.
- [x] **CB1.1-2 — `%%COMBAT%%` format update in system prompt** — two spec constants: `_COMBAT_SPEC_ROUND1` (with `hp: cur/max` for initialisation) and `_COMBAT_SPEC_ONGOING` (no HP columns; references `%%HP%%` for deltas). `_inject_context` injects `_COMBAT_SPEC_ONGOING` when `combat_state.round > 0`.
- [x] **CB1.1-3 — HP context injection** — `[CURRENT HP]` block injected into per-turn system content alongside the combat reminder. Lists each combatant with `name: cur/max (status)` so the LLM can narrate accurately without recomputing HP.
- [x] **CB1.1-4 — `%%HP%%` delta block for non-attack HP changes** — `_HP_BLOCK_RE`, `_parse_hp_deltas`, `_apply_hp_deltas` added. Processed in both section-based and flat-block paths after `%%DELTAS%%` and before `%%COMBAT%%`. Block stripped from player token stream (`"\n%%HP%%"` added to `_END_MARKERS`). Silently ignored when `combat_state` is None.

#### Tests

- [x] **CB1.1-T** — `tests/test_combat_hp.py`: 29 tests. HP inheritance (9 cases: init from LLM, preserve from backend, new combatant, case-insensitive, round-0 unaffected, parse-failure still None, backward-compat); `_parse_hp_deltas` (8 cases); `_apply_hp_deltas` (7 cases: damage, healing-clamp, overkill-clamp, unknown-name, multiple, case-insensitive, None-state); HP context injection (2 cases); stream stripping (1 case); full-turn integration (2 cases). 584 total passing (excl. 2 pre-existing test_end_session failures unrelated to this work).

---

### Tier 1.5 — Interactive PC Attack Flow

The player rolls dice for PC attacks; backend auto-rolls for monsters. LLM writes `%%ATTACK%%`
blocks to signal which attacks happen this round (with stats). All dice are resolved before the
LLM is called again — minimising LLM calls during mechanical resolution and eliminating the
chance of the LLM inventing roll outcomes.

> **Flow:**
> 1. LLM writes `%%ATTACK%%` block (one line per attack, in initiative order)
> 2. Backend splits: NPC attacks auto-resolved immediately; PC attacks queued
> 3. NPC results emitted as `attack_result` SSE events
> 4. `attack_request` SSE emitted for first PC attack → player rolls to-hit (d20)
> 5. Hit → `damage_request` SSE → player rolls damage dice
> 6. Miss / damage resolved → advance queue
> 7. Queue empty → all results injected into history → LLM called → response streamed

#### `%%ATTACK%%` block format

```
%%ATTACK%%
- attacker: Goblin 1   · target: Shalelu   · bonus: +4 · damage: 1d4+2 · type: melee
- attacker: Thaelion   · target: Goblin 2  · bonus: +5 · damage: 1d8+3 · type: melee
```

Fields: `attacker` (name), `target` (name), `bonus` (e.g. `+4`, `-1`), `damage` (dice expr), `type` (`melee`|`ranged`|`spell`, default `melee`). Backend identifies PC vs NPC by comparing `attacker` against known PC names from the session. Multiple `-` lines = multiple attacks this round.

#### Backend

- [x] **CB1.5-1 — `_parse_attack_line` + `_parse_attack_block`** — `_ATTACK_BLOCK_RE` regex; same separator pattern as `_parse_combatant_line`; `"\n%%ATTACK%%"` added to `_END_MARKERS`; NOT added to `_HAS_SECTION_MARKERS_RE`.
- [x] **CB1.5-2 — `_roll_dice(expr: str) → tuple[list[int], int]`** — `_DICE_EXPR_RE` regex; `random.randint` per die; invalid expr → `([], 0)`.
- [x] **CB1.5-3 — `PendingAttack` dataclass + session attack queue** — `PendingAttack` dataclass with hit/damage resolution fields; `GameSession` gains `attack_queue: list[PendingAttack]` and `attack_results: list[dict]`.
- [x] **CB1.5-4 — NPC auto-resolution** — `_resolve_npc_attack` rolls d20+bonus vs target AC, applies HP delta via `_apply_hp_deltas`, emits `attack_result` SSE immediately; `_get_combatant_ac` and `_is_pc_attacker` helpers; `_build_attack_history_message` formats results for history injection.
- [x] **CB1.5-5 — `POST /sessions/{id}/resolve_attack_roll`** — `resolve_attack_roll()` function + endpoint; hit path leaves attack in queue for damage; miss path pops queue and returns `next_attack` info.
- [x] **CB1.5-6 — `POST /sessions/{id}/resolve_damage_roll`** — `resolve_damage_roll()` function + endpoint; applies HP delta, pops queue, returns `next_attack` info.
- [x] **CB1.5-7 — `POST /sessions/{id}/resume_combat`** — `stream_resume_combat()` appends attack history message, clears `attack_results`, delegates to `_stream_chat()`; endpoint streams SSE.
- [x] **CB1.5-8 — System prompt update** — ATTACK RESOLUTION section added to `_COMBAT_SPEC_ONGOING`; `conditions:` field documented in format spec.

#### New SSE events

- `attack_request` — `{ type, attacker, target, bonus, ac, damage_expr, attack_type }` — player must roll to-hit
- `attack_result` — `{ type, attacker, target, roll, bonus, total, ac, hit, damage_rolls, damage_total, attack_type, is_pc }` — one per resolved attack

`SseEvent` union in `api.ts`, `AttackResult` + `AttackPhase` in `types.ts` updated.

#### Frontend

- [x] **CB1.5-9 — DicePanel attack flow** — `attackPhase` prop drives to-hit and damage banners; `onAttackRoll`/`onDamageRoll` callbacks in App.tsx call resolve endpoints; auto-resume when `queue_remaining === 0`; stale-closure guard via refs.
- [x] **CB1.5-10 — DicePanel attack history** — `attackLog` prop rendered above skill-roll history; ⚔ prefix, hit/miss badge, damage total shown.
- [x] **CB1.5-11 — CombatPanel condition chips** — `conditions: list[str]` on `Combatant` dataclass; `_parse_combatant_line` parses `conditions: [prone, shaken]` field; `_serialize_combat_state` includes it; `CombatPanel` renders chips with `CONDITION_TOOLTIPS` map (17 PF1e conditions).

#### Tests

- [x] **CB1.5-T** — `tests/test_combat_attacks.py`: 43 tests. `_roll_dice` (6); `_parse_attack_line` (7); `_parse_attack_block` (3); `_is_pc_attacker` (2); `_resolve_npc_attack` (3); `resolve_attack_roll` hit+miss+no-queue (3); `resolve_damage_roll` damage+no-pending (2); `/resume_combat` injects+streams+404+409 (3); SSE integration: NPC+PC split, NPC HP update, stream filter (3); `_build_attack_history_message` hit/miss/negative-bonus/empty/multi (5); multi-attack queue miss-exposes-next/hit-blocks/damage-exposes-second (3); resolve_attack_roll damage-phase guard (1); NPC attack on 0-HP target (1); resume_combat empty results (1). `_get_combatant_ac` (4) and conditions (4) in `test_combat.py`/`test_combat_hp.py`.

---

### Tier 1.6 — Dedicated Combat System Prompt

`_build_slim_system_prompt` is a narrative GM prompt with combat sections bolted on. In combat the
priorities flip: mechanical accuracy trumps tone guidance, NPC knowledge is irrelevant, and the
LLM must not invent any numbers. This tier replaces the current ad-hoc combat injections with a
purpose-built prompt that is shorter in total tokens, more deterministic in its instructions, and
hardened against hallucinated dice outcomes. It is also the base prompt used by the per-combatant
enemy-turn query system in Tier 1.7.

> **Authority model after Tier 1.6:**
> The combat prompt owns the section tag set. `_inject_context` branches on `session.combat_state
> is not None` and assembles an entirely different system content block — no NPC profiles, no skill
> profiles, no location profiles, no `%%GENERATE%%`/`%%DELTAS%%`/`%%ROLL%%` specs. Instead it
> injects `[INITIATIVE ORDER]`, `[CURRENT HP]`, `[PC COMBAT STATS]`, and `[ACTIVE CONDITIONS]`.

#### What to strip (vs normal narrative prompt)

| Stripped | Reason |
|---|---|
| `%%GENERATE%%` spec | No new NPC stubs mid-combat; combatants already in `combat_state` |
| `%%DELTAS%%` spec | Knowledge logging can wait until after the fight |
| `%%ROLL%%` spec | Dice go through `%%ATTACK%%` + backend rolls; narrative roll flow not used |
| `%%EVENT%%` | Events re-fire after combat; suppress mid-fight to avoid prompt noise |
| NPC profile injection | Personality and knowledge blocks irrelevant while goblins are swinging |
| Skill context injection | Skills resolved mechanically in combat, not via narrative skill profiles |
| Location profile injection | Tavern ambiance does not matter during a fight |
| GM STYLE block | Mechanical accuracy beats narrative tone guidance in combat |
| `_FORMAT_EXAMPLE` | Does not apply — combat sections differ entirely |
| EVENT MAP | Active event content injected directly; full map suppressed |

#### What to add (vs normal narrative prompt)

| Added | Detail |
|---|---|
| `[INITIATIVE ORDER]` | Sorted combatant list, current actor marked; always injected |
| `[CURRENT HP]` | Authoritative HP for all combatants (promoted to top-level block) |
| `[PC COMBAT STATS]` | Full mechanical stats for every PC: AC, max HP, saves, weapon attacks; backend-authoritative — LLM reads, never writes |
| `[ACTIVE CONDITIONS]` | Non-empty `conditions` per combatant with one-line mechanical effect (e.g. "Prone: −4 AC, −4 ranged") |
| Full `%%COMBAT%%` format | Always present — no hint/fallback; full ongoing-round spec inline |
| `%%ATTACK%%` format | Always present; rules on when to omit |
| `%%HP%%` format | Always present; non-attack HP deltas |
| Anti-hallucination rules | "Never write a d20 result. Never narrate HP values. Never resolve dice yourself. Write `%%ATTACK%%` and let the backend roll." |
| Tight `%%NARRATIVE%%` spec | "1–2 paragraphs max. Physical action and immediate observable result only. No exposition, no foreshadowing." |

#### Section tag set for combat turns

```
[SECTIONS ACTIVE THIS TURN — COMBAT MODE]
%%NARRATIVE%%  — 1–2 paragraphs; physical action + immediate observable result only.
%%COMBAT%%     — always required; full format spec injected above.
%%ATTACK%%     — every attack that occurs this round; omit when no attacks happen.
%%HP%%         — non-attack HP changes only (traps, poison, healing); omit otherwise.
```

- [x] **CB1.6-1 — `_build_combat_system_prompt(session)`** — new builder function alongside
  `_build_slim_system_prompt`. Reads party list and situation from the same files (boot.md /
  recap.md). Replaces GM STYLE with a compact combat-conduct block (resolve declared actions,
  no questioning, no guessing, no invented numbers). Appends anti-hallucination rules and the
  full `%%COMBAT%%` / `%%ATTACK%%` / `%%HP%%` format specs. Does NOT append the EVENT MAP.
  Token target: ≤ 60% of the equivalent narrative prompt at the same session state.

- [x] **CB1.6-2 — `_COMBAT_SECTION_SPECS` constant** — the stripped-down `[SECTIONS ACTIVE THIS
  TURN — COMBAT MODE]` block. Used in place of `_NARRATIVE_SPEC` / `_GENERATE_SPEC` /
  `_DELTAS_SPEC` / `_ROLL_SPEC` when combat is active.

- [x] **CB1.6-3 — `_inject_context` combat branch** — when `session.combat_state is not None`,
  skip all of: `_FORMAT_EXAMPLE` injection, NPC detect + profile inject, skill detect + profile
  inject, location detect + re-inject, `_GENERATE_SPEC`, `_DELTAS_SPEC`, `_ROLL_SPEC`, and
  `_build_turn_directive`. Instead build `system_content` from `_build_combat_system_prompt`
  and append: `[INITIATIVE ORDER]` (sorted descending, current actor marked with `→`),
  `[CURRENT HP]` (existing block, promoted), `[PC COMBAT STATS]` (from `pc_profiles`
  `combat_stats` tier), `[ACTIVE CONDITIONS]` (only when any combatant has non-empty
  `conditions`), and `_COMBAT_SECTION_SPECS`. Active event content still injected directly
  (not the full EVENT MAP). Combat rules lookup (`CombatRulesIndex`) still runs.

- [x] **CB1.6-4 — Token benchmark** — `_build_combat_system_prompt` verified ≤ 60% of
  `_build_slim_system_prompt` at same session state (`test_shorter_than_slim_prompt`).
  Combat branch verified not to inject narrative-only blocks (`_NARRATIVE_SPEC`,
  `_GENERATE_SPEC`) via `TestCombatPromptDoesNotAddNarrativeBlocks`.

- [x] **CB1.6-T — Tests** — `tests/test_combat_prompt.py` (75 tests, all passing):
  `TestCombatSectionSpecs` (8), `TestBuildCombatSystemPrompt` (9), `TestInjectContextCombatBranch`
  (36), `TestPreCombatBranch` (20), `TestCombatPromptDoesNotAddNarrativeBlocks` (2). Existing
  tests in `test_inject_context.py` and `test_combat.py` updated to reflect new combat branch
  behavior (6 tests updated). Total suite: 802 pytest passing.

---

### Tier 1.7 — Enemy Turn (Per-Combatant Query Model)

The LLM currently resolves both player and enemy actions in a single open-ended response,
giving it too much authority over pacing and too many opportunities to invent stats.
Tier 1.7 splits each combat round into two explicit phases and changes the enemy-turn
interaction model entirely.

> **Architecture:** instead of asking the LLM "write `%%ATTACK%%` blocks for all enemies",
> the backend asks a tight, focused question per enemy:
> *"Goblin Warchanter's turn. She has a standard action and a move action. What does she do?"*
> The LLM returns `%%NARRATIVE%%` (one sentence) + `%%ACTION%%` (structured decision keywords).
> The backend executes the decision using authoritative data from `session.combat_state`
> (HP, AC, attack stats). No stats are re-written by the LLM.

> **Why this replaces the `_ENEMY_TURN_DIRECTIVE` approach:** a directive that asks the LLM to
> freely write `%%ATTACK%%` blocks still lets the LLM decide attack bonuses and damage dice.
> The per-combatant query gives the LLM only `action`, `target`, and flavor — the backend
> looks up the numbers. See Tier 2 SA-2/SA-6 for the complementary state and dispatch work.

- ~~[ ] **CB1.7-1 — `_ENEMY_TURN_DIRECTIVE` constant**~~ — *obsolete; superseded by
  `_build_enemy_turn_query` (CB1.7-2 below). A broad directive that asks the LLM to write
  %%ATTACK%% blocks for all enemies still gives the LLM authority over attack stats.
  The per-combatant query approach removes that authority entirely.*

- [x] **CB1.7-2 — `%%ACTION%%` block + per-combatant enemy query** — the enemy-turn interaction
  is a tight per-combatant LLM call, not an open-ended streaming turn. Two pieces:

  **`%%ACTION%%` block format** (LLM writes this when asked what a combatant does):
  ```
  %%NARRATIVE%%
  The warchanter shrieks and trains her shortbow on the sorcerer.

  %%ACTION%%
  combatant: Goblin Warchanter
  action_type: standard
  action: attack
  weapon: shortbow
  target: Yanyeeku
  ```
  Fields: `combatant` (name), `action_type` (standard|move|swift|full_round|free),
  `action` (attack|use_ability|move_toward|move_away|full_attack|withdraw|total_defense|delay|cast),
  plus `weapon`/`ability`/`spell`/`target` as required by the action type. `%%ACTION%%` added
  to `_END_MARKERS`; stripped from player stream.

  **`_build_enemy_turn_query(session, combatant_name) → str`** — builds a focused prompt
  (not the full `_build_combat_system_prompt`):
  - Header: `[ENEMY TURN: {name} — round {N}]`
  - Combatant's own stats from `session.combat_state` (HP, status, conditions)
  - Available action budget: standard + move, OR full-round (or as constrained by conditions)
  - Known attacks and abilities from the combatant's `attacks` and `abilities` fields
    (seeded from event file / SA-2 registry — see Tier 2 SA-2)
  - Active combatants list: allies with HP, enemies with AC and approximate distance
  - Instruction: write one `%%NARRATIVE%%` sentence + one `%%ACTION%%` block

  **`_parse_action_block(text) → Optional[dict]`** — parses `%%ACTION%%` into a dict.
  Returns `None` on malformed input. Unknown `action` values return `{"action": "delay"}`.

  **`stream_enemy_turn(session, combatant_name) → Generator`** — builds the query,
  calls the LLM (small payload — ~200 tokens in, ~50 tokens out), parses `%%NARRATIVE%%` +
  `%%ACTION%%`, calls `_execute_action` (SA-6), emits `token`, `attack_result`, and
  `combat_update` SSE events. Does NOT use `_stream_chat` — this is a focused call with
  its own payload builder.

- [x] **CB1.7-3 — `POST /sessions/{id}/enemy_turn` endpoint** — accepts optional body
  `{ "combatant": "Goblin Warchanter" }`; defaults to `session.combat_state.current_actor`
  if omitted. Returns 409 if `session.attack_queue` is non-empty (PC dice still pending).
  Returns 409 if `session.combat_state` is None. Returns 404 on unknown session. Calls
  `stream_enemy_turn(session, combatant_name)` and streams SSE.

- [x] **CB1.7-4 — CombatPanel "Enemy Turn" button** — rendered below "End Combat" in
  `CombatPanel`. Enabled when `attack_queue` is empty and not streaming. Disabled with
  tooltip `"Resolve PC attacks first"` while `attackPhase !== null`. App.tsx wiring:
  `onEnemyTurn` prop on CombatPanel → calls `POST /enemy_turn` → SSE stream handled
  identically to `doResumeCombat` (token/patch_last/combat_update/attack_result events).

- [x] **CB1.7-5 — Turn phase label in CombatPanel header** — small badge next to "Round N"
  showing current phase: `attackPhase !== null` → **PC Attacks** (amber); streaming during
  enemy turn → **Enemy Turn** (red); otherwise nothing. New `enemyTurnStreaming` boolean in
  App.tsx keeps this separate from the normal `streaming` flag so the send button stays
  unlocked during enemy resolution.

- [x] **CB1.7-6 — End Combat narrative** — clicking "End Combat" streams a focused LLM
  closure call before clearing. `POST /sessions/{id}/close_combat` injects the current
  combat snapshot (surviving enemies, party HP) and instructs the LLM to write 1–2
  paragraphs narrating how it ends (escape, standoff, surrender, rout). No `%%COMBAT%%`,
  `%%ATTACK%%`, or `%%ACTION%%` in response. Streams `token` SSE; `DELETE /combat` fires
  only after completion. Falls back to silent clear on LLM timeout or error.

- [x] **CB1.7-T — Tests** — pytest: `_parse_action_block` parses attack/use_ability/
  move_toward correctly; unknown `action` maps to `delay`; malformed block returns `None`;
  `_build_enemy_turn_query` includes combatant stats and active combatants list;
  `stream_enemy_turn` emits `attack_result` + `combat_update` on `action: attack`;
  `stream_enemy_turn` skips attack on `action: delay`; 409 while `attack_queue` non-empty;
  409 when `combat_state` None; 404 unknown session; `close_combat` streams tokens then
  clears; fallback-to-silent-clear on LLM error.
  Vitest: "Enemy Turn" button present in CombatPanel; disabled while `attackPhase !== null`;
  `onEnemyTurn` fires on click; phase badge shows/hides; "End Combat" shows "Closing…" state.
  Implemented in `tests/test_enemy_turn.py`,
  `ui/src/components/__tests__/CombatPanelEnemyTurn.test.tsx`,
  `ui/src/__tests__/App.enemy-turn.test.tsx`, and `ui/e2e/enemy-turn.spec.ts`.

---

### Tier 1.8 — Conditions and Death

Prerequisite for Tier 2 mechanical depth. Condition chips (CB1.5-11) are display-only; these items give them teeth.

- [ ] **CB1.8-1 — Conditions with mechanical effects** — apply PF1e penalties when a combatant has active conditions. `_apply_condition_effects(combatant)` returns AC modifier and attack modifier: Prone (−4 AC, −4 ranged attack, stand = move action), Shaken (−2 attack/saves/checks), Staggered (one standard or move action per round), Entangled (−2 attack and Reflex, no run/charge), Nauseated (move actions only). Modifiers applied in `resolve_attack_roll` and `_resolve_npc_attack` when computing hit/miss.
- [ ] **CB1.8-2 — Death and dying states** — current status `unconscious` covers 0 HP. PF1e requires graduated states: 0 HP = Disabled (can act, then falls unconscious); negative HP and above −CON = Dying (loses 1 HP/round until stabilised or dead); −CON HP or below = Dead. Backend: on HP update in `_apply_hp_deltas`, derive status automatically from HP and a `constitution` field added to `Combatant`. CombatPanel shows Disabled/Dying/Dead badges distinctly. Dying combatants automatically lose 1 HP per round in `_inject_context` unless stabilised.
- [ ] **CB1.8-3 — Healing in combat** — `%%HP%%` delta blocks already apply negative deltas (damage). Add positive delta support: `(target, +N)` raises HP up to `hp_max`. LLM uses positive deltas for cure spells, channel energy, lay on hands, potion use. `_apply_hp_deltas` already clamps at 0 min; add clamp at `hp_max`.

---

### Tier 1.9 — Initiative Authority

Mirrors Tier 1.1 (HP authority): the LLM currently writes final initiative totals in the
`%%COMBAT%%` block, which means it can hallucinate values, ignore modifiers, or repeat the
same number for every combatant. Tier 1.9 moves initiative rolls to the backend on round 1
and treats the LLM's `init:` field as a **modifier** (e.g. `+3`, `−1`) rather than a total.

> **Authority model after Tier 1.9:**
> - **Round 1:** LLM writes `init: <modifier>` for each combatant. Backend rolls `1d20 +
>   modifier` for every combatant and stores the result. For PCs, the modifier is read from
>   `pc_profiles[*]["combat_stats"]["initiative"]` and the LLM's value is ignored entirely.
> - **Round 2+:** Backend retains its own initiative values; `init:` columns in subsequent
>   `%%COMBAT%%` lines are silently discarded (same pattern as HP authority from Tier 1.1).

- [ ] **CB1.9-1 — `_COMBAT_SPEC_ROUND1` format update** — change `init:` field description
  from "initiative score" to "initiative modifier (e.g. `+3`, `−1`); backend will roll
  `1d20 + modifier`". Update `_COMBAT_SPEC_ONGOING` to state "omit `init:` — backend owns
  initiative order from round 1 onward".

- [ ] **CB1.9-2 — Server-side initiative roll on round 1** — in `_parse_combat_block`, when
  `existing_state is None` (first parse): for each combatant extract the `init:` field as a
  signed integer modifier; roll `random.randint(1, 20) + modifier`; store the result as
  `combatant.initiative`. For PCs (name matches `pc_profiles` key), use the modifier from
  `pc_profiles[name]["combat_stats"]["initiative"]` instead of the LLM-written value.
  `_parse_combatant_line` updated to return the raw `init:` string; conversion and rolling
  happen in `_parse_combat_block` where `existing_state` context is available.

- [ ] **CB1.9-3 — Initiative preserved on round 2+** — in `_parse_combat_block` when
  `existing_state is not None`, copy `initiative` from the matching existing combatant by
  name (same lookup as HP authority). New combatants entering after round 1 still get
  server-rolled initiative from their `init:` modifier field.

- [ ] **CB1.9-4 — `[PARTY ROSTER]` init values updated** — `_build_pc_combat_roster` currently
  writes the raw initiative modifier string (e.g. `+2`). After CB1.9-2 the roster should
  still write the modifier (not a pre-rolled value) so the LLM can copy it into `init:` for
  the backend to roll. No change needed to the roster builder — just confirm the format
  remains a modifier, not a total.

- [ ] **CB1.9-T — Tests** — `test_combat.py`: round-1 block with `init: +3` stores a value
  in `[4, 23]` (d20 + 3); PC name in `pc_profiles` uses stored modifier and ignores
  LLM value; round-2 block preserves existing initiative; new combatant on round 2 gets
  fresh roll; `init: 0` and `init: −1` edge cases; two combatants with the same modifier
  get independent rolls (not the same value). `test_inject_context.py`: `_COMBAT_SPEC_ROUND1`
  no longer describes `init:` as a total.

---

### Tier 1.10 — Combat Turn Auto-Speaker

When the current turn advances in the combat tracker, automatically update the active chat speaker to match.

- [x] **CB1.10-1 — PC turn → auto-activate speaker** — when `currentCombatantName` is a PC,
  `inputActiveSpeaker` in App.tsx resolves to that PC's character data (`name`, `rune`, `color`,
  `isEnemy: false`). The InputBar shows the PC's portrait and "Speaking as" badge.
  *(Shipped in combat-active-character feature — `inputActiveSpeaker` computed from
  `currentCombatantName` via `characterMap` lookup; `CombatState.current_actor` drives the value.)*

- [x] **CB1.10-2 — Enemy turn → hostile input state** — when `currentCombatantName` is an enemy
  (not in `characterMap`), `inputActiveSpeaker` has `isEnemy: true`. InputBar shows skull icon,
  red hostile class, enemy name label, and a taunting placeholder phrase (deterministic per name).
  *(Shipped in combat-active-character feature — `InputBar.tsx` hostile state, `SkullIcon`
  component, `ENEMY_TAUNTS` pool. Tested in `InputBarHostile.test.tsx`.)*

- [ ] **CB1.10-3 — Manual override preserved** — if the player manually clicks a different
  character in the sidebar mid-turn, that selection takes precedence over the initiative-driven
  speaker and is not overwritten until the *next* `advance_turn` or `combat_update`. Requires
  a `combatSpeakerOverride: string | null` state in App.tsx; cleared on each `advance_turn`
  response or `combat_update` that changes `current_actor`.

- [ ] **CB1.10-T — Tests (remaining)** — Vitest: `combatSpeakerOverride` set when player
  clicks sidebar character during combat; InputBar shows override speaker (not initiative actor);
  override cleared when turn advances; enemy-speaker hostile state tests already in
  `InputBarHostile.test.tsx`.

---

### Tier 2 — Server-Authoritative State

**The foundational shift: the backend, not the LLM, is the single source of truth for everything displayed on screen.**

Currently, every piece of data the UI shows during combat — who is in the fight, their HP, AC, conditions, whose turn it is — flows through the LLM's `%%COMBAT%%` messages. That means the UI is only as accurate as the LLM's memory. The LLM can drift initiative, forget damage, invent stats, and resurrect dead enemies. This tier ends that dependency.

After this tier:
- `sessions/session_NNN/state.json` is the authoritative record of all game state: combatants, HP, AC, conditions, round, active character, active events. It persists across restarts.
- The LLM reads state via injected `[CURRENT HP]` / `[INITIATIVE ORDER]` blocks. It never writes HP, AC, initiative, or combatant lists directly.
- The `%%COMBAT%%` block is used only on round 1 to introduce new combatants (name + initiative modifier). After that, it is stripped and ignored.
- All state mutations happen through backend endpoints with discrete, validated writes to `state.json`.
- The frontend receives `state_changed` SSE events and reads authoritative state via `GET /api/sessions/{id}/state`. It no longer derives state from LLM token content.

> **Relationship to Tiers 1.7–1.10:** Tier 1.7 (enemy turn) shipped the query/parse/UI shell
> against current `session.combat_state`. SA-1 and SA-2 remain important follow-ups because
> they will replace Tier 1.7's fallback enemy attack profile with authoritative event/bestiary
> stats. Tiers 1.8 (conditions) and 1.9 (initiative) are also consumers of this authority model.

#### SA-1 — Full `state.json` schema

`sessions/session_NNN/state.json` already holds the current visible game state:

```json
{
  "mode": "combat",
  "round": 2,
  "events": ["goblin_attack_starts"],
  "active_character": "Yanyeeku",
  "combatants": [
    { "name": "Yanyeeku",  "hp_current": 18, "hp_max": 22, "ac": 16, "initiative": 14, "status": "active", "conditions": [] },
    { "name": "Goblin 1",  "hp_current": 3,  "hp_max": 5,  "ac": 13, "initiative": 11, "status": "active", "conditions": ["shaken"] }
  ]
}
```

`active_character` doubles as `current_actor` during combat (set to `session.combat_state.current_actor`). A dedicated `current_actor` field at the top level is deferred to SA-4 when the frontend needs to distinguish player-selected character from initiative actor.

- [x] **CB2-SA1 — Extend `_write_session_state`** — `combatants` array serialised when combat active; cleared to `[]` when `combat_state` is None. Template (`sessions/state.template.json`) updated to include `combatants: []`. Spec (`specs/session-state.feature`) updated: story, background, AC-001/002/011/012/Out-of-Scope. `_write_session_state` docstring updated.
- [x] **CB2-SA1-T — Tests** — `test_session_state.py` extended: `TestTemplate` checks `active_character`+`combatants` keys and defaults; `TestBootInit` checks `combatants: []` on boot; `TestCombatStateChanges` asserts combatants are serialised with correct names; `TestOutputValidity` checks `combatants` key always present; `TestBootOverwrite` checks `combatants: []` after reset; new `TestCombatantsSerialization` (5 tests) covers all fields, HP-after-damage, multi-combatant, clear-to-empty. 42 tests total, all passing.
- [ ] **CB2-SA1-2 — Separate `current_actor` field** — add `current_actor` as a distinct top-level field in `state.json` (separate from `active_character`) so SA-4 frontend can distinguish player-selected character from initiative actor. Depends on SA-4.

#### SA-2 — Encounter pre-load (event files + bestiary)

Currently the LLM invents all combatant stats in the first `%%COMBAT%%` block. Replace this
with a two-source seeding system. **Source 1:** a structured `COMBATANTS` table in the event
file (already present in prose; made machine-readable). **Source 2:** `adventure_path/09_monsters/`
bestiary files (Tier 2 SA-4). Source 1 is the short-term practical path; Source 2 centralises
stats long-term. Both feed `session.pending_combatants`; bestiary overrides event file when both
exist.

> **Event file format** — add a markdown table under `## Combatants` in each event file:
> ```markdown
> ## Combatants
> | name | hp | ac | init_mod | attacks |
> |------|----|----|----------|---------|
> | Goblin Warchanter | 8 | 14 | +3 | shortbow +5 (1d4+1), bite +1 (1d4) |
> | Goblin 1 | 5 | 16 | +2 | dogslicer +2 (1d4), shortbow +4 (1d4) |
> ```
> The existing prose combat stats in `goblin_attack_starts.md` already contain this data —
> the table makes it machine-readable without changing the narrative content.

- [ ] **CB2-SA2-1 — `_parse_event_combatants(event_content) → dict[str, dict]`** — reads the
  `## Combatants` markdown table from an event file's content. Returns a dict keyed by name
  (case-insensitive) with `hp`, `ac`, `init_mod`, `attacks` (list of parsed attack dicts).
  Tolerant: if the section is absent or malformed, returns `{}` (graceful fallback — LLM
  values used as before).

- [ ] **CB2-SA2-2 — Seed `session.pending_combatants` on event fire** — `_process_event_block`
  (already exists) gains a seeding step: calls `_parse_event_combatants(ev.content)` and
  merges results into `session.pending_combatants: dict[str, dict]`. `pending_combatants`
  is a new field on `GameSession` (default `{}`). Existing combatants (already in
  `session.combat_state`) are not overwritten.

- [ ] **CB2-SA2-3 — Override LLM-written stats on round 1** — in `_parse_combat_block`, when
  `existing_state is None` (round 1): for each parsed combatant, look the name up in
  `session.pending_combatants`. Where an entry exists, replace HP/AC with seeded values and
  store the `attacks` list on the `Combatant` (requires new `attacks: list` field). Log a
  `[EVENT SEED]` debug line. LLM-invented stats still used for combatants with no seed entry.
  After seeding, entries are removed from `pending_combatants`.

- [ ] **CB2-SA2-4 — `CombatantRegistry` loader (bestiary)** — `api/context/combatant_registry.py`.
  Reads markdown stat blocks from `adventure_path/09_monsters/` (Tier 2 SA-4). Same lazy-loading
  pattern as `SkillIndex`. Overrides event-file values when a canonical entry exists.

- [ ] **CB2-SA2-T — Tests** — `_parse_event_combatants` reads table correctly; returns `{}` on
  missing section; `_parse_combat_block` uses event-file HP, ignores LLM-written HP; fallback
  to LLM value when no seed entry; `attacks` list populated on `Combatant`; `pending_combatants`
  cleared after round-1 seeding; bestiary overrides event file for same name.

#### SA-3 — State read endpoint

- [ ] **CB2-SA3 — `GET /api/sessions/{id}/state`** — returns the full current `state.json` content as JSON. Frontend polls this or uses it to hydrate after a reconnect. Returns 404 on unknown session. Returns the on-disk file if `session.combat_state` is None (social mode). Does NOT trigger a file write — reads from the in-memory `GameSession` serialised on the fly, same structure as `state.json`.

#### SA-4 — Frontend reads state from backend

Replace the pattern where the frontend derives `combatState` from LLM-generated SSE tokens with one where the `combat_update` SSE event is emitted by the backend after its own state write (not by parsing the LLM response). The event carries the same `CombatState` payload as today — the SSE contract does not change — but the data is now authoritative.

- [ ] **CB2-SA4-1 — `combat_update` emitted after state write, not after LLM parse** — `_write_session_state` (or the call sites that call it) emit the `combat_update` SSE event. This means the UI update is driven by the backend's state transition, not by the LLM's text. Existing `combat_update` consumer in `App.tsx` is unchanged.
- [ ] **CB2-SA4-2 — Remove combatant data from LLM token stream entirely** — `%%COMBAT%%` is already stripped from the player-visible token stream in non-dev mode. After this item it is also stripped in dev mode; the dev display instead shows a `[COMBAT STATE UPDATED]` marker so testers can see when a state transition occurred without seeing raw block text.
- [ ] **CB2-SA4-T — Tests** — Playwright: CombatPanel HP values after an attack reflect `state.json`, not LLM token content; `state.json` HP matches CombatPanel display.

#### SA-5 — Deprecate `%%COMBAT%%` for ongoing rounds

After round 1 the LLM no longer needs to write `%%COMBAT%%` blocks. Backend owns round advancement, combatant list, and all numeric fields.

- [ ] **CB2-SA5-1 — System prompt update** — `_COMBAT_SPEC_ONGOING` drops all `%%COMBAT%%` instructions. LLM is told: *"Do not write `%%COMBAT%%` blocks. State is managed by the backend. Write `%%NARRATIVE%%` and `%%ATTACK%%` only."* `_COMBAT_SPEC_ROUND1` retains the combatant-introduction format (names + initiative modifiers + conditions only — no HP or AC; those come from the registry).
- [ ] **CB2-SA5-2 — Parser no longer accepts HP/AC from LLM after round 1** — already partially done via Tier 1.1. This item hardens it: `%%COMBAT%%` blocks on turns where `session.combat_state is not None` are fully ignored for stat fields; only new-combatant lines (names not yet in state) are processed.
- [ ] **CB2-SA5-T** — Tests confirm `%%COMBAT%%` on round 2+ does not mutate HP; new combatant entering round 2 IS added; session state correct after full round trip.

#### SA-6 — `%%ACTION%%` execution dispatch

The `%%ACTION%%` block (defined in Tier 1.7 CB1.7-2) needs a backend execution layer that maps
the parsed decision keywords to the correct game mechanics. This is the execution side of the
enemy query system; Tier 1.7 is the query/parse side.

> **Dispatch table:**
> | `action` keyword | Execution |
> |---|---|
> | `attack` | `_resolve_npc_attack` with stats from `combatant.attacks` (seeded in SA-2) |
> | `full_attack` | Two `_resolve_npc_attack` calls for the same combatant (primary + secondary) |
> | `use_ability` | Look up `ability` in `combatant.abilities`; apply effect (e.g. `inspire_courage` buffs allies; logged, mechanical effect in CB1.8) |
> | `move_toward` / `move_away` | Update `combatant.position` if position tracking is active; otherwise log for narrative purposes only |
> | `withdraw` | Set `combatant.status = "fled"` at end of turn; no attacks provoked |
> | `total_defense` | Apply `+4 AC` condition for one round (requires CB1.8 conditions) |
> | `cast` | Delegate to Tier 4 `%%CAST%%` handler |
> | `delay` (or unknown) | Skip turn; advance initiative; log warning |

- [ ] **CB2-SA6-1 — `_execute_action(session, action_dict) → list[dict]`** — dispatch function.
  Takes the parsed `%%ACTION%%` dict, looks up the combatant in `session.combat_state` by name,
  and routes to the appropriate handler. Returns a list of result dicts (same shape as
  `_resolve_npc_attack` returns) for SSE emission. Emits `attack_result` SSE events inline.
  Updates `session.combat_state` and calls `_write_session_state` after each mutation.

- [ ] **CB2-SA6-2 — `combatant.attacks` and `combatant.abilities` fields** — `Combatant` dataclass
  gains `attacks: list = field(default_factory=list)` and `abilities: list = field(default_factory=list)`.
  Each attack: `{"name": "shortbow", "bonus": 5, "damage": "1d4+1", "type": "ranged"}`.
  Each ability: `{"name": "inspire_courage", "action_type": "standard", "effect": "..."}`.
  Populated from SA-2 seeding. Serialised in `_serialize_combat_state` and `state.json`.
  `_resolve_npc_attack` gains a path that reads `bonus` and `damage` from the attack dict
  when available (overriding the caller-supplied values).

- [ ] **CB2-SA6-T — Tests** — `_execute_action` with `action: attack` calls `_resolve_npc_attack`;
  with `action: delay` skips and returns `[]`; unknown action returns `[]` and logs warning;
  `attacks` field populated after SA-2 seeding; `_serialize_combat_state` includes attacks
  and abilities; `state.json` written after `_execute_action`.

---

### Tier 3 — Advanced Attack Mechanics

Builds on Tier 1.5 and Tier 2. The `%%ATTACK%%` format is already established; Tier 3 adds PF1e mechanical depth.

- [ ] **CB2-1 — Critical hits** — `%%ATTACK%%` line gains optional `crit_range: 18` (default 20) and `crit_mult: 2` fields. Backend: if natural d20 roll ≥ `crit_range`, roll a confirmation attack (same bonus vs same AC); if confirmed, multiply damage by `crit_mult`. `attack_result` event gains `critical: bool`. DicePanel history shows `⚔ CRITICAL HIT (×2)`.
- [ ] **CB2-2 — Iterative attacks** — `%%ATTACK%%` line gains optional `sequence: 1/2/3` field. Parser groups lines by attacker; `sequence` is informational (bonus already accounts for the -5/-10 penalty). Backend resolves each line independently in order. No new resolve flow needed — same queue.
- [ ] **CB2-3 — Combat manoeuvres (CMB/CMD)** — `type: manoeuvre` + `manoeuvre: trip|bull_rush|grapple|disarm|sunder`. Backend: roll CMB vs target CMD (from combatant stats — requires `cmd` field added to `%%COMBAT%%` format). On success, inject corresponding condition into target's next `%%COMBAT%%` update. `attack_result` event includes `manoeuvre` and `success` fields.
- [ ] **CB2-4 — Attack of Opportunity** — `%%ATTACK%%` line gains `trigger: aoo` field. Resolved exactly like a normal attack; `attack_result` event includes `aoo: true`. DicePanel history labels it `⚔ AoO`. No separate flow needed.

---

### Tier 4 — Spells and Area Effects

Extends the combat loop with spell casting, area targeting, and saving throws. No canvas grid —
mechanical depth over visual positioning.

- [ ] **CB3-1 — `%%CAST%%` block** — `spell: Fireball · level: 3 · dc: 14 · save: Reflex · half_on_save: true · targets: [Goblin 1, Goblin 2, Shalelu]`. Backend resolves a Reflex save per target (d20 + target save bonus vs DC); full damage on fail, half on save. Damage rolled once, applied per-target. Emits `save_result` SSE per target + `combat_update`. `%%CAST%%` stripped from player stream.
- [ ] **CB3-2 — Spell slot tracking** — add `spell_slots: { [level]: { max: N, used: N } }` to PC character JSON. CharacterSidebar shows pip rows per spell level. `%%CAST%%` decrements the correct level slot; `slot_update` SSE event; CharacterSidebar updates immediately. Slot state persisted in `session.spell_slots` dict keyed by PC name.
- [ ] **CB3-3 — AoE condition effects** — `%%CAST%%` gains `on_fail_condition: prone` field. Backend applies the condition to failing targets in `combat_state`. Existing condition chip machinery (CB1.5-11) handles display.
- [ ] **CB3-4 — Concentration tracking** — `%%CAST%%` with `concentration: true` sets a `concentrating_on` field on the caster's combatant entry. If the caster takes damage while concentrating, backend automatically queues a Concentration check (DC = 10 or half damage taken, whichever is higher) as a `roll_request` event — same flow as skill checks.
