"""Event index — loads %%EVENT%% content files from adventure_path/02_events/.

Each file has a metadata header (above <!-- INJECT -->) with the event ID and
trigger description, and injectable content below the marker.

The index provides two things:
  - get(event_id)      → EventEntry with injectable content, or None
  - event_map_text     → compact string injected into the system prompt so the
                         LLM knows which event IDs exist and when to fire them

Design:
- Zero extra LLM calls — pure file loading
- Lazy-loaded singleton (same pattern as NpcIndex / LocationIndex)
- Event files live in adventure_path/02_events/<event_id>.md
- Files starting with "_" are skipped (templates, notes)

File format:
  **Event:** <event_id>
  **Trigger:** <one-line description of when to fire this event>
  **Expires:** 5 turns

  <!-- INJECT -->

  ## Active Event — ...
  (content injected into system prompt while event is active)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EventEntry:
    event_id: str
    trigger: str        # human/LLM-readable condition description
    content: str        # injectable markdown, everything below <!-- INJECT -->
    event_type: str = ""  # backend metadata: "combat", "aftermath", etc. Not shown to LLM.


@dataclass
class EventIndex:
    """Lazy-loaded index of event content files.

    Instantiate once per process (module-level singleton in session_manager).
    """
    _repo_root: Path
    _entries: dict[str, EventEntry] = field(default_factory=dict, init=False)
    _loaded: bool = field(default=False, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        events_root = self._repo_root / "adventure_path" / "02_events"
        if not events_root.exists():
            self._loaded = True
            return

        for path in sorted(events_root.glob("*.md")):
            if path.name.startswith("_"):
                continue
            entry = _parse_event_file(path)
            if entry:
                self._entries[entry.event_id] = entry

        self._loaded = True

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, event_id: str) -> Optional[EventEntry]:
        """Return the EventEntry for *event_id*, or None if not found."""
        self._ensure_loaded()
        return self._entries.get(event_id)

    def event_map_text(self) -> str:
        """Return a compact block for the system prompt listing all known events.

        Returns an empty string if no events are loaded (zero-cost when unused).
        """
        self._ensure_loaded()
        if not self._entries:
            return ""

        lines = [
            "AVAILABLE EVENTS — write `%%EVENT%% <id>` on its own line when the condition is met:",
        ]
        for entry in self._entries.values():
            lines.append(f"- {entry.event_id}: {entry.trigger}")
        lines.append("One event per response. Do not repeat an event already fired this session.")
        return "\n".join(lines)

    @property
    def known_event_ids(self) -> list[str]:
        self._ensure_loaded()
        return list(self._entries.keys())


# ── File parser ───────────────────────────────────────────────────────────────

def _parse_event_file(path: Path) -> Optional[EventEntry]:
    """Parse an event file and return an EventEntry, or None if malformed."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    event_id = ""
    trigger = ""
    event_type = ""
    content_lines: list[str] = []
    in_content = False

    for line in text.splitlines():
        if in_content:
            content_lines.append(line)
            continue

        if line.strip() == "<!-- INJECT -->":
            in_content = True
            continue

        m = re.match(r"\*\*Event:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            event_id = m.group(1).strip()
            continue

        m = re.match(r"\*\*Trigger:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            trigger = m.group(1).strip()
            continue

        m = re.match(r"\*\*Type:\*\*\s*(.+)", line, re.IGNORECASE)
        if m:
            event_type = m.group(1).strip()
            continue

    if not event_id or not in_content:
        return None

    content = "\n".join(content_lines).strip()
    return EventEntry(event_id=event_id, trigger=trigger, content=content, event_type=event_type)
