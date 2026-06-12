"""
api/context/npc_extractor.py
────────────────────────────
Section-level extractor for NPC base.md files.

Parses a base.md into named sections and returns only what you ask for,
enabling targeted prompt assembly without dumping the full profile.

Public API
----------
    get_npc_sections(npc_name, sections=None, include_below_line=False)
        → dict[str, str | None]

    list_npc_sections(npc_name, include_below_line=False)
        → list[str]

Section names
-------------
Matching is case-insensitive and prefix-based:
  "location"  →  "Location & Availability — Act I"
  "social"    →  "Social Checks"
  "state"     →  "State Handling"

Above-line sections (injectable, default):
  Name · Aliases · Locations · Personality · Appearance ·
  Location & Availability · GM Notes · Social Checks · Secrets · State Handling
  (any ## header above <!-- REFERENCE -->)

Below-line fields/sections (reference only, opt-in):
  Tier · Role · Flags · Narrative Function
  (any **Key:** field or ## header below <!-- REFERENCE -->)
"""

from __future__ import annotations

import re
from pathlib import Path

_NPC_ROOT = Path(__file__).parent.parent.parent / "adventure_path" / "01_npcs"
_REFERENCE_MARKER = "<!-- REFERENCE -->"


# ── NPC file resolution ───────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """'Abstalar Zantus' → 'abstalar_zantus'"""
    s = name.lower().strip()
    s = re.sub(r"['\"]", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _find_base_md(npc_name: str, npc_root: Path | None = None) -> Path:
    """
    Resolve an NPC name or slug to its base.md path.

    Resolution order:
      1. Direct slug match  →  <npc_root>/<slug>/base.md
      2. Scan all folders for a matching H1 canonical name

    Raises FileNotFoundError if nothing matches.
    """
    root = npc_root or _NPC_ROOT
    slug = _slugify(npc_name)

    direct = root / slug / "base.md"
    if direct.exists():
        return direct

    # Fallback: scan canonical names
    for folder in root.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        candidate = folder / "base.md"
        if not candidate.exists():
            continue
        try:
            first_line = candidate.read_text(encoding="utf-8").split("\n", 1)[0]
        except OSError:
            continue
        if first_line.startswith("# ") and _slugify(first_line[2:]) == slug:
            return candidate

    raise FileNotFoundError(
        f"No base.md for '{npc_name}' (slug '{slug}') under {root}"
    )


# ── Markdown parser ───────────────────────────────────────────────────────────

def _parse_block(text: str) -> dict[str, str]:
    """
    Parse a markdown block into {field_name: content}.

    Captures three things:
      • H1 line              →  key "Name",     value = the name string
      • **Key:** Value lines →  key "Key",       value = rest of line
        (top-level metadata such as Aliases, Locations, Tier, Role, Flags)
      • ## Section headers   →  key = header text, value = content until next ## or end
    """
    result: dict[str, str] = {}

    # H1 name (first match only)
    h1 = re.search(r"^# (.+)$", text, re.MULTILINE)
    if h1:
        result["Name"] = h1.group(1).strip()

    # Split into preamble + alternating (header, content) pairs
    # re.split with a capturing group produces: [pre, hdr1, body1, hdr2, body2, ...]
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    preamble = parts[0]

    # **Key:** Value metadata fields in the preamble
    for m in re.finditer(r"^\*\*([^*]+):\*\*\s*(.+)$", preamble, re.MULTILINE):
        result[m.group(1).strip()] = m.group(2).strip()

    # Section headers + bodies
    i = 1
    while i + 1 <= len(parts) - 1:
        header = parts[i].strip()
        body = parts[i + 1].strip()
        result[header] = body
        i += 2

    return result


def _parse_npc_file(
    path: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Return (above_line, below_line) section dicts for a base.md file.

    above_line: everything before <!-- REFERENCE --> — these are the injectable sections.
    below_line: Tier / Role / Flags / Narrative Function — reference/meta, opt-in only.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileNotFoundError(f"Cannot read {path}: {exc}") from exc

    if _REFERENCE_MARKER in text:
        above_raw, below_raw = text.split(_REFERENCE_MARKER, 1)
    else:
        above_raw, below_raw = text, ""

    return _parse_block(above_raw), _parse_block(below_raw)


# ── Section name matching ─────────────────────────────────────────────────────

def _match_key(needle: str, pool: dict[str, str]) -> tuple[str, str] | None:
    """
    Case-insensitive key lookup with priority rules:
      1. Exact match wins ("Personality" beats "Personality (extra)")
      2. Among prefix matches, longest key wins — section headers like
         "Location & Availability — Act I" beat short metadata fields
         like "Locations" when the needle is "location".

    "location"  →  "Location & Availability — Act I"  (not "Locations")
    "social"    →  "Social Checks"
    "state"     →  "State Handling"
    Returns (matched_key, value) or None.
    """
    needle_lower = needle.strip().lower()
    matches = [
        (k, v) for k, v in pool.items()
        if k.lower() == needle_lower or k.lower().startswith(needle_lower)
    ]
    if not matches:
        return None
    # Exact match takes priority
    exact = [(k, v) for k, v in matches if k.lower() == needle_lower]
    if exact:
        return exact[0]
    # Longest key is most specific (section headers > short metadata fields)
    return max(matches, key=lambda kv: len(kv[0]))


# ── Public API ────────────────────────────────────────────────────────────────

def get_npc_sections(
    npc_name: str,
    sections: list[str] | None = None,
    include_below_line: bool = False,
    _npc_root: Path | None = None,
) -> dict[str, str | None]:
    """
    Extract named sections from an NPC's base.md.

    Parameters
    ----------
    npc_name:
        Display name ("Abstalar Zantus") or folder slug ("abstalar_zantus").
    sections:
        Section/field names to return.  None = return everything above the line.
        Matching is case-insensitive and prefix-based.
        "Name", "Aliases", "Locations" are always returned when present.
    include_below_line:
        Also search Tier / Role / Flags / Narrative Function (below <!-- REFERENCE -->).

    Returns
    -------
    Dict always containing "Name".  Requested keys that are absent → None.

    Examples
    --------
    >>> get_npc_sections("Alma Avertin", ["Personality"])
    {"Name": "Alma Avertin", "Personality": "Alma is Sandpoint's warm..."}

    >>> get_npc_sections("Abstalar Zantus", ["Social Checks", "State Handling"])
    {"Name": "Abstalar Zantus", "Social Checks": "...", "State Handling": "..."}

    >>> get_npc_sections("Ameiko Kaijitsu", include_below_line=True)
    {"Name": "Ameiko Kaijitsu", "Aliases": "...", ..., "Tier": "II — ...", ...}
    """
    path = _find_base_md(npc_name, _npc_root)
    above, below = _parse_npc_file(path)

    # Build the search pool
    pool: dict[str, str] = dict(above)
    if include_below_line:
        # below fields don't overwrite above fields
        for k, v in below.items():
            if k not in pool:
                pool[k] = v

    # Return everything when no filter given
    if sections is None:
        return dict(pool)

    result: dict[str, str | None] = {"Name": pool.get("Name")}

    for req in sections:
        if req.lower() == "name":
            continue  # already included
        match = _match_key(req, pool)
        if match:
            key, val = match
            result[key] = val
        else:
            result[req] = None  # requested but absent

    return result


def list_npc_sections(
    npc_name: str,
    include_below_line: bool = False,
    _npc_root: Path | None = None,
) -> list[str]:
    """
    Return all section / field names available for an NPC.

    Useful for discovery before calling get_npc_sections().

    Example
    -------
    >>> list_npc_sections("Abstalar Zantus")
    ["Name", "Aliases", "Locations", "Personality", "Appearance",
     "Location & Availability — Act I", "GM Notes", "Social Checks",
     "Secrets", "State Handling"]

    >>> list_npc_sections("Abstalar Zantus", include_below_line=True)
    [...above..., "Tier", "Role", "Flags", "Narrative Function"]
    """
    path = _find_base_md(npc_name, _npc_root)
    above, below = _parse_npc_file(path)

    keys = list(above.keys())
    if include_below_line:
        for k in below:
            if k not in above:
                keys.append(k)
    return keys
