"""Combat rules lookup — detects combat-relevant actions in player input and returns
the matching PF1e rules to inject into the current turn's system prompt.

Design mirrors skill_lookup: zero extra LLM calls, per-turn injection only when
combat is active, fully data-driven from adventure_path/04_rules/combat/.

Rule file format (adventure_path/04_rules/combat/<rule>.md):
  # Rule Name
  **Triggers:** phrase one, phrase two, multi word trigger
  ...rules text injected verbatim up to <!-- REFERENCE --> separator...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional


@dataclass
class CombatRuleMatch:
    rule_name: str
    rules_text: str            # GM-facing rules body (before <!-- REFERENCE -->)
    matched_trigger: str = ""  # the trigger phrase that fired the match


@dataclass
class CombatRulesIndex:
    """Lazy-loaded combat rules index built by scanning adventure_path/04_rules/combat/.

    Instantiate once per process (module-level singleton in session_manager).
    """
    _repo_root: Path
    _entries: dict[str, CombatRuleMatch] = field(default_factory=dict, init=False)
    # trigger (lower-cased) → rule_name
    _triggers: dict[str, str] = field(default_factory=dict, init=False)
    _loaded: bool = field(default=False, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        combat_root = self._repo_root / "adventure_path" / "04_rules" / "combat"
        if not combat_root.exists():
            self._loaded = True
            return

        for rule_file in sorted(combat_root.glob("*.md")):
            if rule_file.name.startswith("_"):
                continue

            rule_name, triggers, body = _parse_combat_rule_file(rule_file)
            if not rule_name:
                continue

            self._entries[rule_name] = CombatRuleMatch(
                rule_name=rule_name,
                rules_text=body,
            )

            for trigger in triggers:
                t = trigger.lower().strip()
                if t:
                    self._triggers[t] = rule_name

        self._loaded = True

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> Optional[CombatRuleMatch]:
        """Scan *text* (player input) for any combat rule trigger phrase.

        Returns the best match (longest trigger wins), or None.
        """
        self._ensure_loaded()
        lower = text.lower()
        best_rule: Optional[str] = None
        best_trigger = ""
        best_len = 0

        for trigger, rule_name in self._triggers.items():
            if re.search(rf"\b{re.escape(trigger)}\b", lower) and len(trigger) > best_len:
                best_rule = rule_name
                best_trigger = trigger
                best_len = len(trigger)

        if best_rule:
            return replace(self._entries[best_rule], matched_trigger=best_trigger)
        return None

    def lookup(self, rule_name: str) -> Optional[CombatRuleMatch]:
        """Direct lookup by rule name (case-insensitive)."""
        self._ensure_loaded()
        lower = rule_name.lower()
        for name, entry in self._entries.items():
            if name.lower() == lower:
                return entry
        return None

    def format_context(self, match: CombatRuleMatch) -> str:
        """Return a context block ready for injection into a system prompt."""
        return f"## Combat Reference — {match.rule_name}\n\n{match.rules_text.strip()}"

    @property
    def known_rules(self) -> list[str]:
        self._ensure_loaded()
        return list(self._entries.keys())


# ── File parser ───────────────────────────────────────────────────────────────

def _parse_combat_rule_file(path: Path) -> tuple[str, list[str], str]:
    """Parse a combat rule markdown file.

    Returns (rule_name, triggers, rules_body).
    rule_name from first `# Heading`.
    triggers from `**Triggers:** ...` line.
    rules_body is the GM payload — everything between the triggers line and the
    optional ``<!-- REFERENCE -->`` separator.  Content after that separator is
    reader documentation and is never injected into the system prompt.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "", [], ""

    rule_name = ""
    triggers: list[str] = []
    body_lines: list[str] = []

    for line in text.splitlines():
        if not rule_name and line.startswith("# "):
            rule_name = line[2:].strip()
            continue

        m = re.match(r"\*\*Triggers:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            triggers = [t.strip() for t in m.group(1).split(",") if t.strip()]
            continue

        if line.strip() == "<!-- REFERENCE -->":
            break  # everything below this line is reader-only, never injected

        body_lines.append(line)

    return rule_name, triggers, "\n".join(body_lines).strip()
