#!/usr/bin/env python3
"""
Resolve a prompt to the most relevant FACET file path.

Example:
    "The player needs to roll an Acrobatics Skill check"
    -> facets/FACET_SKILL_CHECK.md
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, Optional


def _normalize_facet_name(filename: str) -> str:
    """Normalize FACET file names with or without extension."""
    return Path(filename).stem.upper()


def scan_facet_files(facets_dir: Path) -> Dict[str, Path]:
    """Return available FACET_* files keyed by normalized facet name."""
    if not facets_dir.exists():
        raise FileNotFoundError(f"Facets directory not found: {facets_dir}")

    facets: Dict[str, Path] = {}
    for item in facets_dir.iterdir():
        if item.is_file() and item.name.upper().startswith("FACET_"):
            facets[_normalize_facet_name(item.name)] = item.resolve()
    return facets


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def infer_facet_name(prompt: str) -> Optional[str]:
    """Infer target FACET name from prompt text."""
    text = prompt.lower()

    skill_terms = (
        "skill check",
        "acrobatics",
        "appraise",
        "bluff",
        "climb",
        "craft",
        "diplomacy",
        "disable device",
        "disguise",
        "escape artist",
        "fly",
        "handle animal",
        "heal",
        "intimidate",
        "knowledge",
        "linguistics",
        "perception",
        "perform",
        "profession",
        "ride",
        "sense motive",
        "sleight of hand",
        "spellcraft",
        "stealth",
        "survival",
        "swim",
        "use magic device",
    )

    checks = (
        ("FACET_SKILL_CHECK", skill_terms),
        ("FACET_SAVING_THROW", ("saving throw", "will save", "reflex save", "fortitude save")),
        ("FACET_COMBAT", ("combat", "attack", "initiative", "damage", "armor class", "flank")),
        ("FACET_MOVEMENT", ("movement", "move action", "speed", "5-foot step", "positioning", "charge")),
        ("FACET_TRAVEL_TIME", ("travel", "journey", "distance", "overland", "march", "hours", "days")),
        ("FACET_INVENTORY", ("inventory", "item", "loot", "equipment", "carry", "encumbrance")),
        ("FACET_NPC_PORTRAYAL", ("npc", "dialogue", "roleplay", "portray", "personality")),
        ("FACET_SCENE_DRESSING", ("scene", "atmosphere", "description", "describe the room", "environment")),
        ("FACET_EVENTS", ("event", "trigger", "timeline", "countdown", "pressure")),
        ("FACET_RULES_RESOLUTION", ("rules", "adjudication", "raw", "resolve", "ruling")),
        ("FACET_PLAYER_MOTIVATION", ("motivation", "goal", "player intent", "hook")),
        ("FACET_CONDITIONS", ("condition", "status", "effect", "buff", "debuff")),
    )

    for facet_name, keywords in checks:
        if _contains_any(text, keywords):
            return facet_name
    return None


def resolve_facet_path(prompt: str, facets_dir: Optional[Path] = None) -> Optional[Path]:
    """Resolve prompt to a matching FACET file path from facets_dir."""
    if facets_dir is None:
        facets_dir = Path(__file__).resolve().parents[2] / "facets"

    available = scan_facet_files(facets_dir)
    inferred = infer_facet_name(prompt)
    if not inferred:
        return None
    return available.get(inferred)


def main() -> int:
    parser = argparse.ArgumentParser(description="Find FACET file path from a text prompt.")
    parser.add_argument("prompt", help="Prompt text to interpret.")
    parser.add_argument(
        "--facets-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "facets",
        help="Directory containing FACET_* files.",
    )
    args = parser.parse_args()

    path = resolve_facet_path(args.prompt, args.facets_dir)
    if path is None:
        print("No matching FACET file found.")
        return 1

    print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
