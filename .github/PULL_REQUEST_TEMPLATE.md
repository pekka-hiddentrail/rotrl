## What changed

<!-- One or two sentences. What does this PR add, fix, or remove? -->

## Type

<!-- Check all that apply -->

- [ ] Campaign content (encounters, NPCs, locations, lore)
- [ ] GM agent / prompts / boot protocol
- [ ] Backend (FastAPI, session manager, NPC lookup)
- [ ] Frontend (UI, components, styles)
- [ ] Infrastructure (scripts, deps, config)
- [ ] Docs / README

## Testing

<!-- How was this verified? Check what applies. -->

- [ ] Booted a dev-mode session and played at least one turn
- [ ] Booted a full-mode session (rules enforcement active)
- [ ] NPC detection tested in the session (`npc_lookup` picks up the right names)
- [ ] Session log written correctly to `outputs/`
- [ ] `npx tsc --noEmit` passes (frontend only)
- [ ] Not testable — explain why:

## Campaign impact

<!-- Leave blank if this is infrastructure/UI only. -->

**Book / Act affected:**
**NPCs affected:**
**World state changes:**

## Checklist

- [ ] NPC `base.md` files follow the canonical format (aliases/locations before `<!-- REFERENCE -->`, metadata after)
- [ ] New `outputs/` files are not committed (git-ignored)
- [ ] `ui/node_modules/` not committed
- [ ] README updated if setup steps or behaviour changed
