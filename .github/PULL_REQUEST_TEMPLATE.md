## Summary

<!-- What problem does this solve, and how? 2–4 sentences. Lead with the "why", not a list of files changed. -->

## Type

- [ ] Campaign content (encounters, NPCs, locations, lore)
- [ ] GM agent / prompts / system prompt
- [ ] Backend (FastAPI, session manager, parsers, state)
- [ ] Frontend (UI, components, styles)
- [ ] Tests (pytest / Vitest / Playwright)
- [ ] Infrastructure (scripts, deps, CI, config)
- [ ] Docs / README / specs

## Changes

<!-- One bullet per logical change. Group by layer if multiple layers are touched. -->

**Backend**
- 

**Frontend**
- 

**Tests**
- 

**Specs / docs**
- 

<!-- Remove sections that don't apply -->

## Breaking changes

<!-- List anything that is not backwards-compatible. Leave blank if none. -->

| Area | What broke | Migration |
|------|-----------|-----------|
| API | | |
| SSE events | | |
| State / file format | | |
| Prompt format | | |

## LLM / prompt impact

<!-- Fill in any that apply; delete the table if no prompt work in this PR -->

| Item | Detail |
|------|--------|
| System prompt token delta | +N / −N tokens (static base) |
| Per-turn injection delta | +N / −N tokens |
| New LLM markers / blocks | e.g. `%%NEW_BLOCK%%` |
| Models tested | e.g. Haiku, Groq 70B |
| Format regression risk | Low / Medium / High — reason |

## Test coverage

<!-- Fill in counts for suites you added or meaningfully extended; leave blank if unchanged -->

| Suite | New tests | Total after |
|-------|-----------|-------------|
| pytest | | |
| Vitest | | |
| Playwright live | | |
| Playwright unit (mocked) | | |

**Feature spec ACs covered:** <!-- e.g. session-state.feature AC-001 – AC-017 -->

## Manual verification

<!-- How to confirm the feature works end-to-end. Be specific enough that a reviewer can follow without asking. -->

1. Boot a session in dev mode (Haiku)
2. 
3. Expected: 

## Screenshots / recordings

<!-- Paste screenshots or a short screen recording for any visible UI change. Delete if backend-only. -->

## Campaign impact

<!-- Leave blank / delete if infrastructure-only -->

**Book / Act:**
**NPCs changed:**
**World state flags:**

## Checklist

- [ ] `npx tsc --noEmit` passes
- [ ] Relevant pytest / Vitest / Playwright suites pass locally
- [ ] New feature has a spec file (`specs/*.feature`) or existing spec updated
- [ ] `sessions/state.template.json` updated if `state.json` schema changed
- [ ] `outputs/` files not committed (git-ignored)
- [ ] `ui/node_modules/` not committed
- [ ] README / TESTING.md updated if setup or commands changed
- [ ] NPC `base.md` files follow canonical format (payload above `<!-- REFERENCE -->`)
