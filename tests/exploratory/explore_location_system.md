# Exploratory Tests — Location System

Spec: specs/location-system.feature

**What automated tests cover:** `LocationIndex` loading (skips `_` dirs, missing `base.md`),
alias detection, longest-alias-wins, `<!-- REFERENCE -->` boundary, `format_context` header,
`scene_locations` accumulation and re-injection, `%%GENERATE%% type: location` stub creation and
index invalidation — all with temp directories.

**Pre-requisites:** `python dev.py --skip-tests` — stack running.

---

## Chain A — Location detection and intent bar  <!-- AC-003 -->

1. Boot a session (Dev Mode OFF).
2. Send: `We head to the garrison to report the goblin attack.`
3. ✔ Intent bar updates — a location chip shows `Sandpoint Garrison` (alias `garrison`).
4. ✔ GM response describes the garrison using physical/social details from `base.md`.
5. ✔ No `## Location Reference —` header leaks into the player-facing chat.

---

## Chain B — Longest alias wins  <!-- AC-004 -->

1. Send: `We enter the Desna Cathedral for the consecration.`
2. ✔ Intent bar shows `Sandpoint Cathedral` — alias matched is `desna cathedral`, not `cathedral`.
3. Send: `We go to the cathedral.`
4. ✔ Intent bar still shows `Sandpoint Cathedral` — shorter alias also works.

---

## Chain C — scene_locations persists across turns  <!-- AC-007 -->

1. Send: `We enter the Rusty Dragon.` — confirm intent bar shows `The Rusty Dragon`.
2. Send: `Ani orders a drink and sits down.` (no location keyword).
3. ✔ Intent bar still shows `The Rusty Dragon` (location re-injected from `scene_locations`).
4. ✔ GM response continues to describe the inn context without being told again.
5. Send five more turns with no location keyword.
6. ✔ Location context persists throughout — GM does not suddenly forget where the party is.

---

## Chain D — Location + named NPC combined injection  <!-- AC-003, AC-005 -->

1. Send: `We go to the garrison and look for Sheriff Hemlock.`
2. ✔ Intent bar shows both a location (`Sandpoint Garrison`) and an NPC (`Belor Hemlock`).
3. ✔ GM response references both the physical garrison and Hemlock's presence specifically.
4. In Dev Mode, confirm two context blocks appear — `## Location Reference — Sandpoint Garrison`
   and `## NPC — Belor Hemlock` — separated by `---`.
5. **Note:** Sending `We go to the garrison.` alone injects only the location profile — Hemlock
   is not added unless explicitly named. NPCs associated with a location are NOT auto-injected.

---

## Chain E — All eight seed locations reachable by alias  <!-- AC-003 -->

Send one turn for each location using one of its aliases. Confirm intent bar fires and GM response
reflects each location's character:

| Input | Expected location |
|---|---|
| `We go to the garrison.` | Sandpoint Garrison |
| `We enter the cathedral.` | Sandpoint Cathedral |
| `We head to the Rusty Dragon.` | The Rusty Dragon |
| `We walk through the festival grounds.` | Festival Grounds |
| `We visit the boneyard at the edge of town.` | Sandpoint Boneyard |
| `We investigate the glassworks.` | Sandpoint Glassworks |
| `We stop at the White Deer for the night.` | The White Deer |
| `We find a spot near the sage stage.` | Sage Stage |

---

## Chain F — Auto-stub from `%%GENERATE%% type: location`  <!-- AC-008, AC-009 -->

1. Boot with Dev Mode ON so you can see raw blocks.
2. Send: `I notice a small apothecary called Bottled Solutions on the main street, run by a
   gossipy old man named Gerhard Pickle.`
3. Wait for the GM response. Look for a `%%GENERATE%%` block with `type: location`.
4. If the model wrote one: open `adventure_path/03_locations/` and confirm a new directory
   (`bottled_solutions/` or similar) was created with a `base.md`.
5. ✔ `base.md` starts with `# Bottled Solutions`.
6. ✔ `**Aliases:**` line is present and includes at least `bottled solutions`.
7. Send: `We step inside Bottled Solutions to browse.`
8. ✔ Intent bar detects the new location — index was invalidated and reloaded after stub creation.

---

## Chain G — Seed file quality audit  <!-- AC-001, AC-002 -->

Open each `base.md` in `adventure_path/03_locations/` and verify the format spec:

- Starts with `# Canonical Name`
- `**Aliases:**` line is present and has at least 2 aliases
- `## Description`, `## Typical Occupants`, and `## Current State` sections exist above
  `<!-- REFERENCE -->`
- Nothing below `<!-- REFERENCE -->` leaks into injected context (verify in dev mode)
- `Current State` reflects current world state accurately
