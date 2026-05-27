"""Delta writer — after each GM response, extracts NPC/location state changes
and appends them to the relevant session delta files.

The extraction is a small, fast second Groq call (non-streaming, ~200 tokens)
that runs in a background thread so the player sees no added latency.

Delta file location:
  adventure_path/05_npcs/<npc_slug>/session_NNN.md

Delta file format (append-only):
  ## Turn N — HH:MM:SS
  **Disposition:** <change or "unchanged">
  **Location:** <current location>
  **Knowledge:** <what the NPC learned, or "nothing new">
  **Summary:** <one sentence of what happened>
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests as _requests


_EXTRACT_PROMPT = """\
You are a state tracker for a tabletop RPG. Your job is to extract NPC state \
changes from a GM response and return structured JSON. Be concise and factual.

NPCs involved in this turn: {npc_list}

GM response:
---
{gm_response}
---

For each NPC listed, extract any state changes. Return ONLY valid JSON, no prose:

{{
  "npcs": [
    {{
      "name": "<canonical NPC name>",
      "disposition": "<change description, or null if unchanged>",
      "location": "<current location, or null if not mentioned>",
      "knowledge": "<what the NPC learned about the PCs, or null>",
      "summary": "<one sentence: what happened with this NPC this turn>"
    }}
  ]
}}

Only include NPCs where something meaningful happened. \
If nothing changed for an NPC, omit them entirely. \
Return {{"npcs": []}} if nothing changed for any NPC."""


def extract_and_write(
    *,
    gm_response: str,
    npc_names: list[str],
    npc_dirs: dict[str, Path],   # canonical_name → npc folder path
    session_number: int,
    turn_number: int,
    api_key: str,
    model: str,
    groq_api_url: str = "https://api.groq.com/openai/v1/chat/completions",
) -> None:
    """Main entry point — call this in a background thread.

    Calls Groq to extract state changes, then writes delta files.
    Errors are silently swallowed (delta writes are best-effort).
    """
    if not npc_names or not api_key:
        return

    try:
        changes = _call_groq_extract(
            gm_response=gm_response,
            npc_names=npc_names,
            api_key=api_key,
            model=model,
            groq_api_url=groq_api_url,
        )
        for npc_data in changes.get("npcs", []):
            name = npc_data.get("name", "").strip()
            if not name:
                continue
            # Match by canonical name (case-insensitive)
            npc_dir = _find_dir(name, npc_dirs)
            if npc_dir is None:
                continue
            _append_delta(
                npc_dir=npc_dir,
                session_number=session_number,
                turn_number=turn_number,
                data=npc_data,
            )
    except Exception:
        pass  # delta writes are best-effort — never crash the main flow


def spawn_extract(
    *,
    gm_response: str,
    npc_names: list[str],
    npc_dirs: dict[str, Path],
    session_number: int,
    turn_number: int,
    api_key: str,
    model: str,
) -> None:
    """Fire-and-forget: run extract_and_write in a daemon thread."""
    if not npc_names or not api_key:
        return
    t = threading.Thread(
        target=extract_and_write,
        kwargs=dict(
            gm_response=gm_response,
            npc_names=npc_names,
            npc_dirs=npc_dirs,
            session_number=session_number,
            turn_number=turn_number,
            api_key=api_key,
            model=model,
        ),
        daemon=True,
        name=f"delta-s{session_number:03d}-t{turn_number:03d}",
    )
    t.start()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _call_groq_extract(
    *,
    gm_response: str,
    npc_names: list[str],
    api_key: str,
    model: str,
    groq_api_url: str,
) -> dict:
    """Make a small non-streaming Groq call to extract state changes."""
    prompt = _EXTRACT_PROMPT.format(
        npc_list=", ".join(npc_names),
        gm_response=gm_response[:3000],  # cap at 3k chars — we only need the narrative
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.0,   # deterministic extraction
        "max_tokens": 400,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = _requests.post(groq_api_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if the LLM wrapped it
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _find_dir(name: str, npc_dirs: dict[str, Path]) -> Optional[Path]:
    """Case-insensitive lookup in the npc_dirs map."""
    lower = name.lower()
    for canonical, path in npc_dirs.items():
        if canonical.lower() == lower:
            return path
    return None


def _append_delta(
    *,
    npc_dir: Path,
    session_number: int,
    turn_number: int,
    data: dict,
) -> None:
    """Append a turn entry to the NPC's session delta file."""
    delta_path = npc_dir / f"session_{session_number:03d}.md"

    ts = datetime.now().strftime("%H:%M:%S")

    lines = [f"## Turn {turn_number} — {ts}"]

    if data.get("disposition"):
        lines.append(f"**Disposition:** {data['disposition']}")
    if data.get("location"):
        lines.append(f"**Location:** {data['location']}")
    if data.get("knowledge"):
        lines.append(f"**Knowledge:** {data['knowledge']}")
    if data.get("summary"):
        lines.append(f"**Summary:** {data['summary']}")

    lines.append("")  # blank line between entries

    entry = "\n".join(lines) + "\n"

    # Append to existing file or create new
    with delta_path.open("a", encoding="utf-8") as f:
        f.write(entry)
