# Known Bugs

Consolidated bug tracker. All open bugs are listed here regardless of area. Fixed bugs are kept in the **Resolved** section for regression context.

**Markup rules**
- `- [ ] **ID — title**` — open bug
- `- [x] **ID — title**` — resolved bug
- `- ~~[ ] **ID — title**~~` — obsolete / invalid

---

## Open

### Combat

- [ ] **B-C01 — Enemy turn dev mode: raw LLM output not visible** — In dev mode the enemy turn
  response shows only the flavor sentence; `%%NARRATIVE%%`, `%%ACTION%%`, and any other sections
  the LLM wrote are stripped before reaching the UI. `stream_enemy_turn` uses a blocking call
  and manually yields only the narrative portion as a `token` event, bypassing the dev-mode
  passthrough that `_stream_with_narrative_filter` normally provides.
  **Fix:** Add a dev mode path in `stream_enemy_turn` that yields the full raw response text
  before parsing, so developers can see exactly what the LLM returned.
  *(spec: enemy-turn.feature AC-007; api/session_manager.py `stream_enemy_turn`)*

- [x] **B-C02 — Speaker prefix uses session activeCharacter, not combat initiative speaker** —
  When it is a PC's turn (e.g. Yanyeeku is current initiative actor) and the player types
  "I attack with firebolt", the message is sent and displayed as generic `player` input instead
  of being prefixed `@Yanyeeku: "..."`. `handleSend` in `App.tsx` reads from `activeCharacter`
  (player-selected character) for the prefix, not from `inputActiveSpeaker` (the
  combat-initiative-driven speaker).
  **Fix:** When combat is active and `currentCombatantName` matches a PC in `characterMap`,
  `handleSend` uses that PC as the speaker — covers both the UI bubble and the `@Name: "..."` prefix sent to the LLM.
  *(spec: combat-active-character.feature AC-008; ui/src/App.tsx `handleSend`)*

- [ ] **B-C03b — PC HP shows as 0/0 in combat — pc_profiles not populated** — Even if the LLM
  writes HP, PCs should start at their `hp_max` from `_build_pc_combat_roster`. The roster reads
  `pc_profiles[*]["combat_stats"]["hp_max"]`. If this is 0, the JSON files are either missing
  the `hp.max` field or the field path in `_build_pc_profiles` doesn't match.
  **Fix:** Verify `player_*.json` files have `hp.max` populated and that `_build_pc_profiles`
  reads the right path. Add a pytest assertion that a session built from the real player JSON
  files has non-zero `hp_max` for each PC in `pc_profiles`.
  *(spec: combat-hp.feature; api/session_manager.py `_build_pc_profiles`)*

- [ ] **B-C04 — Enemy turn LLM outputs unrecognized `%%` sections** — The LLM returns sections
  like `%%COMBAT%%` and `%%ATTACK%%` inside the enemy turn response even though
  `_ENEMY_TURN_SYSTEM` asks for only `%%NARRATIVE%%` + `%%ACTION%%`. The LLM has learned the
  combat section pattern from regular turns and defaults to it.
  **Fix:** Strengthen `_ENEMY_TURN_SYSTEM` with an explicit prohibition list: *"Write ONLY
  %%NARRATIVE%% then %%ACTION%%. Do NOT write %%COMBAT%%, %%ATTACK%%, %%HP%%, %%ROLL%%,
  %%GENERATE%%, %%DELTAS%%, or %%EVENT%%."* Add a dev-mode warning that logs the full LLM
  response when unexpected sections are detected (complements B-C01).
  *(spec: enemy-turn.feature AC-006; api/session_manager.py `_ENEMY_TURN_SYSTEM`)*

- [ ] **B-C05 — Combatants grouped instead of individual (e.g. "Goblin Warriors (4)")** — The
  CombatPanel shows a single row `Goblin Warriors (4)` instead of four separate rows `Goblin 1`
  through `Goblin 4`. The LLM uses group notation because `goblin_attack_starts.md` describes
  them as "Goblin warriors (4–6)" in prose.
  **Fix (two parts):**
  - *Event file:* Add an explicit individual-entry `## Combatants` table to
    `adventure_path/02_events/goblin_attack_starts.md` listing each goblin by name.
  - *Prompt:* Add to `_COMBAT_SPEC_ROUND1`: *"List EVERY combatant as a SEPARATE line —
    never use group notation like 'Goblin Warriors (3)'. Each individual gets its own
    `- name: …` row."*
  *(spec: combat-tracker.feature; enemy-turn.feature)*

- [x] **B-C09 — Turn counter does not advance after PC attack resolves** — After a PC completes their attack (rolls to-hit + damage, `stream_resume_combat` narrates the outcome), the initiative tracker stays on the same combatant. The GM must click "Next Turn →" manually to move to the next actor. For enemy turns, `advance_combat_turn` already fires automatically at the end of `stream_enemy_turn`; the same behaviour is missing from the PC path.
  **Fix:** At the end of `stream_resume_combat`, call `advance_combat_turn(session)` before emitting the final `combat_update` SSE, so the next combatant is highlighted without a manual click.
  *(api/session_manager.py `stream_resume_combat`; mirrors the enemy-turn fix in `stream_enemy_turn`)*

---

### Code Quality

- [ ] **B-Q01 — Inline `import('./types')` in `rollInitiatives` return type** — `api.ts`
  `rollInitiatives` uses an inline dynamic import in its return type annotation
  (`Promise<{ combat_state: import('./types').CombatState }>`). Every other function in the file
  uses a pre-imported type. Minor but inconsistent.
  **Fix:** Add `CombatState` to the top-level `import type` in `ui/src/api.ts`.
  *(ui/src/api.ts `rollInitiatives`)*

---

## Resolved

- [x] **B-R01 — Combatants not sorted by initiative in `roll_initiatives` response** — After
  rolling, `_serialize_combat_state` returned `state.combatants` in insertion order. Spec AC-007
  requires the list sorted descending by initiative.
  **Fixed:** `session.combat_state.combatants.sort(key=lambda c: c.initiative, reverse=True)`
  added before `_write_session_state` in `roll_combat_initiatives`.
  *(api/session_manager.py; fixed June 2026)*

- [x] **B-R02 — `btn-xs` CSS class undefined** — `CombatPanel.tsx` applied class
  `btn btn-secondary btn-xs` to the Roll Initiatives button, but `index.css` had no `.btn-xs`
  rule, causing the button to render at unstyled size.
  **Fixed:** `.btn-xs { padding: 0.1rem 0.4rem; font-size: 0.72rem; }` added to `index.css`.
  *(ui/src/index.css; fixed June 2026)*

- [x] **B-C03a — All combatant HP shows as 0/0 after combat starts** — `_build_combat_system_prompt`
  contained *"Never write hp: for existing combatants"* baked into the base prompt for ALL rounds.
  The LLM obeyed it on round 1 too, producing every combatant at 0/0.
  **Fixed:** HP conduct rule made round-conditional: "Round 1 ONLY: MUST include `hp: cur/max`
  — backend seeds HP from these values. Round 2+: NEVER write `hp:`." Tests added in
  `TestCombatPromptHPConductRule` (4 tests).
  *(api/session_manager.py `_build_combat_system_prompt`; spec: combat-system-prompt.feature)*

- [x] **B-C07 — `POST /enemy_turn` returns 409 during active combat** — When the LLM wrote
  `%%ATTACK%%` blocks inside `stream_resume_combat` narration, PC attacks were added to
  `session.attack_queue` but the `attack_request` SSE events were ignored by `doResumeCombat`,
  leaving `attackPhase` null while the backend queue was non-empty.
  **Fixed (two parts):** Backend clears `session.attack_queue` before the LLM call in
  `stream_resume_combat`; frontend `doResumeCombat` now handles `attack_request` and
  `attack_result` events. Tests: `TestResumeCombatClearsStaleQueue` (3 pytest),
  `TestEnemyTurnStaleQueue` (2 pytest), regression test in `App.test.tsx` (2 Vitest).
  *(spec: enemy-turn.feature AC-010)*

- [x] **B-C08 — `App.enemy-turn.test.tsx` `bootIntoCombat` helper times out** — `closeCombat`
  and `resumeCombat` mocks returned `undefined`; `for await (... of undefined)` threw TypeError
  and corrupted component state.
  **Fixed:** Both mocks now return `(async function* () {})()`. Three tests wrapped in `waitFor`.
  *(ui/src/__tests__/App.enemy-turn.test.tsx)*

- [x] **B-C06 — Initiatives are LLM-invented totals, not rolled from modifiers** — LLM wrote
  arbitrary initiative totals (e.g. every goblin at 12) rather than rolling d20 + modifier.
  **Fixed:** Fully replaced by Tier 1.8 initiative roller — `roll_combat_initiatives()` backend
  function + `POST /combat/roll_initiatives` endpoint + 🎲 Roll Initiatives button in
  CombatPanel. LLM-written initiatives are no longer authoritative.
  *(api/session_manager.py; spec: roll-initiatives.feature)*

- [x] **B-DX01 — `handleDamageRollClick` passes die sides instead of rolled values** — `pending`
  stores die sides (e.g. `[8]` for a d8), not rolled values. `handleDamageRollClick` passed
  `pending` directly as `rolls`, so `onDamageRoll([8], 8)` was called instead of the actual
  d8 result.
  **Fixed:** `pending.map(rollDie)` replaces `[...pending]`. Vitest test added.
  *(ui/src/components/DicePanel.tsx `handleDamageRollClick`)*
