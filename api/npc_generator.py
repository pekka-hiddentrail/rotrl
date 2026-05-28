"""Procedural NPC stub generator for auto-created session NPCs.

Called when %%GENERATE%% references a name not in the NPC index.
Fills any fields the LLM omitted with content from the NPC library.

Library location
----------------
adventure_path/npc_library/
  appearances.txt
  personalities.txt
  narrative_functions.txt
  reactions.txt

Each file contains plain-text entries separated by lines containing only "---".
The comment lines at the top (starting with "#") are stripped automatically.
Add entries freely — the generator picks one at random on each call.

If a library file is missing or empty the generator falls back to a single
hardcoded entry so nothing breaks during development or testing.
"""
from __future__ import annotations

import random
import re
from pathlib import Path


_LIBRARY_DIR = Path(__file__).resolve().parents[1] / "adventure_path" / "npc_library"

# Module-level cache: populated on first use, lives for the process lifetime.
# Restart the server to pick up library edits.
_table_cache: dict[str, list[str]] = {}


# ── Fallbacks (used when a library file is missing or empty) ──────────────────

_FALLBACK: dict[str, list[str]] = {
    "appearances": [
        "Nondescript in appearance, the kind of person easily forgotten in a crowd.",
    ],
    "personalities": [
        "Cooperative and straightforward; gives direct answers to direct questions.",
    ],
    "narrative_functions": [
        "Background local who provides colour and overheard rumour when engaged.",
    ],
    "reactions": [
        "Politely helpful on first meeting; responds well to courtesy.",
    ],
}


# ── Library loader ────────────────────────────────────────────────────────────

def _load_table(name: str) -> list[str]:
    """Read <name>.txt from the library directory and return a list of entries.

    Entries are separated by lines containing only "---".
    Lines starting with "#" are treated as comments and stripped.
    """
    path = _LIBRARY_DIR / f"{name}.txt"
    if not path.exists():
        return _FALLBACK.get(name, ["(missing library entry)"])

    raw = path.read_text(encoding="utf-8")

    # Strip comment lines before splitting
    cleaned_lines = [
        line for line in raw.splitlines()
        if not line.strip().startswith("#")
    ]
    cleaned = "\n".join(cleaned_lines)

    entries = [e.strip() for e in re.split(r"(?m)^---$", cleaned) if e.strip()]
    return entries if entries else _FALLBACK.get(name, ["(empty library)"])


def _get_table(name: str) -> list[str]:
    """Return the cached table for *name*, loading from disk on first access."""
    if name not in _table_cache:
        _table_cache[name] = _load_table(name)
    return _table_cache[name]


def reload_library() -> None:
    """Flush the in-memory cache so the next call re-reads all library files.

    Useful in tests and for a future hot-reload endpoint.
    """
    _table_cache.clear()


# ── Public helpers ────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert a canonical NPC name to a filesystem-safe slug.

    Examples
    --------
    >>> slugify("Gorm Hysys")
    'gorm_hysys'
    >>> slugify("Abstalar Zantus")
    'abstalar_zantus'
    """
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def auto_aliases(name: str) -> list[str]:
    """Return plausible short-form aliases from a canonical name.

    Keeps only parts longer than three characters so short particles
    ('of', 'the', 'van') are not registered as aliases.

    Examples
    --------
    >>> auto_aliases("Gorm Hysys")
    ['gorm', 'hysys']
    >>> auto_aliases("Bo")
    []
    """
    return [p.lower() for p in name.split() if len(p) > 3]


# ── Social check DCs — Tier IV Functional NPC ────────────────────────────────
# These are mechanical constants, not creative content, so they stay in code.

_DIPLOMACY_DC  = 12
_BLUFF_DC      = 14
_INTIMIDATE_DC = 16

_STATE_COOPERATIVE = (
    "Shares what they know without reservation; may ask a small favour in return at some point."
)
_STATE_DISTRUSTFUL = (
    "Clams up and refers the party to the town guard or a more authoritative figure."
)
_STATE_KILLED = (
    "Noted in the town records; Sheriff Hemlock opens a routine inquiry."
)


# ── Generator ─────────────────────────────────────────────────────────────────

def generate_base_md(
    name: str,
    *,
    role: str = "",
    appearance: str = "",
    personality: str = "",
    locations: list[str] | None = None,
    session_number: int = 1,
    rng: random.Random | None = None,
) -> str:
    """Return a fully-formed base.md string for a new session NPC.

    Fields provided by the caller (extracted from a %%GENERATE%% block) are
    used verbatim.  Missing fields are filled at random from the library files
    in adventure_path/npc_library/.

    Parameters
    ----------
    name:
        Canonical NPC name exactly as written by the LLM.
    role:
        Occupation or function (one phrase).  Left as generic if empty.
    appearance:
        Physical description (one sentence).  Drawn from library if empty.
    personality:
        Personality and manner.  Drawn from library if empty.
    locations:
        List of location strings (e.g. ["Gorm's Fireworks", "market street"]).
    session_number:
        Written into the Flags line so the boot cleanup knows which session
        created this NPC.
    rng:
        Optional seeded ``random.Random`` for deterministic tests.
    """
    r = rng or random.Random()

    appearance       = appearance  or r.choice(_get_table("appearances"))
    personality      = personality or r.choice(_get_table("personalities"))
    narrative        = r.choice(_get_table("narrative_functions"))
    reaction         = r.choice(_get_table("reactions"))

    loc_list         = locations or ["Sandpoint"]
    aliases          = auto_aliases(name)
    aliases_str      = ", ".join(aliases) if aliases else name.split()[0].lower()
    locations_str    = ", ".join(loc_list)
    role_str         = role or "Sandpoint local"

    return (
        f"# {name}\n"
        f"\n"
        f"**Tier:** IV — Functional\n"
        f"**Role:** {role_str}\n"
        f"**Flags:** SESSION NPC — auto-generated session_{session_number:03d}\n"
        f"**Aliases:** {aliases_str}\n"
        f"**Locations:** {locations_str}\n"
        f"\n"
        f"## Personality\n"
        f"\n"
        f"{personality}\n"
        f"\n"
        f"## Appearance\n"
        f"\n"
        f"{appearance}\n"
        f"\n"
        f"## Narrative Function\n"
        f"\n"
        f"{narrative}\n"
        f"\n"
        f"## Location & Availability\n"
        f"\n"
        f"- Usually found at {locations_str}.\n"
        f"- Availability varies during major town events.\n"
        f"\n"
        f"## Reaction to PCs\n"
        f"\n"
        f"{reaction}\n"
        f"\n"
        f"## Social Checks\n"
        f"\n"
        f"- **Diplomacy:** DC {_DIPLOMACY_DC} for cooperation\n"
        f"- **Bluff:** DC {_BLUFF_DC} to deceive\n"
        f"- **Intimidate:** DC {_INTIMIDATE_DC} to coerce\n"
        f"\n"
        f"## State Handling\n"
        f"\n"
        f"- **If Cooperative:** {_STATE_COOPERATIVE}\n"
        f"- **If Distrustful:** {_STATE_DISTRUSTFUL}\n"
        f"- **If Killed:** {_STATE_KILLED}\n"
    )


def generate_location_base_md(
    name: str,
    *,
    role: str = "",
    appearance: str = "",
    location_area: str = "",
    summary: str = "",
    session_number: int = 1,
) -> str:
    """Return a base.md string for a new session-generated location stub.

    Called when a %%GENERATE%% block with type: location fires mid-session.
    Fields map directly from the block: role→type, appearance→description,
    location→district, summary→typical occupants / notes.
    """
    aliases = auto_aliases(name)
    slug = slugify(name)
    if slug not in aliases:
        aliases.insert(0, slug.replace("_", " "))
    aliases_str = ", ".join(aliases) if aliases else slug.replace("_", " ")

    description = appearance or "A location encountered during the session."
    occupants = summary or "Occupants vary."
    role_str = role or "Location"
    district = location_area or "Sandpoint"

    return (
        f"# {name}\n"
        f"**Aliases:** {aliases_str}\n"
        f"**Flags:** SESSION LOCATION — auto-generated session_{session_number:03d}\n"
        f"\n"
        f"## Description\n"
        f"\n"
        f"{description}\n"
        f"\n"
        f"## Typical Occupants\n"
        f"\n"
        f"{occupants}\n"
        f"\n"
        f"## Current State\n"
        f"\n"
        f"Encountered during session {session_number:03d}. Current state unknown — update as events develop.\n"
        f"\n"
        f"<!-- REFERENCE -->\n"
        f"**District:** {district}\n"
        f"**Type:** {role_str}\n"
        f"**Flags:** SESSION LOCATION — auto-generated session_{session_number:03d}\n"
    )
