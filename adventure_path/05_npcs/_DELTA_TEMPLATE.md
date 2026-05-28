# NPC Delta File — Format Reference

Delta files are machine-written by the backend after each GM turn.
They live alongside each NPC's `base.md` and `knowledge.md`:

    adventure_path/05_npcs/<npc_slug>/session_001.md
    adventure_path/05_npcs/<npc_slug>/session_002.md
    ...
    adventure_path/05_npcs/<npc_slug>/knowledge.md

`session_NNN.md` files are **git-ignored** and **deleted on session boot** so each
playthrough starts from the canonical `base.md` state for turn-by-turn status.

`knowledge.md` is cumulative across sessions, but is reset when booting **session 1**.

---

## session_NNN.md Format (one entry per turn, append-only)

```
## Turn N — HH:MM:SS
**Disposition:** <change description, e.g. "neutral → suspicious">   ← only if changed
**Location:** <current location>                                      ← only if mentioned
**Summary:** <one sentence of what happened with this NPC this turn>
```

### session_NNN.md Example

```
## Turn 3 — 14:22:07
**Disposition:** neutral → suspicious
**Location:** Festival Square
**Summary:** Kendra grew wary after the failed Bluff attempt and asked the party to stay close.

## Turn 5 — 14:35:44
**Summary:** Kendra thanked the party for intervening with the goblins; disposition reset to warm.
```

## knowledge.md Format (append-only, separate file)

Knowledge lines are written to `knowledge.md`, not to `session_NNN.md`.

```
- [tag] <fact text> — SNNN TNNN
```

Allowed tags:

- `[persistent]`
- `[pcs]`
- `[quest]`
- `[world]`
- `[npcs]`
- `[trivia]`

### knowledge.md Example

```
- [pcs] Ani attempted to deceive her about the fireworks incident — S001 T003
- [quest] The party is investigating fireworks disturbances — S001 T003
```

---

## Notes

- The backend reads the **most recent** `session_NNN.md` for status on every `detect()` call.
- The backend also reads cumulative `knowledge.md` on every `detect()` call.
- `session_NNN.md` intentionally excludes knowledge lines.
- Manual edits to either file take effect immediately on the next player turn.
