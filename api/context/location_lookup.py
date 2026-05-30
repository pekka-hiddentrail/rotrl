"""Location lookup — detects location mentions in player input and returns the
relevant profile to inject into the current turn's system prompt.

Design:
- Zero extra LLM calls: pure text matching, runs in <1 ms
- Per-turn injection only: never modifies session.system_prompt permanently
- Data-driven: all location data and aliases live in adventure_path/03_locations/
- No status or knowledge files — locations are static within a session

Folder structure (relative to repo root):
  adventure_path/03_locations/
    _LOCATION_TEMPLATE.md         template (skipped by index)
    <location_slug>/
      base.md   ← canonical profile (git-tracked)

base.md format:
  # Canonical Name
  **Aliases:** alias one, alias two, multi word alias

  ## Description
  ...

  ## Typical Occupants
  ...

  ## Current State
  ...

  <!-- REFERENCE -->
  ...meta fields never injected...
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional


@dataclass
class LocationMatch:
    canonical_name: str
    profile_text: str     # base.md content above <!-- REFERENCE -->, alias line excluded
    location_dir: Path = field(default_factory=Path)
    matched_alias: str = ""


@dataclass
class LocationIndex:
    """Lazy-loaded location index built by scanning adventure_path/03_locations/.

    Instantiate once per process (module-level singleton in session_manager).
    Re-instantiate via _invalidate_location_index() if location files change mid-session.
    """
    _repo_root: Path
    _entries: dict[str, LocationMatch] = field(default_factory=dict, init=False)
    _aliases: dict[str, str] = field(default_factory=dict, init=False)  # alias (lower) → canonical name
    _loaded: bool = field(default=False, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        locs_root = self._repo_root / "adventure_path" / "03_locations"
        if not locs_root.exists():
            self._loaded = True
            return

        for loc_dir in sorted(locs_root.iterdir()):
            if not loc_dir.is_dir() or loc_dir.name.startswith("_"):
                continue
            base_path = loc_dir / "base.md"
            if not base_path.exists():
                continue

            canonical, aliases, profile = _parse_location_base(base_path)
            if not canonical:
                continue

            self._entries[canonical] = LocationMatch(
                canonical_name=canonical,
                profile_text=profile,
                location_dir=loc_dir,
            )

            for alias in aliases:
                a = alias.lower().strip()
                if a:
                    self._aliases[a] = canonical

        self._loaded = True

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> Optional[LocationMatch]:
        """Scan *text* for any known location alias.

        Returns the best match (longest alias wins), or None.
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
            return replace(entry, matched_alias=best_alias)
        return None

    def format_context(self, match: LocationMatch) -> str:
        """Return a context block ready for injection into a system prompt."""
        return f"## Location Reference — {match.canonical_name}\n\n{match.profile_text.strip()}"

    def lookup(self, canonical_name: str) -> Optional[LocationMatch]:
        """Direct lookup by canonical name (case-insensitive)."""
        self._ensure_loaded()
        lower = canonical_name.lower()
        for name, entry in self._entries.items():
            if name.lower() == lower:
                return entry
        return None

    @property
    def known_locations(self) -> list[str]:
        self._ensure_loaded()
        return list(self._entries.keys())


# ── base.md parser ────────────────────────────────────────────────────────────

def _parse_location_base(path: Path) -> tuple[str, list[str], str]:
    """Parse a location base.md file.

    Returns (canonical_name, aliases, profile_body).
    profile_body is all content above <!-- REFERENCE -->, excluding the header
    line and the **Aliases:** line.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "", [], ""

    canonical = ""
    aliases: list[str] = []
    body_lines: list[str] = []

    for line in text.splitlines():
        if not canonical and line.startswith("# "):
            canonical = line[2:].strip()
            continue

        m = re.match(r"\*\*Aliases:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            aliases = [a.strip() for a in m.group(1).split(",") if a.strip()]
            continue

        if line.strip() == "<!-- REFERENCE -->":
            break

        body_lines.append(line)

    profile = "\n".join(body_lines).strip()
    return canonical, aliases, profile
