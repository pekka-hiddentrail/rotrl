from __future__ import annotations

import json
import os
import random
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

import time as _time

import requests as _requests

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None  # type: ignore[assignment]  # optional; required only for "anthropic" provider

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on env vars being set externally

from api.context.npc_lookup import NpcIndex
from api.context.skill_lookup import SkillIndex
from api.context.location_lookup import LocationIndex, parse_zone_adjacency_table
from api.context.event_index import EventIndex
from api.context.combat_lookup import CombatRulesIndex
from api.api_logger import write_api_log
from api.npc_generator import generate_base_md, generate_location_base_md, slugify as _slugify

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTPUTS_DIR = _REPO_ROOT / "outputs"

# Context indexes — built lazily on first use, shared across all sessions
_npc_index: Optional[NpcIndex] = None
_skill_index: Optional[SkillIndex] = None
_location_index: Optional[LocationIndex] = None
_event_index: Optional[EventIndex] = None
_combat_rules_index: Optional[CombatRulesIndex] = None


def _get_npc_index() -> NpcIndex:
    global _npc_index
    if _npc_index is None:
        _npc_index = NpcIndex(_repo_root=_REPO_ROOT)
    return _npc_index


def _get_skill_index() -> SkillIndex:
    global _skill_index
    if _skill_index is None:
        _skill_index = SkillIndex(_repo_root=_REPO_ROOT)
    return _skill_index


def _get_location_index() -> LocationIndex:
    global _location_index
    if _location_index is None:
        _location_index = LocationIndex(_repo_root=_REPO_ROOT)
    return _location_index


def _invalidate_npc_index() -> None:
    """Force the NPC index to reload on next use.

    Called after a new NPC stub is created mid-session so that subsequent
    %%DELTAS%% writes and keyword detection find the new entry immediately.
    """
    global _npc_index
    _npc_index = None


def _invalidate_location_index() -> None:
    """Force the location index to reload on next use.

    Called after a new location stub is created mid-session so that
    subsequent turns can detect the new location immediately.
    """
    global _location_index
    _location_index = None


def _get_combat_rules_index() -> CombatRulesIndex:
    global _combat_rules_index
    if _combat_rules_index is None:
        _combat_rules_index = CombatRulesIndex(_repo_root=_REPO_ROOT)
    return _combat_rules_index


def _get_event_index() -> EventIndex:
    global _event_index
    if _event_index is None:
        _event_index = EventIndex(_repo_root=_REPO_ROOT)
    return _event_index

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MAX_RETRIES = 4
_GROQ_RETRY_BASE = float(os.getenv("ROTRL_GROQ_RETRY_BASE", "5.0"))  # seconds — doubled each attempt


def _groq_post(api_key: str, payload: dict, stream: bool = False) -> _requests.Response:
    """POST to Groq with automatic retry on 429 (rate-limit).

    Reads the ``retry-after`` or ``x-ratelimit-reset-requests`` response header
    when present; otherwise falls back to exponential back-off starting at
    ``_GROQ_RETRY_BASE`` seconds.  Raises on any non-retryable error.

    Some older Groq models (e.g. llama3-8b-8192) reject ``stream_options``
    with a 400.  On the first 400 we silently drop that key and retry once
    so usage tracking degrades gracefully rather than hard-failing.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # Work on a shallow copy so the caller's payload is never mutated.
    payload = dict(payload)
    _stream_options_dropped = False
    wait = _GROQ_RETRY_BASE
    for attempt in range(_GROQ_MAX_RETRIES + 1):
        resp = _requests.post(
            _GROQ_API_URL,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=60,
        )
        if resp.status_code == 413:
            raise RuntimeError(
                "Groq rejected the request: payload too large. "
                "The session context has grown too big for the model. "
                "Try starting a new session or switching to dev mode."
            )
        # Older models return 400 when stream_options is present — drop it and
        # retry immediately (does not count against the rate-limit retry budget).
        if resp.status_code == 400 and not _stream_options_dropped and "stream_options" in payload:
            payload.pop("stream_options")
            _stream_options_dropped = True
            continue
        if resp.status_code == 400:
            # Surface Groq's error body so the player sees "model not found" /
            # "model deprecated" instead of a bare HTTP 400.
            try:
                err_msg = (resp.json().get("error") or {}).get("message", "")
                if err_msg:
                    raise RuntimeError(f"Groq rejected the request: {err_msg}")
            except (ValueError, KeyError):
                pass
            resp.raise_for_status()
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        if attempt == _GROQ_MAX_RETRIES:
            # Try to surface a human-readable message (e.g. daily token limit exceeded)
            try:
                err_body = resp.json()
                err_msg = (err_body.get("error") or {}).get("message", "")
                if err_msg:
                    raise RuntimeError(f"Groq rate limit: {err_msg}")
            except (ValueError, KeyError):
                pass
            resp.raise_for_status()  # fall back to bare HTTPError

        # Use the server-suggested wait if provided; otherwise keep the running
        # exponential backoff value.  Note: if the header is present on retry N
        # but absent on retry N+1, the doubled header value becomes the new base —
        # acceptable since the server already said "wait this long" once.
        retry_after = (
            resp.headers.get("retry-after")
            or resp.headers.get("x-ratelimit-reset-requests")
        )
        if retry_after:
            try:
                wait = float(retry_after)
            except ValueError:
                pass
        _time.sleep(wait)
        wait = min(wait * 2, 60.0)  # cap at 60 s

    # Should never reach here
    raise RuntimeError("Groq: exhausted retries")  # pragma: no cover

# Dev mode limits: keep only the last N messages (pairs of user+assistant)
_DEV_MAX_HISTORY        = int(os.getenv("ROTRL_DEV_MAX_HISTORY",       "6"))   # 3 exchanges
_FULL_MAX_HISTORY       = int(os.getenv("ROTRL_FULL_MAX_HISTORY",      "30"))  # 15 exchanges — Ollama
_GROQ_MAX_HISTORY       = int(os.getenv("ROTRL_GROQ_MAX_HISTORY",      "10"))  # 5 exchanges  — Groq
_ANTHROPIC_MAX_HISTORY  = int(os.getenv("ROTRL_ANTHROPIC_MAX_HISTORY", "60"))  # 30 exchanges — Anthropic
_DEV_MAX_TOKENS         = int(os.getenv("ROTRL_DEV_MAX_TOKENS",        "180")) # cap generation length in dev mode
# Groq: hard ceiling on the system prompt character count.
# Injected context chunks beyond this point are silently dropped.
# ~30 000 chars ≈ 7 500 tokens — keeps all early context (base + Critical +
# Act Overview + Adjudication) and trims only the later/lower-priority chunks.
_GROQ_MAX_SYSTEM_CHARS = int(os.getenv("ROTRL_GROQ_MAX_SYSTEM_CHARS", "30000"))

# Regex that matches a %%ROLL%% … %%END%% block anywhere in GM output.
#
# The LLM sometimes writes the skill line in non-standard ways:
#   skill: Diplomacy          ← correct
#   Diplomacy: 15             ← LLM added an extra number (Sense Motive modifier etc.)
#   skill: Sense Motive       ← multi-word, correct
#   Sense Motive: 12          ← multi-word with extra number
#
# The pattern handles all of these:
#   (?:skill:\s*)? — optional "skill:" prefix
#   (?P<skill>[^\n:]+?) — skill name (stops at colon or newline, lazy)
#   (?:\s*:\s*\d+)? — optional ": <number>" suffix (swallowed, not captured)
# Regex that matches a %%DELTA%% … %%END%% block in GM output.
# Matches the entire %%DELTA%%…%%END%% block and captures the body.
# Deliberately loose: DOTALL so the body can span multiple lines in any order,
# and \s* on both ends so leading/trailing blank lines don't break the match.
# Field extraction is handled by _parse_delta_fields() below.
_DELTA_BLOCK_RE = re.compile(
    r'\s*%%DELTA%%[ \t]*\n(.*?)(?:%%END%%[ \t]*|(?=\s*%%DELTA%%|\Z))',
    re.IGNORECASE | re.DOTALL,
)

# Matches a %%GENERATE%% block emitted by the LLM when it introduces a NEW NPC.
# Processed before %%DELTA%% so that stub folders exist by the time delta writes run.
_GENERATE_BLOCK_RE = re.compile(
    r'\s*%%GENERATE%%[ \t]*\n(.*?)(?:%%END%%[ \t]*|(?=\s*%%GENERATE%%|\Z))',
    re.IGNORECASE | re.DOTALL,
)

# ── Section-based response parser ─────────────────────────────────────────────
# Primary format: the LLM structures output using %%SECTION%% markers.
# Old flat-block format (%%DELTA%%…%%END%%) is retained as a fallback.
#
# A section marker is a line containing only %%WORD%%.
# Each section's content runs from that marker to the next (or end of text).
_SECTION_MARKER_RE = re.compile(r'^%%([A-Z]+)%%[ \t]*$', re.MULTILINE)

# A bracket block is [ on its own line … ] on its own line.
# Used inside %%DELTAS%% and %%GENERATE%% sections.
# The pattern is non-greedy so consecutive blocks are split correctly.
_BRACKET_BLOCK_RE = re.compile(
    r'^\[[ \t]*\n(.*?)\n[ \t]*\]',
    re.MULTILINE | re.DOTALL,
)

# Fallback: LLM sometimes writes all fields on a single line:
# [ npc: X  disposition: old→new  key: value ]
_BRACKET_BLOCK_INLINE_RE = re.compile(
    r'^\[[ \t]+(.+?)[ \t]+\][ \t]*$',
    re.MULTILINE,
)

# Detect whether the response uses section markers at all (vs old flat format).
_HAS_SECTION_MARKERS_RE = re.compile(r'^%%(?:NARRATIVE|ROLL|DELTAS|GENERATE|EVENT)%%', re.MULTILINE)

# Detect a %%EVENT%% tag line: %%EVENT%% <event_id>
# Uses [A-Za-z]\w* so a bare %%EVENT%% followed by a newline + another %%EVENT%% ...
# line cannot cause the marker itself to be captured as the ID.
_EVENT_LINE_RE = re.compile(r'^%%EVENT%%\s+([A-Za-z]\w*)', re.MULTILINE)

# ── Narrative name detection ──────────────────────────────────────────────────
# Used to catch NPCs the LLM introduces in prose without any structured block.
# Detected names are added to session.scene_npcs so the NEXT turn's directive
# asks for a %%DELTAS%% block — stub creation happens via Layer 2 at that point.
#
# Requires ≥3 chars per word so sentence-starting words like "As", "He", "In"
# never produce a match.
_NARRATIVE_NAME_RE = re.compile(r'\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b')
# Single Title Case word (≥4 chars) — used only against the known alias table.
_NARRATIVE_SINGLE_RE = re.compile(r'\b([A-Z][a-z]{3,})\b')

# Words that appear capitalised in prose but are NOT person names.
# If EITHER word of a candidate pair is in this set, the pair is skipped.
# Loaded from adventure_path/00_system_authority/name_exclude_words.txt at import time;
# falls back to the hardcoded set if the file is absent or unreadable.
_NAME_EXCLUDE_WORDS_FALLBACK: frozenset[str] = frozenset({
    "mayor", "sheriff", "father", "mother", "brother", "sister",
    "lord", "lady", "master", "captain", "sergeant", "doctor",
    "mister", "mistress", "dame", "sir",
    "baron", "duke", "earl", "count", "prince", "princess", "king", "queen",
    "square", "hall", "street", "road", "lane", "alley", "avenue",
    "cathedral", "temple", "church", "shrine",
    "inn", "tavern", "lodge", "stage", "grounds", "plaza",
    "gate", "bridge", "market", "district", "quarter",
    "tower", "keep", "castle", "fort", "garrison",
    "shop", "store", "stall", "dock", "docks", "wharf",
    "rise", "runelords", "varisia", "sandpoint", "desna",
    "festival", "swallowtail", "lost", "coast",
    "burnt", "offerings", "pathfinder",
    "what", "who", "where", "when", "why", "how",
    "this", "that", "these", "those",
})

def _load_name_exclude_words() -> frozenset[str]:
    _path = _REPO_ROOT / "adventure_path" / "00_system_authority" / "name_exclude_words.txt"
    try:
        words = {
            line.strip().lower()
            for line in _path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        return frozenset(words) if words else _NAME_EXCLUDE_WORDS_FALLBACK
    except Exception:
        return _NAME_EXCLUDE_WORDS_FALLBACK

_NAME_EXCLUDE_WORDS: frozenset[str] = _load_name_exclude_words()


def _parse_delta_fields(body: str) -> dict[str, str]:
    """Extract key: value pairs from a %%DELTA%% block body.

    Order-independent and tolerant of extra fields the LLM may add.
    Returns a plain dict with lower-cased keys and stripped values.
    """
    fields: dict[str, str] = {}
    for line in body.splitlines():
        m = re.match(r'(\w+):\s*(.+)', line.strip())
        if m:
            fields[m.group(1).lower()] = m.group(2).strip()
    return fields

def _extract_knowledge_items(body: str) -> list[str]:
    """Return all knowledge: lines from a %%DELTA%% block body.

    Each item is a single string such as "[pcs] Yanyeeku is interested in fireworks."
    A response may have multiple knowledge: lines — all are returned.
    """
    items: list[str] = []
    for line in body.splitlines():
        m = re.match(r"knowledge:\s*(.+)", line.strip(), re.IGNORECASE)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_combatant_line(line: str) -> Optional["Combatant"]:
    """Parse a single combatant row from a %%COMBAT%% block.

    Expected format (middle-dot separated fields):
        - name: Shalelu · hp: 18/24 · ac: 17 · init: 14 · status: active
    All fields except name are optional and fall back to safe defaults.
    """
    line = re.sub(r'^\s*[-•]\s*', '', line)
    parts = re.split(r'\s*[·•]\s*', line)
    fields: dict[str, str] = {}
    for part in parts:
        if ':' in part:
            key, _, val = part.partition(':')
            fields[key.strip().lower()] = val.strip()

    name = fields.get('name', '').strip()
    if not name:
        # Bare format: "Goblin Warrior 1 · hp: 5/5 · ..." or "· Vanx · hp: ..."
        # The line may start with a leading separator making parts[0] empty — check
        # the first two segments for a non-empty, non-"key: value" candidate.
        for part in parts[:2]:
            candidate = re.sub(r'^\s*[-•·]\s*', '', part).strip()
            if candidate and ':' not in candidate:
                name = candidate
                break
    if not name:
        return None

    hp_raw = fields.get('hp', '0/0')
    hp_parts = hp_raw.split('/')
    try:
        hp_current = int(hp_parts[0].strip())
        hp_max = int(hp_parts[1].strip()) if len(hp_parts) > 1 else hp_current
    except (ValueError, IndexError):
        hp_current, hp_max = 0, 0

    try:
        ac = int(fields.get('ac', '10'))
    except ValueError:
        ac = 10

    try:
        initiative = int(fields.get('init', '0'))
    except ValueError:
        initiative = 0

    status = fields.get('status', 'active').lower().strip()

    # Parse optional conditions: "conditions: [prone, shaken]"
    conditions_raw = fields.get('conditions', '').strip()
    conditions: list = []
    if conditions_raw:
        inner = conditions_raw.strip('[]')
        conditions = [c.strip().lower() for c in inner.split(',') if c.strip()]

    return Combatant(
        name=name,
        hp_current=hp_current,
        hp_max=hp_max,
        ac=ac,
        initiative=initiative,
        status=status,
        conditions=conditions,
    )


def _parse_combat_block(
    text: str,
    existing_state: Optional["CombatState"] = None,
) -> Optional["CombatState"]:
    """Parse the body of a %%COMBAT%% section into a CombatState.

    Return values:
    - ``CombatState(round=0, combatants=[])`` — LLM wrote ``round: 0``; caller should
      clear ``session.combat_state``.  This is the *intentional clear signal*.
    - ``None`` — block is empty/None, or ``round`` was missing/0 with no combatants
      parsed (i.e. a formatting error).  Caller should **not** change existing state.
    - ``CombatState(round≥1, combatants=[...])`` — valid update; caller should store it.

    The distinction between "intentional clear" and "parse failure" prevents a single
    malformed turn from silently wiping live combat state.

    HP authority (Tier 1.1):
    When *existing_state* is provided (round 2+), HP values for **known** combatants
    are copied from *existing_state* instead of taken from the LLM block. New combatants
    (name not in existing_state) are initialised with LLM-provided HP values.
    Status and other fields are always updated from the LLM block.
    """
    if not text:
        return None

    round_num = 0
    found_round = False
    combatants: list[Combatant] = []

    for line in text.splitlines():
        round_m = re.match(r'^\s*round\s*:\s*(\d+)', line, re.IGNORECASE)
        if round_m:
            round_num = int(round_m.group(1))
            found_round = True
            continue
        # Match both labeled ("- name: Foo · hp: ...") and bare ("Foo · hp: ...") formats.
        if re.match(r'^\s*[-•·]\s*name:', line, re.IGNORECASE) or re.search(r'[·•]\s*hp\s*:', line, re.IGNORECASE):
            c = _parse_combatant_line(line)
            if c is not None:
                combatants.append(c)

    # Intentional clear: LLM explicitly wrote round: 0
    if found_round and round_num == 0:
        return CombatState(round=0, combatants=[])

    # Parse failure: no valid round found, or round > 0 but all combatant rows
    # were malformed — do not disturb existing combat state.
    if not found_round or not combatants:
        return None

    # HP authority: for round 2+, inherit HP from backend for known combatants.
    if existing_state is not None:
        existing_by_name = {c.name.lower(): c for c in existing_state.combatants}
        for c in combatants:
            existing = existing_by_name.get(c.name.lower())
            if existing is not None:
                # Keep backend HP and attack profile; update status/conditions from LLM.
                c.hp_current = existing.hp_current
                c.hp_max = existing.hp_max
                c.attacks = existing.attacks  # preserve seeded attack profile
                # Guard: LLM may speculatively mark a combatant dead/unconscious
                # before damage is actually applied (HP is owned by the backend in
                # round 2+).  If the backend HP is still positive the combatant is
                # alive — force status back to active.
                if c.hp_current > 0 and c.status in ('dead', 'unconscious'):
                    c.status = 'active'
            # New combatant (not in existing_state): use LLM-provided HP as-is.

    # current_actor: seed from initiative order on round 1; carry over on round 2+.
    if existing_state is not None:
        # Preserve whatever the backend last set (may have been advanced by the
        # advance_turn endpoint between turns).
        current_actor: Optional[str] = existing_state.current_actor
    else:
        # Round 1: highest-initiative active combatant is the first to act.
        _sorted_for_init = sorted(combatants, key=lambda c: c.initiative, reverse=True)
        _first_active = next((c for c in _sorted_for_init if c.status == "active"), None)
        current_actor = _first_active.name if _first_active else None

    return CombatState(round=round_num, combatants=combatants, current_actor=current_actor)


def _serialize_combat_state(state: Optional[CombatState]) -> Optional[dict]:
    """Convert a CombatState to a JSON-serialisable dict, or None."""
    if state is None:
        return None
    _occupied = {c.zone for c in state.combatants if c.zone and c.zone != "default"}
    _all_zones = sorted(_occupied | set(state.known_zones))
    return {
        "round": state.round,
        "current_actor": state.current_actor,
        "zones": _all_zones,
        "combatants": [
            {
                "name": c.name,
                "hp_current": c.hp_current,
                "hp_max": c.hp_max,
                "ac": c.ac,
                "effective_ac": _effective_ac(c),
                "initiative": c.initiative,
                "status": c.status,
                "conditions": list(c.conditions),
                "active_effects": list(c.active_effects),
                "zone": c.zone,
            }
            for c in state.combatants
        ],
    }


def _parse_response_sections(text: str) -> dict[str, str]:
    """Split a section-formatted LLM response into named sections.

    Returns a dict mapping uppercase section name → stripped content string.
    Graceful fallback: if no %%SECTION%% markers are found, returns
    ``{"NARRATIVE": text}`` so the full response is treated as narrative.
    """
    parts = _SECTION_MARKER_RE.split(text)
    # split() with a capturing group gives:
    #   [pre_marker_text, NAME, content, NAME, content, …]
    if len(parts) < 3:
        return {"NARRATIVE": text.strip()}
    sections: dict[str, str] = {}
    i = 1
    while i + 1 < len(parts):
        name = parts[i].strip()
        content = parts[i + 1].strip()
        if name in sections and sections[name] and content:
            sections[name] = f"{sections[name]}\n\n{content}"
        elif name not in sections or content:
            sections[name] = content
        i += 2
    if "NARRATIVE" not in sections:
        sections["NARRATIVE"] = text.strip()
    return sections


def _parse_inline_block_fields(content: str) -> dict:
    """Parse a single-line bracket-block interior into key→value pairs.

    Splits on ``word:`` boundary tokens so multi-word values (e.g. NPC names,
    disposition arrows, long summaries) are captured correctly.
    """
    fields: dict = {}
    key_spans = [(m.start(), m.group(1)) for m in re.finditer(r'\b(\w+):', content)]
    for i, (pos, key) in enumerate(key_spans):
        val_start = pos + len(key) + 1  # skip "key:"
        val_end = key_spans[i + 1][0] if i + 1 < len(key_spans) else len(content)
        val = content[val_start:val_end].strip()
        if val:
            fields[key.lower()] = val
    return fields


def _parse_bracket_blocks(text: str) -> list[dict]:
    """Extract [ … ] blocks from section text and parse each as key:value fields.

    Supports both multi-line blocks (``[`` on its own line) and single-line
    blocks (``[ key: val  key: val ]`` all on one line).  Multi-line blocks are
    tried first; single-line is the fallback when no multi-line blocks are found.

    Multiple ``knowledge:`` lines within a multi-line block are collected into a
    list so that all knowledge items are preserved (the field dict maps
    "knowledge" → list[str] rather than a single string).
    """
    blocks: list[dict] = []
    for m in _BRACKET_BLOCK_RE.finditer(text):
        fields: dict = {}
        for line in m.group(1).splitlines():
            lm = re.match(r'(\w+):\s*(.+)', line.strip())
            if lm:
                key = lm.group(1).lower()
                val = lm.group(2).strip()
                if key == "knowledge":
                    fields.setdefault("knowledge", []).append(val)
                else:
                    fields[key] = val
        if fields:
            blocks.append(fields)
    if not blocks:
        for m in _BRACKET_BLOCK_INLINE_RE.finditer(text):
            fields = _parse_inline_block_fields(m.group(1))
            if fields:
                blocks.append(fields)
    return blocks


def _write_npc_delta(fields: dict, session: GameSession) -> None:
    """Write one NPC delta — session status file and cumulative knowledge log.

    ``fields`` is a parsed bracket-block dict where ``fields["knowledge"]``
    is either absent, a single string, or a list[str].

    Applies Layer 2 (auto-stub creation) when the NPC is not yet in the index.
    """
    npc_name = fields.get("npc", "").strip()
    if not npc_name:
        return

    npc_dir = _get_npc_index().npc_dir_for(npc_name)
    if npc_dir is None:
        # Layer 2: create a minimal stub so the delta write can proceed.
        stub_parts = [f"npc: {npc_name}"]
        if fields.get("location"):
            stub_parts.append(f"location: {fields['location']}")
        _process_generate_block("\n".join(stub_parts), session)
        npc_dir = _get_npc_index().npc_dir_for(npc_name)
        if npc_dir is None:
            return  # stub creation failed

    ts_now = _ts()

    # ── Session delta file (turn-by-turn status) ───────────────────────────────
    status_lines = [f"## Turn {session.turn_number} — {ts_now}"]
    if fields.get("disposition"):
        status_lines.append(f"**Disposition:** {fields['disposition']}")
    if fields.get("location"):
        status_lines.append(f"**Location:** {fields['location']}")
    if fields.get("summary"):
        status_lines.append(f"**Summary:** {fields['summary']}")
    status_lines.append("")
    delta_path = npc_dir / f"session_{session.session_number:03d}.md"
    with delta_path.open("a", encoding="utf-8") as df:
        df.write("\n".join(status_lines) + "\n")
    _log(session, f"\n> *[Status written: {npc_name} → {delta_path.name}]*\n")

    # ── Knowledge log (cumulative across sessions) ─────────────────────────────
    k_items = fields.get("knowledge", [])
    if isinstance(k_items, str):
        k_items = [k_items]
    if k_items:
        knowledge_path = npc_dir / "knowledge.md"
        k_lines = [
            f"- {item} — S{session.session_number:03d} T{session.turn_number:03d}"
            for item in k_items
        ]
        with knowledge_path.open("a", encoding="utf-8") as kf:
            kf.write("\n".join(k_lines) + "\n")
        _log(session, f"\n> *[Knowledge written: {npc_name} ({len(k_items)} item(s))]*\n")


# Matches a %%COMBAT%% block in the old flat-block format (fallback path).
_COMBAT_BLOCK_RE = re.compile(
    r'^%%COMBAT%%[ \t]*\n(.*?)(?=^%%|\Z)',
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

def _apply_hp_deltas(combat_state: Optional["CombatState"], deltas: list) -> None:
    """Apply a list of (name, delta) HP changes to *combat_state* in-place.

    Clamps each combatant's hp_current to [0, hp_max].
    Unknown names and None combat_state are silently ignored.
    """
    if combat_state is None or not deltas:
        return
    by_name = {c.name.lower(): c for c in combat_state.combatants}
    for name, delta in deltas:
        combatant = by_name.get(name.lower())
        if combatant is not None:
            combatant.hp_current = max(0, min(combatant.hp_current + delta, combatant.hp_max))
            if delta < 0 and combatant.hp_current == 0 and combatant.status == "active":
                combatant.status = "unconscious"


# ── Tier 1.5 — Attack resolution helpers ─────────────────────────────────────

# Matches a %%ATTACK%% block (same structure as _COMBAT_BLOCK_RE).
_ATTACK_BLOCK_RE = re.compile(
    r'^%%ATTACK%%[ \t]*\n(.*?)(?=^%%|\Z)',
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

# Dice expression: NdN, NdN+M, NdN-M  (e.g. "2d6+3", "1d8", "1d4-1")
_DICE_EXPR_RE = re.compile(r'^(?P<n>\d+)d(?P<f>\d+)(?P<mod>[+-]\d+)?$', re.IGNORECASE)

# Valid PF1e conditions for combatants.
_VALID_CONDITIONS = frozenset({
    "prone", "grappled", "pinned", "blinded", "deafened", "shaken",
    "frightened", "panicked", "sickened", "nauseated", "dazed", "stunned",
    "entangled", "paralyzed", "helpless", "fatigued", "exhausted",
})


def _roll_dice(expr: str) -> tuple:
    """Roll a PF1e dice expression such as '2d6+3', '1d8', '1d4-1'.

    Returns ``(individual_rolls: list[int], total: int)``.
    On invalid or empty expression returns ``([], 0)``.
    """
    if not expr:
        return ([], 0)
    m = _DICE_EXPR_RE.match(expr.strip())
    if not m:
        return ([], 0)
    n = int(m.group("n"))
    faces = int(m.group("f"))
    mod = int(m.group("mod")) if m.group("mod") else 0
    rolls = [random.randint(1, faces) for _ in range(n)]
    return (rolls, sum(rolls) + mod)


def _parse_attack_line(line: str) -> Optional[dict]:
    """Parse a single attack row from a %%ATTACK%% block.

    Expected format (middle-dot separated):
        - attacker: Thaelion · target: Goblin 1 · bonus: +5 · damage: 1d8+3 · type: melee
    Returns a dict with keys attacker/target/bonus/damage/type, or None if the line
    is missing attacker or target.
    """
    line = re.sub(r'^\s*[-•]\s*', '', line)
    parts = re.split(r'\s*[·•]\s*', line)
    fields: dict[str, str] = {}
    for part in parts:
        if ':' in part:
            key, _, val = part.partition(':')
            fields[key.strip().lower()] = val.strip()

    attacker = fields.get('attacker', '').strip()
    target = fields.get('target', '').strip()
    if not attacker or not target:
        return None

    # Parse bonus: "+4" → 4, "-1" → -1, "4" → 4
    bonus_raw = fields.get('bonus', '+0').strip().lstrip('+')
    try:
        bonus = int(bonus_raw)
    except ValueError:
        bonus = 0

    return {
        "attacker": attacker,
        "target": target,
        "bonus": bonus,
        "damage": fields.get('damage', '1d4').strip(),
        "type": fields.get('type', 'melee').strip().lower(),
    }


def _parse_attack_block(text: Optional[str]) -> list:
    """Parse the body of a %%ATTACK%% section into a list of attack dicts.

    Returns an empty list on empty/None input or if no valid lines found.
    """
    if not text:
        return []
    attacks = []
    for line in text.splitlines():
        if re.match(r'^\s*[-•]\s*attacker:', line, re.IGNORECASE):
            a = _parse_attack_line(line)
            if a is not None:
                attacks.append(a)
    return attacks


_ACTION_FIELD_RE = re.compile(
    r'(?:^|[·•|;]\s*)(?P<key>[a-z_]+)\s*:\s*(?P<value>[^·•|;\n]+)',
    re.IGNORECASE,
)


def _parse_action_block(text: Optional[str]) -> Optional[dict]:
    """Parse a focused enemy-turn %%ACTION%% block.

    Unknown actions become ``delay`` so an over-creative response never causes
    the backend to invent mechanics.
    """
    if not text:
        return None
    sections = _parse_response_sections(text)
    block = sections.get("ACTION", text).strip()
    if not block:
        return None

    fields: dict[str, str] = {}
    for line in block.splitlines():
        stripped = line.strip().lstrip("-*•").strip()
        if not stripped:
            continue
        for match in _ACTION_FIELD_RE.finditer(stripped):
            fields[match.group("key").lower()] = match.group("value").strip()

    action = fields.get("action", "").lower()
    if not action:
        return None
    if action not in {"attack", "use_ability", "move", "delay"}:
        action = "delay"

    # ── action_type field (AC-001 to AC-004 of enemy-action-type.feature) ────
    _VALID_ACTION_TYPES = {
        "standard", "move", "full", "swift", "free", "five_foot_step", "delay",
    }
    _ACTION_TYPE_INFERENCE = {
        "attack":      "standard",
        "use_ability": "standard",
        "move":        "move",
        "delay":       "delay",
    }
    raw_at = fields.get("action_type", "").lower().strip()
    if raw_at in _VALID_ACTION_TYPES:
        action_type = raw_at
    elif raw_at:
        action_type = "standard"  # unknown value → normalise
    else:
        action_type = _ACTION_TYPE_INFERENCE.get(action, "standard")  # infer from action

    return {
        "action":      action,
        "action_type": action_type,
        "target":      fields.get("target",   ""),
        "weapon":      fields.get("weapon",   ""),
        "bonus":       fields.get("bonus",    ""),
        "damage":      fields.get("damage",   ""),
        "ability":     fields.get("ability",  ""),
        "movement":    fields.get("movement", ""),
        "reason":      fields.get("reason",   ""),
        "if_hit":      fields.get("if_hit",   ""),
        "if_miss":     fields.get("if_miss",  ""),
    }


def _effective_ac(combatant: "Combatant") -> int:
    """Return a combatant's AC including all active bonus effects."""
    return combatant.ac + sum(e.get("ac_bonus", 0) for e in combatant.active_effects)


def _apply_ac_effect(combatant: "Combatant", name: str, bonus_type: str,
                     ac_bonus: int, rounds: int) -> None:
    """Add a typed AC bonus effect to a combatant, replacing any existing same-type effect.

    Same bonus_type effects do not stack (PF1e rule). The new entry always replaces
    the old one — caller should pass the higher value when appropriate.
    """
    combatant.active_effects = [
        e for e in combatant.active_effects if e.get("bonus_type") != bonus_type
    ]
    combatant.active_effects.append({
        "name": name,
        "bonus_type": bonus_type,
        "ac_bonus": ac_bonus,
        "rounds_remaining": rounds,
    })


def _tick_effects(combatant: "Combatant") -> None:
    """Decrement rounds_remaining on all active effects; remove expired ones."""
    updated = []
    for e in combatant.active_effects:
        remaining = e.get("rounds_remaining", 0) - 1
        if remaining > 0:
            updated.append({**e, "rounds_remaining": remaining})
    combatant.active_effects = updated


def _get_combatant_ac(name: str, combat_state: Optional["CombatState"]) -> int:
    """Look up a combatant's effective AC (base + active effects) by name.

    Falls back through: exact match → partial word match → first active combatant
    of the appropriate type (so vague LLM targets like "nearest PC" still resolve).
    Returns 10 only when combat_state is None.
    """
    if combat_state is None:
        return 10
    name_lower = name.lower()
    # Exact match
    for c in combat_state.combatants:
        if c.name.lower() == name_lower and c.status == "active":
            return _effective_ac(c)
    # Partial match — any significant word (≥4 chars) from the target string
    # appears in a combatant's name (handles "Goblin Warrior" matching "Goblin Warrior 1")
    for word in name_lower.split():
        if len(word) < 4:
            continue
        for c in combat_state.combatants:
            if word in c.name.lower() and c.status == "active":
                return _effective_ac(c)
    # Last resort: if the name suggests a PC target ("pc", "player", "character",
    # "wizard", "cleric", etc.) return the first active combatant regardless.
    # This handles LLM vague targets like "nearest PC" or "the wizard".
    active = [c for c in combat_state.combatants if c.status == "active"]
    if active:
        return _effective_ac(active[0])
    return 10


def _is_pc_attacker(name: str, session: "GameSession") -> bool:
    """Return True if *name* matches a known PC (from session.pc_profiles)."""
    return name.lower() in session.pc_profiles


def _resolve_npc_attack(attack: dict, session: "GameSession") -> dict:
    """Auto-resolve a single NPC attack. Rolls d20 + bonus vs target AC.
    On hit, rolls damage and applies HP delta to combat_state.
    Returns a result dict suitable for the attack_result SSE event.
    """
    ac = _get_combatant_ac(attack["target"], session.combat_state)
    roll = random.randint(1, 20)
    total = roll + attack["bonus"]
    hit = total >= ac

    damage_rolls: list = []
    damage_total = 0
    damage_expr_error: Optional[str] = None
    if hit and session.combat_state is not None:
        expr = attack.get("damage", "")
        if not _DICE_EXPR_RE.match(expr.strip()):
            damage_expr_error = f"invalid damage_expr: '{expr}'"
            _log(session, (
                f"\n> *[WARN: {damage_expr_error} for {attack['attacker']} — 0 damage applied]*\n"
            ))
        else:
            damage_rolls, damage_total = _roll_dice(expr)
            _apply_hp_deltas(session.combat_state, [(attack["target"], -damage_total)])
        _log(session, (
            f"\n> *[NPC attack: {attack['attacker']}→{attack['target']} "
            f"rolled {roll}+{attack['bonus']}={total} vs AC {ac} — "
            f"HIT, {damage_total} damage]*\n"
        ))
    else:
        _log(session, (
            f"\n> *[NPC attack: {attack['attacker']}→{attack['target']} "
            f"rolled {roll}+{attack['bonus']}={total} vs AC {ac} — MISS]*\n"
        ))

    result: dict = {
        "attacker": attack["attacker"],
        "target": attack["target"],
        "roll": roll,
        "bonus": attack["bonus"],
        "total": total,
        "ac": ac,
        "hit": hit,
        "damage_rolls": damage_rolls,
        "damage_total": damage_total,
        "attack_type": attack["type"],
        "is_pc": False,
    }
    if damage_expr_error:
        result["error"] = damage_expr_error
    return result


def _build_attack_history_message(results: list, round_num: int) -> str:
    """Format resolved attack results as a user message for session history injection."""
    lines = [f"[ATTACK RESULTS — round {round_num}]"]
    for r in results:
        attacker = r.get("attacker", "?")
        target = r.get("target", "?")
        roll = r.get("roll", 0)
        bonus = r.get("bonus", 0)
        total = r.get("total", 0)
        ac = r.get("ac", 10)
        hit = r.get("hit", False)
        if hit:
            dmg_rolls = r.get("damage_rolls", [])
            dmg_total = r.get("damage_total", 0)
            lines.append(
                f"{attacker} → {target}: rolled {roll}{'+' if bonus >= 0 else ''}{bonus}={total} "
                f"vs AC {ac} — HIT, {dmg_rolls}={dmg_total} damage"
            )
        else:
            lines.append(
                f"{attacker} → {target}: rolled {roll}{'+' if bonus >= 0 else ''}{bonus}={total} "
                f"vs AC {ac} — MISS"
            )
    return "\n".join(lines)


def _next_attack_info(session: "GameSession") -> Optional[dict]:
    """Return info about the next PC attack in the queue, or None if queue is empty
    or the first item is currently in the damage-roll phase (hit=True, not yet resolved)."""
    if not session.attack_queue:
        return None
    first = session.attack_queue[0]
    # If first item hit but damage not yet rolled, it's waiting for damage — not "next attack"
    if first.hit is True:
        return None
    return {
        "attacker": first.attacker,
        "target": first.target,
        "bonus": first.bonus,
        "ac": _get_combatant_ac(first.target, session.combat_state),
        "damage_expr": first.damage_expr,
        "attack_type": first.attack_type,
    }


def resolve_attack_roll(session: "GameSession", rolled: int) -> dict:
    """Process a player's to-hit roll for the first queued PC attack.

    On miss: finalises the attack, removes it from the queue, populates next_attack.
    On hit: marks hit=True but leaves the attack in queue waiting for damage roll.
    Returns a dict the endpoint sends back to the frontend.
    """
    if not session.attack_queue:
        raise ValueError("No pending attack roll")
    attack = session.attack_queue[0]
    # Only process if we're in the to-hit phase (hit not yet determined)
    if attack.hit is not None:
        raise ValueError("Attack already resolved — submit damage roll instead")
    ac = _get_combatant_ac(attack.target, session.combat_state)
    total = rolled + attack.bonus
    hit = total >= ac
    attack.hit_roll = rolled
    attack.hit_total = total
    attack.hit = hit

    if not hit:
        result = {
            "attacker": attack.attacker, "target": attack.target,
            "roll": rolled, "bonus": attack.bonus, "total": total, "ac": ac,
            "hit": False, "damage_rolls": [], "damage_total": 0,
            "attack_type": attack.attack_type, "is_pc": True,
        }
        session.attack_results.append(result)
        session.attack_queue.pop(0)
        _log(session, (
            f"\n> *[PC attack: {attack.attacker}→{attack.target} "
            f"rolled {rolled}+{attack.bonus}={total} vs AC {ac} — MISS]*\n"
        ))

    next_attack = _next_attack_info(session)
    return {
        "hit": hit,
        "ac": ac,
        "roll": rolled,
        "bonus": attack.bonus,
        "total": total,
        "damage_expr": attack.damage_expr if hit else None,
        "queue_remaining": len(session.attack_queue),
        "next_attack": next_attack,
    }


def resolve_damage_roll(session: "GameSession", rolls: list, total: int) -> dict:
    """Process a player's damage roll for the current hit PC attack.

    Applies HP delta, finalises the attack, removes it from the queue.
    Returns a dict the endpoint sends back to the frontend.
    """
    if not session.attack_queue or session.attack_queue[0].hit is not True:
        raise ValueError("No pending damage roll")
    attack = session.attack_queue[0]
    attack.damage_rolls = list(rolls)
    attack.damage_total = total
    if session.combat_state is not None:
        if attack.is_heal:
            # Positive delta: heal the target; also restore unconscious → active.
            _apply_hp_deltas(session.combat_state, [(attack.target, +total)])
            target_c = next(
                (c for c in session.combat_state.combatants
                 if c.name.lower() == attack.target.lower()), None
            )
            if target_c and target_c.status == "unconscious" and target_c.hp_current > 0:
                target_c.status = "active"
        else:
            _apply_hp_deltas(session.combat_state, [(attack.target, -total)])
    result = {
        "attacker": attack.attacker, "target": attack.target,
        "roll": attack.hit_roll, "bonus": attack.bonus,
        "total": attack.hit_total,
        "ac": _get_combatant_ac(attack.target, session.combat_state),
        "hit": True, "damage_rolls": list(rolls), "damage_total": total,
        "attack_type": attack.attack_type, "is_pc": True,
        "is_spell": attack.is_spell,
        "spell_name": attack.spell_name if attack.is_spell else None,
        "is_heal": attack.is_heal,
    }
    session.attack_results.append(result)
    session.attack_queue.pop(0)
    action = "healed" if attack.is_heal else "damage"
    _log(session, (
        f"\n> *[PC {action}: {attack.attacker}→{attack.target} "
        f"rolled {rolls} = {total} {action}]*\n"
    ))
    next_attack = _next_attack_info(session)
    return {
        "damage_rolls": list(rolls),
        "damage_total": total,
        "queue_remaining": len(session.attack_queue),
        "next_attack": next_attack,
    }


_ROLL_BLOCK_RE = re.compile(
    r'\s*%%ROLL%%\s*\n'
    r'(?:skill:\s*)?(?P<skill>[^\n:]+?)(?:\s*:\s*\d+)?\s*\n'
    r'dc:\s*(?P<dc>\d+)\s*\n'
    r'success:\s*(?P<success>[^\n]+)\n'
    r'failure:\s*(?P<failure>[^\n]+)\n?'   # trailing newline optional (last line)
    r'(?:%%END%%\s*)?',                    # %%END%% optional — LLMs often omit it
    re.IGNORECASE,
)


def _parse_roll_section(text: str) -> Optional[dict]:
    """Parse a %%ROLL%% section body into skill/DC/success/failure fields."""
    if not text:
        return None

    _roll_blocks = _parse_bracket_blocks(text)
    if not _roll_blocks:
        # Fallback: single-line bracket format (what the spec shows):
        #   [ skill: X  dc: N  success: long text  failure: long text ]
        # _BRACKET_BLOCK_RE requires [ on its own line; this handles inline.
        _inline_m = re.search(
            r"skill:\s*(?P<skill>.+?)\s+dc:\s*(?P<dc>\d+)\s+success:\s*(?P<success>.+?)\s+failure:\s*(?P<failure>.+?)\s*\]",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if _inline_m:
            _roll_blocks = [{
                "skill":   _inline_m.group("skill").strip(),
                "dc":      _inline_m.group("dc").strip(),
                "success": _inline_m.group("success").strip(),
                "failure": _inline_m.group("failure").strip(),
            }]
    if not _roll_blocks:
        # Live models sometimes write the section body as plain fields:
        # skill: Perception
        # dc: 15
        # success: ...
        # failure: ...
        _line_m = re.search(
            r"(?:skill:\s*)?(?P<skill>[^\n:]+?)(?:\s*:\s*\d+)?\s*\n"
            r"dc:\s*(?P<dc>\d+)\s*\n"
            r"success:\s*(?P<success>.*?)\n"
            r"failure:\s*(?P<failure>.*)\s*$",
            text.strip(),
            re.DOTALL | re.IGNORECASE,
        )
        if _line_m:
            _roll_blocks = [{
                "skill":   _line_m.group("skill").strip(),
                "dc":      _line_m.group("dc").strip(),
                "success": _line_m.group("success").strip(),
                "failure": _line_m.group("failure").strip(),
            }]
    if not _roll_blocks:
        return None

    _rf = _roll_blocks[0]
    try:
        return {
            "skill":   _rf.get("skill", "").strip(),
            "dc":      int(_rf.get("dc", 0)),
            "success": _rf.get("success", "").strip(),
            "failure": _rf.get("failure", "").strip(),
        }
    except (ValueError, KeyError):
        return None

# The system prompt is fixed at boot.
# Dynamic context (NPC profiles, skill rules, location NPCs) is injected per-turn
# via keyword detection in _stream_chat — never appended permanently.


@dataclass
class ActiveEvent:
    """An event currently injecting content into the system prompt."""
    event_id: str
    content: str
    turns_remaining: int


@dataclass
class WarmEvent:
    """Runtime state for one schedulable event tracked by the temperature scheduler."""
    readiness: float = 0.0
    threshold: float = 75.0
    base_gain: float = 1.0
    failed_rolls: int = 0
    frozen: bool = False
    last_zone_match_turn: int = 0
    turns_remaining: int = 0          # >0 while this event is the active_event_id
    zones: list = field(default_factory=list)        # location canonical names that grant gain
    action_gain_map: dict = field(default_factory=dict)  # intent_tag → extra gain


@dataclass
class EventRuntime:
    """Scheduler state persisted to state.json each turn."""
    active_event_id: Optional[str] = None
    active_chain_id: Optional[str] = None
    active_node_id: Optional[str] = None
    warm_events: dict = field(default_factory=dict)   # event_id → WarmEvent
    completed_events: list = field(default_factory=list)
    cooldowns: dict = field(default_factory=dict)     # event_id → turns_remaining


@dataclass
class Combatant:
    """A single combatant in the active combat tracker."""
    name: str
    hp_current: int
    hp_max: int
    ac: int
    initiative: int
    status: str = "active"  # "active" | "unconscious" | "fled" | "dead"
    conditions: list = field(default_factory=list)  # list[str] — PF1e condition names
    attacks: dict = field(default_factory=dict)     # {"melee": [...], "ranged": [...]} seeded from event file
    # Active spell/ability effects. Each entry: {name, bonus_type, ac_bonus, rounds_remaining}.
    # bonus_type values: "shield", "deflection", "morale", "dodge", etc. Same-type effects
    # do not stack — the new entry replaces the old one (higher value wins in _apply_ac_effect).
    active_effects: list = field(default_factory=list)
    zone: str = "default"           # named zone from event file; "default" = no zone tracking

    def __post_init__(self) -> None:
        self.hp_current = max(0, min(self.hp_current, self.hp_max))
        if self.status not in ("active", "unconscious", "fled", "dead"):
            self.status = "active"
        # Validate conditions — silently drop unknown values
        self.conditions = [c for c in self.conditions if c in _VALID_CONDITIONS]


@dataclass
class CombatState:
    """Current combat round and combatant list."""
    round: int
    combatants: list  # list[Combatant]
    current_actor: Optional[str] = None  # name of whoever is acting this turn
    known_zones: list = field(default_factory=list)  # all zone names from event file


@dataclass
class PendingAttack:
    """A single queued PC attack awaiting player dice rolls (Tier 1.5)."""
    attacker: str
    target: str
    bonus: int
    damage_expr: str
    attack_type: str = "melee"   # "melee" | "ranged" | "spell" | "heal"
    is_pc: bool = False
    is_spell: bool = False        # True for spell-based attacks (no attack roll)
    spell_name: str = ""          # e.g. "Magic Missile"; empty for weapon attacks
    is_heal: bool = False         # True for healing spells — positive HP delta
    # Filled progressively during resolution
    hit_roll: Optional[int] = None
    hit_total: Optional[int] = None
    hit: Optional[bool] = None
    damage_rolls: list = field(default_factory=list)
    damage_total: int = 0


@dataclass
class GameSession:
    id: str
    session_number: int
    model: str
    host: str
    temperature: float
    dev_mode: bool = False
    event_scheduler: bool = False
    provider: str = "ollama"   # "ollama" | "groq" | "anthropic"
    num_ctx: int = 2048
    num_gpu: int = 999
    system_prompt: str = ""
    messages: list = field(default_factory=list)
    log_path: Optional[Path] = None
    turn_number: int = 0  # incremented at the start of each player turn
    # Set when GM requests a dice roll; cleared after resolve_roll() is called.
    pending_roll: Optional[dict] = None  # {skill, dc, success, failure, speaker?}
    # Canonical NPC names active in the current scene, accumulated across turns.
    # Used to keep injecting the %%DELTAS%% instruction even when the player
    # doesn't name an NPC explicitly on a later turn.
    scene_npcs: list = field(default_factory=list)
    # Canonical location names visited in the current session, accumulated across turns.
    # Full location profiles are re-injected as ambient context on subsequent turns.
    scene_locations: list = field(default_factory=list)
    # Active location/encounter zone graph. Keys and values use display names so
    # they line up with current Combatant.zone values.
    current_location_id: str = ""
    party_zone_id: str = ""
    zone_map: dict = field(default_factory=dict)         # dict[str, set[str]]
    zone_properties: dict = field(default_factory=dict)  # dict[str, list[str]]
    # Events currently active — each has content injected for turns_remaining turns.
    active_events: list = field(default_factory=list)  # list[ActiveEvent]
    # Combatant data seeded from event files when a combat event fires.
    # Keys are lowercase names; values carry at minimum {"init_mod": int}.
    # SA-2 will extend entries with hp, ac, attacks. Consumed by roll_combat_initiatives.
    pending_combatants: dict = field(default_factory=dict)
    # Set True when round-1 %%COMBAT%% is parsed with an active combat event and combatants
    # have been seeded. Tells the SSE layer to emit "initiative_pending" instead of
    # "combat_update" so the UI can prompt the player to click Roll Initiatives.
    # Cleared after the initiative_pending SSE is emitted OR after roll_combat_initiatives.
    _await_initiative_roll: bool = False
    # Set True by stream_resume_combat so that _stream_chat auto-advances to the next
    # combatant before emitting the final combat_update SSE.  Mirrors the auto-advance
    # that stream_enemy_turn already does at the end of each enemy turn.
    _advance_combat_after_stream: bool = False
    # Name of the combatant who most recently finished their turn.
    # Set by advance_combat_turn before changing current_actor.
    # Used by _build_enemy_turn_user to give the LLM narrative continuity.
    last_actor: str = ""
    # Stores resolved PC turn intent + original text pending LLM narration.
    # Set by stream_pc_turn; consumed by stream_resume_combat → _stream_pc_turn_narration.
    _pending_pc_narration: Optional[dict] = None
    # Set True when combat is auto-initialized from a combat event file.
    # Causes the LLM's %%COMBAT%% block to be discarded this turn (backend owns the state).
    _skip_combat_block: bool = False
    # Active combat state — set when the LLM writes a %%COMBAT%% block with round ≥ 1.
    # Cleared to None when round == 0 or all combatants are inactive.
    combat_state: Optional[CombatState] = None
    # Slim PC profiles built once at boot. Keys are lowercase canonical names.
    # Each entry has "narrative" (appearance + personality) and "mechanical" (stats).
    pc_profiles: dict = field(default_factory=dict)
    # Tier 1.5 — PC attack queue and resolved results for this combat round.
    # attack_queue: PC attacks awaiting player dice; attack_results: all resolved
    # attacks collected until /resume_combat injects them into history and calls LLM.
    attack_queue: list = field(default_factory=list)   # list[PendingAttack]
    attack_results: list = field(default_factory=list) # list[dict]
    # Active character in the UI — PC name when a character is selected, "party" otherwise.
    # Set by the frontend via PUT /sessions/{id}/active_character.
    active_character: str = "party"
    # PC HP tracker — persists current HP between combats within a session.
    # Keys are lowercase PC names. Updated from combat_state on every _write_session_state call.
    # Used instead of hp_max when seeding a new combat so healed-only recovery is respected.
    pc_current_hp: dict = field(default_factory=dict)
    # Temperature scheduler runtime — only active when session.event_scheduler is True.
    event_runtime: EventRuntime = field(default_factory=EventRuntime)


_sessions: dict[str, GameSession] = {}


def _session_state_path(session: "GameSession") -> Path:
    return _REPO_ROOT / "sessions" / f"session_{session.session_number:03d}" / "state.json"


def _serialize_event_runtime(rt: "EventRuntime") -> dict:
    """Serialize EventRuntime to a JSON-safe dict for state.json."""
    import dataclasses as _dc
    d = _dc.asdict(rt)
    # warm_events keys are event_id strings; asdict converts WarmEvent instances to dicts automatically.
    return d


def _write_session_state(session: "GameSession") -> None:
    """Write a state snapshot to sessions/session_NNN/state.json.

    Fields: mode, round, events, active_character, combatants (empty list when not in combat).
    """
    import json as _json
    path = _session_state_path(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Snapshot current PC HP from active combat state so it survives combat end
    if session.combat_state is not None:
        pc_keys = set(session.pc_profiles.keys())
        for _c in session.combat_state.combatants:
            if _c.name.lower() in pc_keys:
                session.pc_current_hp[_c.name.lower()] = _c.hp_current
    state = {
        "mode":             "combat" if session.combat_state is not None else "social",
        "round":            session.combat_state.round if session.combat_state is not None else 0,
        "events":           [ev.event_id for ev in session.active_events],
        # In combat, the current initiative actor drives active_character in state.json.
        # Falls back to session.active_character when combat is inactive or no actor set.
        "active_character": (
            session.combat_state.current_actor
            if session.combat_state is not None and session.combat_state.current_actor is not None
            else session.active_character
        ),
        "combatants": (
            _serialize_combat_state(session.combat_state)["combatants"]
            if session.combat_state is not None else []
        ),
        "pc_current_hp": session.pc_current_hp,
        "current_location_id": session.current_location_id,
        "party_zone_id": session.party_zone_id,
        "zone_map": {k: sorted(v) for k, v in session.zone_map.items()},
        "zone_properties": session.zone_properties,
        # event_runtime is written for external inspection (Event Status panel) only.
        # It is NOT read back on session restore — see BUG-003 / EVENT-TODO E1-9.
        "event_runtime": _serialize_event_runtime(session.event_runtime),
    }
    try:
        path.write_text(_json.dumps(state, indent=2), encoding="utf-8")
    except PermissionError:
        # File is locked by another process (e.g. editor has it open).
        # Log and continue — state.json is a convenience snapshot, not the source of truth.
        _log(session, f"\n> *[WARN: could not write state.json — file locked ({path})]*\n")


def advance_combat_turn(session: "GameSession") -> dict:
    """Advance current_actor to the next active combatant in initiative order.

    Wraps around at the end of the list.  Skips combatants whose status is not
    "active".  Writes the updated state to state.json and returns:
        { "current_actor": str | None, "is_pc": bool }

    Raises ValueError when session.combat_state is None (caller should 409).
    """
    if session.combat_state is None:
        raise ValueError("No active combat")

    combat = session.combat_state
    # Active combatants only, sorted highest-initiative first (the canonical order).
    active = [c for c in sorted(combat.combatants, key=lambda c: c.initiative, reverse=True)
              if c.status == "active"]

    if not active:
        # No one left to act — leave current_actor as-is.
        _write_session_state(session)
        is_pc = _is_pc_attacker(combat.current_actor or "", session)
        return {"current_actor": combat.current_actor, "is_pc": is_pc}

    # Find the current actor's position; advance to the next (with wrap-around).
    names = [c.name for c in active]
    round_incremented = False
    try:
        idx = names.index(combat.current_actor)
        next_idx = (idx + 1) % len(names)
        # Wrapped past the last combatant → new round.
        if next_idx == 0 and idx == len(names) - 1:
            combat.round += 1
            round_incremented = True
    except ValueError:
        # current_actor not found in active list (None, dead, etc.) → pick first.
        next_idx = 0

    session.last_actor = combat.current_actor or ""

    # Tick down active effects for the outgoing actor (end-of-turn expiry).
    outgoing_name = combat.current_actor or ""
    outgoing = next((c for c in combat.combatants if c.name == outgoing_name), None)
    if outgoing is not None:
        _tick_effects(outgoing)

    combat.current_actor = names[next_idx]
    _write_session_state(session)
    is_pc = _is_pc_attacker(combat.current_actor, session)
    return {
        "current_actor": combat.current_actor,
        "is_pc": is_pc,
        "position": next_idx + 1,          # 1-based position in initiative order
        "combatant_count": len(names),
        "round": combat.round,
        "round_incremented": round_incremented,
    }


def _extract_attack_names(raw: str) -> list:
    """Strip bonuses and damage dice from a weapon string; return name-only list.

    Each item in the raw string is a comma-separated weapon entry:
        "shortbow +5 (1d4+1), bite +1 (1d4)"  →  ["shortbow", "bite"]
        "dogslicer +2 (1d4)"                   →  ["dogslicer"]
        "bite"                                 →  ["bite"]
        ""                                     →  []

    Everything from the first '+' or '(' onward is stripped so the LLM
    sees weapon names only — the backend owns the mechanics.
    """
    if not raw or not raw.strip():
        return []
    names = []
    for item in raw.split(','):
        item = item.strip()
        if not item:
            continue
        # Cut at first '+' or '('
        for cutoff in ('+', '('):
            idx = item.find(cutoff)
            if idx != -1:
                item = item[:idx]
        name = item.strip()
        if name:
            names.append(name)
    return names


def _parse_event_combatants(content: str) -> dict:
    """Parse the ## Combatants markdown table from event file content.

    Returns a dict keyed by lowercase name with at minimum {"init_mod": int}.
    Returns {} if the section is absent or malformed — never raises.

    Preferred table format (melee/ranged columns):
        ## Combatants
        | name | hp | ac | init_mod | melee | ranged |
        |------|----|----|----------|-------|--------|
        | Goblin Warchanter | 8 | 14 | +3 | bite +1 (1d4) | shortbow +5 (1d4+1) |

    The attacks entry in the result dict is a nested dict:
        {"melee": ["bite"], "ranged": ["shortbow"]}

    Old single 'attacks' column is still accepted for backward compat; the
    attacks dict will be empty (omitted) in that case.
    """
    import re as _re
    result: dict = {}
    try:
        # Find the ## Combatants section
        section_m = _re.search(r'^##\s+Combatants\s*$', content, _re.MULTILINE | _re.IGNORECASE)
        if not section_m:
            return {}
        # Collect table lines after the header
        lines = content[section_m.end():].splitlines()
        header_idx = None
        col_names: list = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('|') and header_idx is None:
                # First pipe-delimited line = column headers
                col_names = [c.strip().lower() for c in stripped.strip('|').split('|')]
                header_idx = i
                continue
            if header_idx is not None and stripped.startswith('|---'):
                continue  # separator row
            if header_idx is not None and stripped.startswith('|'):
                values = [v.strip() for v in stripped.strip('|').split('|')]
                if len(values) < len(col_names):
                    continue
                row = dict(zip(col_names, values))
                name = row.get('name', '').strip()
                if not name:
                    continue
                raw_mod = row.get('init_mod', '0').strip()
                try:
                    mod = int(raw_mod.replace('+', '').strip())
                except ValueError:
                    mod = 0
                entry: dict = {'init_mod': mod}
                # Preserve hp and ac for SA-2 consumption if present
                for key in ('hp', 'ac'):
                    if key in row:
                        try:
                            entry[key] = int(row[key])
                        except ValueError:
                            pass
                # Parse typed attack columns (preferred: melee + ranged)
                melee_raw  = row.get('melee', '').strip()
                ranged_raw = row.get('ranged', '').strip()
                if melee_raw or ranged_raw:
                    entry['attacks'] = {
                        'melee':  _extract_attack_names(melee_raw),
                        'ranged': _extract_attack_names(ranged_raw),
                    }
                # Old single 'attacks' column — ignored for names (kept for compat)
                # Zone column — strip parentheticals like "(random)"; fall back to "default"
                raw_zone = row.get('zone', '').strip()
                if raw_zone and not raw_zone.startswith('('):
                    entry['zone'] = raw_zone
                else:
                    entry['zone'] = 'default'
                entry['name'] = name  # preserve original capitalisation
                result[name.lower()] = entry
            elif header_idx is not None:
                break  # end of table
    except Exception:
        return {}
    return result


def _load_event_zone_data(session: "GameSession", event_entry) -> None:
    """Load zone adjacency/properties for a combat event into session state.

    Inline event ## Zones tables are treated as an encounter override. If an
    event has no inline zone table, its **Location:** metadata can point at a
    canonical location file that owns the zone graph.
    """
    zone_map, zone_properties = parse_zone_adjacency_table(event_entry.content)

    if not zone_map and getattr(event_entry, "location_id", ""):
        loc_idx = _get_location_index()
        zone_map = loc_idx.get_zones(event_entry.location_id)
        zone_properties = loc_idx.get_zone_properties(event_entry.location_id)

    if zone_map:
        session.zone_map = {name: set(adjacent) for name, adjacent in zone_map.items()}
        session.zone_properties = {name: list(props) for name, props in zone_properties.items()}
        if getattr(event_entry, "location_id", ""):
            session.current_location_id = event_entry.location_id
        if session.combat_state is not None:
            session.combat_state.known_zones = sorted(session.zone_map.keys())
        _log(session, f"\n> *[Zone map loaded: {len(session.zone_map)} zone(s)]*\n")


def _refresh_combat_known_zones(session: "GameSession") -> None:
    if session.combat_state is None:
        return
    zone_names = set(session.zone_map.keys())
    zone_names.update(
        c.zone for c in session.combat_state.combatants
        if c.zone and c.zone != "default"
    )
    session.combat_state.known_zones = sorted(zone_names)


def _seed_round1_combatants(session: "GameSession", combat_state: "CombatState") -> None:
    """Override LLM-written round-1 combatant data with authoritative backend values.

    - PCs: replace hp/ac with pc_profiles values (LLM often writes — when roster not
      injected on the turn the event fires).
    - Enemies: if pending_combatants is non-empty, REPLACE all non-PC combatants with
      individual entries from the event file table (fixes grouped notation like
      "Goblin Mob (Wave 1)").

    Mutates combat_state.combatants in-place.
    """
    pc_keys = set(session.pc_profiles.keys())  # already lowercase

    seeded: list = []
    seen_pc_keys: set = set()

    # First pass: PCs from the LLM's list — override with real HP/AC
    for c in combat_state.combatants:
        key = c.name.lower()
        if key in pc_keys:
            profile = session.pc_profiles[key]
            cs_data = profile.get("combat_stats", {})
            hp_max = cs_data.get("hp_max", 0) or 10
            ac     = cs_data.get("ac",     10) or 10
            c.hp_max     = hp_max
            c.hp_current = hp_max  # PCs start at full HP
            c.ac         = ac
            seeded.append(c)
            seen_pc_keys.add(key)

    # Add any PCs the LLM omitted entirely
    for key, profile in session.pc_profiles.items():
        if key not in seen_pc_keys:
            cs_data = profile.get("combat_stats", {})
            name   = cs_data.get("name", "")
            hp_max = cs_data.get("hp_max", 10)
            ac     = cs_data.get("ac",     10)
            if name:
                seeded.append(Combatant(
                    name=name, hp_current=hp_max, hp_max=hp_max, ac=ac, initiative=0,
                ))

    # Enemy combatants
    if session.pending_combatants:
        # Replace ALL non-PC combatants with authoritative entries from the event file
        for _key, data in session.pending_combatants.items():
            name = data.get("name", _key.title())
            hp      = data.get("hp", 5)
            ac      = data.get("ac", 13)
            attacks = data.get("attacks", {})
            seeded.append(Combatant(
                name=name, hp_current=hp, hp_max=hp, ac=ac, initiative=0,
                attacks=attacks,
                zone=data.get("zone", "default"),
            ))
        _log(session,
             f"\n> *[Round-1 seed: replaced enemy list with {len(session.pending_combatants)} "
             f"event-file combatants; {len(seen_pc_keys)} PC(s) seeded from profiles]*\n")
    else:
        # No event seeding — keep LLM-written enemies (may have 0 stats from —)
        for c in combat_state.combatants:
            if c.name.lower() not in pc_keys:
                seeded.append(c)

    combat_state.combatants = seeded


def _seed_pc_stats(session: "GameSession", combat_state: "CombatState") -> None:
    """Seed HP/AC for PCs already in the combat list from pc_profiles (B-C03b fix).

    Called unconditionally on round-1 %%COMBAT%% parse.  Only fixes existing PC
    rows — does NOT add PCs the LLM omitted (that is handled by _seed_round1_combatants
    when a full combat event fires).
    """
    pc_keys = set(session.pc_profiles.keys())
    fixed: list = []

    for c in combat_state.combatants:
        key = c.name.lower()
        if key in pc_keys:
            profile = session.pc_profiles[key]
            cs_data = profile.get("combat_stats", {})
            hp_max = cs_data.get("hp_max", 0) or 10
            ac     = cs_data.get("ac",     10) or 10
            c.hp_max     = hp_max
            c.hp_current = hp_max
            c.ac         = ac
            fixed.append(c.name)

    if fixed:
        _log(session, f"\n> *[PC HP/AC seeded from profiles: {fixed}]*\n")


def _seed_enemy_stats(session: "GameSession", combat_state: "CombatState") -> None:
    """Seed enemy combatants from event file pending_combatants on round 1.

    Only called when a combat event is active.  Replaces LLM-written enemy list
    with individual named entries from the ## Combatants table (fixes grouped notation).
    Also ensures all PCs from pc_profiles are present (LLM often omits them).
    """
    if not session.pending_combatants:
        return
    pc_keys = set(session.pc_profiles.keys())

    # Keep PCs already in the LLM list; seed HP/AC from profiles
    seeded = []
    seen_pc_keys: set = set()
    for c in combat_state.combatants:
        key = c.name.lower()
        if key in pc_keys:
            profile = session.pc_profiles[key]
            cs_data = profile.get("combat_stats", {})
            c.hp_max = cs_data.get("hp_max", 0) or 10
            c.ac     = cs_data.get("ac", 10) or 10
            # Preserve tracked HP between combats; fall back to max for first combat
            c.hp_current = session.pc_current_hp.get(key, c.hp_max)
            seeded.append(c)
            seen_pc_keys.add(key)

    # Add any PCs the LLM omitted entirely
    for key, profile in session.pc_profiles.items():
        if key not in seen_pc_keys:
            cs_data = profile.get("combat_stats", {})
            name   = cs_data.get("name", "")
            hp_max = cs_data.get("hp_max", 10)
            ac     = cs_data.get("ac", 10)
            hp_cur = session.pc_current_hp.get(key, hp_max)
            if name:
                seeded.append(Combatant(name=name, hp_current=hp_cur, hp_max=hp_max, ac=ac, initiative=0))

    # Replace all non-PC combatants with authoritative event-file entries
    for _key, data in session.pending_combatants.items():
        name    = data.get("name", _key.title())
        hp      = data.get("hp", 5)
        ac      = data.get("ac", 13)
        attacks = data.get("attacks", {})
        zone    = data.get("zone", "default")
        seeded.append(Combatant(name=name, hp_current=hp, hp_max=hp, ac=ac, initiative=0,
                                attacks=attacks, zone=zone))

    combat_state.combatants = seeded
    _log(session, f"\n> *[Enemy stats seeded: {len(session.pending_combatants)} enemies + "
                  f"{len(seen_pc_keys)} existing PCs + "
                  f"{len(seeded) - len(seen_pc_keys) - len(session.pending_combatants)} added PCs]*\n")


def roll_combat_initiatives(session: "GameSession") -> Optional[dict]:
    """Roll d20 + modifier for every combatant and update initiative order.

    PC modifiers are read from pc_profiles[name]["combat_stats"]["initiative"]
    (e.g. "+2", "-1").  Enemy modifiers default to +0 until SA-2 event-file
    seeding supplies them.  Returns the serialised CombatState, or None when
    no combat is active.
    """
    if session.combat_state is None:
        return None

    for c in session.combat_state.combatants:
        # _is_pc_attacker checks pc_profiles membership — correct for initiative context too
        if _is_pc_attacker(c.name, session):
            raw_mod = (
                session.pc_profiles
                .get(c.name.lower(), {})
                .get("combat_stats", {})
                .get("initiative", "+0")
            )
            try:
                modifier = int(str(raw_mod).replace("+", "").strip())
            except (ValueError, AttributeError):
                modifier = 0
        else:
            # Check pending_combatants for event-seeded modifier; default to flat d20
            seeded = session.pending_combatants.get(c.name.lower(), {})
            modifier = seeded.get("init_mod", 0)

        c.initiative = random.randint(1, 20) + modifier

    # Consume pending_combatants entries and clear initiative-pending flag
    session.pending_combatants.clear()
    session._await_initiative_roll = False

    # Update current_actor to the new highest-initiative active combatant
    active_sorted = sorted(
        (c for c in session.combat_state.combatants if c.status == "active"),
        key=lambda c: c.initiative,
        reverse=True,
    )
    session.combat_state.current_actor = active_sorted[0].name if active_sorted else None
    # Ties broken by original insertion order (modifier-based tie rules deferred to SA-2)
    session.combat_state.combatants.sort(key=lambda c: c.initiative, reverse=True)
    _write_session_state(session)
    _log(session, f"\n> *[Roll initiatives: new order {', '.join(f'{c.name} {c.initiative}' for c in active_sorted)}]*\n")
    return _serialize_combat_state(session.combat_state)


def _ts(moment: Optional[datetime] = None) -> str:
    return (moment or datetime.now()).strftime("%H:%M:%S")


def _ts_file(moment: Optional[datetime] = None) -> str:
    return (moment or datetime.now()).strftime("%Y%m%d_%H%M%S")


def _ts_human(moment: Optional[datetime] = None) -> str:
    return (moment or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def _log(session: GameSession, text: str) -> None:
    if session.log_path is None:
        return
    with session.log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


# ── Dynamic-injection prompt fragments ───────────────────────────────────────
# These constants are NOT part of the static system prompt; _inject_context
# appends them conditionally to the per-turn copy only when needed.

# Injected once on the first player turn so the model sees the full format,
# then dropped — the compact section headers in the base prompt are sufficient.
_FORMAT_EXAMPLE = """\
EXAMPLE OF A CORRECT FULL RESPONSE (follow this format exactly):

%%NARRATIVE%%
The crowd parts as you approach Mayor Deverin and Father Zantus near the cathedral steps. \
She turns with a warm smile, extending her hand in greeting. "Welcome to Sandpoint — I hope \
you're enjoying the festival. The apothecary's got some interesting remedies, if you're into \
that sort of thing," she says with a wink. "Just visit Gerhard Pickle down by the docks.

%%GENERATE%%
[
type: npc
name: Gerhard Pickle
role: apothecary
appearance: gloomy, hair hidden beneath a scarf
location: Bottled Solutions
summary: knows the comings and goings of ships and sailors
],
[
type: location
name: Bottled Solutions
role: apothecary shop
appearance: a cluttered storefront filled with shelves of strange ingredients and remedies
location: main street
summary: run by Gerhard Pickle, who is a font of gossip and local news
]

%%DELTAS%%
[
npc: Kendra Deverin
disposition: neutral → friendly
location: cathedral steps
knowledge: [pcs] Yanyeeku introduced himself to the mayor
summary: Kendra greeted Yanyeeku warmly and answered his opening question.
],
[
npc: Abstalar Zantus
disposition: friendly → neutral
location: cathedral steps
knowledge: [quest] Asks Yanyeeku to fetch him a drink from the tavern
summary: Abstalar Zantus asked Yanyeeku to fetch him a drink from the tavern.
]"""

# Injected on the turn combat STARTS (session.combat_state is None when _inject_context runs).
# LLM must supply hp: cur/max for every combatant so the backend can initialise HP values.
_COMBAT_SPEC_ROUND1 = """\
COMBAT CONDUCT (binding for every combat turn):
- Always write %%NARRATIVE%% first — narrate the action and its immediate result.
- Never ask the player for initiative. Never question or comment on the player's declared action.

Format (round 1):
%%COMBAT%%
round: 1
combatants:
  - name: <Name> · hp: <cur>/<max> · ac: <AC> · init: <modifier> · status: active|unconscious|fled|dead

PC rules: copy stats EXACTLY from [PARTY ROSTER] — never write — for any field.
Enemy rules: list EVERY enemy as an INDIVIDUAL line — never group (write "Goblin Warrior 1", NOT "Goblins (4)"). Copy hp/ac from [Active Event] stats; write init modifier (e.g. +3, -1), NOT a total.
NEVER write — or unknown for any field. If you do not know a value, use 0.
Sort descending by initiative modifier; round: 0 ends combat and clears the tracker."""

# Injected on round 2+. The backend owns HP values; the LLM must NOT write hp: fields for
# existing combatants (they are ignored). New combatants entering after round 1 still need hp:.
_COMBAT_SPEC_ONGOING = """\
COMBAT CONDUCT (binding):
- Always write %%NARRATIVE%% first. Never ask the player for information. Never question their declared action. Resolve it.

Format (ongoing — backend manages HP; omit hp field for existing combatants):
%%COMBAT%%
round: N
combatants:
  - name: <Name> · ac: <AC> · init: <init> · status: active|unconscious|fled|dead [· conditions: [prone,shaken]]
  [NEW combatants only: add hp: <cur>/<max>]

Attacks (write alongside %%COMBAT%% when attacks happen this round):
%%ATTACK%%
- attacker: <Name> · target: <Name> · bonus: +N · damage: NdN+N · type: melee|ranged|spell
[one line per attack; omit %%ATTACK%% on rounds with no attacks]

Rules: sort descending by initiative; increment round when all combatants have acted; \
round: 0 ends combat and clears the tracker; list ALL combatants every turn."""

# Per-turn section specs — injected conditionally by _inject_context based on what
# the turn context signals.  Only pay for specs that are actually relevant this turn.
_NARRATIVE_SPEC = (
    "%%NARRATIVE%%  — 2–4 paragraphs of prose; no markdown, no bullet points."
)

_ROLL_SPEC = (
    "%%ROLL%%  — at most ONE block per response, when a skill check is needed:\n"
    "[ skill: <name>  dc: <N>  success: <2 paragraphs>  failure: <2 paragraphs> ]"
)

_GENERATE_SPEC = (
    "%%GENERATE%%  — REQUIRED for every NEW named character/location introduced this turn.\n"
    "Skip if the name already appears in [ACTIVE SCENE NPCS] — do not re-generate known characters.\n"
    "[ type: npc|location  name: <exact name>  role: <phrase>  appearance: <sentence>"
    "  personality: <sentence>  location: <place>  summary: <sentence> ]"
)

_DELTAS_SPEC = (
    "%%DELTAS%%  — one bracket block per named NPC active in the scene.\n"
    "RULES: named NPCs only — NEVER a PC, a group, a crowd, an object, or scene state.\n"
    "FORMAT: use this exact bracket notation only — never bullet points, never prose:\n"
    "[ npc: <name>  disposition: <old→new>  location: <place>"
    "  knowledge: [tag] <fact>  summary: <sentence> ]\n"
    "Tags (use exactly one): [persistent] [pcs] [quest] [world] [npcs] [trivia] [threat]"
)

# Combat-mode section spec — replaces the narrative section block when combat is active.
# Strips %%GENERATE%%, %%DELTAS%%, %%ROLL%%, %%EVENT%%; promotes tight %%NARRATIVE%% target.
_COMBAT_SECTION_SPECS = """\
[SECTIONS ACTIVE THIS TURN — COMBAT MODE]
%%NARRATIVE%%  — 1–2 paragraphs; physical action and immediate observable result only.
%%COMBAT%%     — always required this turn; full format spec below.
%%ATTACK%%     — one line per attack this round; omit when no attacks occur.
FORBIDDEN in combat: do NOT write GENERATE, DELTAS, ROLL, EVENT, or HP sections."""


def _build_combat_system_prompt(session: "GameSession") -> str:
    """Build the combat-mode base prompt used when session.combat_state is not None.

    Much shorter than _build_slim_system_prompt — strips narrative tone guidance,
    NPC knowledge prose, skill guidelines, GM STYLE, and unused section specs.
    Called fresh each combat turn by _inject_context; not stored on session.
    """
    party_lines = [
        f"  - {p['combat_stats']['name']}"
        for p in session.pc_profiles.values()
        if p.get("combat_stats", {}).get("name")
    ]
    party_block = "\n".join(party_lines) if party_lines else "  - (no character files found)"

    return f"""You are the GM for a Pathfinder 1E combat encounter. Session {session.session_number}.

PARTY (PCs — never roll dice for them; never narrate their decisions before the player declares)
{party_block}

COMBAT CONDUCT (binding every turn)
- Write %%NARRATIVE%% first: 1–2 paragraphs, physical action and immediate observable result only.
- Always write %%COMBAT%% with the updated initiative list and statuses.
- Never ask the player for information. Accept and resolve their declared action immediately.
- Never invent a d20 result, damage number, or HP total. Write %%ATTACK%% and let the backend roll.
- Round 1 ONLY: MUST include hp: cur/max for EVERY combatant — the backend seeds HP from these values.
- Round 2+: NEVER write hp: for existing combatants — backend owns HP from round 1.
- Never narrate what a PC does before the player declares it.

FORBIDDEN in combat — do NOT write GENERATE, DELTAS, ROLL, or EVENT sections.
Everything after %%NARRATIVE%% is stripped before the player sees the response."""


def _build_slim_system_prompt(
    session_number: int,
    pc_profiles: Optional[dict] = None,
) -> str:
    """Build the fixed base system prompt for this session.

    Loaded once at boot and never modified.  Per-turn context (NPC profiles,
    skill rules, location NPCs, format example on turn 1, combat spec when
    active) is injected dynamically by _inject_context.

    ``pc_profiles`` should be pre-built by ``_build_pc_profiles`` so that the
    system prompt and combat mechanics share the same single source of truth
    (ui/public/data/player_NN.json).  When omitted the function loads the
    profiles itself (used by tests and legacy callers).
    """
    repo_root = _REPO_ROOT

    if pc_profiles is None:
        pc_profiles = _build_pc_profiles(repo_root / "ui" / "public" / "data")

    # Party block from the JSON profiles — same source of truth as combat mechanics.
    party_lines: list[str] = []
    for _pkey, _prof in sorted(pc_profiles.items()):
        _cs = _prof.get("combat_stats", {})
        _name = _cs.get("name", "")
        _cls = _cs.get("cls_full", "")
        if _name and _cls:
            party_lines.append(f"  - {_name} ({_cls})")

    party_block = "\n".join(party_lines) if party_lines else "  - (no character files found)"

    # Session boot context: prefer sessions/session_NNN/boot.md (GM-facing),
    # fall back to recap from previous session, then bare notice.
    sessions_dir = repo_root / "sessions"
    boot_path = sessions_dir / f"session_{session_number:03d}" / "boot.md"
    if not boot_path.exists() and session_number > 1:
        boot_path = sessions_dir / f"session_{session_number - 1:03d}" / "recap.md"
    situation = boot_path.read_text(encoding="utf-8") if boot_path.exists() else "(No boot context found for this session.)"

    _base_prompt = f"""You are the GM for a Pathfinder 1E campaign: Rise of the Runelords.
Session number: {session_number}

CORE BEHAVIOR (always active)
- Describe only what the characters can directly perceive. No hinting, no foreshadowing.
- Never describe what a PC is doing or saying before the player declares it.
- Never suggest actions, hint at correct choices, or guide the players.
- Never invent lore, NPCs, or mechanics outside what you have been given. If unsure, say so.
- Resolve what the player declares before narrating its outcome.

GM STYLE
- NPCs: lead with demeanor and immediate goal; no biography unless asked.
- Locations: 3–6 sensory details, one social detail, one interactive element.
- Mechanics: state ruling, DC, and consequence in one sentence; no lengthy explanation.
- Pacing: fire triggers on the first turn the condition is met; do not telegraph upcoming ones.

PARTY
{party_block}

CURRENT SITUATION
{situation}

RESPONSE STRUCTURE — per-turn instructions list which sections are active this turn.
Only write sections listed in [SECTIONS ACTIVE THIS TURN]. Exception: %%EVENT%% and %%GENERATE%% may always be added when triggered. %%DELTAS%% MUST NOT be written unless it appears in [SECTIONS ACTIVE THIS TURN].
Markers in order: %%NARRATIVE%%  %%ROLL%%  %%GENERATE%%  %%DELTAS%%  %%EVENT%%  %%COMBAT%%

SCENE EVENT — append after %%DELTAS%% (or %%GENERATE%% if %%DELTAS%% is not active) on the first turn a trigger is met:
%%EVENT%% <event_id>   ← ID on the SAME LINE; nothing else on this line
CORRECT: %%EVENT%% goblin_attack_begins
WRONG:   %%EVENT%%  |  %%EVENT%%\\n%%EVENT%% id  |  %%EVENT%% id (Note: …)

%%COMBAT%% — write when starting or continuing combat; omit when no combat.
round: 0 ends and clears combat. Compact round-1 format (use when starting combat):
%%COMBAT%%
round: 1
combatants:
  - name: <Name> · hp: <cur>/<max> · ac: <AC> · init: <init> · status: active
Full spec re-injected per-turn when active events or combat is ongoing.

Everything after %%NARRATIVE%% is stripped before the player sees the response."""

    # Append event map if any events are defined for this adventure
    _event_map = _get_event_index().event_map_text()
    if _event_map:
        _base_prompt += f"\n\n---\nEVENT MAP\n{_event_map}"

    return _base_prompt


def _build_pc_profiles(data_dir: Path) -> dict:
    """Build slim narrative and mechanical profiles for each PC at session boot.

    Reads from ui/public/data/player_XX.json — structured and pre-validated,
    avoids fragile markdown parsing.  Returns a dict keyed by lowercase
    canonical name; each value has "narrative" and "mechanical" string tiers.
    Missing fields are skipped gracefully.
    """
    profiles: dict = {}
    if not data_dir.exists():
        return profiles

    _save_short = {"Fortitude": "Fort", "Reflex": "Ref", "Will": "Will"}

    for json_path in sorted(data_dir.glob("player_*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        name = data.get("name", "")
        if not name:
            continue

        race = data.get("race", "")
        cls = data.get("class", "")
        archetype = data.get("archetype", "")
        cls_full = f"{cls} / {archetype}" if archetype else cls
        appearance = data.get("appearance", "")

        hdr = f"## PC — {name} ({race} {cls_full})" if race else f"## PC — {name} ({cls_full})"
        narr_lines = [hdr]
        if appearance:
            narr_lines.append(f"Appearance: {appearance}")

        # Mechanical profile
        hp_max = data.get("hp", {}).get("max", "")
        ac_total = data.get("ac", {}).get("total", "")
        initiative = data.get("initiative", "")
        speed = data.get("speed", "")

        ab_mods = [
            f"{ab['name']} {ab['mod']}"
            for ab in data.get("abilities", [])
        ]
        saves = [
            f"{_save_short.get(sv['name'], sv['name'])} {sv['total']}"
            for sv in data.get("saves", [])
        ]
        spell_names = [sp["name"] for sp in data.get("spells", {}).get("list", [])]

        mech_lines = [f"## PC Stats — {name}"]
        stats = []
        if hp_max:
            stats.append(f"HP: {hp_max}")
        if ac_total:
            stats.append(f"AC: {ac_total}")
        if initiative:
            stats.append(f"Init: {initiative}")
        if speed:
            stats.append(f"Speed: {speed}")
        if stats:
            mech_lines.append("  ".join(stats))
        if ab_mods:
            mech_lines.append("  ".join(ab_mods))
        if saves:
            mech_lines.append("Saves: " + " / ".join(saves))
        if spell_names:
            mech_lines.append("Spells: " + ", ".join(spell_names[:6]))

        # Weapon list — used by PC combat action system to queue attacks from real stats
        weapons = []
        for w in data.get("weapons", []):
            w_name = w.get("name", "").strip()
            w_atk  = w.get("atk",  "").strip()
            w_dmg  = w.get("dmg",  "").strip()
            w_type = w.get("type", "Melee").strip().lower()
            if w_name:
                weapons.append({
                    "name":  w_name,
                    "atk":   w_atk  or "+0",
                    "dmg":   w_dmg  or "1d4",
                    "type":  "ranged" if "ranged" in w_type else "melee",
                })

        # Spell list — used by PC combat action system to resolve spells from profile data.
        # Rules-agnostic: any caster with a "spells" list in their JSON gets this automatically.
        # Example: Bonnie the Sorcerer with Magic Missile → auto_hit=True, damage_expr="1d4+1".
        _DICE_EXPR_RE   = re.compile(r'\b(\d+d\d+(?:[+-]\d+)?)\b')
        _AC_BONUS_RE    = re.compile(r'\+(\d+)\s+(\w+)\s+bonus\s+to\s+AC', re.IGNORECASE)
        # "Heals Xd8+Y" or "heals Xd8" — positive-energy healing spells.
        _HEALING_RE     = re.compile(r'[Hh]eals?\s+(\d+d\d+(?:[+-]\d+)?)', re.IGNORECASE)
        spells = []
        for sp in data.get("spells", {}).get("list", []):
            effect       = sp.get("effect", "") or ""
            dmg_match    = _DICE_EXPR_RE.search(effect)
            ac_match     = _AC_BONUS_RE.search(effect)
            heal_match   = _HEALING_RE.search(effect)
            healing_expr = heal_match.group(1) if heal_match else ""
            spells.append({
                "name":         sp.get("name", "").strip(),
                "school":       sp.get("school", "").strip(),
                "sr":           sp.get("sr", "") == "Yes",
                "save":         (sp.get("save", "") or "").strip(),
                "auto_hit":     "never misses" in effect.lower(),
                "damage_expr":  dmg_match.group(1) if (dmg_match and not healing_expr) else "",
                "buff_ac":      int(ac_match.group(1)) if ac_match else 0,
                "buff_type":    ac_match.group(2).lower() if ac_match else "",
                "healing_expr": healing_expr,
                "is_heal":      bool(healing_expr),
                "per_day":      (sp.get("perDay", "") or "").strip(),
                "cast_time":    (sp.get("castTime", "") or "1 standard action").strip(),
                "range_raw":    (sp.get("range", "") or "").strip(),
            })

        profiles[name.lower()] = {
            "narrative": "\n".join(narr_lines),
            "mechanical": "\n".join(mech_lines),
            # Raw values used by _build_pc_combat_roster to format %%COMBAT%% lines.
            # hp_max is used as hp_current on round 1 (PCs start at full HP).
            "combat_stats": {
                "name": name,
                "race": race,
                "cls_full": cls_full,
                "hp_max": int(hp_max) if str(hp_max).isdigit() else 0,
                "ac": int(ac_total) if str(ac_total).isdigit() else 10,
                "initiative": initiative or "+0",
            },
            # Weapon list: first entry = equipped (primary).
            "weapons": weapons,
            # Spell list: all known spells with mechanical fields extracted from JSON.
            "spells": spells,
        }

    return profiles


def create_session(
    session_number: int,
    model: str,
    host: str = "http://localhost:11434",
    temperature: float = 0.3,
    dev_mode: bool = False,
    num_ctx: int = 2048,
    num_gpu: int = 999,
    provider: str = "ollama",
    event_scheduler: bool = False,
) -> GameSession:
    _pc_profiles = _build_pc_profiles(_REPO_ROOT / "ui" / "public" / "data")
    system_prompt = _build_slim_system_prompt(session_number, _pc_profiles)

    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    log_name = f"session_{session_number:03d}_{_ts_file(started)}.log.md"

    session = GameSession(
        id=str(uuid.uuid4()),
        session_number=session_number,
        model=model,
        host=host,
        temperature=temperature,
        dev_mode=dev_mode,
        event_scheduler=event_scheduler,
        provider=provider,
        num_ctx=num_ctx,
        num_gpu=num_gpu,
        system_prompt=system_prompt,
        log_path=_OUTPUTS_DIR / log_name,
        pc_profiles=_pc_profiles,
    )

    # Populate warm events from schedulable event definitions (when scheduler enabled).
    # NOTE: readiness/failed_rolls/completed_events start at zero every boot — runtime
    # state is not restored from state.json (BUG-003). See EVENT-TODO E1-9 for tracking.
    if event_scheduler:
        for _entry in _get_event_index().schedulable_entries():
            session.event_runtime.warm_events[_entry.event_id] = WarmEvent(
                threshold=_entry.threshold,
                base_gain=_entry.base_gain,
                zones=list(_entry.zones),
                action_gain_map=dict(_entry.action_gain_map),
            )

    # Seed scene_locations from the session boot file so the scheduler has a zone
    # from turn 1 even if the player never explicitly names the location.
    _boot_path = _REPO_ROOT / "sessions" / f"session_{session_number:03d}" / "boot.md"
    if _boot_path.exists():
        import re as _re
        for _line in _boot_path.read_text(encoding="utf-8").splitlines():
            _loc_m = _re.match(r"^-?\s*Location:\s*(.+)", _line)
            if _loc_m:
                _boot_loc_match = _get_location_index().detect(_loc_m.group(1))
                if _boot_loc_match and _boot_loc_match.canonical_name not in session.scene_locations:
                    session.scene_locations.append(_boot_loc_match.canonical_name)
                break

    # Initialise session state file from template (resets mode to 'social' each boot).
    _template = _REPO_ROOT / "sessions" / "state.template.json"
    _state_path = _session_state_path(session)
    _state_path.parent.mkdir(parents=True, exist_ok=True)
    if _template.exists():
        import shutil as _shutil
        _shutil.copy2(_template, _state_path)

    # Boot cleanup — runs against adventure_path/01_npcs/ on every session start.
    #
    # 1. SESSION NPC folders: auto-created stubs are deleted unless the GM has
    #    promoted the NPC by removing the "SESSION NPC" flag from base.md.
    #    This keeps the index clean between sessions.
    #
    # 2. Session delta files (session_NNN.md): deleted for the current session
    #    number so each re-run of a session starts from a clean state.
    #
    # 3. knowledge.md: reset only when booting session 1. For all other
    #    session numbers, keep existing knowledge and continue append-only
    #    writes during play.
    _npcs_root = _REPO_ROOT / "adventure_path" / "01_npcs"
    if _npcs_root.exists():
        _delta_filename = f"session_{session_number:03d}.md"
        for _npc_dir in list(_npcs_root.iterdir()):
            if not _npc_dir.is_dir() or _npc_dir.name.startswith("_"):
                continue
            # Session NPC? Delete the whole folder.
            _base_path = _npc_dir / "base.md"
            if _base_path.exists():
                try:
                    if "SESSION NPC" in _base_path.read_text(encoding="utf-8"):
                        shutil.rmtree(_npc_dir, ignore_errors=True)
                        continue  # folder gone — skip delta cleanup
                except OSError:
                    pass
            # Not a session NPC — just delete this session's delta file.
            _old_delta = _npc_dir / _delta_filename
            if _old_delta.exists():
                _old_delta.unlink()

            # Session 1 boot defines a fresh campaign-memory baseline.
            if session_number == 1:
                _knowledge_path = _npc_dir / "knowledge.md"
                if _knowledge_path.exists():
                    _knowledge_path.write_text("", encoding="utf-8")

    # Directories were deleted above — clear the in-memory index so the next
    # turn builds it fresh from disk.  Without this, a deleted session NPC
    # remains in the stale index and _process_generate_block() silently skips
    # recreating its directory on the very next turn.
    _invalidate_npc_index()

    # Restore scene_npcs from the previous session's boot.md if present.
    _boot_path = _REPO_ROOT / "sessions" / f"session_{session_number:03d}" / "boot.md"
    _restored_npcs = _parse_scene_npcs_from_boot(_boot_path)
    if _restored_npcs:
        session.scene_npcs = _restored_npcs

    _sessions[session.id] = session

    mode_label = "dev" if dev_mode else "full"
    _log(session, f"# Session {session_number:03d} — {_ts_human(started)}")
    _log(session, f"Model: `{model}` | Mode: {mode_label} | Temp: {temperature}\n")
    if _restored_npcs:
        _log(session, f"> *[Scene NPCs restored from boot.md: {', '.join(_restored_npcs)}]*\n")
    _log(session, "## System Prompt\n")
    _log(session, f"```\n{system_prompt}\n```\n")
    _log(session, "---\n")

    return session


def get_session(session_id: str) -> Optional[GameSession]:
    return _sessions.get(session_id)


def stream_boot(session: GameSession) -> Generator[str, None, None]:
    # Context is primed in the system prompt — no LLM call at boot.
    # The static intro card handles the visual. The GM responds on the
    # player's first message.
    _log(session, f"\n## Boot complete — waiting for first player input\n")
    yield f"data: {json.dumps({'type': 'done', 'session_id': session.id})}\n\n"


def validate_turn_input(text: str) -> Optional[str]:
    """Return an error string if the input is invalid, else None."""
    if not text or not text.strip():
        return "Player input must not be empty."
    if len(text) > 4000:
        return f"Player input is too long ({len(text)} chars; max 4000)."
    return None


def validate_generated_text(text: str, label: str, min_length: int = 80) -> Optional[str]:
    """Return an error string if generated output looks malformed, else None."""
    if not text or not text.strip():
        return f"{label}: LLM returned an empty response."
    if len(text.strip()) < min_length:
        return f"{label}: response is suspiciously short ({len(text.strip())} chars)."
    return None


def stream_turn(session: GameSession, user_input: str) -> Generator[str, None, None]:
    err = validate_turn_input(user_input)
    if err:
        yield f"data: {json.dumps({'type': 'error', 'message': err})}\n\n"
        return
    session.messages.append({"role": "user", "content": user_input})
    try:
        yield from _stream_chat(session)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def log_roll(session: GameSession, expr: str, rolls: list[int], total: int) -> None:
    breakdown = " + ".join(str(r) for r in rolls) if len(rolls) > 1 else str(rolls[0])
    _log(session, f"\n### [{_ts()}] DICE — {expr}")
    _log(session, f"{breakdown} = **{total}**\n")
    _log(session, "---\n")


def _speaker_from_user_input(text: str) -> Optional[str]:
    """Extract an active-speaker prefix from UI payloads like @Vanx: "..."."""
    m = re.match(r'^\s*@([^:\n]+):\s*"', text)
    if not m:
        return None
    speaker = m.group(1).strip()
    return speaker or None


def resolve_roll(session: GameSession, rolled: int) -> dict:
    """Compare *rolled* against the pending roll DC and record the outcome.

    Returns {passed, skill, dc, rolled, outcome} or raises if no roll is pending.
    Adds the result to session.messages so the LLM stays in context.
    """
    if not session.pending_roll:
        raise ValueError("No pending roll for this session.")

    pr = session.pending_roll
    passed = rolled >= pr["dc"]
    outcome = pr["success"] if passed else pr["failure"]
    label = "SUCCESS" if passed else "FAILURE"
    speaker = pr.get("speaker")

    # Inform the LLM of the result so it has full context on the next turn
    session.messages.append({
        "role": "assistant",
        "content": (
            f"[{pr['skill']} check — rolled {rolled} vs DC {pr['dc']}: {label}]\n\n"
            f"{outcome}"
        ),
    })

    _log(session, f"\n### [{_ts()}] ROLL RESULT — {pr['skill']} DC {pr['dc']}")
    if speaker:
        session.messages[-1]["content"] = session.messages[-1]["content"].replace(
            f"[{pr['skill']} check",
            f"[{speaker}'s {pr['skill']} check",
            1,
        )

    _log(session, f"Rolled: {rolled}  |  {label}")
    _log(session, f"{outcome}\n")
    _log(session, "---\n")

    session.pending_roll = None
    return {"passed": passed, "skill": pr["skill"], "dc": pr["dc"], "rolled": rolled, "outcome": outcome, "speaker": speaker}


def write_session_state(session: GameSession) -> None:
    """Public alias for _write_session_state — callable from main.py."""
    _write_session_state(session)


def set_active_character(session: GameSession, name: str) -> None:
    """Set the active character and persist to state.json.

    Pass "party" to deselect all characters (default social state).
    Any non-empty string is accepted — validation is the caller's responsibility.
    """
    session.active_character = name.strip() or "party"
    _write_session_state(session)


def get_location_zone_state(session: GameSession) -> dict:
    """Return the active location/encounter zone snapshot for the GUI."""
    location_id = session.current_location_id
    loc_idx = _get_location_index()
    loc_match = loc_idx.lookup(location_id) if location_id else None
    graph = loc_idx.get_zone_graph(location_id) if location_id else None

    current_zone_name = session.party_zone_id
    if session.combat_state is not None and session.combat_state.current_actor:
        actor = next(
            (c for c in session.combat_state.combatants if c.name == session.combat_state.current_actor),
            None,
        )
        if actor and actor.zone and actor.zone != "default":
            current_zone_name = actor.zone
    if not current_zone_name and session.zone_map:
        current_zone_name = next(iter(session.zone_map.keys()))

    zones: list[dict] = []
    access_points: list[dict] = []
    zone_name_to_id: dict[str, str] = {}

    if graph and graph.zones:
        for zone in graph.zones.values():
            zones.append({
                "id": zone.id,
                "name": zone.name,
                "description": zone.description,
                "visible": zone.visible,
                "source": zone.source,
                "tags": list(zone.tags),
            })
            zone_name_to_id[zone.name.lower()] = zone.id
        for ap in graph.access_points:
            access_points.append({
                "id": ap.id,
                "from": ap.from_zone_id,
                "to": ap.to_zone_id,
                "label": ap.label,
                "state": ap.state,
                "bidirectional": ap.bidirectional,
                "requirements": ap.requirements,
                "description": ap.description,
                "source": ap.source,
            })
    else:
        for zone_name in sorted(session.zone_map.keys()):
            zone_id = _slugify(zone_name)
            zone_name_to_id[zone_name.lower()] = zone_id
            zones.append({
                "id": zone_id,
                "name": zone_name,
                "description": "",
                "visible": True,
                "source": "event",
                "tags": list(session.zone_properties.get(zone_name, [])),
            })
        seen: set[frozenset[str]] = set()
        for from_name, adjacent in session.zone_map.items():
            for to_name in adjacent:
                key = frozenset({from_name, to_name})
                if key in seen:
                    continue
                seen.add(key)
                from_id = zone_name_to_id.get(from_name.lower(), _slugify(from_name))
                to_id = zone_name_to_id.get(to_name.lower(), _slugify(to_name))
                access_points.append({
                    "id": _slugify(f"{from_name}_{to_name}"),
                    "from": from_id,
                    "to": to_id,
                    "label": f"{from_name} to {to_name}",
                    "state": "open",
                    "bidirectional": True,
                    "requirements": "",
                    "description": "",
                    "source": "event",
                })

    current_zone_id = zone_name_to_id.get(current_zone_name.lower(), _slugify(current_zone_name)) if current_zone_name else ""

    occupants: list[dict] = []
    if session.combat_state is not None:
        for c in session.combat_state.combatants:
            if c.zone and c.zone != "default":
                occupants.append({
                    "actor_id": _slugify(c.name),
                    "label": c.name,
                    "zone_id": zone_name_to_id.get(c.zone.lower(), _slugify(c.zone)),
                })
    elif current_zone_id:
        occupants.append({"actor_id": "party", "label": "Party", "zone_id": current_zone_id})

    available_moves: list[dict] = []
    for ap in access_points:
        if ap["state"] != "open":
            continue
        destination = ""
        if ap["from"] == current_zone_id:
            destination = ap["to"]
        elif ap["bidirectional"] and ap["to"] == current_zone_id:
            destination = ap["from"]
        if destination:
            available_moves.append({
                "access_point_id": ap["id"],
                "to_zone_id": destination,
                "label": ap["label"],
                "state": ap["state"],
            })

    return {
        "current_location": {
            "id": location_id,
            "name": loc_match.canonical_name if loc_match else location_id,
        },
        "current_zone_id": current_zone_id,
        "zones": zones,
        "access_points": access_points,
        "occupants": occupants,
        "available_moves": available_moves,
    }


def _apply_actor_zone_change(session: "GameSession", actor_id: str, destination_zone_name: str) -> None:
    """Update an actor's zone in session state and write to disk.

    actor_id == "party"  → updates session.party_zone_id
    anything else        → matches a combatant by slug or lowercase name
    """
    if actor_id == "party":
        old = session.party_zone_id
        session.party_zone_id = destination_zone_name
        _log(session, f"\n> *[Zone move: party {old} → {destination_zone_name}]*\n")
    else:
        combatants = session.combat_state.combatants if session.combat_state else []
        mover = next(
            (c for c in combatants
             if _slugify(c.name) == actor_id or c.name.lower() == actor_id.lower()),
            None,
        )
        if mover:
            old = mover.zone
            mover.zone = destination_zone_name
            _log(session, f"\n> *[Zone move: {mover.name} {old} → {destination_zone_name}]*\n")
    _write_session_state(session)


def apply_zone_move(session: "GameSession", actor_id: str, access_point_id: str) -> dict:
    """Validate and apply a zone move via an access point, returning refreshed zone state.

    Raises ValueError with a human-readable message on any validation failure.
    """
    state = get_location_zone_state(session)

    ap = next((a for a in state["access_points"] if a["id"] == access_point_id), None)
    if ap is None:
        raise ValueError(f"Access point '{access_point_id}' not found")
    if ap["state"] != "open":
        raise ValueError(f"Access point '{access_point_id}' is {ap['state']}")

    # Resolve actor's current zone id
    if actor_id == "party":
        current_zone_id = state["current_zone_id"]
    else:
        combatants = session.combat_state.combatants if session.combat_state else []
        mover = next(
            (c for c in combatants
             if _slugify(c.name) == actor_id or c.name.lower() == actor_id.lower()),
            None,
        )
        if mover is None:
            raise ValueError(f"Actor '{actor_id}' not found")
        current_zone_id = _slugify(mover.zone) if mover.zone else ""

    # Validate the actor is at one end of this access point
    if ap["from"] == current_zone_id:
        dest_zone_id = ap["to"]
    elif ap["bidirectional"] and ap["to"] == current_zone_id:
        dest_zone_id = ap["from"]
    else:
        raise ValueError(
            f"Actor is in zone '{current_zone_id}', not reachable via '{access_point_id}'"
        )

    # Resolve destination zone name from id
    dest_zone = next((z for z in state["zones"] if z["id"] == dest_zone_id), None)
    dest_zone_name = dest_zone["name"] if dest_zone else dest_zone_id

    _apply_actor_zone_change(session, actor_id, dest_zone_name)
    result = get_location_zone_state(session)
    result["combat_state"] = _serialize_combat_state(session.combat_state)
    return result


def save_session(session: GameSession) -> Path:
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    _log(session, f"\n## Session Ended — {_ts()}")
    _log(session, f"Total exchanges: {len([m for m in session.messages if m['role'] == 'user'])}\n")

    out = _OUTPUTS_DIR / f"session_{session.session_number:03d}_notes.json"
    out.write_text(
        json.dumps(
            {
                "session_id": session.id,
                "session_number": session.session_number,
                "model": session.model,
                "turns": [{"role": m["role"], "content": m["content"]} for m in session.messages],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    del _sessions[session.id]
    return out


def _build_turn_directive(npc_match, skill_match, location_matches=None, scene_npcs=None) -> str:
    """Return an explicit GM instruction for the current turn based on what was detected.

    This is injected as the last section of the system prompt so the model
    sees a clear, unambiguous action item rather than having to infer from
    the reference data above.
    """
    has_npc   = npc_match   is not None
    has_skill = skill_match is not None
    loc_npc_names = [m.canonical_name for m in (location_matches or [])]

    # NPCs detected this turn
    current_turn_npcs: list[str] = []
    if has_npc:
        current_turn_npcs.append(npc_match.canonical_name)
    for n in loc_npc_names:
        if n not in current_turn_npcs:
            current_turn_npcs.append(n)

    # For delta instructions use the full scene NPC list when available —
    # this ensures NPCs that were introduced on earlier turns are still tracked.
    active_npc_names = list(scene_npcs) if scene_npcs else current_turn_npcs

    # %%DELTAS%% instruction — just names the NPCs; format is in the system prompt.
    _delta_instruction = ""
    if active_npc_names:
        npc_list_str = ", ".join(active_npc_names)
        _delta_instruction = (
            f"\n\nWrite a %%DELTAS%% section covering: {npc_list_str}."
            "\nIf your narrative names any character NOT already in that list, "
            "you MUST write a %%GENERATE%% block for them — no exceptions."
        )

    if has_skill and has_npc:
        npc_name   = npc_match.canonical_name
        skill_name = skill_match.skill_name
        return (
            f"THIS TURN: the player is attempting a {skill_name} check against {npc_name}.\n\n"
            "STEP 1 — Write 1–2 sentences of scene setup in %%NARRATIVE%%. Do not reveal the outcome.\n\n"
            "STEP 2 — Decide: is the outcome genuinely uncertain?\n"
            f"  YES → Write a %%ROLL%% section with skill: {skill_name}\n"
            "  NO (auto-fail / impossible) → Narrate the failure in %%NARRATIVE%%. No %%ROLL%% section."
            + _delta_instruction
        )

    elif has_skill:
        skill_name = skill_match.skill_name
        return (
            f"THIS TURN: the player is attempting a {skill_name} check.\n\n"
            "STEP 1 — Write 1–2 sentences of scene setup in %%NARRATIVE%%.\n\n"
            "STEP 2 — Decide: is the outcome genuinely uncertain?\n"
            f"  YES → Write a %%ROLL%% section with skill: {skill_name}\n"
            "  NO → Narrate the result directly in %%NARRATIVE%%. No %%ROLL%% section."
            + _delta_instruction
        )

    elif has_npc:
        npc_name = npc_match.canonical_name
        return (
            f"THIS TURN: the player is interacting with {npc_name}.\n"
            f"Use the {npc_name} profile above.\n"
            "If a skill check is needed (Diplomacy, Bluff, Intimidate, Sense Motive): "
            "write scene setup in %%NARRATIVE%% then add a %%ROLL%% section.\n"
            "If no check is needed: narrate the NPC's reaction in %%NARRATIVE%%."
            + _delta_instruction
        )

    elif location_matches:
        loc_keyword = location_matches[0].matched_location
        npc_names = ", ".join(m.canonical_name for m in location_matches)
        return (
            f"THIS TURN: the player is at or heading to '{loc_keyword}'.\n"
            f"NPCs present: {npc_names}. Use the profiles above.\n"
            "If the player interacts with an NPC and a check is needed, write a %%ROLL%% section."
            + _delta_instruction
        )

    # Fallback — location-only context, or location re-injection with scene NPCs
    return "Respond to the player's action using the reference context above." + _delta_instruction


def _process_generate_block(body: str, session: GameSession) -> None:
    """Create a new NPC or location stub from a %%GENERATE%% block body.

    For type: location — creates a stub in adventure_path/03_locations/ and
    invalidates the location index so the new entry is detectable immediately.
    For NPC entries — creates a dot-prefixed stub in adventure_path/01_npcs/.
    Silently skipped if the entry already exists or the name field is missing.
    """
    fields = _parse_delta_fields(body)

    block_type = fields.get("type", "").lower()
    block_name = (fields.get("name") or fields.get("npc", "")).strip()
    if not block_name:
        return

    if block_type == "location":
        loc_slug = _slugify(block_name)
        loc_dir  = _REPO_ROOT / "adventure_path" / "03_locations" / loc_slug
        if loc_dir.exists():
            _log(session, f"\n> *[Location already exists, skipping: {block_name}]*\n")
            return
        loc_dir.mkdir(parents=True, exist_ok=True)
        base_md = generate_location_base_md(
            block_name,
            role         = fields.get("role", ""),
            appearance   = fields.get("appearance", ""),
            location_area= fields.get("location", ""),
            summary      = fields.get("summary", ""),
            session_number = session.session_number,
        )
        (loc_dir / "base.md").write_text(base_md, encoding="utf-8")
        _invalidate_location_index()
        _log(session, f"\n> *[New location stub created: {block_name} → {loc_dir.name}/base.md]*\n")
        return

    # NPC block (default when type is absent or not "location")
    # New format uses name:, old format used npc: — accept both.
    if _get_npc_index().npc_dir_for(block_name) is not None:
        return

    npc_slug = _slugify(block_name)
    # Dot-prefix marks this as a session NPC (temporary, purgeable from the UI).
    npc_dir  = _REPO_ROOT / "adventure_path" / "01_npcs" / f".{npc_slug}"
    npc_dir.mkdir(parents=True, exist_ok=True)

    loc_str   = fields.get("location", "")
    locations = [l.strip() for l in loc_str.split(",") if l.strip()] if loc_str else []

    base_md = generate_base_md(
        block_name,
        role        = fields.get("role", ""),
        appearance  = fields.get("appearance", ""),
        personality = fields.get("personality", ""),
        locations   = locations or None,
        session_number = session.session_number,
    )
    (npc_dir / "base.md").write_text(base_md, encoding="utf-8")
    _invalidate_npc_index()

    _log(session, f"\n> *[New NPC stub created: {block_name} → {npc_dir.name}/base.md]*\n")


def list_session_npcs() -> list[str]:
    """Return the slug names of all session NPCs (dot-prefixed directories)."""
    npc_base = _REPO_ROOT / "adventure_path" / "01_npcs"
    if not npc_base.exists():
        return []
    return sorted(
        d.name[1:]  # strip the leading dot to expose the slug
        for d in npc_base.iterdir()
        if d.is_dir() and d.name.startswith(".")
    )


def purge_session_npcs() -> int:
    """Delete all session NPC directories (dot-prefixed).

    Returns the number of directories removed.  The NPC index is invalidated
    so the next turn no longer injects profiles for purged NPCs.
    """
    import shutil as _shutil
    npc_base = _REPO_ROOT / "adventure_path" / "01_npcs"
    if not npc_base.exists():
        return 0
    count = 0
    for d in list(npc_base.iterdir()):
        if d.is_dir() and d.name.startswith("."):
            _shutil.rmtree(d)
            count += 1
    if count:
        _invalidate_npc_index()
    return count


def _stream_with_narrative_filter(
    raw_gen: Generator[str, None, None],
    dev_mode: bool,
) -> Generator[str, None, None]:
    """Wrap a raw SSE token stream to hide section markers from players.

    Dev mode  — all events pass through unchanged (markers visible for debugging).
    Non-dev   — only the %%NARRATIVE%% section content is forwarded as tokens.
                Non-token events (context, roll_request, done …) always pass through.

    Detection rules
    ───────────────
    • A response starting with ``%%NARRATIVE%%\\n`` uses the new section format.
      Tokens before the marker are suppressed; tokens from a subsequent section
      marker (``\\n%%ROLL%%``, ``\\n%%DELTAS%%``, ``\\n%%GENERATE%%``) onwards are
      suppressed.
    • If no ``%%NARRATIVE%%`` marker is found within the first 200 accumulated
      characters, the response is assumed to use the old flat-block format.
      Tokens are streamed as normal and the existing ``patch_last`` removes any
      trailing blocks.

    Cross-boundary detection
    ────────────────────────
    Section markers can span token boundaries (e.g. one token ends ``\\n%%`` and
    the next starts ``DELTAS%%\\n``).  A 16-character holdback buffer prevents
    premature emission — the last 16 chars are held and only released once the
    following token confirms they are not the start of a marker.
    """
    if dev_mode:
        yield from raw_gen
        return

    _NARRATIVE_START = "%%NARRATIVE%%\n"
    _END_MARKERS     = ("\n%%ROLL%%", "\n%%DELTAS%%", "\n%%GENERATE%%", "\n%%EVENT%%", "\n%%COMBAT%%", "\n%%HP%%", "\n%%ATTACK%%", "\n%%ACTION%%")
    _HOLDBACK        = 16   # ≥ len("%%GENERATE%%\n") = 14; also covers "%%COMBAT%%\n" = 12

    buf           = ""      # not-yet-emitted accumulation
    in_narrative  = False
    done          = False

    def _emit(text: str) -> Generator[str, None, None]:
        if text:
            yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

    for _raw_event in raw_gen:
        # Non-token events always pass through
        try:
            _ev = json.loads(_raw_event[6:])
        except Exception:
            yield _raw_event
            continue
        if _ev.get("type") != "token":
            yield _raw_event
            continue

        if done:
            continue

        buf += _ev.get("content", "")

        if not in_narrative:
            if _NARRATIVE_START in buf:
                buf = buf.split(_NARRATIVE_START, 1)[1]
                in_narrative = True
            elif len(buf) > 200:
                # Old format — no %%NARRATIVE%% found; stream everything
                in_narrative = True
            else:
                continue

        # In narrative: watch for end markers; hold back _HOLDBACK chars
        for _em in _END_MARKERS:
            _pos = buf.find(_em)
            if _pos >= 0:
                yield from _emit(buf[:_pos])
                done = True
                buf  = ""
                break
        else:
            # No end marker — emit up to the safe boundary
            _safe = max(0, len(buf) - _HOLDBACK)
            yield from _emit(buf[:_safe])
            buf = buf[_safe:]

    # Flush any remaining buffered narrative content
    if not done and in_narrative and buf:
        for _em in _END_MARKERS:
            _pos = buf.find(_em)
            if _pos >= 0:
                buf = buf[:_pos]
                break
        yield from _emit(buf)


def _detect_narrative_npcs(text: str, session: GameSession) -> None:
    """Scan completed narrative text for NPC names.

    Two passes:
    1. Single Title Case word (≥4 chars) — matched against the known alias table.
       If a single word like "Aldern" resolves to a canonical NPC, track it.
    2. Two Title Case words — heuristic for unknown NPCs not yet in the index.

    Adds candidates to session.scene_npcs so the NEXT turn's directive requests
    a %%DELTAS%% block.  Layer 2 creates the stub when the model writes the delta.
    No stub is created here — detection and creation are intentionally separated.
    """
    # Pass 1 — single word matched against known alias table
    for _m in _NARRATIVE_SINGLE_RE.finditer(text):
        _word = _m.group(1)
        if _word.lower() in _NAME_EXCLUDE_WORDS:
            continue
        _canonical = _get_npc_index().canonical_for(_word)
        if _canonical and _canonical not in session.scene_npcs:
            session.scene_npcs.append(_canonical)
            _log(session, f"\n> *[Known NPC detected by single name \"{_word}\": {_canonical} — added to scene tracking]*\n")

    # Pass 2 — two Title Case words (unknown-NPC heuristic)
    for _m in _NARRATIVE_NAME_RE.finditer(text):
        _first, _last = _m.group(1), _m.group(2)
        if _first.lower() in _NAME_EXCLUDE_WORDS or _last.lower() in _NAME_EXCLUDE_WORDS:
            continue
        _full_name = f"{_first} {_last}"
        if _full_name in session.scene_npcs:
            continue
        if _get_npc_index().npc_dir_for(_full_name) is not None:
            continue
        session.scene_npcs.append(_full_name)
        _log(session, f"\n> *[Suspected NPC detected in narrative: {_full_name} — added to scene tracking]*\n")


def _build_pc_combat_roster(session: "GameSession") -> str:
    """Return a [PARTY ROSTER] block with every PC as a ready-to-use %%COMBAT%% line.

    Called only on the turn combat starts (round 1 injection).  HP is initialised
    to full (hp_max) because PCs begin sessions at full health; the backend takes
    authority over HP from round 2 onward via the existing HP-authority mechanism.
    """
    if not session.pc_profiles:
        return ""
    lines = ["[PARTY ROSTER — include ALL of these in your %%COMBAT%% block]"]
    for profile in session.pc_profiles.values():
        cs = profile.get("combat_stats", {})
        name = cs.get("name", "")
        hp   = cs.get("hp_max", 0)
        ac   = cs.get("ac", 10)
        init = cs.get("initiative", "+0")
        if name:
            lines.append(f"  - name: {name} · hp: {hp}/{hp} · ac: {ac} · init: {init} · status: active")
    return "\n".join(lines)


_SCHEDULER_PITY_LIMIT = 6
_SCHEDULER_DEFAULT_TTL = 5


def _complete_active_event(session: GameSession) -> None:
    rt = session.event_runtime
    eid = rt.active_event_id
    if eid:
        rt.completed_events.append(eid)
        rt.active_event_id = None
        _log(session, f"\n> *[Scheduler: {eid} EXPIRED (TTL exhausted)]*\n")


def _fire_event(session: GameSession, event_id: str, source: str) -> None:
    rt = session.event_runtime
    rt.active_event_id = event_id
    we = rt.warm_events[event_id]
    we.turns_remaining = _SCHEDULER_DEFAULT_TTL
    _log(session, f"\n> *[Scheduler: {event_id} TRIGGERED via {source} — readiness={we.readiness:.0f}, failed_rolls={we.failed_rolls}]*\n")


def _trigger_phase(session: GameSession) -> None:
    rt = session.event_runtime
    if rt.active_event_id:
        return
    for event_id, we in rt.warm_events.items():
        if we.frozen:
            continue
        if we.readiness < we.threshold:
            continue
        if event_id in rt.completed_events:
            continue
        if rt.cooldowns.get(event_id, 0) > 0:
            continue
        if we.failed_rolls >= _SCHEDULER_PITY_LIMIT:
            _fire_event(session, event_id, source="pity")
            return
        roll = random.randint(1, 100)
        if roll <= we.readiness:
            _fire_event(session, event_id, source=f"roll({roll})")
            return
        we.failed_rolls += 1
        _log(session, f"\n> *[Scheduler: {event_id} miss — roll {roll} vs {we.readiness:.0f} (failed={we.failed_rolls})]*\n")


def _format_active_event_context(rt: "EventRuntime") -> Optional[str]:
    """Return a compact [ACTIVE EVENT] context block for the system prompt, or None."""
    if not rt.active_event_id:
        return None
    we = rt.warm_events.get(rt.active_event_id)
    lines = ["[ACTIVE EVENT]", f"Event: {rt.active_event_id}"]
    if we:
        lines += [
            f"Readiness at trigger: {we.readiness:.0f}",
            f"Turns remaining: {we.turns_remaining}",
        ]
    return "\n".join(lines)


def _tick_event_scheduler(session: GameSession, current_location: Optional[str], intent_tags: list) -> None:
    """Update readiness for all warm events. Called from _inject_context after zone detection.

    When session.event_scheduler is False this is a no-op.
    """
    if not session.event_scheduler:
        return
    rt = session.event_runtime

    # If an event is active, just tick its TTL and return — no new triggers.
    if rt.active_event_id:
        we = rt.warm_events.get(rt.active_event_id)
        if we and we.turns_remaining > 0:
            we.turns_remaining -= 1
            if we.turns_remaining == 0:
                _complete_active_event(session)
        return

    # Tick all cooldowns down every turn regardless of readiness or zone (BUG-002).
    for _eid, _cd in list(rt.cooldowns.items()):
        if _cd > 0:
            rt.cooldowns[_eid] = _cd - 1

    # Normalize current location to lowercase with spaces so both slug-style zone names
    # ("festival_square") and display-name canonicals ("Festival Square") match.
    loc_lower = current_location.lower().replace("_", " ") if current_location else ""
    for event_id, we in rt.warm_events.items():
        if event_id in rt.completed_events:
            continue
        in_zone = bool(loc_lower and any(loc_lower == z.lower().replace("_", " ") for z in we.zones))
        if in_zone:
            gain = we.base_gain
            matched_actions: list[str] = []
            for tag, extra in we.action_gain_map.items():
                if tag in intent_tags:
                    gain += extra
                    matched_actions.append(f"{tag}+{extra:.0f}")
            old = we.readiness
            we.readiness = min(100.0, we.readiness + gain)
            we.frozen = False
            we.last_zone_match_turn = session.turn_number
            if we.readiness != old:
                _action_str = ("; actions: " + ", ".join(matched_actions)) if matched_actions else ""
                _log(session, f"\n> *[Scheduler: {event_id} readiness {old:.0f}→{we.readiness:.0f} (+{gain:.0f} @ {current_location}{_action_str})]*\n")
        else:
            we.frozen = True

    _trigger_phase(session)


def _inject_context(session: GameSession) -> tuple[str, dict]:
    """Assemble the per-turn system prompt and context metadata.

    Handles steps 1–5 of the turn pipeline:
    1. Message history trimming to provider/mode limits
    2. Groq system prompt truncation
    3. NPC / skill / location keyword detection in the last player message
    4. scene_npcs accumulation (mutates session.scene_npcs as a side-effect)
    5. Context injection or delta-reminder appended to system_content

    Returns
    -------
    system_content : str
        Fully assembled system prompt for this turn (base + injected context).
    context_info : dict
        Keys for the SSE ``context`` event (npc, npc_trigger, skill,
        skill_trigger, location, location_npcs) plus ``history`` (the trimmed
        message list the caller uses to build the LLM payload).

    Note: signature changes in M4 — the function will write to
    session.context_blocks instead of returning system_content as a string.
    """
    if session.dev_mode:
        max_hist = _DEV_MAX_HISTORY
    elif session.provider == "groq":
        max_hist = _GROQ_MAX_HISTORY
    elif session.provider == "anthropic":
        max_hist = _ANTHROPIC_MAX_HISTORY
    else:
        max_hist = _FULL_MAX_HISTORY
    history = session.messages[-max_hist:] if len(session.messages) > max_hist else session.messages

    last_user = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )

    # ── COMBAT MODE — dedicated prompt, skip narrative injection ──────────────
    # Fires in two cases:
    #   (a) combat_state is set — live combat, round >= 1
    #   (b) no combat_state yet, but active events require a %%COMBAT%% block
    #       (pre-combat: goblin wave fired, combat about to start this turn)
    # In both cases: narrative base prompt, NPC/skill/location injection, section
    # specs, format example, delta directive, and PC narrative profiles are all
    # bypassed.  Only mechanically-relevant context is injected.
    _in_combat = session.combat_state is not None
    _combat_events_active = any("%%COMBAT%%" in ev.content for ev in session.active_events)

    if _in_combat or _combat_events_active:
        system_content = _build_combat_system_prompt(session)
        if session.provider == "groq" and len(system_content) > _GROQ_MAX_SYSTEM_CHARS:
            system_content = system_content[:_GROQ_MAX_SYSTEM_CHARS] + "\n\n…[later context omitted to stay within payload limit]"

        _log(session, f"\n> *[Combat mode ({'live' if _in_combat else 'pre-combat'}) — using _build_combat_system_prompt]*\n")

        # Active events — TTL decrement first (shared by both sub-cases)
        _expired_ids: list[str] = []
        for _ev in session.active_events:
            _ev.turns_remaining -= 1
            if _ev.turns_remaining <= 0:
                _expired_ids.append(_ev.event_id)
        if _expired_ids:
            session.active_events = [e for e in session.active_events if e.event_id not in _expired_ids]
            _log(session, f"\n> *[Events expired: {', '.join(_expired_ids)}]*\n")
            _write_session_state(session)

        _combat_injected: list[str] = []
        for _ev in session.active_events:
            _combat_injected.append(f"## Active Event — {_ev.event_id}\n\n{_ev.content}")

        # Combat rules lookup — always active in combat mode
        _crules_match = _get_combat_rules_index().detect(last_user)
        if _crules_match:
            _combat_injected.append(_get_combat_rules_index().format_context(_crules_match))
            _log(session, f"\n> *[Combat rules injected: {_crules_match.rule_name} (trigger: \"{_crules_match.matched_trigger}\")]*\n")

        if _combat_injected:
            system_content += "\n\n---\n[COMBAT CONTEXT]\n" + "\n\n---\n".join(_combat_injected)

        if _in_combat:
            # ── Live combat (round >= 1) — inject tracker, HP, stats, conditions ──
            combat = session.combat_state

            # [INITIATIVE ORDER] — sorted descending; current actor (highest active) marked →
            _sorted = sorted(combat.combatants, key=lambda c: c.initiative, reverse=True)
            _active = [c for c in _sorted if c.status == "active"]
            _current_name = _active[0].name if _active else None
            _init_lines = []
            for _c in _sorted:
                _marker = "→ " if _c.name == _current_name else "  "
                _init_lines.append(f"{_marker}{_c.name}: init {_c.initiative}  AC {_c.ac}  ({_c.status})")
            system_content += (
                f"\n\n[INITIATIVE ORDER — round {combat.round}]\n"
                + "\n".join(_init_lines)
            )

            # [CURRENT HP] — authoritative; backend owns these values
            _hp_lines = "\n".join(
                f"  {_c.name}: {_c.hp_current}/{_c.hp_max} ({_c.status})"
                for _c in _sorted
            )
            system_content += f"\n\n[CURRENT HP]\n{_hp_lines}"

            # [PC COMBAT STATS] — mechanical profiles for all PCs
            if session.pc_profiles:
                _pc_stat_blocks = [
                    _tiers["mechanical"]
                    for _tiers in session.pc_profiles.values()
                    if _tiers.get("mechanical")
                ]
                if _pc_stat_blocks:
                    system_content += "\n\n[PC COMBAT STATS]\n" + "\n\n".join(_pc_stat_blocks)

            # [ACTIVE CONDITIONS] — only when at least one combatant has conditions
            _cond_entries = [
                f"  {_c.name}: {', '.join(_c.conditions)}"
                for _c in combat.combatants
                if _c.conditions
            ]
            if _cond_entries:
                system_content += "\n\n[ACTIVE CONDITIONS]\n" + "\n".join(_cond_entries)

            # Section specs (combat-mode variant) + full ongoing format
            system_content += f"\n\n---\n{_COMBAT_SECTION_SPECS}\n\n{_COMBAT_SPEC_ONGOING}"
            _log(session, f"\n> *[Combat turn: round {combat.round}, current actor: {_current_name}]*\n")
        else:
            # ── Pre-combat (events require %%COMBAT%% but round not started) ────────
            # Inject PC combat stats so the LLM has HP/AC/init for the %%COMBAT%% block
            # it must write.  No initiative order or HP tracker yet — those don't exist.
            if session.pc_profiles:
                _pc_stat_blocks = [
                    _tiers["mechanical"]
                    for _tiers in session.pc_profiles.values()
                    if _tiers.get("mechanical")
                ]
                if _pc_stat_blocks:
                    system_content += "\n\n[PC COMBAT STATS]\n" + "\n\n".join(_pc_stat_blocks)

            # Round-1 format + party roster (same as old pre-combat injection)
            _pc_roster = _build_pc_combat_roster(session)
            system_content += (
                f"\n\n---\n[COMBAT START FORMAT — write this now]\n"
                f"{_COMBAT_SPEC_ROUND1}"
                + (f"\n\n{_pc_roster}" if _pc_roster else "")
            )
            # Combat-mode section specs (no %%GENERATE%%/%%DELTAS%%/%%ROLL%%)
            system_content += f"\n\n---\n{_COMBAT_SECTION_SPECS}"
            _log(session, "\n> *[Pre-combat turn: events require %%COMBAT%% block]*\n")

        # Tick scheduler TTL even in combat so active events expire on schedule.
        # No zone detection or trigger phase — combat blocks new soft triggers anyway.
        _tick_event_scheduler(session, current_location=None, intent_tags=[])

        _active_event_ids = [e.event_id for e in session.active_events]

        return system_content, {
            "npc":           None,
            "npc_trigger":   None,
            "skill":         None,
            "skill_trigger": None,
            "location":      None,
            "location_npcs": [],
            "loc":           None,
            "loc_trigger":   None,
            "active_events": _active_event_ids,
            "scene_npcs":    list(session.scene_npcs),
            "history":       history,
        }

    # ── NARRATIVE MODE — standard injection pipeline ───────────────────────────
    system_content = session.system_prompt
    if session.provider == "groq" and len(system_content) > _GROQ_MAX_SYSTEM_CHARS:
        system_content = system_content[:_GROQ_MAX_SYSTEM_CHARS] + "\n\n…[later context omitted to stay within payload limit]"

    # Turn-1 format example — injected only on the first player turn.
    if len(session.messages) == 1:
        system_content += f"\n\n---\n{_FORMAT_EXAMPLE}"
        _log(session, "\n> *[Format example injected: first player turn]*\n")

    injected: list[str] = []

    # Detect skill first — needed to choose full vs short NPC profile below.
    skill_match = _get_skill_index().detect(last_user)
    if skill_match:
        injected.append(_get_skill_index().format_context(skill_match))
        _log(session, f"\n> *[Skill context injected: {skill_match.skill_name} (trigger: \"{skill_match.matched_trigger}\")]*\n")

    # NPC injection: full profile when a social/skill check is active this turn;
    # short stub (name + hook + DC + current state) otherwise.
    npc_match = _get_npc_index().detect(last_user)
    if npc_match:
        if skill_match:
            injected.append(_get_npc_index().format_context(npc_match))
            _log(session, f"\n> *[NPC context injected: {npc_match.canonical_name} (full — skill active, alias: \"{npc_match.matched_alias}\")]*\n")
        else:
            injected.append(_get_npc_index().format_short_context(npc_match))
            _log(session, f"\n> *[NPC context injected: {npc_match.canonical_name} (short, alias: \"{npc_match.matched_alias}\")]*\n")

    # If no NPC was named by the player but one is active in the scene (they just
    # responded on the previous turn), inject their profile so the GM has the right
    # context — e.g. when the player continues a conversation without repeating the name.
    _scene_npc_match = None
    if not npc_match and session.scene_npcs:
        _scene_npc_match = _get_npc_index().lookup(session.scene_npcs[-1])
        if _scene_npc_match:
            if skill_match:
                injected.append(_get_npc_index().format_context(_scene_npc_match))
                _log(session, f"\n> *[NPC context injected: {_scene_npc_match.canonical_name} (full — skill active, implicit from scene)]*\n")
            else:
                injected.append(_get_npc_index().format_short_context(_scene_npc_match))
                _log(session, f"\n> *[NPC context injected: {_scene_npc_match.canonical_name} (short, implicit from scene)]*\n")

    # Location-based NPC injection removed — only inject NPCs the player
    # explicitly named or directly interacted with (not all NPCs at a location).
    location_matches: list = []

    # Location profile detection (LocationIndex — separate from NPC-at-location)
    loc_match = _get_location_index().detect(last_user)
    loc_canonical: Optional[str] = None
    loc_trigger: Optional[str] = None

    if loc_match:
        injected.append(_get_location_index().format_context(loc_match))
        loc_canonical = loc_match.canonical_name
        loc_trigger = loc_match.matched_alias
        if loc_canonical not in session.scene_locations:
            session.scene_locations.append(loc_canonical)
        _log(session, f"\n> *[Location profile injected: {loc_canonical} (alias: \"{loc_trigger}\")]*\n")
    elif session.scene_locations:
        # Re-inject all active location profiles as ambient context (AC-007)
        loc_idx = _get_location_index()
        for _loc_name in session.scene_locations:
            _ambient = loc_idx.lookup(_loc_name)
            if _ambient:
                injected.append(loc_idx.format_context(_ambient))
        loc_canonical = session.scene_locations[-1]
        _log(session, f"\n> *[Location profile re-injected: {', '.join(session.scene_locations)}]*\n")

    if npc_match and npc_match.canonical_name not in session.scene_npcs:
        session.scene_npcs.append(npc_match.canonical_name)

    # ── Scheduler tick ────────────────────────────────────────────────────────
    # Runs after zone/location detection so loc_canonical is available.
    # intent_tags: whitespace-split tokens from the player message. action_gain_map
    # keys must therefore be single words (e.g. "explore", "attack") — multi-word
    # keys will never match. See E1-2 notes in EVENT-TODO.md.
    _intent_tags = last_user.lower().split()
    _tick_event_scheduler(session, loc_canonical, _intent_tags)

    # ── Active scheduler event injection ─────────────────────────────────────
    if session.event_scheduler:
        _evt_ctx = _format_active_event_context(session.event_runtime)
        if _evt_ctx:
            injected.append(_evt_ctx)

    # ── Sections active this turn ─────────────────────────────────────────────
    # Inject only the specs that are relevant based on detection results.
    # %%NARRATIVE%% and %%GENERATE%% are always included; %%ROLL%% only when a
    # skill is detected; %%DELTAS%% only when NPCs are present in the scene.
    _active_specs = [_NARRATIVE_SPEC, _GENERATE_SPEC]
    _active_spec_names = ["NARRATIVE", "GENERATE"]
    if skill_match:
        _active_specs.append(_ROLL_SPEC)
        _active_spec_names.append("ROLL")
    if session.scene_npcs or npc_match:
        _active_specs.append(_DELTAS_SPEC)
        _active_spec_names.append("DELTAS")
    system_content += (
        f"\n\n---\n[SECTIONS ACTIVE THIS TURN]\n"
        + "\n\n".join(_active_specs)
    )
    _log(session, f"\n> *[Section specs: {' '.join(_active_spec_names)}]*\n")

    # ── PC profile injection ──────────────────────────────────────────────────
    # Narrative profile injected when the PC's name appears in the player input.
    # Mechanical profile added on top when a skill check is also detected.
    _last_lower = last_user.lower()
    for _pc_name, _pc_tiers in session.pc_profiles.items():
        if _pc_name in _last_lower:
            system_content += f"\n\n{_pc_tiers['narrative']}"
            _log(session, f"\n> *[PC narrative profile injected: {_pc_name}]*\n")
            if skill_match:
                system_content += f"\n\n{_pc_tiers['mechanical']}"
                _log(session, f"\n> *[PC mechanical profile injected: {_pc_name}]*\n")
            break  # at most one PC per turn

    # ── Active events — decrement TTL, inject content ─────────────────────────
    expired_ids: list[str] = []
    for _ev in session.active_events:
        _ev.turns_remaining -= 1
        if _ev.turns_remaining <= 0:
            expired_ids.append(_ev.event_id)
    if expired_ids:
        session.active_events = [e for e in session.active_events if e.event_id not in expired_ids]
        _log(session, f"\n> *[Events expired: {', '.join(expired_ids)}]*\n")
        _write_session_state(session)

    for _ev in session.active_events:
        injected.append(f"## Active Event — {_ev.event_id}\n\n{_ev.content}")

    active_event_ids = [e.event_id for e in session.active_events]

    # ── Combat rules lookup — only when combat is active ─────────────────────
    if session.combat_state is not None and session.combat_state.round > 0:
        combat_rule_match = _get_combat_rules_index().detect(last_user)
        if combat_rule_match:
            injected.append(_get_combat_rules_index().format_context(combat_rule_match))
            _log(session, f"\n> *[Combat rules injected: {combat_rule_match.rule_name} (trigger: \"{combat_rule_match.matched_trigger}\")]*\n")

    if injected:
        block = "\n\n---\n".join(injected)
        directive = _build_turn_directive(npc_match or _scene_npc_match, skill_match, location_matches, session.scene_npcs)
        system_content = (
            system_content
            + f"\n\n---\n[CONTEXT FOR THIS TURN]\n{block}"
            + f"\n\n---\n[GM DIRECTIVE FOR THIS TURN — follow exactly]\n{directive}"
        )
    elif session.scene_npcs:
        _npc_list = ", ".join(session.scene_npcs)
        system_content += (
            f"\n\n---\n[GM DIRECTIVE FOR THIS TURN — follow exactly]\n"
            f"Continue the scene naturally.\n\n"
            f"Write a %%DELTAS%% section covering: {_npc_list}.\n"
            "If your narrative names any character NOT already in that list, "
            "you MUST write a %%GENERATE%% block for them — no exceptions."
        )
        _log(session, f"\n> *[Delta reminder injected for scene NPCs: {_npc_list}]*\n")

    # ── Pre-combat round-1 spec for non-combat events ─────────────────────────
    # When active events are present that do NOT require a %%COMBAT%% block
    # (e.g. a pure narrative event), still hint the round-1 format so the LLM
    # can start combat if the player triggers it.  Events that DO require
    # %%COMBAT%% are handled by the combat branch above (returned early).
    if session.active_events:  # _combat_events_active is False here — early-returned above
        _pc_roster = _build_pc_combat_roster(session)
        system_content += (
            f"\n\n---\n[COMBAT START FORMAT — use if starting combat this turn]\n"
            f"{_COMBAT_SPEC_ROUND1}"
            + (f"\n\n{_pc_roster}" if _pc_roster else "")
        )
        _log(session, "\n> *[Combat round-1 spec injected (narrative events, no combat yet)]*\n")

    context_info: dict = {
        "npc":           npc_match.canonical_name    if npc_match else None,
        "npc_trigger":   npc_match.matched_alias     if npc_match else None,
        "skill":         skill_match.skill_name      if skill_match else None,
        "skill_trigger": skill_match.matched_trigger if skill_match else None,
        "location":      location_matches[0].matched_location if location_matches else None,
        "location_npcs": [m.canonical_name for m in location_matches] if location_matches else [],
        "loc":           loc_canonical,
        "loc_trigger":   loc_trigger,
        "active_events": active_event_ids,
        "scene_npcs":    list(session.scene_npcs),
        "history":       history,
    }

    return system_content, context_info


def _process_response(
    response_text: str,
    session: "GameSession",
) -> "tuple[str, Optional[dict], list[str]]":
    """Parse all structured sections in a completed LLM response.

    Mutates *session* in place (NPC writes, combat state updates, pending_roll,
    attack queue, etc.) and returns ``(display_text, roll_data, pending_sse)``.

    ``pending_sse`` is a list of pre-formatted ``data: ...\\n\\n`` strings that
    need to be yielded by the caller *after* this function returns — keeping all
    SSE emission at the generator level rather than buried inside a plain function.
    """
    pending_sse: list[str] = []
    roll_data: Optional[dict] = None

    _use_sections = bool(_HAS_SECTION_MARKERS_RE.search(response_text))

    if _use_sections:
        _sections = _parse_response_sections(response_text)
        display_text = _sections.get("NARRATIVE", "").strip() or response_text.strip()

        # ── %%GENERATE%% ──────────────────────────────────────────────────────
        # Processed before %%DELTAS%% so new stubs are in the index immediately.
        _gen_section = _sections.get("GENERATE", "")
        if _gen_section:
            for _gf in _parse_bracket_blocks(_gen_section):
                try:
                    _body = "\n".join(f"{k}: {v}" for k, v in _gf.items())
                    _process_generate_block(_body, session)
                except Exception as _e:
                    _log(session, f"\n> *[%%GENERATE%% processing error: {_e}]*\n")

        # ── %%DELTAS%% ────────────────────────────────────────────────────────
        _deltas_section = _sections.get("DELTAS", "")
        if _deltas_section:
            for _df in _parse_bracket_blocks(_deltas_section):
                try:
                    _write_npc_delta(_df, session)
                except Exception as _e:
                    _log(session, f"\n> *[%%DELTAS%% processing error: {_e}]*\n")

        # ── %%EVENT%% ─────────────────────────────────────────────────────────
        _event_m = _EVENT_LINE_RE.search(response_text)
        if _event_m:
            _fired_id = _event_m.group(1).strip()
            _already_active = any(e.event_id == _fired_id for e in session.active_events)
            if not _already_active:
                _entry = _get_event_index().get(_fired_id)
                if _entry:
                    session.active_events.append(
                        ActiveEvent(event_id=_fired_id, content=_entry.content, turns_remaining=5)
                    )
                    _log(session, f"\n> *[Event fired: {_fired_id} — active for 5 turns]*\n")
                    _load_event_zone_data(session, _entry)
                    # Seed combatants from ## Combatants table and auto-initialize combat state.
                    # The LLM does not need to write %%COMBAT%% for event-driven combat starts —
                    # the backend owns the authoritative data; LLM block is discarded this turn.
                    if _entry.event_type == "combat" and session.combat_state is None:
                        _seeded = _parse_event_combatants(_entry.content)
                        if _seeded:
                            session.pending_combatants.update(_seeded)
                        # Parse optional PC starting zone from event content
                        _pcz_m = re.search(r'\*\*PC Starting Zone:\*\*\s*(.+)', _entry.content)
                        _pc_start_zone = _pcz_m.group(1).strip() if _pcz_m else "default"
                        if _pc_start_zone != "default":
                            session.party_zone_id = _pc_start_zone
                        # Build CombatState: PCs from profiles + enemies from event file
                        _init_combatants: list = []
                        for _pk, _pp in session.pc_profiles.items():
                            _cs = _pp.get("combat_stats", {})
                            _pname = _cs.get("name", "")
                            _php   = _cs.get("hp_max", 10) or 10
                            _pac   = _cs.get("ac",     10) or 10
                            _pcur  = session.pc_current_hp.get(_pk, _php)
                            if _pname:
                                _init_combatants.append(Combatant(
                                    name=_pname, hp_current=_pcur, hp_max=_php, ac=_pac, initiative=0,
                                    zone=_pc_start_zone,
                                ))
                        for _ek, _ed in session.pending_combatants.items():
                            _init_combatants.append(Combatant(
                                name=_ed.get("name", _ek.title()),
                                hp_current=_ed.get("hp", 5),
                                hp_max=_ed.get("hp", 5),
                                ac=_ed.get("ac", 13),
                                initiative=0,
                                attacks=_ed.get("attacks", {}),
                                zone=_ed.get("zone", "default"),
                            ))
                        session.combat_state = CombatState(round=1, combatants=_init_combatants)
                        _refresh_combat_known_zones(session)
                        session._await_initiative_roll = True
                        session._skip_combat_block = True
                        _log(session, f"\n> *[Combat auto-initialized from event file: "
                                      f"{len(session.pc_profiles)} PC(s) + "
                                      f"{len(session.pending_combatants)} enemy(ies)]*\n")
                        pending_sse.append(
                            f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
                        )
                    _write_session_state(session)
                else:
                    _log(session, f"\n> *[Event ignored: unknown id \"{_fired_id}\"]*\n")

        # ── %%HP%% — discarded; LLM no longer instructed to write this block ──
        if _sections.get("HP"):
            _log(session, "\n> *[WARN: %%HP%% block received and discarded — LLM should not write this]*\n")

        # ── %%COMBAT%% ────────────────────────────────────────────────────────
        _combat_section = _sections.get("COMBAT", "")
        if _combat_section:
            try:
                # Discard LLM %%COMBAT%% when combat was auto-initialized from an event file
                # this same turn (round 0 = intentional clear signal, never skip that).
                if session._skip_combat_block:
                    session._skip_combat_block = False
                    _log(session, "\n> *[%%COMBAT%% block discarded — combat auto-initialized from event file]*\n")
                    _write_session_state(session)
                    _combat_result = None
                else:
                    _combat_result = _parse_combat_block(_combat_section, existing_state=session.combat_state)
                if _combat_result is not None:
                    if _combat_result.round == 0:          # intentional clear signal
                        session.combat_state = None
                        _log(session, "\n> *[Combat state updated: cleared]*\n")
                    else:                                   # valid update
                        _is_round1 = session.combat_state is None
                        session.combat_state = _combat_result
                        _log(session, f"\n> *[Combat state updated: round {_combat_result.round}]*\n")
                        # Round 1: always seed PC HP/AC from pc_profiles so the
                        # CombatPanel never shows 0/0 for PCs (B-C03b fix).
                        if _is_round1 and _combat_result.round == 1:
                            _seed_pc_stats(session, session.combat_state)

                        # Initiative roll + enemy seeding only when a combat event is active
                        if _is_round1 and _combat_result.round == 1:
                            _idx = _get_event_index()
                            _has_combat_event = any(
                                (lambda _e: _e is not None and _e.event_type == "combat")(_idx.get(ev.event_id))
                                for ev in session.active_events
                            )
                            if _has_combat_event:
                                _seed_enemy_stats(session, session.combat_state)
                                session._await_initiative_roll = True
                                _log(session, "\n> *[Initiative pending — awaiting player roll]*\n")
                    _write_session_state(session)
                # None → parse failure; leave session.combat_state unchanged
            except Exception as _e:
                _log(session, f"\n> *[%%COMBAT%% processing error: {_e}]*\n")

        # ── %%ATTACK%% (Tier 1.5) ─────────────────────────────────────────────
        _attack_section = _sections.get("ATTACK", "")
        if _attack_section and session.combat_state is not None:
            try:
                _attacks = _parse_attack_block(_attack_section)
                for _att in _attacks:
                    if _is_pc_attacker(_att["attacker"], session):
                        session.attack_queue.append(PendingAttack(
                            attacker=_att["attacker"], target=_att["target"],
                            bonus=_att["bonus"], damage_expr=_att["damage"],
                            attack_type=_att.get("type", "melee"), is_pc=True,
                        ))
                    else:
                        _npc_result = _resolve_npc_attack(_att, session)
                        session.attack_results.append(_npc_result)
                        pending_sse.append(
                            f"data: {json.dumps({'type': 'attack_result', **_npc_result})}\n\n"
                        )
                _log(session, f"\n> *[%%ATTACK%%: {len(_attacks)} attack(s) parsed, "
                              f"{len(session.attack_queue)} queued for player]*\n")
            except Exception as _e:
                _log(session, f"\n> *[%%ATTACK%% processing error: {_e}]*\n")

    else:
        # ── Fallback: old flat-block format ───────────────────────────────────
        display_text = response_text
        _sections = {}

        # %%ROLL%%
        _roll_m = _ROLL_BLOCK_RE.search(display_text)
        if _roll_m:
            _sections["ROLL"] = (
                f"skill: {_roll_m.group('skill').strip()}\n"
                f"dc: {_roll_m.group('dc').strip()}\n"
                f"success: {_roll_m.group('success').strip()}\n"
                f"failure: {_roll_m.group('failure').strip()}"
            )
            display_text = _ROLL_BLOCK_RE.sub("", display_text).rstrip()

        # %%GENERATE%%
        _gen_matches = list(_GENERATE_BLOCK_RE.finditer(display_text))
        if _gen_matches:
            display_text = _GENERATE_BLOCK_RE.sub("", display_text).strip()
            for _gm in _gen_matches:
                try:
                    _process_generate_block(_gm.group(1), session)
                except Exception as _e:
                    _log(session, f"\n> *[%%GENERATE%% processing error: {_e}]*\n")

        # %%DELTA%%
        _delta_matches = list(_DELTA_BLOCK_RE.finditer(display_text))
        if _delta_matches:
            display_text = _DELTA_BLOCK_RE.sub("", display_text).strip()
            for _dm in _delta_matches:
                try:
                    _fields = _parse_delta_fields(_dm.group(1))
                    _fields["knowledge"] = _extract_knowledge_items(_dm.group(1))
                    _write_npc_delta(_fields, session)
                except Exception as _e:
                    _log(session, f"\n> *[%%DELTA%% processing error: {_e}]*\n")

        # %%EVENT%% (flat-block fallback path)
        _event_m_flat = _EVENT_LINE_RE.search(response_text)
        if _event_m_flat:
            _fired_id = _event_m_flat.group(1).strip()
            _already_active = any(e.event_id == _fired_id for e in session.active_events)
            if not _already_active:
                _entry = _get_event_index().get(_fired_id)
                if _entry:
                    session.active_events.append(
                        ActiveEvent(event_id=_fired_id, content=_entry.content, turns_remaining=5)
                    )
                    _log(session, f"\n> *[Event fired: {_fired_id} — active for 5 turns]*\n")
                    _load_event_zone_data(session, _entry)
                    if _entry.event_type == "combat":
                        _seeded = _parse_event_combatants(_entry.content)
                        if _seeded:
                            session.pending_combatants.update(_seeded)
                            _log(session, f"\n> *[Combat event seeded {len(_seeded)} combatant(s) into pending_combatants]*\n")
                    _write_session_state(session)
                else:
                    _log(session, f"\n> *[Event ignored: unknown id \"{_fired_id}\"]*\n")

        # %%HP%% (flat-block fallback path) — discarded
        if "%%HP%%" in response_text.upper():
            _log(session, "\n> *[WARN: %%HP%% block received and discarded (flat path) — LLM should not write this]*\n")

        # %%COMBAT%% (flat-block fallback path)
        _combat_m = _COMBAT_BLOCK_RE.search(response_text)
        if _combat_m:
            try:
                _combat_result = _parse_combat_block(_combat_m.group(1), existing_state=session.combat_state)
                if _combat_result is not None:
                    if _combat_result.round == 0:
                        session.combat_state = None
                        _log(session, "\n> *[Combat state updated (flat): cleared]*\n")
                    else:
                        _is_round1_flat = session.combat_state is None
                        session.combat_state = _combat_result
                        _log(session, f"\n> *[Combat state updated (flat): round {_combat_result.round}]*\n")
                        if _is_round1_flat and _combat_result.round == 1:
                            _seed_pc_stats(session, session.combat_state)
                            _idx = _get_event_index()
                            _has_combat_event = any(
                                (lambda _e: _e is not None and _e.event_type == "combat")(_idx.get(ev.event_id))
                                for ev in session.active_events
                            )
                            if _has_combat_event:
                                _seed_enemy_stats(session, session.combat_state)
                                session._await_initiative_roll = True
                                _log(session, "\n> *[Initiative pending — awaiting player roll (flat path)]*\n")
                    _write_session_state(session)
            except Exception as _e:
                _log(session, f"\n> *[%%COMBAT%% processing error: {_e}]*\n")

        # %%ATTACK%% (flat-block fallback path — Tier 1.5)
        _attack_m = _ATTACK_BLOCK_RE.search(response_text)
        if _attack_m and session.combat_state is not None:
            try:
                _attacks = _parse_attack_block(_attack_m.group(1))
                for _att in _attacks:
                    if _is_pc_attacker(_att["attacker"], session):
                        session.attack_queue.append(PendingAttack(
                            attacker=_att["attacker"], target=_att["target"],
                            bonus=_att["bonus"], damage_expr=_att["damage"],
                            attack_type=_att.get("type", "melee"), is_pc=True,
                        ))
                    else:
                        _npc_result = _resolve_npc_attack(_att, session)
                        session.attack_results.append(_npc_result)
                        pending_sse.append(
                            f"data: {json.dumps({'type': 'attack_result', **_npc_result})}\n\n"
                        )
            except Exception as _e:
                _log(session, f"\n> *[%%ATTACK%% processing error (flat): {_e}]*\n")

    _roll_fields = _parse_roll_section(_sections.get("ROLL", ""))
    if _roll_fields:
        roll_data = {
            **_roll_fields,
            "speaker": _speaker_from_user_input(session.messages[-1]["content"]) if session.messages else None,
        }
        session.pending_roll = roll_data
        _log(session, f"\n> *[Roll requested: {roll_data['skill']} DC {roll_data['dc']}]*\n")

    return display_text, roll_data, pending_sse


def _stream_chat(session: GameSession) -> Generator[str, None, None]:
    session.turn_number += 1

    system_content, context_info = _inject_context(session)
    history = context_info["history"]

    # ── Context detection event (dev tooling) ─────────────────────────────────
    yield "data: " + json.dumps({
        "type":          "context",
        "npc":           context_info["npc"],
        "npc_trigger":   context_info["npc_trigger"],
        "skill":         context_info["skill"],
        "skill_trigger": context_info["skill_trigger"],
        "location":      context_info["location"],
        "location_npcs": context_info["location_npcs"],
        "loc":           context_info["loc"],
        "loc_trigger":   context_info["loc_trigger"],
        "active_events": context_info["active_events"],
        "scene_npcs":    context_info["scene_npcs"],
    }) + "\n\n"

    messages = [{"role": "system", "content": system_content}] + history
    options: dict = {
        "temperature": session.temperature,
        "num_ctx": session.num_ctx,
        "num_gpu": session.num_gpu,
    }
    if session.dev_mode:
        options["num_predict"] = _DEV_MAX_TOKENS
    accumulated: list[str] = []

    last_user = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )
    _log(session, f"\n### [{_ts()}] PLAYER")
    _log(session, f"{last_user}\n")

    # ── Full LLM payload ──────────────────────────────────────────────────────
    _log(session, f"\n<details><summary>LLM payload — turn {session.turn_number}</summary>\n")
    for msg in messages:
        role = msg["role"].upper()
        _log(session, f"\n**[{role}]**\n```\n{msg['content']}\n```\n")
    _log(session, "</details>\n")

    # Build the exact payload that will be posted — mirrored from each provider's function
    if session.provider == "groq":
        _raw_request: dict = {
            "model":          session.model,
            "messages":       messages,
            "stream":         True,
            "temperature":    session.temperature,
            "max_tokens":     1024,
            "stream_options": {"include_usage": True},
        }
    elif session.provider == "anthropic":
        _system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        _raw_request = {
            "model":       session.model,
            "system":      _system_msg,
            "messages":    [m for m in messages if m["role"] != "system"],
            "stream":      True,
            "temperature": session.temperature,
            "max_tokens":  1024,
        }
    else:
        _raw_request = {
            "model":    session.model,
            "messages": messages,
            "stream":   True,
            "options":  options,
        }

    _llm_start = _time.monotonic()
    _timing: dict = {"start": _llm_start}
    _usage: dict = {}

    # ── Buffer tokens; retry once if %%NARRATIVE%% is absent ─────────────────
    # Tokens are held server-side until the full response is validated.  This
    # prevents blank GM bubbles when the model omits the %%NARRATIVE%% marker.
    # Flat-format responses (small models without %% markers) always pass.
    _MAX_NARRATIVE_RETRIES = 1   # 2 total attempts
    _buffered_sse: list[str] = []

    for _attempt in range(_MAX_NARRATIVE_RETRIES + 1):
        if _attempt > 0:
            _log(session,
                 f"\n> *[%%NARRATIVE%% missing — retry {_attempt}/{_MAX_NARRATIVE_RETRIES}]*\n")
            accumulated.clear()
            _usage.clear()
            _timing = {"start": _time.monotonic()}
            _buffered_sse.clear()

        _llm_error: Optional[str] = None
        try:
            if session.provider == "groq":
                _raw = _stream_groq(session, messages, accumulated, _usage, _timing)
            elif session.provider == "anthropic":
                _raw = _stream_anthropic(session, messages, accumulated, _usage, _timing)
            else:
                _raw = _stream_ollama(session, messages, options, accumulated, _timing)
            for _sse_chunk in _stream_with_narrative_filter(_raw, session.dev_mode):
                _buffered_sse.append(_sse_chunk)
        except Exception as _llm_exc:
            _llm_error = str(_llm_exc)
            raise
        finally:
            _llm_ms = int((_time.monotonic() - _timing.get("start", _llm_start)) * 1000)
            _response_text = "".join(accumulated)
            # null when no content arrived (error before first token); bool otherwise.
            _section_format_ok: Optional[bool] = (
                bool(_HAS_SECTION_MARKERS_RE.search(_response_text)) if _response_text else None
            )
            write_api_log(
                provider=session.provider,
                session_id=session.id,
                session_number=session.session_number,
                turn=session.turn_number,
                raw_request=_raw_request,
                response_text=_response_text,
                duration_ms=_llm_ms,
                first_token_ms=_timing.get("first_token_ms"),
                section_format_ok=_section_format_ok,
                status="error" if _llm_error else "ok",
                error=_llm_error,
                usage=_usage or None,
            )

        # Validate: %%NARRATIVE%% must appear as an explicit marker in section format.
        # Flat-format responses (no %% markers) pass unconditionally.
        # NOTE: _parse_response_sections cannot be used here — it adds a NARRATIVE
        # fallback for any input lacking the marker, which would defeat the guard.
        _resp_v = "".join(accumulated)
        if bool(_HAS_SECTION_MARKERS_RE.search(_resp_v)):
            _narrative_ok = bool(re.search(r'^%%NARRATIVE%%', _resp_v, re.MULTILINE))
        else:
            _narrative_ok = bool(_resp_v.strip())

        if _narrative_ok or _attempt >= _MAX_NARRATIVE_RETRIES:
            if not _narrative_ok:
                _log(session,
                     f"\n> *[%%NARRATIVE%% still missing after {_MAX_NARRATIVE_RETRIES} "
                     f"retries — proceeding with response as-is]*\n")
            break

    yield from _buffered_sse

    # Emit rate limit info captured from Groq response headers (Groq only; None for Ollama).
    # The UI uses this to show remaining requests/tokens in the header.
    if _usage.get("rate_limits"):
        yield f"data: {json.dumps({'type': 'rate_limits', **_usage['rate_limits']})}\n\n"

    response_text = "".join(accumulated)

    display_text, roll_data, _pending_sse = _process_response(response_text, session)
    yield from _pending_sse

    # ── Single patch_last if anything was stripped ────────────────────────────
    # Emitting one event after all stripping avoids the UI briefly flashing
    # intermediate states (e.g. showing delta markup while the roll block is gone).
    # Dev mode: all tokens were already streamed unfiltered (markers visible) —
    # suppress patch_last so the raw response isn't replaced with cleaned text.
    history_text = display_text
    if not session.dev_mode and history_text != response_text:
        yield f"data: {json.dumps({'type': 'patch_last', 'content': history_text})}\n\n"

    # Roll request comes after the clean text is in place
    if roll_data:
        yield f"data: {json.dumps({'type': 'roll_request', **roll_data})}\n\n"

    # Auto-advance to next combatant after PC attack resolution (stream_resume_combat)
    if session._advance_combat_after_stream and session.combat_state is not None:
        session._advance_combat_after_stream = False
        try:
            advance_combat_turn(session)
        except ValueError:
            _write_session_state(session)

    # Combat state — emitted as initiative_pending when waiting for player to roll,
    # otherwise as combat_update (null when no combat so UI can show/hide panel).
    if session._await_initiative_roll:
        session._await_initiative_roll = False
        yield f"data: {json.dumps({'type': 'initiative_pending', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"

    # Tier 1.5 — if PC attacks are queued, emit attack_request for the first one.
    if session.attack_queue:
        _first = session.attack_queue[0]
        _first_ac = _get_combatant_ac(_first.target, session.combat_state)
        yield f"data: {json.dumps({'type': 'attack_request', 'attacker': _first.attacker, 'target': _first.target, 'bonus': _first.bonus, 'ac': _first_ac, 'damage_expr': _first.damage_expr, 'attack_type': _first.attack_type})}\n\n"

    session.messages.append({"role": "assistant", "content": history_text})
    _log(session, f"\n### [{_ts()}] GM")
    _log(session, f"{history_text}\n")
    _log(session, "---\n")

    # Scan the finalised narrative for NPC names the model introduced without
    # any structured block.  Adds suspects to scene_npcs so the next turn's
    # directive requests deltas for them; Layer 2 creates stubs at that point.
    try:
        _detect_narrative_npcs(history_text, session)
    except Exception as _e:
        _log(session, f"\n> *[NPC narrative detection error: {_e}]*\n")


def _stream_ollama(
    session: GameSession,
    messages: list,
    options: dict,
    accumulated: list[str],
    timing_out: dict,
) -> Generator[str, None, None]:
    with _requests.post(
        f"{session.host}/api/chat",
        json={"model": session.model, "messages": messages, "stream": True, "options": options},
        stream=True,
        timeout=180,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content = (chunk.get("message") or {}).get("content", "")
            if content:
                if "first_token_ms" not in timing_out:
                    timing_out["first_token_ms"] = int((_time.monotonic() - timing_out["start"]) * 1000)
                accumulated.append(content)
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            if chunk.get("done"):
                break


def _stream_groq(
    session: GameSession,
    messages: list,
    accumulated: list[str],
    usage_out: dict,
    timing_out: dict,
) -> Generator[str, None, None]:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Get a free key at https://console.groq.com"
        )
    payload = {
        "model": session.model,
        "messages": messages,
        "stream": True,
        "temperature": session.temperature,
        "max_tokens": 1024,
        # Request a final usage-only chunk after the stream ends.
        # Groq sends: {"choices": [], "usage": {prompt_tokens, completion_tokens, ...}}
        "stream_options": {"include_usage": True},
    }
    with _groq_post(api_key, payload, stream=True) as resp:
        # Capture per-minute rate limit headers sent on every successful Groq response.
        # Per-day limits only surface in 429 error bodies; we surface those via the
        # RuntimeError message instead.
        _RL_HEADERS = {
            "x-ratelimit-limit-requests":     "rpm_limit",
            "x-ratelimit-remaining-requests": "rpm_remaining",
            "x-ratelimit-reset-requests":     "rpm_reset",
            "x-ratelimit-limit-tokens":       "tpm_limit",
            "x-ratelimit-remaining-tokens":   "tpm_remaining",
            "x-ratelimit-reset-tokens":       "tpm_reset",
        }
        rl = {alias: resp.headers.get(hdr) for hdr, alias in _RL_HEADERS.items() if resp.headers.get(hdr)}
        if rl:
            usage_out["rate_limits"] = rl
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            if line == "data: [DONE]":
                break
            if not line.startswith("data: "):
                continue
            chunk = json.loads(line[6:])
            # Final usage-only chunk: choices is empty, usage is populated.
            if not chunk.get("choices") and chunk.get("usage"):
                usage_out.update(chunk["usage"])
                continue
            content = ((chunk.get("choices") or [{}])[0].get("delta") or {}).get("content", "")
            if content:
                if "first_token_ms" not in timing_out:
                    timing_out["first_token_ms"] = int((_time.monotonic() - timing_out["start"]) * 1000)
                accumulated.append(content)
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"


def _stream_anthropic(
    session: GameSession,
    messages: list,
    accumulated: list[str],
    usage_out: dict,
    timing_out: dict,
) -> Generator[str, None, None]:
    if _anthropic is None:
        raise RuntimeError(
            "anthropic package is not installed. Run: pip install anthropic"
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Get a key at https://console.anthropic.com"
        )
    # Anthropic SDK requires system prompt at top level, not as a message.
    system_text = next((m["content"] for m in messages if m["role"] == "system"), "")
    non_system = [m for m in messages if m["role"] != "system"]

    # temperature is deprecated for Claude 4+ models.
    _claude4 = bool(re.search(r'claude-\w+-4', session.model))
    _stream_kwargs: dict = {"temperature": session.temperature} if not _claude4 else {}

    client = _anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=session.model,
        system=system_text,
        messages=non_system,
        max_tokens=1024,
        **_stream_kwargs,
    ) as stream:
        for text in stream.text_stream:
            if text:
                if "first_token_ms" not in timing_out:
                    timing_out["first_token_ms"] = int((_time.monotonic() - timing_out["start"]) * 1000)
                accumulated.append(text)
                yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"
        # Capture usage from the final message object.
        final = stream.get_final_message()
        if final and final.usage:
            usage_out["prompt_tokens"] = final.usage.input_tokens
            usage_out["completion_tokens"] = final.usage.output_tokens


# ── Session-end recap generation ──────────────────────────────────────────────

def _parse_scene_npcs_from_boot(boot_path: Path) -> list[str]:
    """Extract NPC names from the '## NPCs Active at Session End' section of boot.md.

    Returns an empty list if the section is absent or the file cannot be read.
    This section is written by stream_end_session so the next session can restore
    scene_npcs without the GM starting cold.
    """
    try:
        text = boot_path.read_text(encoding="utf-8")
    except OSError:
        return []
    names: list[str] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## NPCs Active at Session End":
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):  # next section — stop
                break
            m = re.match(r"^-\s+(.+)", stripped)
            if m:
                names.append(m.group(1).strip())
    return names


def _parse_turns_from_log(log_path: Path) -> list[dict]:
    """Extract only PLAYER and GM turns from the session log.
    Strips system prompt, context injections, LLM payload blocks, and separators.
    Returns list of {"role": "PLAYER"|"GM", "content": str}.
    """
    entries: list[dict] = []
    current_role: Optional[str] = None
    current_lines: list[str] = []
    in_details = False

    _TURN_HEADER = re.compile(r"^### \[\d{2}:\d{2}:\d{2}\] (PLAYER|GM)\s*$")

    def _flush():
        nonlocal current_role, current_lines
        if current_role:
            content = "\n".join(current_lines).strip()
            if content:
                entries.append({"role": current_role, "content": content})
        current_role = None
        current_lines = []

    for line in log_path.read_text(encoding="utf-8").splitlines():
        # Skip <details>…</details> LLM payload blocks
        if "<details" in line:
            _flush()
            in_details = True
            continue
        if "</details>" in line:
            in_details = False
            continue
        if in_details:
            continue

        # Detect PLAYER / GM turn headers
        m = _TURN_HEADER.match(line)
        if m:
            _flush()
            current_role = m.group(1)
            continue

        if current_role:
            # Stop collecting on any structural marker
            if (line.startswith("## ") or line.startswith("# ")
                    or line.startswith("> *[") or line.strip() == "---"):
                _flush()
                continue
            current_lines.append(line)

    _flush()
    return entries


def _enforce_recap_header(text: str, session_number: int) -> str:
    """Guarantee recap.md always starts with the canonical header block.

    The LLM is asked to produce just the body, but if it slips in a header
    anyway we strip it and replace with the canonical form.
    Expected output structure:
        # Session N — [Title]
        *[place] — [date]*
        ---
        [body paragraphs]
        ---
    """
    lines = text.splitlines()

    # Pull the title if the LLM produced one (first # heading)
    title = "Previously…"
    place_date = ""
    body_lines: list[str] = []
    i = 0

    # Skip leading blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1

    if i < len(lines) and lines[i].startswith("# "):
        # LLM produced a heading — extract title after "# Session N — "
        heading = lines[i].strip()
        if " — " in heading:
            title = heading.split(" — ", 1)[1]
        elif heading.startswith("# Session"):
            title = heading[len("# Session"):].strip().lstrip("0123456789").strip().lstrip("— ").strip()
        i += 1

    # Skip blank line after heading
    while i < len(lines) and not lines[i].strip():
        i += 1

    # Pull the italicised place/date line if present
    if i < len(lines) and lines[i].strip().startswith("*") and lines[i].strip().endswith("*"):
        place_date = lines[i].strip()
        i += 1

    # Skip the --- separator the LLM may have added
    while i < len(lines) and lines[i].strip() in ("---", ""):
        i += 1

    # Everything remaining is body — strip trailing --- if present
    body_lines = lines[i:]
    while body_lines and body_lines[-1].strip() in ("---", ""):
        body_lines.pop()

    body = "\n".join(body_lines).strip()

    if not place_date:
        place_date = "*Sandpoint, Varisia — 4707 AR*"

    return f"# Session {session_number} — {title}\n\n{place_date}\n\n---\n\n{body}\n\n---\n"


def _call_blocking(session: GameSession, system: str, user: str) -> str:
    """Single non-streaming LLM call dispatched by provider.

    Used for enemy turns, combat-close narration, and end-of-session recap generation.
    Sends only the given system + user message pair (no session history).
    Writes to outputs/api_log/ so the call is visible in the API Logs panel.
    """
    import time as _time
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    _t0 = _time.monotonic()
    _response_text = ""
    _usage: Optional[dict] = None
    _status = "ok"
    _error: Optional[str] = None
    _raw_request: dict = {}

    try:
        if session.provider == "groq":
            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY environment variable is not set.")
            _raw_request = {
                "model": session.model,
                "messages": messages,
                "stream": False,
                "temperature": 0.5,
                "max_tokens": 2048,
            }
            resp = _groq_post(api_key, _raw_request, stream=False)
            _body = resp.json()
            _response_text = (_body["choices"][0]["message"] or {}).get("content", "").strip()
            _usage_raw = _body.get("usage", {})
            if _usage_raw:
                _usage = {
                    "prompt_tokens":     _usage_raw.get("prompt_tokens", 0),
                    "completion_tokens": _usage_raw.get("completion_tokens", 0),
                    "total_tokens":      _usage_raw.get("total_tokens", 0),
                }

        elif session.provider == "anthropic":
            if _anthropic is None:
                raise RuntimeError("anthropic package is not installed.")
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
            _claude4 = bool(re.search(r'claude-\w+-4', session.model))
            _create_kwargs: dict = {"temperature": 0.5} if not _claude4 else {}
            _raw_request = {
                "model": session.model,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "max_tokens": 2048,
                **_create_kwargs,
            }
            client = _anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(**_raw_request)
            _response_text = (msg.content[0].text if msg.content else "").strip()
            if hasattr(msg, "usage") and msg.usage:
                _usage = {
                    "prompt_tokens":     getattr(msg.usage, "input_tokens", 0),
                    "completion_tokens": getattr(msg.usage, "output_tokens", 0),
                    "total_tokens":      getattr(msg.usage, "input_tokens", 0) + getattr(msg.usage, "output_tokens", 0),
                }

        else:
            _raw_request = {
                "model": session.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.5, "num_ctx": 4096, "num_gpu": session.num_gpu},
            }
            resp = _requests.post(f"{session.host}/api/chat", json=_raw_request, timeout=300)
            resp.raise_for_status()
            _response_text = (resp.json().get("message") or {}).get("content", "").strip()

    except Exception as _exc:
        _status = "error"
        _error = str(_exc)
        raise
    finally:
        _duration_ms = int((_time.monotonic() - _t0) * 1000)
        _section_ok = bool(_HAS_SECTION_MARKERS_RE.search(_response_text)) if _response_text else None
        try:
            write_api_log(
                provider=session.provider,
                session_id=session.id,
                session_number=session.session_number,
                turn=len(session.messages),
                raw_request=_raw_request,
                response_text=_response_text,
                duration_ms=_duration_ms,
                section_format_ok=_section_ok,
                status=_status,
                error=_error,
                usage=_usage,
            )
        except Exception:
            pass  # logging failure must never break the turn

    return _response_text


_ENEMY_TURN_SYSTEM = """You are the Game Master for a Pathfinder 1E campaign: Rise of the Runelords.
Write vivid but brief action narration, then exactly one %%ACTION%% block.
Write ONLY %%NARRATIVE%% then %%ACTION%%. Do NOT write %%COMBAT%%, %%ATTACK%%, %%HP%%, %%ROLL%%, %%GENERATE%%, %%DELTAS%%, or %%EVENT%%.
Do not roll dice, choose AC, alter HP, or update initiative. The backend resolves mechanics after your action choice."""


def _combatant_line_for_enemy_query(c: Combatant, marker: str = "-") -> str:
    cond = f", conditions: {', '.join(c.conditions)}" if c.conditions else ""
    return f"{marker} {c.name}: hp {c.hp_current}/{c.hp_max}, {c.status}{cond}"


def _enemy_action_budget(c: Combatant) -> str:
    conditions = set(c.conditions)
    if c.status != "active":
        return "No actions; this combatant is not active."
    if conditions.intersection({"paralyzed", "helpless", "stunned", "dazed"}):
        return "No meaningful actions; choose delay unless narration only is appropriate."
    if "nauseated" in conditions:
        return "Single move action only; no attacks or spells."
    if "grappled" in conditions or "pinned" in conditions:
        return "Restricted action budget; prefer escape, constrained attack, or delay."
    return "Normal turn: one standard action plus one move action, or one full-round action."


def _find_combatant(session: "GameSession", name: str) -> Optional[Combatant]:
    if session.combat_state is None:
        return None
    for combatant in session.combat_state.combatants:
        if combatant.name.lower() == name.lower():
            return combatant
    return None


def _current_enemy_actor(session: "GameSession", name: Optional[str] = None) -> Optional[Combatant]:
    if session.combat_state is None:
        return None
    if name:
        return _find_combatant(session, name)
    if session.combat_state.current_actor:
        return _find_combatant(session, session.combat_state.current_actor)
    active = [
        c for c in sorted(session.combat_state.combatants, key=lambda x: x.initiative, reverse=True)
        if c.status == "active"
    ]
    return active[0] if active else None


def _build_enemy_turn_system(session: "GameSession", name: str) -> str:
    """Build the system message for one enemy turn: GM identity + full [ENEMY TURN BRIEFING].

    The briefing is authoritative instruction (not a user request), so it belongs in the
    system message for highest LLM compliance.  The user message is a short turn trigger
    built by _build_enemy_turn_user().
    """
    if session.combat_state is None:
        raise ValueError("No active combat")
    actor = _find_combatant(session, name)
    if actor is None:
        raise ValueError(f"Combatant not found: {name}")

    enemies = [c for c in session.combat_state.combatants if not _is_pc_attacker(c.name, session)]
    pcs     = [c for c in session.combat_state.combatants if _is_pc_attacker(c.name, session)]
    allies  = [c for c in enemies if c.name.lower() != actor.name.lower()]

    # ── Zone-aware weapon equip ───────────────────────────────────────────────
    # When no PCs share the actor's zone, ranged is the natural "in-hand" weapon.
    # When PCs are adjacent (same zone), melee is equipped and ranged is available.
    _atk        = actor.attacks if isinstance(actor.attacks, dict) else {}
    _melee      = _atk.get("melee",  [])
    _ranged     = _atk.get("ranged", [])
    _actor_zone = actor.zone if actor.zone else "default"
    _pcs_in_zone = [c for c in pcs if (c.zone if c.zone else "default") == _actor_zone]

    if _melee and _ranged:
        if _pcs_in_zone:
            _equipped, _available = _melee[0], _ranged[0]
        else:
            # No PCs adjacent — ranged weapon is already drawn
            _equipped, _available = _ranged[0], _melee[0]
    elif _melee:
        _equipped, _available = _melee[0], None
    elif _ranged:
        _equipped, _available = _ranged[0], None
    else:
        _equipped, _available = None, None

    _equipped_line  = f"Equipped weapon: {_equipped}" if _equipped else "Equipped weapon: (unarmed)"
    _available_line = f"Available weapon: {_available}" if _available else "Available weapon: (none)"

    # ── Tactic note (future: seeded from event file per-combatant prose) ─────
    _tactic = actor.tactic if hasattr(actor, "tactic") and actor.tactic else "(none)"

    # ── Ally and PC lines ─────────────────────────────────────────────────────
    def _ally_line(c: Combatant) -> str:
        cond = f", conditions: {', '.join(c.conditions)}" if c.conditions else ""
        return f"- {c.name}: {c.status}{cond}"

    def _pc_line(c: Combatant) -> str:
        cond  = f", conditions: {', '.join(c.conditions)}" if c.conditions else ""
        zone  = f", zone: {c.zone}" if c.zone and c.zone != "default" else ""
        return f"- {c.name}: hp {c.hp_current}/{c.hp_max}, {c.status}{cond}{zone}"

    _actor_cond   = f", conditions: {', '.join(actor.conditions)}" if actor.conditions else ""
    _actor_zone_label = f", zone: {_actor_zone}" if _actor_zone != "default" else ""
    _allies_block = "\n".join(_ally_line(c) for c in allies) if allies else "- (none)"
    _pcs_block    = "\n".join(_pc_line(c)   for c in pcs)    if pcs    else "- (none)"

    _known_zones  = session.combat_state.known_zones if session.combat_state.known_zones else []
    _zones_line   = f"Known zones: {', '.join(_known_zones)}" if _known_zones else "Known zones: (none)"

    briefing = f"""[ENEMY TURN BRIEFING]
Round: {session.combat_state.round}
Actor: {actor.name}, {actor.status}{_actor_cond}{_actor_zone_label}
Action budget: {_enemy_action_budget(actor)}
{_equipped_line}
{_available_line}
Tactic: {_tactic}
{_zones_line}

Allies:
{_allies_block}

Player characters:
{_pcs_block}

Choose one tactical action for {actor.name}.
Standard: one standard action (attack/ability) + one move action.
Full-round: full attack (all iterative attacks) or charge.

%%NARRATIVE%%
<1–2 sentences describing what {actor.name} visibly attempts>

%%ACTION%%
action: attack|use_ability|move|delay
action_type: standard|move|full|swift|free|five_foot_step
target: <combatant name if attack or use_ability> | <destination zone name if move — must be from Known zones>
weapon: <weapon name, if attack — must match Equipped or Available weapon>
ability: <ability name, if use_ability>
movement: <brief flavor description of the movement, if move>
if_hit: <one sentence narrating the outcome if the attack hits — e.g. "The blade bites into Vanx's shoulder!">
if_miss: <one sentence narrating the outcome if the attack misses — e.g. "Vanx sidesteps and the blow glances off.">"""

    return f"{_ENEMY_TURN_SYSTEM}\n\n{briefing}"


def _build_enemy_turn_user(session: "GameSession", name: str) -> str:
    """Build the short user-message trigger for one enemy turn.

    Gives the LLM narrative continuity: it knows who acted before this combatant
    and can pick tactically coherent follow-up actions.
    """
    actor = _find_combatant(session, name)
    actor_name = actor.name if actor else name
    round_n = session.combat_state.round if session.combat_state else 1
    if session.last_actor:
        return f"{session.last_actor} just acted. Now it is {actor_name}'s turn."
    return f"Round {round_n} begins. It is {actor_name}'s turn."


def _build_enemy_turn_query(session: "GameSession", name: str) -> str:
    """Backward-compat alias — returns the briefing portion only (for tests)."""
    return _build_enemy_turn_system(session, name)


def _extract_narrative(text: str) -> str:
    sections = _parse_response_sections(text or "")
    raw = sections.get("NARRATIVE", "").strip()
    # _parse_response_sections falls back to storing the entire text as NARRATIVE
    # when no %%NARRATIVE%% marker is present but other markers are.  Detect this
    # by checking whether the "narrative" value itself contains section markers —
    # if so it is raw LLM output that the player should never see.
    if _SECTION_MARKER_RE.search(raw):
        return ""
    return raw


def _get_attack_for_enemy(action: dict, attacker_name: str) -> dict:
    weapon = (action.get("weapon") or "").lower()
    attack_type = "ranged" if any(word in weapon for word in ("bow", "sling", "javelin", "dart")) else "melee"

    # Use bonus/damage if the LLM provided them in the %%ACTION%% block; fall back to
    # generic defaults only when the values are absent or unparseable.
    bonus_raw = (str(action.get("bonus") or "")).strip().lstrip("+")
    if re.match(r"^-?\d+$", bonus_raw):
        bonus = int(bonus_raw)
    else:
        bonus = 4  # generic fallback — Tier 2 will look up per-NPC stats

    damage_raw = (action.get("damage") or "").strip()
    damage = damage_raw if re.fullmatch(r"\d+d\d+([+-]\d+)?", damage_raw) else "1d4"

    return {
        "attacker": attacker_name,
        "target": action.get("target") or "",
        "bonus": bonus,
        "damage": damage,
        "type": attack_type,
    }


def _hp_descriptor(hp_current: int, hp_max: int) -> str:
    """Return a plain-English HP descriptor for the LLM briefing."""
    if hp_max <= 0 or hp_current <= 0:
        return "dying"
    pct = hp_current / hp_max
    if pct > 0.66:
        return "healthy"
    if pct > 0.33:
        return "wounded"
    return "badly wounded"


def _parse_atk_bonus(atk_str: str) -> int:
    """Parse an attack bonus string like '+4' or '-1' into an int."""
    try:
        return int(str(atk_str).replace("+", "").strip())
    except (ValueError, AttributeError):
        return 0


# Maps the UI hint labels to internal action_type values used by stream_pc_turn.
_HINT_TO_ACTION_TYPE: dict[str, str] = {
    "standard": "attack",
    "move":     "move",
    "full":     "attack",   # full-round attack treated as attack for now
}


def _build_session_zone_map(session: "GameSession") -> dict:
    """Return a {lowercase_name: original_name} map of all zones in active combat events.

    Prefer the parsed session.zone_map, then include combatant positions and
    legacy event-table scraping as a compatibility fallback.
    """
    if session.combat_state is None:
        return {}
    _combatant_names_lower = {_c.name.lower() for _c in session.combat_state.combatants}
    _zm: dict = {}
    for _zone_name in session.zone_map.keys():
        if _zone_name:
            _zm[_zone_name.lower()] = _zone_name
    for _zone_name in session.combat_state.known_zones:
        if _zone_name:
            _zm[_zone_name.lower()] = _zone_name
    for _c in session.combat_state.combatants:
        if _c.zone and _c.zone != "default":
            _zm[_c.zone.lower()] = _c.zone
    for _ev in session.active_events:
        _ze = _get_event_index().get(_ev.event_id)
        if _ze and _ze.event_type == "combat":
            import re as _re_z
            _skip = {"zone", "adjacent to", "name", "hp", "ac", "init", "properties", "starting zone"}
            for _zma in _re_z.finditer(r'^\|\s*([A-Za-z][^|]*?)\s*\|', _ze.content, _re_z.MULTILINE):
                _zn = _zma.group(1).strip()
                if (_zn and "---" not in _zn and _zn.lower() not in _skip
                        and len(_zn) > 2 and _zn.lower() not in _combatant_names_lower):
                    _zm[_zn.lower()] = _zn
    return _zm


def _extract_pc_combat_intent(text: str, session: "GameSession", action_type_hint: Optional[str] = None, target_hint: Optional[str] = None, action_type_hints: Optional[list] = None) -> dict:
    """Extract PC combat intent from free-text player input.

    Returns a dict with: actor, action_type, weapon_name, weapon_atk,
    weapon_dmg, weapon_type, target, original_text.

    Fallback rule: anything unparseable → standard attack with equipped
    (first) weapon against a random active enemy. No confirmation prompt.
    """
    if session.combat_state is None:
        return {}

    actor_name = session.combat_state.current_actor or ""
    actor_key  = actor_name.lower()
    profile    = session.pc_profiles.get(actor_key, {})
    weapons    = profile.get("weapons", [])
    text_lower = text.lower()

    # ── Spell detection (checked before weapon matching) ─────────────────
    # Matches any caster's spell list — e.g. Bonnie the Sorcerer's "Magic Missile"
    # or Ani the Warpriest's "Protection from Evil". Not Yanyeeku-specific.
    spells = profile.get("spells", [])
    matched_spell: Optional[dict] = None
    if spells:
        # Direct spell name match (handles "I cast Magic Missile", "fire magic missile", etc.)
        for sp in spells:
            if sp["name"].lower() in text_lower:
                matched_spell = sp
                break
        # Partial word match (e.g. "missile" → "Magic Missile"; min 4 chars to avoid noise)
        # "shoot" and "fire" excluded — those are weapon attack words, not spell triggers.
        if matched_spell is None:
            _cast_words = {"cast", "invoke", "conjure", "launch", "hurl", "use"}
            if any(w in text_lower for w in _cast_words):
                for sp in spells:
                    for part in sp["name"].lower().split():
                        if len(part) >= 4 and part in text_lower:
                            matched_spell = sp
                            break
                    if matched_spell:
                        break

    # Detect unambiguous cast keyword with no spell match → unknown spell.
    # "shoot" and "fire" excluded — they refer to bows/crossbows, not spells.
    if matched_spell is None:
        _cast_words_check = {"cast", "invoke", "conjure", "launch", "hurl"}
        if any(w in text_lower for w in _cast_words_check) and spells:
            # Player tried to cast something; nothing matched. Signal a "spell not found" intent
            # so stream_pc_turn can return a proper error instead of silently falling to weapon.
            return {
                "actor":         actor_name,
                "action_type":   "cast_unknown",
                "spell_name":    "",
                "spell_data":    {},
                "target":        "",
                "original_text": text,
            }

    if matched_spell is not None:
        # Spell intent detected — resolve target.
        is_buff  = matched_spell.get("buff_ac", 0) > 0
        is_heal  = matched_spell.get("is_heal", False)
        all_combatants = session.combat_state.combatants
        all_active     = [c for c in all_combatants if c.status == "active"]
        all_pcs        = [c for c in all_combatants if _is_pc_attacker(c.name, session)]
        active_enemies = [c for c in all_active if not _is_pc_attacker(c.name, session)]

        # Healing spells can target any PC (including unconscious — that's the point).
        # Buff spells target any active combatant. Damage spells target active enemies.
        if is_heal:
            target_pool = all_pcs
        elif is_buff:
            target_pool = all_active
        else:
            target_pool = active_enemies

        spell_target: Optional[Combatant] = None
        for c in target_pool:
            if c.name.lower() in text_lower:
                spell_target = c
                break
        if spell_target is None:
            for c in target_pool:
                for part in c.name.lower().split():
                    if len(part) >= 4 and part in text_lower:
                        spell_target = c
                        break
                if spell_target:
                    break
        # Fallback defaults by spell type.
        if spell_target is None:
            if is_heal:
                # Prefer the most wounded PC; fall back to caster.
                wounded = sorted(
                    [c for c in all_pcs if c.hp_max > 0],
                    key=lambda c: c.hp_current / c.hp_max,
                )
                spell_target = wounded[0] if wounded else next(
                    (c for c in all_pcs if c.name == actor_name), None
                )
            elif is_buff:
                spell_target = next((c for c in all_active if c.name == actor_name), None)
            elif active_enemies:
                import random as _random
                spell_target = _random.choice(active_enemies)

        # ── UI target hint overrides all text inference for spells ────────
        if target_hint:
            _th = next(
                (c for c in session.combat_state.combatants
                 if c.name.lower() == target_hint.lower()),
                None,
            )
            if _th:
                spell_target = _th

        return {
            "actor":         actor_name,
            "action_type":   "cast",
            "spell_name":    matched_spell["name"],
            "spell_data":    matched_spell,
            "target":        spell_target.name if spell_target else "",
            "original_text": text,
        }

    # ── Weapon resolution ────────────────────────────────────────────────
    matched_weapon: Optional[dict] = None
    for w in weapons:
        if w["name"].lower() in text_lower:
            matched_weapon = w
            break
    # Partial / substring match (e.g. "sword" matching "longsword")
    if matched_weapon is None:
        for w in weapons:
            parts = w["name"].lower().split()
            if any(p in text_lower for p in parts if len(p) >= 4):
                matched_weapon = w
                break
    # Fallback: prefer first melee weapon when attack words imply melee; otherwise first weapon.
    if matched_weapon is None and weapons:
        _melee_intent = {"strike", "swing", "hit", "stab", "slash", "smash", "bash", "lunge", "attack"}
        if any(w in text_lower for w in _melee_intent):
            matched_weapon = next((w for w in weapons if w["type"] == "melee"), weapons[0])
        else:
            matched_weapon = weapons[0]

    weapon_name = matched_weapon["name"]  if matched_weapon else "unarmed"
    weapon_atk  = matched_weapon["atk"]   if matched_weapon else "+0"
    weapon_dmg  = matched_weapon["dmg"]   if matched_weapon else "1d3"
    weapon_type = matched_weapon["type"]  if matched_weapon else "melee"

    # ── Action type ───────────────────────────────────────────────────────
    _attack_words  = {"attack", "strike", "swing", "hit", "stab", "shoot",
                      "fire", "slash", "smash", "bash", "charge", "lunge"}
    _move_words    = {"move", "run", "walk", "step", "approach", "retreat",
                      "flee", "position", "go to"}
    _ability_words = {"cast", "use", "activate", "channel", "lay on",
                      "inspire", "rage", "bardic"}
    action_type = "attack"  # default
    for word in _attack_words:
        if word in text_lower:
            action_type = "attack"
            break
    for phrase in _move_words:
        # BUG: guard only checks for the literal word "attack"; words like "strike", "swing"
        # don't protect against a [Moved to: Zone] suffix overriding the intent to "move".
        # Fix: replace "attack" not in text_lower with:
        #   _has_attack_intent = any(w in text_lower for w in _attack_words)
        if phrase in text_lower and "attack" not in text_lower:
            action_type = "move"
            break
    for phrase in _ability_words:
        if phrase in text_lower:
            action_type = "use_ability"
            break

    # ── Apply UI action-type hint(s) ──────────────────────────────────────
    # action_type_hints (list) takes priority over action_type_hint (str).
    # - Non-empty list → use first primary-capable hint for main action_type;
    #                    remaining hints become secondary_actions.
    # - Empty list     → no hint override (keyword inference stands).
    # - None           → fall back to legacy single action_type_hint.
    _PRIMARY_HINT_ORDER = ["standard", "full", "move"]
    secondary_actions: list[dict] = []

    def _build_zone_map() -> dict:
        return _build_session_zone_map(session)

    def _zone_from_text(tl: str) -> str:
        """Find the best matching zone name in player text."""
        _zm = _build_zone_map()
        _best = 0
        _dest = ""
        for _zlow, _zorig in _zm.items():
            if _zlow in tl and len(_zlow) > _best:
                _dest = _zorig
                _best = len(_zlow)
        return _dest

    if action_type_hints is not None:
        if action_type_hints:
            # Primary hint: first of standard/full/move found in the list.
            # swift/free are never primary — always secondary.
            _primary_hint: Optional[str] = None
            for _ph in _PRIMARY_HINT_ORDER:
                if _ph in action_type_hints:
                    _primary_hint = _ph
                    break
            if _primary_hint and _primary_hint in _HINT_TO_ACTION_TYPE:
                if _primary_hint == "move" or action_type not in ("use_ability", "cast"):
                    action_type = _HINT_TO_ACTION_TYPE[_primary_hint]
            # Remaining hints become secondary actions
            for _h in action_type_hints:
                if _h != _primary_hint:
                    secondary_actions.append({"type": _h})
        # else: empty list → no hint override; keyword inference stands
    elif action_type_hint and action_type_hint in _HINT_TO_ACTION_TYPE:
        # Legacy single-hint path (backward compat)
        if action_type_hint == "move" or action_type not in ("use_ability", "cast"):
            action_type = _HINT_TO_ACTION_TYPE[action_type_hint]

    # ── Target resolution ─────────────────────────────────────────────────
    active_enemies = [
        c for c in session.combat_state.combatants
        if c.status == "active" and not _is_pc_attacker(c.name, session)
    ]
    matched_target: Optional[Combatant] = None
    # Full name match first
    for c in active_enemies:
        if c.name.lower() in text_lower:
            matched_target = c
            break
    # Partial match (e.g. "goblin" matching "Goblin Warrior 1")
    if matched_target is None:
        for c in active_enemies:
            for part in c.name.lower().split():
                if len(part) >= 4 and part in text_lower:
                    matched_target = c
                    break
            if matched_target:
                break
    # Fallback to first active enemy
    if matched_target is None and active_enemies:
        import random as _random
        matched_target = _random.choice(active_enemies)

    target_name = matched_target.name if matched_target else ""

    # ── UI target hint overrides all text inference ───────────────────────────
    if target_hint:
        target_name = target_hint

    # ── Destination zone (primary move action) ────────────────────────────────
    destination_zone = ""
    if action_type == "move":
        destination_zone = _zone_from_text(text_lower)

    # Populate destination_zone in any secondary move actions
    for _sa in secondary_actions:
        if _sa["type"] == "move":
            _sa["destination_zone"] = _zone_from_text(text_lower)

    return {
        "actor":             actor_name,
        "action_type":       action_type,
        "weapon_name":       weapon_name,
        "weapon_atk":        weapon_atk,
        "weapon_dmg":        weapon_dmg,
        "weapon_type":       weapon_type,
        "target":            target_name,
        "destination_zone":  destination_zone,
        "secondary_actions": secondary_actions,
        "available_zones":   sorted(_build_zone_map().values()),
        "original_text":     text,
    }


def stream_enemy_turn(session: GameSession, name: Optional[str] = None) -> Generator[str, None, None]:
    """Run one focused enemy turn and let the backend resolve mechanics."""
    actor = _current_enemy_actor(session, name)
    if session.combat_state is None or actor is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No active enemy turn'})}\n\n"
        return
    if _is_pc_attacker(actor.name, session):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Current actor is a PC'})}\n\n"
        return

    system   = _build_enemy_turn_system(session, actor.name)
    user_msg = _build_enemy_turn_user(session, actor.name)
    try:
        response = _call_blocking(session, system, user_msg)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Enemy turn failed: {e}'})}\n\n"
        return

    narrative = _extract_narrative(response)
    action    = _parse_action_block(response)

    # Log the chosen action so AC-007 test and devs can see action_type in the session log.
    if action:
        _log(session, f"\n> *[Enemy action parsed: {actor.name} — {action.get('action', '?')} (action_type: {action.get('action_type', 'standard')})]*\n")

    # B-C04: warn when the LLM wrote unexpected sections (%%COMBAT%%, %%ATTACK%%, etc.)
    _unexpected_sections = _SECTION_MARKER_RE.findall(response)
    _allowed = {"NARRATIVE", "ACTION"}
    _bad = [s for s in _unexpected_sections if s not in _allowed]
    if _bad:
        _log(session, f"\n> *[Enemy turn warning: LLM wrote unexpected sections {_bad} — ignored]*\n")
        if session.dev_mode:
            yield f"data: {json.dumps({'type': 'token', 'content': f'[DEV WARNING: unexpected sections {_bad} in enemy turn response — only %%NARRATIVE%% and %%ACTION%% are processed]'})}\n\n"

    # CB1.9-2: validate chosen weapon against combatant's seeded attack profile.
    # If the LLM hallucinated a weapon, fall back to the first known one and log a warning.
    if action and action.get("action") == "attack" and actor is not None:
        _chosen = (action.get("weapon") or "").lower().strip()
        _atk    = actor.attacks if isinstance(actor.attacks, dict) else {}
        _known  = [w.lower() for w in _atk.get("melee", []) + _atk.get("ranged", [])]
        if _known and _chosen not in _known:
            _fallback = (_atk.get("melee") or _atk.get("ranged") or [None])[0]
            if _fallback:
                _log(session, f"\n> *[CB1.9-2: weapon '{_chosen}' not in profile — using '{_fallback}']*\n")
                action = {**action, "weapon": _fallback}

    # Apply zone move before narrating so combat_update sees the updated position
    if action and action.get("action") == "move" and action.get("target"):
        _dest_raw = action["target"].strip()
        _known_z  = {z.lower(): z for z in (session.combat_state.known_zones or [])}
        _canonical_z = _known_z.get(_dest_raw.lower(), "")
        if _canonical_z:
            _apply_actor_zone_change(session, _slugify(actor.name), _canonical_z)
        else:
            _log(session, f"\n> *[Zone move ignored: '{_dest_raw}' not in known zones {list(_known_z.values())}]*\n")

    # Resolve the attack before building the visible message so we know hit/miss
    result: Optional[dict] = None
    if action and action.get("action") == "attack" and action.get("target"):
        attack = _get_attack_for_enemy(action, actor.name)
        result = _resolve_npc_attack(attack, session)

    # Build the outcome sentence from the LLM's pre-authored branches
    outcome = ""
    if result is not None:
        outcome = action.get("if_hit", "") if result["hit"] else action.get("if_miss", "")

    # Combine narrative + outcome into a single player-facing message
    full_narrative = narrative
    if outcome:
        full_narrative = f"{narrative}\n\n{outcome}" if narrative else outcome

    # Action card — emitted BEFORE narrative so the player sees the mechanical
    # outcome first (centered combat-event card in the chat), then reads the flavor.
    if result is not None:
        _at = action.get("action_type", "standard") if action else "standard"
        yield f"data: {json.dumps({'type': 'action_card', 'action_type': _at, **result})}\n\n"

    # Dev mode: stream full raw response (all %%MARKERS%% visible) with the resolved
    # outcome injected before %%ACTION%% so the developer can see which branch was chosen.
    if session.dev_mode:
        dev_response = response
        if outcome:
            label = "[HIT]" if (result and result.get("hit")) else "[MISS]"
            annotation = f"\n\n{label} {outcome}"
            # Insert just before %%ACTION%% so markers remain intact below
            dev_response = response.replace("\n\n%%ACTION%%", f"{annotation}\n\n%%ACTION%%", 1)
        yield f"data: {json.dumps({'type': 'token', 'content': dev_response})}\n\n"
        session.messages.append({"role": "assistant", "content": dev_response})
    else:
        if full_narrative:
            yield f"data: {json.dumps({'type': 'token', 'content': full_narrative})}\n\n"
            session.messages.append({"role": "assistant", "content": full_narrative})

    if result is not None:
        yield f"data: {json.dumps({'type': 'attack_result', **result})}\n\n"

    # Advance to the next combatant automatically — no manual "Next Turn" click needed
    try:
        advance_combat_turn(session)
    except ValueError:
        _write_session_state(session)  # fallback if advance fails
    yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def stream_pc_turn(session: GameSession, player_text: str, action_type_hint: Optional[str] = None, target_hint: Optional[str] = None, action_type_hints: Optional[list] = None) -> Generator[str, None, None]:
    """Handle a PC combat turn: extract intent, queue attack from profile, prompt dice.

    No LLM call is made here — the attack is queued from the PC's actual weapon stats.
    The narration happens later in _stream_pc_turn_narration (called from stream_resume_combat).
    """
    if session.combat_state is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No active combat'})}\n\n"
        return

    # Refresh known zones from event files so zone chips are always up-to-date.
    _zone_map = _build_session_zone_map(session)
    if _zone_map:
        session.combat_state.known_zones = sorted(_zone_map.values())

    intent = _extract_pc_combat_intent(player_text, session, action_type_hint, target_hint, action_type_hints)
    if not intent:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Could not resolve PC turn intent'})}\n\n"
        return

    if intent.get("action_type") == "cast_unknown":
        actor = intent.get("actor", "The character")
        msg = f"{actor} doesn't know that spell."
        yield f"data: {json.dumps({'type': 'attention', 'message': msg})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # Append the player's original text to message history
    session.messages.append({"role": "user", "content": player_text})

    if intent["action_type"] == "attack":
        if not intent["target"]:
            # No active enemies — can't attack
            yield f"data: {json.dumps({'type': 'error', 'message': 'No active enemies to attack. All foes may be defeated or fled.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # Queue the attack from profile data — not from LLM-generated bonus/damage
        bonus = _parse_atk_bonus(intent["weapon_atk"])
        session.attack_queue.append(PendingAttack(
            attacker=intent["actor"],
            target=intent["target"],
            bonus=bonus,
            damage_expr=intent["weapon_dmg"],
            attack_type=intent["weapon_type"],
            is_pc=True,
        ))
        session._pending_pc_narration = intent
        # Build log suffix for secondary actions (swift/free/move)
        _secondary = intent.get("secondary_actions", [])
        _sec_types = [a["type"] for a in _secondary]
        _sec_suffix = f" + {', '.join(_sec_types)}" if _sec_types else ""
        _log(session,
             f"\n> *[PC turn: {intent['actor']} → {intent['target']} "
             f"with {intent['weapon_name']} ({intent['weapon_atk']}, {intent['weapon_dmg']}){_sec_suffix}]*\n")

        # Apply any secondary move action before emitting attack_request so the LLM
        # narration (via _stream_pc_turn_narration) sees the updated zone.
        for _sa in _secondary:
            if _sa["type"] == "move":
                _dest = _sa.get("destination_zone", "")
                if _dest:
                    _mover = next(
                        (c for c in session.combat_state.combatants
                         if c.name.lower() == intent["actor"].lower()), None
                    )
                    if _mover:
                        _old_zone = _mover.zone
                        _mover.zone = _dest
                        _log(session, f"\n> *[Zone move: {intent['actor']} {_old_zone} → {_dest}]*\n")
                        _write_session_state(session)
                        yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
                # If no zone recognised, silently skip — don't block the attack

        # Emit attack_request to activate the dice tray
        target_ac = _get_combatant_ac(intent["target"], session.combat_state)
        yield f"data: {json.dumps({'type': 'attack_request', 'attacker': intent['actor'], 'target': intent['target'], 'bonus': bonus, 'ac': target_ac, 'damage_expr': intent['weapon_dmg'], 'attack_type': intent['weapon_type']})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    elif intent["action_type"] == "cast":
        spell = intent.get("spell_data", {}) or {}
        if not intent.get("target"):
            yield f"data: {json.dumps({'type': 'error', 'message': 'No valid target for spell.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        if spell.get("auto_hit") and spell.get("damage_expr"):
            # Auto-hit damage spell (e.g. Magic Missile, or any spell with "never misses"
            # in its effect text). Pre-set hit=True to skip the attack roll phase entirely.
            session.attack_queue.append(PendingAttack(
                attacker=intent["actor"],
                target=intent["target"],
                bonus=0,
                damage_expr=spell["damage_expr"],
                attack_type="spell",
                is_pc=True,
                is_spell=True,
                spell_name=spell["name"],
                hit=True,
                hit_roll=0,
                hit_total=0,
            ))
            session._pending_pc_narration = intent
            _log(session,
                 f"\n> *[PC spell: {intent['actor']} → {intent['target']} "
                 f"{spell['name']} ({spell['damage_expr']}, auto-hit)]*\n")
            yield f"data: {json.dumps({'type': 'damage_request', 'caster': intent['actor'], 'target': intent['target'], 'spell_name': spell['name'], 'damage_expr': spell['damage_expr']})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        elif spell.get("buff_ac", 0) > 0:
            # Self-buff AC spell (e.g. Shield: +4 shield bonus, 10 rounds). No dice.
            caster = next(
                (c for c in session.combat_state.combatants if c.name == intent["actor"]),
                None,
            )
            if caster is not None:
                _apply_ac_effect(caster, spell["name"], spell.get("buff_type", "untyped"), spell["buff_ac"], rounds=10)
            _log(session,
                 f"\n> *[PC spell: {intent['actor']} casts {spell['name']} "
                 f"(+{spell['buff_ac']} shield AC, 10 rounds)]*\n")
            # Emit combat_update immediately — effect is already applied to the combatant.
            yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
            system   = _build_pc_turn_system(session, intent, {})
            user_msg = intent.get("original_text", "")
            try:
                response = _call_blocking(session, system, user_msg)
                if session.dev_mode:
                    yield f"data: {json.dumps({'type': 'token', 'content': response})}\n\n"
                    session.messages.append({"role": "assistant", "content": response})
                else:
                    narrative = _extract_narrative(response)
                    if narrative:
                        session.messages.append({"role": "assistant", "content": narrative})
                        yield f"data: {json.dumps({'type': 'token', 'content': narrative})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Spell narration failed: {e}'})}\n\n"
            try:
                advance_combat_turn(session)
            except ValueError:
                _write_session_state(session)
            yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        elif spell.get("is_heal") and spell.get("healing_expr"):
            # Healing spell (Cure Light Wounds, etc.). Auto-hits willing allies.
            # Queue with is_heal=True so resolve_damage_roll applies a positive delta.
            session.attack_queue.append(PendingAttack(
                attacker=intent["actor"],
                target=intent["target"],
                bonus=0,
                damage_expr=spell["healing_expr"],
                attack_type="heal",
                is_pc=True,
                is_spell=True,
                is_heal=True,
                spell_name=spell["name"],
                hit=True,
                hit_roll=0,
                hit_total=0,
            ))
            session._pending_pc_narration = intent
            _log(session,
                 f"\n> *[PC spell: {intent['actor']} casts {spell['name']} "
                 f"({spell['healing_expr']}, heal target={intent['target']})]*\n")
            yield f"data: {json.dumps({'type': 'heal_request', 'caster': intent['actor'], 'target': intent['target'], 'spell_name': spell['name'], 'damage_expr': spell['healing_expr']})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        else:
            # Non-auto-hit or non-damage spell — narrate immediately without dice.
            _log(session, f"\n> *[PC spell: {intent['actor']} casts {spell.get('name', 'spell')} (no damage dice)]*\n")
            system   = _build_pc_turn_system(session, intent, {})
            user_msg = intent.get("original_text", "")
            try:
                response = _call_blocking(session, system, user_msg)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Spell narration failed: {e}'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            if session.dev_mode:
                yield f"data: {json.dumps({'type': 'token', 'content': response})}\n\n"
                session.messages.append({"role": "assistant", "content": response})
            else:
                narrative = _extract_narrative(response)
                if narrative:
                    session.messages.append({"role": "assistant", "content": narrative})
                    yield f"data: {json.dumps({'type': 'token', 'content': narrative})}\n\n"
            try:
                advance_combat_turn(session)
            except ValueError:
                _write_session_state(session)
            yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    else:
        # Non-attack actions (move, use_ability, delay).
        # No dice to roll — narrate immediately in this stream rather than waiting for resume_combat.
        _log(session, f"\n> *[PC turn: {intent['actor']} action={intent['action_type']}]*\n")

        # Apply zone movement before narrating so the LLM sees the updated state
        if intent.get("action_type") == "move":
            _dest = intent.get("destination_zone", "")
            _zone_names = intent.get("available_zones", [])
            if not _dest and _zone_names:
                # Zones are defined but destination wasn't recognised — surface a warning.
                # Only triggered when the session has a zone map; when no zones are configured
                # (test sessions, out-of-zone-combat) fall through to normal narration.
                _actor_name = intent["actor"]
                _zones_hint = ", ".join(_zone_names)
                yield f"data: {json.dumps({'type': 'attention', 'message': f'{_actor_name} — zone not recognised. Available zones: {_zones_hint}.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return  # don't advance the turn — player can try again with a valid zone
            elif _dest:
                _mover = next((c for c in session.combat_state.combatants
                               if c.name.lower() == intent["actor"].lower()), None)
                if _mover:
                    _old_zone = _mover.zone
                    _mover.zone = _dest
                    _log(session, f"\n> *[Zone move: {intent['actor']} {_old_zone} → {_dest}]*\n")
                    _write_session_state(session)
                    # Emit the updated state immediately so the UI reflects the move
                    yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"

        system   = _build_pc_turn_system(session, intent, {})
        user_msg = intent.get("original_text", "")
        try:
            response = _call_blocking(session, system, user_msg)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'PC turn narration failed: {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        narrative = _extract_narrative(response)
        if narrative:
            session.messages.append({"role": "assistant", "content": narrative})
            yield f"data: {json.dumps({'type': 'token', 'content': narrative})}\n\n"
        try:
            advance_combat_turn(session)
        except ValueError:
            _write_session_state(session)
        yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _build_combat_close_directive(session: "GameSession") -> str:
    """Build the focused close-combat instruction with the current snapshot."""
    if session.combat_state is None:
        raise ValueError("No active combat")
    rows = "\n".join(
        f"- {c.name}: hp {c.hp_current}/{c.hp_max}, status {c.status}, conditions {', '.join(c.conditions) if c.conditions else 'none'}"
        for c in sorted(session.combat_state.combatants, key=lambda x: x.initiative, reverse=True)
    )
    return f"""Close the combat scene in one short narrative beat.

Round: {session.combat_state.round}
Current actor: {session.combat_state.current_actor or 'none'}
Combatants:
{rows}

Write only player-facing narrative. Do not write %%COMBAT%%, %%ATTACK%%, %%ACTION%%, %%HP%%, %%ROLL%%, %%DELTAS%%, or %%EVENT%%."""


def stream_close_combat(session: GameSession) -> Generator[str, None, None]:
    """Narrate combat closure, then clear combat state even if narration fails."""
    if session.combat_state is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No active combat'})}\n\n"
        return

    try:
        response = _call_blocking(session, "You close a Pathfinder combat scene briefly.", _build_combat_close_directive(session))
        narrative = _extract_narrative(response)
        if narrative:
            session.messages.append({"role": "assistant", "content": narrative})
            yield f"data: {json.dumps({'type': 'token', 'content': narrative})}\n\n"
    except Exception:
        pass

    session.combat_state = None
    session.attack_queue = []
    session.attack_results = []
    _write_session_state(session)
    yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': None})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


_PC_TURN_SYSTEM = """You are the Game Master for a Pathfinder 1E campaign: Rise of the Runelords.
Begin your response with the EXACT literal line:
%%NARRATIVE%%
Then write 2–5 sentences of vivid action narration.
Write ONLY the %%NARRATIVE%% section. Do NOT write %%ACTION%%, %%COMBAT%%, %%ATTACK%%, %%ROLL%%, %%GENERATE%%, %%DELTAS%%, or %%EVENT%%.
Do not mention dice numbers, bonuses, or AC values. The backend has already resolved all mechanics."""


def _build_pc_turn_system(session: "GameSession", intent: dict, result: dict) -> str:
    """Build the focused system message for PC turn narration.

    The roll outcome is already known — the LLM just writes the story.
    """
    actor_name  = intent.get("actor", "")
    target_name = intent.get("target", "")
    hit         = result.get("hit", False)
    damage      = result.get("damage_total", 0)

    if intent.get("action_type") == "cast":
        spell = intent.get("spell_data", {}) or {}
        buff_ac = spell.get("buff_ac", 0)
        is_heal = result.get("is_heal") or spell.get("is_heal", False)
        if is_heal:
            outcome_line = (
                f"Spell: {spell.get('name', 'Unknown')} ({spell.get('school', 'unknown school')}, healing touch)\n"
                f"Healed: {damage} hp → {target_name}"
            )
        elif buff_ac > 0:
            outcome_line = (
                f"Spell: {spell.get('name', 'Unknown')} ({spell.get('school', 'unknown school')}, "
                f"self-buff: +{buff_ac} shield bonus to AC, 10 rounds)"
            )
        elif damage:
            outcome_line = (
                f"Spell: {spell.get('name', 'Unknown')} ({spell.get('school', 'unknown school')}, auto-hit)\n"
                f"Damage: {damage}"
            )
        else:
            outcome_line = (
                f"Spell: {spell.get('name', 'Unknown')} ({spell.get('school', 'unknown school')})"
            )
    else:
        roll  = result.get("roll", 0)
        bonus = result.get("bonus", 0)
        total = result.get("total", 0)
        ac    = result.get("ac", 0)
        sign  = f"+{bonus}" if bonus >= 0 else str(bonus)
        outcome_line = (
            f"To hit: 1d20 {sign} = {total} vs AC {ac} → HIT\nDamage: {damage}"
            if hit else
            f"To hit: 1d20 {sign} = {total} vs AC {ac} → MISS"
        )

    # Build combatant blocks
    pcs      = [c for c in (session.combat_state.combatants if session.combat_state else [])
                if _is_pc_attacker(c.name, session)]
    enemies  = [c for c in (session.combat_state.combatants if session.combat_state else [])
                if not _is_pc_attacker(c.name, session)]

    def _pc_line(c: Combatant) -> str:
        return f"- {c.name}: hp {c.hp_current}/{c.hp_max}, {_hp_descriptor(c.hp_current, c.hp_max)}"

    def _enemy_line(c: Combatant) -> str:
        return f"- {c.name}: {c.status}, {_hp_descriptor(c.hp_current, c.hp_max)}"

    # Target descriptor (after damage applied)
    target_combatant = next((c for c in enemies if c.name == target_name), None)
    target_desc = _hp_descriptor(target_combatant.hp_current, target_combatant.hp_max) \
        if target_combatant else "active"

    briefing = f"""[PC TURN BRIEFING]
Actor: {actor_name}
Target: {target_name} ({target_desc})
{outcome_line}

PCs:
{chr(10).join(_pc_line(c) for c in pcs) if pcs else "- (none)"}

Enemies:
{chr(10).join(_enemy_line(c) for c in enemies) if enemies else "- (none)"}"""

    return f"{_PC_TURN_SYSTEM}\n\n{briefing}"


def _stream_pc_turn_narration(session: GameSession) -> Generator[str, None, None]:
    """Narrate the outcome of a resolved PC combat turn.

    Called from stream_resume_combat when session._pending_pc_narration is set.
    The roll result is already known — no if_hit/if_miss branching needed.
    Emits action_card BEFORE the narrative token (mirrors enemy turn ordering).
    """
    intent = session._pending_pc_narration
    session._pending_pc_narration = None

    # Use most recent attack result if available
    result: dict = session.attack_results[-1] if session.attack_results else {}
    session.attack_results = []

    system   = _build_pc_turn_system(session, intent, result)
    user_msg = intent.get("original_text", "")

    try:
        response = _call_blocking(session, system, user_msg)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'PC turn narration failed: {e}'})}\n\n"
        return

    # Warn if LLM wrote unexpected sections (B-C04 parity with enemy turns)
    _unexpected = [s for s in _SECTION_MARKER_RE.findall(response) if s not in {"NARRATIVE"}]
    if _unexpected:
        _log(session, f"\n> *[PC turn narration warning: LLM wrote unexpected sections {_unexpected} — ignored]*\n")
        if session.dev_mode:
            yield f"data: {json.dumps({'type': 'token', 'content': f'[DEV WARNING: unexpected sections {_unexpected} in PC narration response]'})}\n\n"

    # Action card BEFORE narrative (emitted regardless of dev mode)
    if result:
        yield f"data: {json.dumps({'type': 'action_card', **result})}\n\n"

    # Dev mode: stream full raw response so all markers are visible
    if session.dev_mode:
        yield f"data: {json.dumps({'type': 'token', 'content': response})}\n\n"
        session.messages.append({"role": "assistant", "content": response})
    else:
        narrative = _extract_narrative(response)
        if narrative:
            session.messages.append({"role": "assistant", "content": narrative})
            yield f"data: {json.dumps({'type': 'token', 'content': narrative})}\n\n"

    # Auto-advance to next combatant
    try:
        advance_combat_turn(session)
    except ValueError:
        _write_session_state(session)
    yield f"data: {json.dumps({'type': 'combat_update', 'combat_state': _serialize_combat_state(session.combat_state)})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def stream_resume_combat(session: GameSession) -> Generator[str, None, None]:
    """Inject resolved attack results into history, then call LLM to narrate outcomes.

    Called after all PC attack dice have been resolved (attack_queue is empty).
    Clears attack_results after injection.  Streams the same SSE events as stream_turn.
    """
    # Defensively clear any stale pending-attack entries.  Resume is only triggered
    # when the frontend believes the queue is drained; anything left is an orphaned
    # entry from a previous LLM response that wrote %%ATTACK%% blocks during narration.
    if session.attack_queue:
        _log(session, f"\n> *[Combat resume: clearing {len(session.attack_queue)} stale attack-queue entries]*\n")
        session.attack_queue = []

    # PC combat action path — focused narration with known outcome
    if session._pending_pc_narration:
        _log(session, "\n> *[Combat resume: PC turn narration path]*\n")
        yield from _stream_pc_turn_narration(session)
        return

    round_num = session.combat_state.round if session.combat_state else 0
    history_msg = _build_attack_history_message(session.attack_results, round_num)
    session.messages.append({"role": "user", "content": history_msg})
    _log(session, f"\n> *[Combat resume: injecting {len(session.attack_results)} attack result(s)]*\n")
    session.attack_results = []
    # Delegate to the main turn streamer — the attack results message is already
    # appended to session.messages, so the LLM sees them as the latest user turn.
    # Set the flag so _stream_chat auto-advances to the next combatant before emitting
    # the final combat_update (mirrors stream_enemy_turn's auto-advance).
    session._advance_combat_after_stream = True
    yield from _stream_chat(session)


def stream_end_session(session: GameSession) -> Generator[str, None, None]:
    """Generate recap + boot files, save session, stream status events to caller."""

    def _status(msg: str) -> str:
        return f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"

    # ── 1. Parse turns ────────────────────────────────────────────────────────
    yield _status("Parsing session log…")
    if session.log_path is None or not session.log_path.exists():
        yield f"data: {json.dumps({'type': 'error', 'message': 'No log file found'})}\n\n"
        return

    turns = _parse_turns_from_log(session.log_path)
    if not turns:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No PLAYER/GM turns found in log'})}\n\n"
        return

    transcript = "\n\n".join(
        f"**{t['role']}:** {t['content']}" for t in turns
    )
    n = session.session_number
    next_n = n + 1

    # ── 2. Generate player-facing recap (intro card for next session) ─────────
    yield _status("Generating session recap…")
    recap_system = (
        "You are a skilled tabletop RPG chronicler writing for Pathfinder 1st Edition. "
        "Write only what is requested. No meta-commentary, no out-of-character notes."
    )
    recap_user = f"""Below is the full transcript of Session {n} of Rise of the Runelords.

TRANSCRIPT:
{transcript}

Write a player-facing session recap. This will be shown to players as an intro card at the start of Session {next_n}.

Output format — produce exactly these parts in order:
1. A single line: # Session {n} — [short evocative title of 3-5 words]
2. A single italicised line with place and in-world date, e.g.: *Sandpoint, Varisia — 1st of Lamashan, 4707 AR*
3. A line containing only: ---
4. 4–6 paragraphs of atmospheric prose body
5. A final line containing only: ---

Prose rules:
- Second person ("you", "the party")
- Describe only what the characters experienced — no GM meta-commentary
- Name specific characters, NPCs, and locations that appeared
- End the body on the situation as it stood when the session ended
- No bullet points. No subheadings beyond the title line."""

    try:
        recap_text = _call_blocking(session, recap_system, recap_user)
        err = validate_generated_text(recap_text, "Recap", min_length=120)
        if err:
            yield f"data: {json.dumps({'type': 'error', 'message': err})}\n\n"
            return
        recap_text = _enforce_recap_header(recap_text, n)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Recap generation failed: {e}'})}\n\n"
        return

    # ── 3. Generate GM-facing boot context for next session ───────────────────
    yield _status("Generating GM boot context…")
    boot_system = (
        "You are a precise tabletop RPG game-master assistant. "
        "Write only structured markdown as specified. No prose, no commentary."
    )
    boot_user = f"""Below is the full transcript of Session {n} of Rise of the Runelords.

TRANSCRIPT:
{transcript}

Write a GM-facing boot context document for Session {next_n}. This is loaded into the GM's system prompt at session start.

Produce exactly these sections in this order:

# Session {next_n} Boot Context

## Scene State
(bullet list — Act, Scene, Location, Time, Weather, Area state)

## What Is Happening Right Now
(2–4 sentences — the immediate situation the party is in as Session {next_n} begins)

## Who Is Present
(bullet list — named NPCs and their current disposition/status)

## Party Status
(1–2 sentences — party condition, where they are, any immediate pressures)

## What the GM Must Not Do in This Scene
(bullet list — specific constraints based on where the session ended)

Be factual and precise. Base everything strictly on the transcript."""

    try:
        boot_text = _call_blocking(session, boot_system, boot_user)
        err = validate_generated_text(boot_text, "Boot context", min_length=80)
        if err:
            yield f"data: {json.dumps({'type': 'error', 'message': err})}\n\n"
            return
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Boot generation failed: {e}'})}\n\n"
        return

    # ── 4. Write files ────────────────────────────────────────────────────────
    yield _status("Writing session files…")
    sessions_dir = _REPO_ROOT / "sessions"

    recap_path = sessions_dir / f"session_{n:03d}" / "recap.md"
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text(recap_text, encoding="utf-8")

    # Append active scene_npcs so create_session can restore them next boot.
    if session.scene_npcs:
        boot_text += (
            "\n\n## NPCs Active at Session End\n"
            + "\n".join(f"- {name}" for name in session.scene_npcs)
        )

    boot_path = sessions_dir / f"session_{next_n:03d}" / "boot.md"
    boot_path.parent.mkdir(parents=True, exist_ok=True)
    boot_path.write_text(boot_text, encoding="utf-8")

    _log(session, f"\n## Recap generated → {recap_path.relative_to(_REPO_ROOT)}")
    _log(session, f"## Boot generated  → {boot_path.relative_to(_REPO_ROOT)}\n")

    # ── 5. Save session ───────────────────────────────────────────────────────
    yield _status("Saving session…")
    saved_to = save_session(session)

    yield f"data: {json.dumps({'type': 'done', 'recap_path': str(recap_path), 'boot_path': str(boot_path), 'saved_to': str(saved_to)})}\n\n"
