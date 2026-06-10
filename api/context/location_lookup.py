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
class LocationZone:
    id: str
    name: str
    description: str = ""
    visible: bool = True
    source: str = "authored"
    tags: list[str] = field(default_factory=list)


@dataclass
class LocationAccessPoint:
    id: str
    from_zone_id: str
    to_zone_id: str
    label: str = ""
    state: str = "open"
    bidirectional: bool = True
    requirements: str = ""
    description: str = ""
    source: str = "authored"


@dataclass
class LocationZoneGraph:
    location_id: str = ""
    location_name: str = ""
    zones: dict[str, LocationZone] = field(default_factory=dict)
    access_points: list[LocationAccessPoint] = field(default_factory=list)
    default_zone_id: str = ""

    def adjacency_by_id(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {zone_id: set() for zone_id in self.zones}
        for ap in self.access_points:
            if ap.state == "hidden":
                continue
            graph.setdefault(ap.from_zone_id, set()).add(ap.to_zone_id)
            if ap.bidirectional:
                graph.setdefault(ap.to_zone_id, set()).add(ap.from_zone_id)
        return graph

    def adjacency_by_name(self) -> dict[str, set[str]]:
        by_id = self.adjacency_by_id()
        out: dict[str, set[str]] = {}
        for zone_id, adjacent_ids in by_id.items():
            zone = self.zones.get(zone_id)
            if zone is None:
                continue
            out[zone.name] = {
                self.zones[adj_id].name
                for adj_id in adjacent_ids
                if adj_id in self.zones
            }
        return out

    def zone_properties_by_name(self) -> dict[str, list[str]]:
        return {
            zone.name: list(zone.tags)
            for zone in self.zones.values()
            if zone.tags
        }


@dataclass
class LocationIndex:
    """Lazy-loaded location index built by scanning adventure_path/03_locations/.

    Instantiate once per process (module-level singleton in session_manager).
    Re-instantiate via _invalidate_location_index() if location files change mid-session.
    """
    _repo_root: Path
    _entries: dict[str, LocationMatch] = field(default_factory=dict, init=False)
    _aliases: dict[str, str] = field(default_factory=dict, init=False)  # alias (lower) → canonical name
    _zone_graphs: dict[str, LocationZoneGraph] = field(default_factory=dict, init=False)
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

            graph = _parse_location_zone_graph(base_path, loc_dir.name, canonical)
            if graph.zones:
                self._zone_graphs[canonical] = graph

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
        return self._entry_for_location_id(canonical_name)

    @property
    def known_locations(self) -> list[str]:
        self._ensure_loaded()
        return list(self._entries.keys())

    def get_zone_graph(self, location_id: str) -> LocationZoneGraph:
        """Return the parsed zone graph for a canonical name, slug, or alias."""
        self._ensure_loaded()
        canonical = self._canonical_for_location_id(location_id)
        if not canonical:
            return LocationZoneGraph()
        return self._zone_graphs.get(canonical, LocationZoneGraph())

    def get_zones(self, location_id: str) -> dict[str, set[str]]:
        """Return a display-name adjacency map for *location_id*."""
        return self.get_zone_graph(location_id).adjacency_by_name()

    def get_zone_properties(self, location_id: str) -> dict[str, list[str]]:
        """Return zone properties/tags by display name for *location_id*."""
        return self.get_zone_graph(location_id).zone_properties_by_name()

    def get_access_points(self, location_id: str) -> list[LocationAccessPoint]:
        """Return access points for *location_id*."""
        return list(self.get_zone_graph(location_id).access_points)

    def _canonical_for_location_id(self, location_id: str) -> str:
        needle = location_id.lower().strip()
        if not needle:
            return ""
        alias_match = self._aliases.get(needle)
        if alias_match:
            return alias_match
        for name, entry in self._entries.items():
            if name.lower() == needle or entry.location_dir.name.lower() == needle:
                return name
        normalized = needle.replace("_", " ")
        for name, entry in self._entries.items():
            if name.lower() == normalized or entry.location_dir.name.lower().replace("_", " ") == normalized:
                return name
        return ""

    def _entry_for_location_id(self, location_id: str) -> Optional[LocationMatch]:
        canonical = self._canonical_for_location_id(location_id)
        if not canonical:
            return None
        return self._entries.get(canonical)


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


def _parse_location_zone_graph(path: Path, location_id: str = "", location_name: str = "") -> LocationZoneGraph:
    """Parse ## Zones and ## Access Points sections from a location base.md."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return LocationZoneGraph()

    payload = text.split("<!-- REFERENCE -->", 1)[0]
    zones, legacy_adjacency = _parse_zone_rows(payload)
    access_points = _parse_access_point_rows(payload, zones)

    if not access_points and legacy_adjacency:
        access_points = _access_points_from_adjacency(legacy_adjacency, zones)

    return LocationZoneGraph(
        location_id=location_id,
        location_name=location_name,
        zones=zones,
        access_points=access_points,
        default_zone_id=next(iter(zones), ""),
    )


def parse_zone_adjacency_table(text: str) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Parse a legacy ## Zones table into display-name adjacency and properties."""
    zones, legacy_adjacency = _parse_zone_rows(text)
    graph = LocationZoneGraph(
        zones=zones,
        access_points=_access_points_from_adjacency(legacy_adjacency, zones),
    )
    return graph.adjacency_by_name(), graph.zone_properties_by_name()


def _parse_zone_rows(text: str) -> tuple[dict[str, LocationZone], dict[str, set[str]]]:
    rows = _extract_table_after_heading(text, "Zones")
    zones: dict[str, LocationZone] = {}
    legacy_adjacency: dict[str, set[str]] = {}

    for row in rows:
        raw_id = row.get("id", "").strip()
        raw_name = (row.get("name") or row.get("zone") or raw_id).strip()
        if not raw_name:
            continue
        zone_id = _zone_id(raw_id or raw_name)
        tags = _split_list(row.get("tags", "") or row.get("properties", ""))
        zones[zone_id] = LocationZone(
            id=zone_id,
            name=raw_name,
            description=row.get("description", "").strip(),
            visible=_truthy(row.get("visible", "yes")),
            source=(row.get("source", "").strip() or "authored"),
            tags=tags,
        )

        adjacent_raw = row.get("adjacent to", "") or row.get("adjacent", "")
        adjacent = {_zone_id(v) for v in _split_list(adjacent_raw)}
        if adjacent:
            legacy_adjacency[zone_id] = adjacent

    return zones, legacy_adjacency


def _parse_access_point_rows(text: str, zones: dict[str, LocationZone]) -> list[LocationAccessPoint]:
    rows = _extract_table_after_heading(text, "Access Points")
    out: list[LocationAccessPoint] = []
    for row in rows:
        from_id = _zone_id(row.get("from", "") or row.get("from_zone_id", ""))
        to_id = _zone_id(row.get("to", "") or row.get("to_zone_id", ""))
        if not from_id or not to_id or from_id not in zones or to_id not in zones:
            continue
        label = row.get("label", "").strip() or f"{zones[from_id].name} to {zones[to_id].name}"
        access_id = _zone_id(row.get("id", "").strip() or f"{from_id}_{to_id}")
        out.append(LocationAccessPoint(
            id=access_id,
            from_zone_id=from_id,
            to_zone_id=to_id,
            label=label,
            state=(row.get("state", "").strip() or "open").lower(),
            bidirectional=_truthy(row.get("bidirectional", "yes")),
            requirements=_clean_empty(row.get("requirements", "")),
            description=row.get("description", "").strip(),
            source=(row.get("source", "").strip() or "authored"),
        ))
    return out


def _access_points_from_adjacency(
    adjacency: dict[str, set[str]],
    zones: dict[str, LocationZone],
) -> list[LocationAccessPoint]:
    out: list[LocationAccessPoint] = []
    seen: set[frozenset[str]] = set()
    for from_id, to_ids in adjacency.items():
        if from_id not in zones:
            continue
        for to_id in to_ids:
            if to_id not in zones:
                continue
            key = frozenset({from_id, to_id})
            if key in seen:
                continue
            seen.add(key)
            out.append(LocationAccessPoint(
                id=_zone_id("_".join(sorted(key))),
                from_zone_id=from_id,
                to_zone_id=to_id,
                label=f"{zones[from_id].name} to {zones[to_id].name}",
                state="open",
                bidirectional=True,
                source="authored",
            ))
    return out


def _extract_table_after_heading(text: str, heading: str) -> list[dict[str, str]]:
    heading_re = re.compile(rf"^##[ \t]+{re.escape(heading)}(?:[ \t]+.*)?[ \t]*$", re.IGNORECASE | re.MULTILINE)
    match = heading_re.search(text)
    if not match:
        return []

    section = text[match.end():]
    next_heading = re.search(r"^##\s+", section, re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start()]

    table_lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []

    header_line = ""
    data_lines: list[str] = []
    for line in table_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not header_line and _is_separator_row(cells):
            continue
        if not header_line:
            header_line = line
            continue
        data_lines.append(line)
    if not header_line:
        return []

    header = [_normalize_col(c) for c in header_line.strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in data_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if _is_separator_row(cells):
            continue
        if len(cells) < len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _normalize_col(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells if c.strip())


def _zone_id(value: str) -> str:
    raw = value.strip().lower().replace("-", " ")
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def _split_list(value: str) -> list[str]:
    cleaned = _clean_empty(value)
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"\s*,\s*", cleaned) if part.strip()]


def _truthy(value: str) -> bool:
    return value.strip().lower() not in {"no", "false", "0", "hidden"}


def _clean_empty(value: str) -> str:
    cleaned = value.strip()
    return "" if cleaned in {"-", "—", "–", ""} else cleaned
