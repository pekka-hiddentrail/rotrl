"""NPC lookup — detects NPC mentions in player input and returns the relevant
profile + per-turn status + cumulative knowledge to inject into the current
turn's system prompt.

Design:
- Zero extra LLM calls: pure text matching, runs in <1 ms
- Per-turn injection only: never modifies session.system_prompt permanently
- Data-driven: all NPC data and aliases live in adventure_path/01_npcs/
- Status and knowledge files are read FRESH on every detection call

Folder structure (relative to repo root):
  adventure_path/01_npcs/
    <npc_slug>/
      base.md          ← canonical profile (git-tracked)
      knowledge.md     ← tagged knowledge list (git-ignored, grows each session)
      session_001.md   ← per-turn status log: disposition / location / summary
      session_002.md   ← (one file per session number, deleted on session boot)

base.md format:
  # Canonical Name
  **Aliases:** alias one, alias two, multi word alias
  **Locations:** place one, place two
  ...rest is the profile text injected verbatim...

knowledge.md format (append-only, tags determine injection priority):
  - [persistent] Always-relevant fact about this NPC.
  - [pcs] Yanyeeku is interested in fireworks.        ← what NPC knows about the party
  - [quest] The fireworks merchant is south of town.
  - [world] Sandpoint was rebuilt after the Late Unpleasantness.
  - [npcs] Father Zantus is performing the ceremony.
  - [trivia] She collects pressed flowers.

  Tags: persistent | pcs | quest | world | npcs | trivia

session_NNN.md format (per-turn status, append-only within a session):
  ## Turn N — HH:MM:SS
  **Disposition:** <change or current state>
  **Location:** <current location>
  **Summary:** <one sentence — what happened this turn>

  (knowledge lines are intentionally excluded — those go to knowledge.md)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional


@dataclass
class NpcMatch:
    canonical_name: str
    profile_text: str        # contents of base.md (minus header/alias/location lines)
    status: str = ""         # most recent turn's status block (disposition/location/summary)
    knowledge_text: str = "" # tagged knowledge list from knowledge.md
    npc_dir: Path = field(default_factory=Path)
    matched_alias: str = ""
    matched_location: str = ""


@dataclass
class NpcIndex:
    """Lazy-loaded NPC index built by scanning adventure_path/01_npcs/.

    Instantiate once per process (module-level singleton in session_manager).
    Re-instantiate if NPC files change (backend restart required).
    Status and knowledge files are re-read on every detect() call — no restart needed.
    """
    _repo_root: Path
    _entries: dict[str, NpcMatch] = field(default_factory=dict, init=False)
    # alias (lower-cased) → canonical name
    _aliases: dict[str, str] = field(default_factory=dict, init=False)
    # location keyword (lower-cased) → list of canonical names present there
    _locations: dict[str, list[str]] = field(default_factory=dict, init=False)
    _loaded: bool = field(default=False, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        npcs_root = self._repo_root / "adventure_path" / "01_npcs"
        if not npcs_root.exists():
            self._loaded = True
            return

        for npc_dir in sorted(npcs_root.iterdir()):
            if not npc_dir.is_dir() or npc_dir.name.startswith("_"):
                continue
            base_path = npc_dir / "base.md"
            if not base_path.exists():
                continue

            canonical, aliases, locations, profile = _parse_base(base_path)
            if not canonical:
                continue

            # Store entry without live data — status/knowledge are read fresh on detect()
            self._entries[canonical] = NpcMatch(
                canonical_name=canonical,
                profile_text=profile,
                status="",
                knowledge_text="",
                npc_dir=npc_dir,
            )

            # Register explicit aliases from the file
            for alias in aliases:
                a = alias.lower().strip()
                if a:
                    self._aliases[a] = canonical

            # Auto-register each word of the canonical name as a fallback alias
            for word in canonical.lower().split():
                if len(word) > 3 and word not in self._aliases:
                    self._aliases[word] = canonical

            # Register location keywords (location → list of NPCs there)
            for loc in locations:
                l = loc.lower().strip()
                if l:
                    self._locations.setdefault(l, []).append(canonical)

        self._loaded = True

    # ── Fresh data readers ────────────────────────────────────────────────────

    def _fresh_status(self, npc_dir: Path) -> str:
        """Return only the most recent turn block from the latest session delta.

        Looks for the most recent session_NNN.md and extracts the last
        '## Turn N' block, so only current state is injected (not full history).
        """
        deltas = sorted(npc_dir.glob("session_*.md"))
        if not deltas:
            return ""
        try:
            content = deltas[-1].read_text(encoding="utf-8").strip()
        except OSError:
            return ""
        if not content:
            return ""
        # Split on ## Turn headers and return the last block
        blocks = re.split(r"(?=^## Turn \d)", content, flags=re.MULTILINE)
        last = blocks[-1].strip() if blocks else ""
        return last

    def _fresh_knowledge(self, npc_dir: Path) -> str:
        """Read the cumulative knowledge.md for this NPC.

        Returns the full content (all tags), ready to inject verbatim.
        Returns "" if the file does not exist yet.
        """
        path = npc_dir / "knowledge.md"
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> Optional[NpcMatch]:
        """Scan *text* for any known NPC reference.

        Returns the best match (longest alias wins), with fresh status + knowledge.
        """
        self._ensure_loaded()
        lower = text.lower()
        best_canonical: Optional[str] = None
        best_alias = ""
        best_len = 0

        for alias, canonical in self._aliases.items():
            if re.search(rf"\b{re.escape(alias)}\b", lower) and len(alias) > best_len:
                best_canonical = canonical
                best_alias = alias
                best_len = len(alias)

        if best_canonical:
            entry = self._entries[best_canonical]
            return replace(
                entry,
                status=self._fresh_status(entry.npc_dir),
                knowledge_text=self._fresh_knowledge(entry.npc_dir),
                matched_alias=best_alias,
            )
        return None

    def detect_all(self, text: str) -> list[NpcMatch]:
        """Return ALL NPCs mentioned in *text* (not just the longest match).

        Returns one NpcMatch per canonical NPC, with fresh status + knowledge.
        """
        self._ensure_loaded()
        lower = text.lower()

        # canonical → (best_alias_len, best_alias)
        best: dict[str, tuple[int, str]] = {}

        for alias, canonical in self._aliases.items():
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                prev_len, _ = best.get(canonical, (0, ""))
                if len(alias) > prev_len:
                    best[canonical] = (len(alias), alias)

        results: list[NpcMatch] = []
        for canonical, (_, alias) in best.items():
            entry = self._entries[canonical]
            results.append(replace(
                entry,
                status=self._fresh_status(entry.npc_dir),
                knowledge_text=self._fresh_knowledge(entry.npc_dir),
                matched_alias=alias,
            ))
        return results

    def detect_by_location(self, text: str) -> list[NpcMatch]:
        """Return all NPCs whose location keywords appear in *text*.

        Uses longest-match per location keyword. Returns at most one match per
        canonical NPC. Each match has fresh status + knowledge.
        """
        self._ensure_loaded()
        lower = text.lower()

        best_per_npc: dict[str, tuple[int, str]] = {}
        for loc, canonicals in self._locations.items():
            if re.search(rf"\b{re.escape(loc)}\b", lower):
                for canonical in canonicals:
                    prev_len, _ = best_per_npc.get(canonical, (0, ""))
                    if len(loc) > prev_len:
                        best_per_npc[canonical] = (len(loc), loc)

        results: list[NpcMatch] = []
        for canonical, (_, keyword) in best_per_npc.items():
            entry = self._entries[canonical]
            results.append(replace(
                entry,
                status=self._fresh_status(entry.npc_dir),
                knowledge_text=self._fresh_knowledge(entry.npc_dir),
                matched_location=keyword,
            ))
        return results

    def lookup(self, canonical_name: str) -> Optional[NpcMatch]:
        """Direct lookup by canonical name (case-insensitive), with fresh data."""
        self._ensure_loaded()
        lower = canonical_name.lower()
        for name, entry in self._entries.items():
            if name.lower() == lower:
                return replace(
                    entry,
                    status=self._fresh_status(entry.npc_dir),
                    knowledge_text=self._fresh_knowledge(entry.npc_dir),
                )
        return None

    def npc_dir_for(self, canonical_name: str) -> Optional[Path]:
        """Return the NPC folder path for writing delta/knowledge files."""
        self._ensure_loaded()
        lower = canonical_name.lower()
        for name, entry in self._entries.items():
            if name.lower() == lower:
                return entry.npc_dir
        return None

    def format_context(self, match: NpcMatch) -> str:
        """Return a context block ready for injection into a system prompt.

        Sections:
          ## NPC Reference — <name>
          <profile>

          ### Current Status        ← most recent turn (disposition/location/summary)
          <status block>

          ### What <name> Knows     ← tagged knowledge list
          <knowledge entries>
        """
        parts = [f"## NPC Reference — {match.canonical_name}", "", match.profile_text.strip()]
        if match.status:
            parts += ["", "### Current Status", "", match.status]
        if match.knowledge_text:
            parts += ["", f"### What {match.canonical_name} Knows", "", match.knowledge_text]
        return "\n".join(parts)

    # ── Introspection ─────────────────────────────────────────────────────────

    def canonical_for(self, word: str) -> str | None:
        """Return canonical NPC name if *word* matches any registered alias, else None.

        Uses the same alias table as detect_all(). Single-word lookups only.
        The NPC index auto-registers each word of every canonical name (≥4 chars)
        as a fallback alias, so "Aldern" resolves to "Aldern Foxglove" without
        any explicit alias entry in base.md.
        """
        self._ensure_loaded()
        return self._aliases.get(word.lower())

    @property
    def known_npcs(self) -> list[str]:
        self._ensure_loaded()
        return list(self._entries.keys())

    @property
    def known_aliases(self) -> dict[str, str]:
        self._ensure_loaded()
        return dict(self._aliases)


# ── base.md parser ────────────────────────────────────────────────────────────

def _parse_base(path: Path) -> tuple[str, list[str], list[str], str]:
    """Parse a base.md file.

    Returns (canonical_name, aliases, locations, profile_body).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "", [], [], ""

    canonical = ""
    aliases: list[str] = []
    locations: list[str] = []
    body_lines: list[str] = []

    for line in text.splitlines():
        if not canonical and line.startswith("# "):
            canonical = line[2:].strip()
            continue

        m = re.match(r"\*\*Aliases:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            aliases = [a.strip() for a in m.group(1).split(",") if a.strip()]
            continue

        m = re.match(r"\*\*Locations:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            locations = [l.strip() for l in m.group(1).split(",") if l.strip()]
            continue

        if line.strip() == "<!-- REFERENCE -->":
            break  # everything below is reader documentation, never injected

        body_lines.append(line)

    profile = "\n".join(body_lines).strip()
    return canonical, aliases, locations, profile
