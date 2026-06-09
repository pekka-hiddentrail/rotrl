# Feature Specification Index

Quick reference for finding relevant specifications. Use tags to match PR changes to affected specs.

---

## Feature Files

| Feature File | Domain | Tags | ACs | Key Components |
|-------------|--------|------|-----|----------------|
| [session-boot.feature](session-boot.feature) | Backend | `@session` `@boot` `@intro` | 5 | `create_session()`, `boot.md`, `intro` endpoint, `NpcIndex` |
| [player-turn.feature](player-turn.feature) | Backend \| Frontend | `@turn` `@streaming` `@core` | 5 | `stream_turn()`, SSE token events, section filter |
| [session-end-recap.feature](session-end-recap.feature) | Backend \| Frontend | `@session` `@recap` `@end` `@llm` | 4 | `stream_end_session()`, `recap.md`, `boot.md`, `notes.json` |
| [llm-providers.feature](llm-providers.feature) | Backend \| Frontend | `@llm` `@groq` `@ollama` `@provider` | 6 | Groq API, Ollama API, rate-limit headers, `stream_options` fallback, `Header.tsx` model dropdown |
| [context-detection.feature](context-detection.feature) | Backend | `@context` `@npc` `@skill` `@location` `@token` | 7 | `NpcIndex`, `SkillIndex`, `context` SSE event, `format_short_context()` stub vs full-profile skill gate |
| [location-system.feature](location-system.feature) | Backend | `@location` `@index` `@generator` `@context` `@injection` | 9 | `LocationIndex`, `location_lookup.py`, `03_locations/`, `scene_locations`, `%%GENERATE%%` stub |
| [response-parsing.feature](response-parsing.feature) | Backend | `@parsing` `@sections` `@narrative` `@streaming` | 6 | Streaming filter, holdback buffer, `patch_last` event, `%%NARRATIVE%%` retry guard |
| [npc-system.feature](npc-system.feature) | Backend | `@npc` `@index` `@generator` `@knowledge` `@deltas` | 6 | `NpcIndex`, `npc_generator.py`, `base.md`, `knowledge.md` |
| [skill-system.feature](skill-system.feature) | Backend | `@skill` `@detection` `@injection` `@dc` | 5 | `SkillIndex`, `skill_lookup.py`, `04_rules/skills/` |
| [session-logging.feature](session-logging.feature) | Backend \| Frontend | `@logging` `@session-log` `@api-log` `@dice` | 10 | `api_logger.py`, `*.log.md`, `api_log/`, `section_format_ok`, `ApiLogPanel.tsx` |
| [session-controls.feature](session-controls.feature) | Frontend | `@header` `@boot` `@provider` `@controls` | 8 | `Header.tsx`, provider toggle, model dropdown, rate-limits badge, kill button, API Logs button |
| [chat-display.feature](chat-display.feature) | Frontend | `@chat` `@streaming` `@bubbles` `@markdown` | 7 | `ChatWindow.tsx`, `MessageBubble.tsx`, thinking indicator |
| [dice-panel.feature](dice-panel.feature) | Frontend | `@dice` `@roll` `@pending-roll` `@history` | 15 | `DicePanel.tsx`, `resolve_roll` endpoint, skill bonus auto-apply, active character integration, `pendingRoll.speaker` fallback speaker, hidden before session boot |
| [character-system.feature](character-system.feature) | Frontend | `@character` `@sidebar` `@sheet` `@data` | 13 | `CharacterSidebar.tsx`, `CharacterSheet.tsx`, `useCharacters`, `loadCharacterSheet`, active character state, speaker badge |
| [intent-bar.feature](intent-bar.feature) | Frontend | `@intent` `@context` `@tags` `@sse` | 5 | `IntentBar.tsx`, `context` SSE event |
| [system-prompt.feature](system-prompt.feature) | Backend | `@prompt` `@injection` `@boot` `@per-turn` `@groq` | 10 | `_build_slim_system_prompt()`, per-turn copy, Groq cap, `_FORMAT_EXAMPLE`, `_COMBAT_FULL_SPEC`, `_NARRATIVE_SPEC`, `_ROLL_SPEC`, `_GENERATE_SPEC`, `_DELTAS_SPEC`, `_build_pc_profiles()` |
| [startup-hardening.feature](startup-hardening.feature) | Runtime / Tooling | `@startup` `@windows` `@dev-tooling` `@process-cleanup` | 7 | `dev.py` `_free_port()` `_kill_tree()`, `start_backend.ps1`, `start_ui.ps1` |
| [event-injection.feature](event-injection.feature) | Backend | `@event` `@injection` `@context` `@parsing` `@session` | 9 | `EventIndex`, `active_events`, `%%EVENT%%` parser, event map in system prompt, `EventEntry.event_type` metadata |
| [event-temperature-mvp.feature](event-temperature-mvp.feature) | Backend | `@event` `@temperature` `@scheduler` `@session` `@state` | 13 | `event_runtime` state snapshot, readiness tick, threshold roll, pity trigger, active lockout, prompt [ACTIVE EVENT] context, scheduler logging, zone-location dependency — `tests/test_event_scheduler.py` |
| [event-chain-runtime.feature](event-chain-runtime.feature) | Backend | `@event` `@chain` `@runtime` `@session` `@state` | 8 | `active_chain_id`/`active_node_id`, hard transitions, chain lock, chain persistence, prompt [CHAIN STATE] context |
| [event-temperature-stability.feature](event-temperature-stability.feature) | Backend | `@event` `@temperature` `@stability` `@interrupt` `@cooldown` | 8 | readiness vs urgency, interrupt policy, pending_interrupt queue, multi-event arbitration, cooldowns, max-fires, optional decay |
| [event-status-panel.feature](event-status-panel.feature) | Backend \| Frontend | `@event` `@temperature` `@scheduler` `@debug` `@ui` `@api` | 15 | `GET /api/sessions/{id}/event_status`, `EventStatus.tsx`, readiness bars, threshold markers, status badges, TTL bar, auto-refresh — `tests/test_event_status.py` |
| [combat-tracker.feature](combat-tracker.feature) | Backend \| Frontend | `@combat` `@parsing` `@session` `@streaming` `@layout` | 18 | `CombatState`, `Combatant`, `_parse_combat_block`, `CombatPanel.tsx`, `HpBar.tsx`, `combat_update` SSE, `DELETE /combat`, per-turn combat reminder, `CombatRulesIndex`, condition chips, `currentCombatantName`, highlight advance, enemy-turn controls |
| [combat-hp.feature](combat-hp.feature) | Backend | `@combat` `@hp` `@session` `@parsing` | 10 | `_parse_combat_block(existing_state)`, `_parse_hp_deltas`, `_apply_hp_deltas`, `%%HP%%` block, `[CURRENT HP]` context injection, `_COMBAT_SPEC_ROUND1`, `_COMBAT_SPEC_ONGOING`, HP-status guard |
| [attack-resolution.feature](attack-resolution.feature) | Backend \| Frontend | `@combat` `@attack` `@dice` `@session` `@streaming` `@parsing` | 9 | `_parse_attack_block`, `_roll_dice`, `PendingAttack`, `_resolve_npc_attack`, `resolve_attack_roll`, `resolve_damage_roll`, `stream_resume_combat`, `attack_request`/`attack_result` SSE, `AttackPhase`, `DicePanel` attack banners |
| [enemy-turn.feature](enemy-turn.feature) | Backend \| Frontend | `@combat` `@enemy` `@action` `@session` `@streaming` `@layout` | 18 | `_ENEMY_TURN_SYSTEM`, `_build_enemy_turn_system`, `_build_enemy_turn_user`, `_parse_action_block` (if_hit/if_miss), `stream_enemy_turn` (action_card SSE, auto-advance), `POST /enemy_turn`, close-combat, `Message` role `combat-event`, `MessageBubble.tsx` action card, `CombatEventCard.test.tsx` |
| [player-bubble-speaker.feature](player-bubble-speaker.feature) | Frontend | `@chat` `@bubbles` `@character` `@speaker` `@identity` | 6 | `MessageBubble.tsx`, `types.ts` `MessageSpeaker`, `App.tsx` speaker snapshot, `index.css` |
| [token-benchmark.feature](token-benchmark.feature) | Backend \| Frontend \| Infrastructure | `@benchmark` `@api-log` `@token` `@quality-of-life` | 10 | `GET /api/benchmarks`, `GET /api/benchmarks/combat`, `outputs/token_benchmarks.csv`, `outputs/token_benchmarks_combat.csv`, `TokenBenchmarks.tsx`, `test_token_benchmark.py`, `Header.tsx` Benchmarks button |
| [splash-hints.feature](splash-hints.feature) | Frontend | `@splash` `@hints` `@ui` `@rotation` | 6 | `SplashHint.tsx`, `hints.ts`, `App.tsx`, `index.css` |
| [coverage-matrix.feature](coverage-matrix.feature) | Backend \| Frontend \| Infrastructure | `@coverage` `@developer-tools` `@quality-of-life` | 7 | `scripts/build_coverage.py`, `outputs/coverage.json`, `GET /api/coverage`, `CoverageMatrix.tsx`, `Header.tsx` Coverage button |
| [combat-system-prompt.feature](combat-system-prompt.feature) | Backend | `@combat` `@prompt` `@injection` `@per-turn` `@token` | 16 | `_build_combat_system_prompt()`, `_COMBAT_SECTION_SPECS`, `_inject_context` combat branch (live + pre-combat), `[INITIATIVE ORDER]`, `[CURRENT HP]`, `[PC COMBAT STATS]`, `[ACTIVE CONDITIONS]`, `tests/test_combat_prompt.py` |
| [session-state.feature](session-state.feature) | Backend | `@session` `@state` `@persistence` `@boot` | 17 | `_write_session_state()`, `write_session_state()`, `set_active_character()`, `PUT /active_character`, `sessions/state.template.json`, `sessions/session_NNN/state.json`, `create_session()` boot init, `tests/test_session_state.py` |
| [combat-active-character.feature](combat-active-character.feature) | Backend \| Frontend | `@combat` `@session` `@prompt` `@streaming` `@layout` | 14 | `CombatState.current_actor`, `advance_combat_turn()`, `POST /combat/advance_turn`, `_write_session_state` combat actor, `ActiveSpeaker.isEnemy`, `InputBar` hostile state + skull icon + taunting placeholder, `tests/test_combat_active_character.py`, `InputBarHostile.test.tsx` |
| [roll-initiatives.feature](roll-initiatives.feature) | Backend \| Frontend | `@combat` `@initiative` `@session` `@layout` | 9 | `roll_combat_initiatives()`, `_parse_event_combatants()`, `pending_combatants` seeding, auto-roll hook on round-1 `%%COMBAT%%` with combat event, `POST /combat/roll_initiatives` (debug), `tests/test_roll_initiatives.py`, `CombatPanelRollInit.test.tsx` |

| [pc-combat-turn.feature](pc-combat-turn.feature) | Backend \| Frontend | `@combat` `@pc` `@action` `@turn` `@streaming` `@parsing` | 10 | `_extract_pc_combat_intent`, `stream_pc_turn`, `_stream_pc_turn_narration`, `_PC_TURN_SYSTEM`, `_build_pc_turn_system`, `POST /pc_turn`, `session._pending_pc_narration`, `pc_profiles.weapons`, App.tsx routing, `pcTurn()` in api.ts |
| [magic-spell-system.feature](magic-spell-system.feature) | Backend \| Frontend | `@magic` `@spell` `@combat` `@pc` `@action` `@streaming` | 14 | `_build_pc_profiles` spell parsing, `_extract_pc_combat_intent` spell detection, `stream_pc_turn` `cast` branch, `PendingAttack.is_spell`, `damage_request` SSE, `AttackPhase` `spell_damage`, `DicePanel.tsx` spell banner, `MessageBubble.tsx` spell card |
| [healing-spells.feature](healing-spells.feature) | Backend \| Frontend | `@magic` `@spell` `@heal` `@combat` `@pc` | 12 | `_build_pc_profiles` `healing_expr`/`is_heal`, `stream_pc_turn` heal branch, `PendingAttack.is_heal`, `heal_request` SSE, `AttackPhase` `spell_heal`, `DicePanel.tsx` heal banner, `MessageBubble.tsx` heal card, `resolve_damage_roll` positive delta, unconscious→active restore |
| [ac-buffs.feature](ac-buffs.feature) | Backend \| Frontend | `@magic` `@spell` `@buff` `@combat` `@ac` | 13 | `Combatant.active_effects`, `_effective_ac`, `_apply_ac_effect`, `_tick_effects`, `_build_pc_profiles` `buff_ac`, `stream_pc_turn` buff branch, `advance_combat_turn` effect expiry, `_serialize_combat_state` `effective_ac`, `CombatPanel.tsx` ✦ indicator. Covers shield, deflection, luck, natural, dodge (future) |
| [action-economy.feature](action-economy.feature) | Backend \| Frontend | `@combat` `@pc` `@action` `@turn` `@input` `@economy` | 9 | `InputBar.tsx` action-type row (Standard/Move/Full-Round buttons), `inPcCombatTurn` prop, `actionType` state + toggle + reset on turn-advance, `action_type_hint` POST field, `PcTurnRequest` Pydantic model, `_HINT_TO_ACTION_TYPE`, `_extract_pc_combat_intent` hint override, `pcTurn()` in api.ts |
| [zone-combat.feature](zone-combat.feature) | Backend \| Frontend | `@combat` `@zone` `@movement` | 8 | `Combatant.zone`, `_parse_event_combatants` Zone column, `(random)` fallback to `"default"`, `_seed_round1_combatants` zone seed, `_serialize_combat_state` zone field, `CombatPanel.tsx` `.zone-badge` below HP bar, `tests/test_combat.py TestZone`, `tests/test_roll_initiatives.py TestZoneColumnParsing` |
| [click-to-target.feature](click-to-target.feature) | Frontend \| Backend | `@combat` `@pc` `@action` `@target` `@input` `@economy` | 9 | `selectedTarget` state in App.tsx, `combatant-targeted` CSS class, target badge near InputBar, `target_hint` POST field, `PcTurnRequest.target_hint`, `_extract_pc_combat_intent` target_hint override, `CombatPanel.tsx` row click handler |
| [enemy-action-type.feature](enemy-action-type.feature) | Backend | `@combat` `@enemy` `@action` `@economy` `@parsing` `@session` | 7 | `_parse_action_block` `action_type` field, normalisation to canonical set, inference from `action` when absent, `_build_enemy_turn_system` prompt update, `action_card` SSE `action_type`, session log |

| [music-calm-generation.feature](music-calm-generation.feature) | Backend | `@music` `@generation` `@calm` `@symbolic` `@backend` | 13 | `CalmConfig`, `NoteEvent`, `PhraseState`, degree→note mapping, bar-fill algorithm, cadence weighting, motif carry-forward, validation/repair loop — `tests/test_music_generation.py` |
| [music-api-contract.feature](music-api-contract.feature) | Backend \| Frontend | `@music` `@api` `@calm` `@symbolic` `@contract` | 7 | `POST /api/music/calm/next_phrase`, `CalmPhrase` response schema, `NoteEvent` event shape, `PhraseState` motif state, 422 error contract |
| [music-calm-playback.feature](music-calm-playback.feature) | Frontend | `@music` `@playback` `@calm` `@ui` `@webaudio` | 9 | `MusicPlayer.tsx`, `ui/src/music/synth.ts`, `ui/src/music/player.ts`, Tone.js `Synth`, phrase scheduling, motif state rolling, debug phrase view |

**Total: 433 acceptance criteria across 45 feature files**

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [_FEATURE_TEMPLATE.md](_FEATURE_TEMPLATE.md) | Template for new feature specs |
| [dev.py](../dev.py) | One-command dev startup — port cleanup, process-tree teardown |
| [api/main.py](../api/main.py) | All API endpoint definitions |
| [api/session_manager.py](../api/session_manager.py) | Session lifecycle, streaming, context detection, response parsing |
| [ui/src/App.tsx](../ui/src/App.tsx) | Frontend state and session orchestration |

---

## Tag Reference

| Tag | Meaning | Match PR changes to… |
|-----|---------|----------------------|
| `@boot` | Session boot logic | `api/session_manager.py` `create_session()`, `sessions/` files |
| `@chat` | Chat display components | `ui/src/components/ChatWindow.tsx`, `MessageBubble.tsx` |
| `@character` | Character data and sheet UI | `ui/src/components/CharacterSidebar.tsx`, `ui/public/data/` |
| `@context` | NPC/skill/location detection | `api/context/npc_lookup.py`, `api/context/skill_lookup.py` |
| `@core` | Player turn round-trip | `api/main.py` `/turn` endpoint, `stream_turn()` |
| `@deltas` | NPC state delta writes | `%%DELTAS%%` parsing, `session_NNN.md`, `knowledge.md` |
| `@dice` | Dice panel and roll logging | `ui/src/components/DicePanel.tsx`, `/roll` endpoint |
| `@groq` | Groq provider behaviour | `api/session_manager.py` Groq branch, `.env` `GROQ_API_KEY` |
| `@header` | Session control header | `ui/src/components/Header.tsx` |
| `@intent` | Intent bar display | `ui/src/components/IntentBar.tsx` |
| `@llm` | LLM provider switching | `Header.tsx` provider toggle, `api/session_manager.py` `_stream_chat()` |
| `@logging` | Session and API call logs | `api/api_logger.py`, `outputs/` |
| `@narrative` | Narrative streaming filter | `stream_turn()` holdback buffer, `patch_last` SSE event |
| `@npc` | NPC database and index | `api/context/npc_lookup.py`, `adventure_path/01_npcs/` |
| `@location` | Location profile database and index | `api/context/location_lookup.py`, `adventure_path/03_locations/` |
| `@ollama` | Ollama provider behaviour | `api/session_manager.py` Ollama branch, `num_ctx`/`num_gpu` |
| `@parsing` | `%%SECTION%%` response parsing | `stream_turn()` section parser, `%%ROLL%%` / `%%GENERATE%%` / `%%DELTAS%%` |
| `@prompt` | System prompt assembly | `_build_slim_system_prompt()`, `sessions/` boot files |
| `@recap` | Session end and recap | `stream_end_session()`, `recap.md`, `boot.md` |
| `@session` | Session lifecycle | `api/session_manager.py`, `GameSession` dataclass |
| `@skill` | Skill detection and injection | `api/context/skill_lookup.py`, `adventure_path/04_rules/skills/` |
| `@startup` | Dev startup process cleanup | `dev.py`, `start_backend.ps1`, `start_ui.ps1` |
| `@streaming` | SSE token streaming | `StreamingResponse`, token/done/error/patch_last events |
| `@event` | Scene-triggered event injection | `api/context/event_index.py`, `adventure_path/02_events/`, `active_events`, `%%EVENT%%` |
| `@debug` | Diagnostic / developer tooling panels | `api/main.py` debug endpoints, `ui/src/components/` debug panels |
| `@music` | Procedural adaptive music system | `api/music/`, `ui/src/music/`, `ui/src/components/MusicPlayer.tsx`, `/music/` endpoints |
| `@generation` | Rule-based symbolic phrase generation | `CalmConfig`, phrase generator, validation/repair loop |
| `@playback` | Browser-side audio synthesis | `MusicPlayer.tsx`, `synth.ts`, `player.ts`, Tone.js |
| `@webaudio` | Web Audio API / Tone.js integration | `Tone.Transport`, `Tone.Synth`, AudioContext lifecycle |
| `@symbolic` | Symbolic note representation (no audio files) | `NoteEvent`, `CalmPhrase`, MIDI→frequency mapping |
| `@contract` | API request/response shape specs | Pydantic models, TypeScript types, casing convention |
| `@temperature` | Readiness-based event warming and trigger chance | `event_runtime`, scheduler tick, threshold/pity logic |
| `@chain` | Deterministic event node progression | `active_chain_id`, `active_node_id`, hard transitions |
| `@stability` | Event pacing conflict controls | readiness vs urgency, arbitration, cooldown protections |
| `@combat` | Combat tracker panel and state | `api/session_manager.py` `CombatState`, `CombatPanel.tsx`, `HpBar.tsx`, `%%COMBAT%%` block, `api/context/combat_lookup.py` `CombatRulesIndex` |
| `@layout` | UI column layout switching | `ui/src/index.css` `.main-content.combat-active`, flex `order` rules |
| `@persistence` | State files written to disk mid-session | `sessions/session_NNN/state.json`, `_write_session_state()` |
| `@state` | Lightweight "state of play" snapshot | `sessions/state.template.json`, mode/round/events fields |
