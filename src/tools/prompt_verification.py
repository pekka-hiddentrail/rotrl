#!/usr/bin/env python3
"""
Reusable prompt and ruleset verification helpers.

This module centralizes checklist validation so prompt files can be
deterministically self-verified from Python (for example, session boot prompts).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DEFAULT_BOOT_SYSTEM_AUTHORITY_FILES = [
    "00_system_authority/GM_OPERATING_RULES.md",
    "00_system_authority/ADJUDICATION_PRINCIPLES.md",
    "00_system_authority/COMBAT_AND_POSITIONING.md",
    "00_system_authority/PF1E_RULES_SCOPE.md",
    "00_system_authority/SESSION_NOTES_PROTOCOL.md",
]


@dataclass(frozen=True)
class VerificationResult:
    item: str
    passed: bool
    message: str
    prompt_source: str


def extract_checklist_items(markdown_text: str) -> List[str]:
    """Extract checklist lines from markdown text."""
    items: List[str] = []
    for line in markdown_text.splitlines():
        match = re.match(r"^\s*(?:\*|-)\s*\[\s*\]\s*(.+?)\s*$", line)
        if match:
            items.append(match.group(1))
    return items


def verify_prompt(
    checklist_items: Iterable[str],
    prompt_text: str,
    *,
    prompt_source: str = "SESSION_BOOT_PROMPT",
    audit: Optional[Dict] = None,
    loaded_files: Optional[Iterable[str]] = None,
    required_system_authority_files: Optional[Iterable[str]] = None,
) -> List[VerificationResult]:
    """
    Verify prompt checklist items against deterministic checks and optional audit output.

    Args:
        checklist_items: Checklist labels to evaluate.
        prompt_text: Generated prompt output/narration text to validate.
        prompt_source: Name of prompt template being evaluated.
        audit: Optional semantic audit payload from an LLM checker.
        loaded_files: Optional list of loaded context files.
        required_system_authority_files: Optional required authority set.
    """
    results: List[VerificationResult] = []
    lower_prompt = prompt_text.lower()

    loaded_set = set(loaded_files or [])
    required_set = set(required_system_authority_files or DEFAULT_BOOT_SYSTEM_AUTHORITY_FILES)

    for item in checklist_items:
        key = item.strip().lower()

        if "loaded and prioritized system authority" in key:
            missing = sorted(required_set.difference(loaded_set))
            ok = len(missing) == 0
            msg = "All required System Authority files loaded." if ok else f"Missing files: {missing}"
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "system authority as the only behavioral constraint" in key:
            disallowed_prefixes = ("01_world_setting/", "02_campaign_setting/", "03_books/")
            disallowed = sorted(f for f in loaded_set if f.startswith(disallowed_prefixes))
            ok = len(disallowed) == 0
            msg = "No non-boot authority files loaded." if ok else f"Disallowed files loaded: {disallowed}"
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "non-authority files only for silent alignment" in key:
            allowed_optional = {"PLAYER_CHARACTERS.md", "PLAYER_LIMITS_AND_EXPECTATIONS.md", "SESSION_NOTES_LAST.md"}
            optional_loaded = {f for f in loaded_set if not f.startswith("00_system_authority/")}
            unknown_optional = sorted(optional_loaded.difference(allowed_optional))
            ok = len(unknown_optional) == 0
            msg = "Optional alignment files are valid." if ok else f"Unexpected optional files: {unknown_optional}"
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        # Audit-backed check (explicit example requested by user):
        if "avoided forming or resolving plans, triggers, or outcomes" in key and audit:
            prompt_source = "SESSION_BOOT_PROMPT"
            ok = bool(audit["no_plans_triggers_outcomes"]["pass"])
            msg = audit["no_plans_triggers_outcomes"]["notes"]
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "narration based only on established" in key and audit:
            ok = bool(audit["on_screen_facts_only"]["pass"])
            msg = audit["on_screen_facts_only"]["notes"]
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "avoiding implication of future threats or events" in key and audit:
            ok = bool(audit["no_future_implication"]["pass"])
            msg = audit["no_future_implication"]["notes"]
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "prevented escalation, dialogue, rolls, or time advancement" in key and audit:
            ok = bool(audit["no_escalation_dialogue_rolls_time"]["pass"])
            msg = audit["no_escalation_dialogue_rolls_time"]["notes"]
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if ('end exactly with "what do you do?"' in key or "end exactly with" in key) and audit:
            ok = bool(audit["ends_with_what_do_you_do"]["pass"])
            msg = audit["ends_with_what_do_you_do"]["notes"]
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "avoided using player motivations" in key:
            phrases = ("your goal", "you want", "you came here to", "you decided to")
            ok = not any(p in lower_prompt for p in phrases)
            msg = "No explicit motivation framing detected." if ok else "Motivation framing detected."
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if "stable, non-demanding state" in key:
            urgency_markers = ("hurry", "immediately", "right now", "at once", "you must", "forced")
            ok = not any(m in lower_prompt for m in urgency_markers)
            msg = "No urgency/compulsion phrasing detected." if ok else "Urgency/compulsion phrasing detected."
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        if 'end exactly with "what do you do?"' in key:
            ok = prompt_text.rstrip().endswith("What do you do?")
            msg = 'Ends with exactly "What do you do?"' if ok else 'Does not end with "What do you do?"'
            results.append(VerificationResult(item=item, passed=ok, message=msg, prompt_source=prompt_source))
            continue

        # Default fallback: unknown checklist item.
        results.append(
            VerificationResult(
                item=item,
                passed=False,
                message="Unknown checklist item. Extend prompt_verification mapping.",
                prompt_source=prompt_source,
            )
        )

    return results


def summarize_results(results: Iterable[VerificationResult]) -> Dict[str, object]:
    """Build a compact summary payload for logging or display."""
    result_list = list(results)
    failures = [r for r in result_list if not r.passed]
    return {
        "ok": len(failures) == 0,
        "total": len(result_list),
        "passed": len(result_list) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }


def load_markdown(path: Path) -> str:
    """Read markdown text from disk."""
    return path.read_text(encoding="utf-8")

