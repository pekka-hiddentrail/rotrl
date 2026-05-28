"""Skill lookup — detects skill-relevant actions in player input and returns
the matching PF1e skill rules to inject into the current turn's system prompt.

Design mirrors npc_lookup: zero extra LLM calls, per-turn injection only,
fully data-driven from adventure_path/06_rules/skills/.

Skill file format (adventure_path/06_rules/skills/<skill>.md):
  # Skill Name
  **Triggers:** verb one, verb two, multi word trigger
  ...rest is the rules text injected verbatim...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional


@dataclass
class SkillMatch:
    skill_name: str
    rules_text: str           # full skill file body (minus header/triggers line)
    matched_trigger: str = "" # the trigger string that fired the match


@dataclass
class SkillIndex:
    """Lazy-loaded skill index built by scanning adventure_path/06_rules/skills/.

    Instantiate once per process (module-level singleton in session_manager).
    """
    _repo_root: Path
    _entries: dict[str, SkillMatch] = field(default_factory=dict, init=False)
    # trigger (lower-cased) → skill_name
    _triggers: dict[str, str] = field(default_factory=dict, init=False)
    _loaded: bool = field(default=False, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        skills_root = self._repo_root / "adventure_path" / "06_rules" / "skills"
        if not skills_root.exists():
            self._loaded = True
            return

        for skill_file in sorted(skills_root.glob("*.md")):
            if skill_file.name.startswith("_"):
                continue

            skill_name, triggers, body = _parse_skill_file(skill_file)
            if not skill_name:
                continue

            self._entries[skill_name] = SkillMatch(
                skill_name=skill_name,
                rules_text=body,
            )

            for trigger in triggers:
                t = trigger.lower().strip()
                if t:
                    self._triggers[t] = skill_name

        self._loaded = True

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> Optional[SkillMatch]:
        """Scan *text* (player input) for any skill trigger phrase.

        Returns the best match (longest trigger wins), or None.
        """
        self._ensure_loaded()
        lower = text.lower()
        best_skill: Optional[str] = None
        best_trigger = ""
        best_len = 0

        for trigger, skill_name in self._triggers.items():
            if re.search(rf"\b{re.escape(trigger)}\b", lower) and len(trigger) > best_len:
                best_skill = skill_name
                best_trigger = trigger
                best_len = len(trigger)

        if best_skill:
            return replace(self._entries[best_skill], matched_trigger=best_trigger)
        return None

    def lookup(self, skill_name: str) -> Optional[SkillMatch]:
        """Direct lookup by skill name (case-insensitive)."""
        self._ensure_loaded()
        lower = skill_name.lower()
        for name, entry in self._entries.items():
            if name.lower() == lower:
                return entry
        return None

    def format_context(self, match: SkillMatch) -> str:
        """Return a context block ready for injection into a system prompt."""
        return f"## Skill Reference — {match.skill_name}\n\n{match.rules_text.strip()}"

    @property
    def known_skills(self) -> list[str]:
        self._ensure_loaded()
        return list(self._entries.keys())


# ── File parser ───────────────────────────────────────────────────────────────

def _parse_skill_file(path: Path) -> tuple[str, list[str], str]:
    """Parse a skill markdown file.

    Returns (skill_name, triggers, rules_body).
    skill_name from first `# Heading`.
    triggers from `**Triggers:** ...` line.
    rules_body is the GM payload — everything between the triggers line and the
    optional ``<!-- REFERENCE -->`` separator.  Content after that separator is
    reader documentation and is never injected into the system prompt.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "", [], ""

    skill_name = ""
    triggers: list[str] = []
    body_lines: list[str] = []

    for line in text.splitlines():
        if not skill_name and line.startswith("# "):
            skill_name = line[2:].strip()
            continue

        m = re.match(r"\*\*Triggers:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            triggers = [t.strip() for t in m.group(1).split(",") if t.strip()]
            continue

        if line.strip() == "<!-- REFERENCE -->":
            break  # everything below this line is reader-only, never injected

        body_lines.append(line)

    return skill_name, triggers, "\n".join(body_lines).strip()
