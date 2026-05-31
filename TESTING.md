# Manual Testing Guide

Exploratory tests have been split into individual files under `tests/exploratory/`.
Each file has a `Spec: specs/<id>.feature` header and inline `AC-NNN` references so
`scripts/build_coverage.py` can count exploratory coverage alongside pytest / Vitest / Playwright.

**Run the automated suite first.** If it is red, do not bother with manual testing.

```
pytest
cd ui && npm run test
npm run test:e2e
npx playwright test --config playwright.live.config.ts
```

Start the stack:

```
python dev.py --skip-tests
```

---

## Exploratory Test Files

| File | Feature Spec | Covers |
|------|-------------|--------|
| [explore_session_boot.md](tests/exploratory/explore_session_boot.md) | session-boot | Chains A-C: happy path, invalid session, re-boot |
| [explore_system_prompt.md](tests/exploratory/explore_system_prompt.md) | system-prompt | Chains A-D: format example gate, combat spec gate, conditional sections, PC profile |
| [explore_llm_output_quality.md](tests/exploratory/explore_llm_output_quality.md) | response-parsing | Chains A-D: dev-mode markers, narrative quality, roll trigger, combat prose |
| [explore_npc_system.md](tests/exploratory/explore_npc_system.md) | npc-system | Chains A-D: delta write, auto-stub, NPC promotion, purge |
| [explore_dice_panel.md](tests/exploratory/explore_dice_panel.md) | dice-panel | Chains A-D: queue/roll, auto-bonus, toggle, history cap |
| [explore_location_system.md](tests/exploratory/explore_location_system.md) | location-system | Chains A-G: detection, longest alias, scene persistence, stub, quality audit |
| [explore_character_system.md](tests/exploratory/explore_character_system.md) | character-system | Chains A-I: load, HP colour, sheet, speaker, action menu |
| [explore_streaming_feel.md](tests/exploratory/explore_streaming_feel.md) | chat-display | Chains A-D: token flow, patch_last, input lockout, error recovery |
| [explore_session_end.md](tests/exploratory/explore_session_end.md) | session-end-recap | Chains A-B: full flow, kill button |
| [explore_llm_providers.md](tests/exploratory/explore_llm_providers.md) | llm-providers | Chains A-C: model switch, rate-limit badge, Ollama switch |
| [explore_session_controls.md](tests/exploratory/explore_session_controls.md) | session-controls | Chains A-F: header state, purge confirm, benchmarks/coverage buttons |
| [explore_event_injection.md](tests/exploratory/explore_event_injection.md) | event-injection | Chains A-E: event fires, hidden from player, TTL expiry, wave transition, event map |
| [explore_logging.md](tests/exploratory/explore_logging.md) | session-logging | Chains A-E: log structure, latency fields, error-path nulls, API log browser |
| [explore_attack_resolution.md](tests/exploratory/explore_attack_resolution.md) | attack-resolution | Chains A-H: NPC auto-HP update, PC to-hit banner, hit→damage→HP, miss path, multi-attack queue, attack log visual, %%ATTACK%% hidden from player, End Combat clears queue |
| [explore_combat_tracker.md](tests/exploratory/explore_combat_tracker.md) | combat-tracker | Chains A-D: panel appearance+initiative order, HP bar colour shift, condition chip+tooltip, End Combat cleanup |
| [explore_edge_cases.md](tests/exploratory/explore_edge_cases.md) | (multi-feature) | Chains A-E: long input, NPC typo, two NPCs, stress, delta inspection |

---

## Coverage

Click **Coverage** in the header to rebuild and view the current feature AC matrix. The API
also writes the refreshed data to `outputs/coverage.json`; `python scripts/build_coverage.py`
does the same from the CLI. The script scans `specs/**/*.feature`, including newly added
features and AC headings, and maps coverage across pytest / Vitest / Playwright / Exploratory.
