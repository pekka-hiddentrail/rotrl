from __future__ import annotations

import json
import os
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
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on env vars being set externally

from api.context.npc_lookup import NpcIndex
from api.context.skill_lookup import SkillIndex
from api.api_logger import write_api_log
from api.npc_generator import generate_base_md, slugify as _slugify

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTPUTS_DIR = _REPO_ROOT / "outputs"

# Context indexes — built lazily on first use, shared across all sessions
_npc_index: Optional[NpcIndex] = None
_skill_index: Optional[SkillIndex] = None


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


def _invalidate_npc_index() -> None:
    """Force the NPC index to reload on next use.

    Called after a new NPC stub is created mid-session so that subsequent
    %%DELTAS%% writes and keyword detection find the new entry immediately.
    """
    global _npc_index
    _npc_index = None

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MAX_RETRIES = 4
_GROQ_RETRY_BASE = 5.0  # seconds — doubled each attempt


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
_DEV_MAX_HISTORY   = 6   # 3 exchanges
_FULL_MAX_HISTORY  = 30  # 15 exchanges — Ollama (local, no payload limit)
_GROQ_MAX_HISTORY  = 10  # 5 exchanges  — Groq (cloud, tighter payload limit)
_DEV_MAX_TOKENS    = 180  # cap generation length in dev mode
# Groq: hard ceiling on the system prompt character count.
# Injected context chunks beyond this point are silently dropped.
# ~30 000 chars ≈ 7 500 tokens — keeps all early context (base + Critical +
# Act Overview + Adjudication) and trims only the later/lower-priority chunks.
_GROQ_MAX_SYSTEM_CHARS = 30_000

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

# Detect whether the response uses section markers at all (vs old flat format).
_HAS_SECTION_MARKERS_RE = re.compile(r'^%%(?:NARRATIVE|ROLL|DELTAS|GENERATE)%%', re.MULTILINE)

# ── Narrative name detection ──────────────────────────────────────────────────
# Used to catch NPCs the LLM introduces in prose without any structured block.
# Detected names are added to session.scene_npcs so the NEXT turn's directive
# asks for a %%DELTAS%% block — stub creation happens via Layer 2 at that point.
#
# Requires ≥3 chars per word so sentence-starting words like "As", "He", "In"
# never produce a match.
_NARRATIVE_NAME_RE = re.compile(r'\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b')

# Words that appear capitalised in prose but are NOT person names.
# If EITHER word of a candidate pair is in this set, the pair is skipped.
_NAME_EXCLUDE_WORDS: frozenset[str] = frozenset({
    # Titles / honorifics
    "mayor", "sheriff", "father", "mother", "brother", "sister",
    "lord", "lady", "master", "captain", "sergeant", "doctor",
    "mister", "mistress", "dame", "sir",
    "baron", "duke", "earl", "count", "prince", "princess", "king", "queen",
    # Place-type words
    "square", "hall", "street", "road", "lane", "alley", "avenue",
    "cathedral", "temple", "church", "shrine",
    "inn", "tavern", "lodge",
    "gate", "bridge", "market", "district", "quarter",
    "tower", "keep", "castle", "fort",
    # Campaign / setting proper nouns that are not NPC names
    "rise", "runelords", "varisia", "sandpoint", "desna",
    "festival", "swallowtail", "lost", "coast",
    "burnt", "offerings", "pathfinder",
    # Common sentence-start words
    "what", "who", "where", "when", "why", "how",
    "this", "that", "these", "those",
})


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
        sections[parts[i].strip()] = parts[i + 1].strip()
        i += 2
    if "NARRATIVE" not in sections:
        sections["NARRATIVE"] = text.strip()
    return sections


def _parse_bracket_blocks(text: str) -> list[dict]:
    """Extract [ … ] blocks from section text and parse each as key:value fields.

    Opening ``[`` and closing ``]`` must each appear on their own line.
    Multiple ``knowledge:`` lines within a block are collected into a list so
    that all knowledge items are preserved (the field dict maps "knowledge" →
    list[str] rather than a single string).
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

    ts_now = datetime.now().strftime("%H:%M:%S")

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


_ROLL_BLOCK_RE = re.compile(
    r'\s*%%ROLL%%\s*\n'
    r'(?:skill:\s*)?(?P<skill>[^\n:]+?)(?:\s*:\s*\d+)?\s*\n'
    r'dc:\s*(?P<dc>\d+)\s*\n'
    r'success:\s*(?P<success>[^\n]+)\n'
    r'failure:\s*(?P<failure>[^\n]+)\n?'   # trailing newline optional (last line)
    r'(?:%%END%%\s*)?',                    # %%END%% optional — LLMs often omit it
    re.IGNORECASE,
)

# The system prompt is fixed at boot.
# Dynamic context (NPC profiles, skill rules, location NPCs) is injected per-turn
# via keyword detection in _stream_chat — never appended permanently.


@dataclass
class GameSession:
    id: str
    session_number: int
    model: str
    host: str
    temperature: float
    dev_mode: bool = False
    provider: str = "ollama"   # "ollama" | "groq"
    num_ctx: int = 2048
    num_gpu: int = 999
    system_prompt: str = ""
    messages: list = field(default_factory=list)
    log_path: Optional[Path] = None
    turn_number: int = 0  # incremented at the start of each player turn
    # Set when GM requests a dice roll; cleared after resolve_roll() is called.
    pending_roll: Optional[dict] = None  # {skill, dc, success, failure}
    # Canonical NPC names active in the current scene, accumulated across turns.
    # Used to keep injecting the %%DELTAS%% instruction even when the player
    # doesn't name an NPC explicitly on a later turn.
    scene_npcs: list = field(default_factory=list)


_sessions: dict[str, GameSession] = {}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _log(session: GameSession, text: str) -> None:
    if session.log_path is None:
        return
    with session.log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def _build_slim_system_prompt(session_number: int) -> str:
    """Build the fixed base system prompt for this session.

    Loaded once at boot and never modified.  Per-turn context (NPC profiles,
    skill rules, location NPCs) is injected dynamically inside _stream_chat.
    """
    repo_root = _REPO_ROOT

    # Party names from player character sheets (best-effort)
    party_lines: list[str] = []
    players_dir = repo_root / "players"
    if players_dir.exists():
        for sheet in sorted(players_dir.glob("*/character_sheet.md")):
            name = ""
            cls = ""
            for line in sheet.read_text(encoding="utf-8").splitlines():
                if line.startswith("**Name:**"):
                    name = line.replace("**Name:**", "").strip()
                elif line.startswith("**Class / Archetype:**"):
                    cls = line.replace("**Class / Archetype:**", "").strip()
            if name and cls:
                party_lines.append(f"  - {name} ({cls})")

    party_block = "\n".join(party_lines) if party_lines else "  - (no character files found)"

    # Session boot context: prefer sessions/session_NNN/boot.md (GM-facing),
    # fall back to recap from previous session, then bare notice.
    sessions_dir = repo_root / "sessions"
    boot_path = sessions_dir / f"session_{session_number:03d}" / "boot.md"
    if not boot_path.exists() and session_number > 1:
        boot_path = sessions_dir / f"session_{session_number - 1:03d}" / "recap.md"
    situation = boot_path.read_text(encoding="utf-8") if boot_path.exists() else "(No boot context found for this session.)"

    return f"""You are the Game Master for a Pathfinder 1st Edition campaign: Rise of the Runelords.
Session number: {session_number}

CORE BEHAVIOR (always active)
- Describe only what the characters can directly perceive. No hinting, no foreshadowing.
- Never describe what a PC is doing or saying before the player declares it.
- Never suggest actions, hint at correct choices, or guide the players.
- Never invent lore, NPCs, or mechanics outside what you have been given. If unsure, say so.
- Resolve what the player declares before narrating its outcome.

GM STYLE
- NPCs: open with demeanor and immediate goal. Do not dump biography unless asked.
- Locations: 3–6 sensory details, one social detail, one interactive element.
- Rules rulings: state the ruling, DC, and consequence in one sentence. No lengthy explanation.
- Player drift: if momentum stalls, remind non-directively ("Your vow to X would apply here…").
- Events: when time passes or PCs cross a boundary, fire only eligible triggers — do not telegraph upcoming ones.
- Inventory: on loot, shopping, or consumables mention only changes and immediately relevant reminders.
- Travel: give distance/time estimate, encounter cadence, and arrival conditions.

PARTY
{party_block}

CURRENT SITUATION
{situation}

RESPONSE STRUCTURE (strictly enforced)
Every response must use these sections in this exact order.
Each section begins with its %%MARKER%% on a line by itself.
Omit sections that are not needed for this turn.

%%NARRATIVE%%
Your narration — 2 to 4 paragraphs of natural prose.
No markdown. No bullet points. No bold or italic formatting.

%%ROLL%%
Include only when a dice roll is needed. One block, opened by [ on its own line and closed by ] on its own line:
[
skill: [skill name only — no numbers or modifiers]
dc: [integer]
success: [one sentence — what happens if the roll meets or exceeds DC]
failure: [one sentence — what happens if the roll falls below DC]
]

%%GENERATE%%
REQUIRED whenever your narrative introduces any NEW named character not already in the scene.
Do NOT skip this section if you name a new character — omitting it is an error.
One block per new NPC or location:
[
type: [npc | location]
name: [full name of npc or location exactly as written in your narrative]
role: [occupation or type of location — one short phrase]
appearance: [one sentence] ← omit if unsure
location: [where they or it are usually found — area or city for locations]  ← omit if unsure
summary: [one sentence — what the npc knows or wants, or what the location is known for]
]

%%DELTAS%%
Include when any named NPCs are active in the scene. One block per NPC.
Each block MUST be wrapped in square brackets exactly as shown — [ on its own line, ] on its own line:
[
npc: [canonical NPC name]
disposition: [change e.g. neutral → curious]  ← omit if unchanged
location: [where they are now]                ← omit if unchanged
knowledge: [tag] [one fact this NPC learned]  ← repeat this line for each fact; omit if nothing new
summary: [one sentence — what happened with this NPC this turn]
]

Knowledge tags: [persistent] [pcs] [quest] [world] [npcs] [trivia]

EXAMPLE OF A CORRECT FULL RESPONSE (follow this format exactly):

%%NARRATIVE%%
The crowd parts as you approach Mayor Deverin and Father Zantus near the cathedral steps. She turns with a warm smile, extending her hand in greeting. "Welcome to Sandpoint — I hope you're enjoying the festival. The apothecary's got some interesting remedies, if you're into that sort of thing," she says with a wink. "Just visit Gerhard Pickle down by the docks.

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
disposition:  friendly → neutral
location: cathedral steps
knowledge: [quest] Asks Yanyeeku to fetch him a drink from the tavern
summary: Abstalar Zantus asked Yanyeeku to fetch him a drink from the tavern.
]

Everything after %%NARRATIVE%% is stripped before the player sees the response."""


def create_session(
    session_number: int,
    model: str,
    host: str = "http://localhost:11434",
    temperature: float = 0.3,
    dev_mode: bool = False,
    num_ctx: int = 2048,
    num_gpu: int = 999,
    provider: str = "ollama",
) -> GameSession:
    system_prompt = _build_slim_system_prompt(session_number)

    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    log_name = f"session_{session_number:03d}_{started.strftime('%Y%m%d_%H%M%S')}.log.md"

    session = GameSession(
        id=str(uuid.uuid4()),
        session_number=session_number,
        model=model,
        host=host,
        temperature=temperature,
        dev_mode=dev_mode,
        provider=provider,
        num_ctx=num_ctx,
        num_gpu=num_gpu,
        system_prompt=system_prompt,
        log_path=_OUTPUTS_DIR / log_name,
    )

    # Boot cleanup — runs against adventure_path/05_npcs/ on every session start.
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
    _npcs_root = _REPO_ROOT / "adventure_path" / "05_npcs"
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

    _sessions[session.id] = session

    mode_label = "dev" if dev_mode else "full"
    _log(session, f"# Session {session_number:03d} — {started.strftime('%Y-%m-%d %H:%M:%S')}")
    _log(session, f"Model: `{model}` | Mode: {mode_label} | Temp: {temperature}\n")
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

    # Inform the LLM of the result so it has full context on the next turn
    session.messages.append({
        "role": "assistant",
        "content": (
            f"[{pr['skill']} check — rolled {rolled} vs DC {pr['dc']}: {label}]\n\n"
            f"{outcome}"
        ),
    })

    _log(session, f"\n### [{_ts()}] ROLL RESULT — {pr['skill']} DC {pr['dc']}")
    _log(session, f"Rolled: {rolled}  |  {label}")
    _log(session, f"{outcome}\n")
    _log(session, "---\n")

    session.pending_roll = None
    return {"passed": passed, "skill": pr["skill"], "dc": pr["dc"], "rolled": rolled, "outcome": outcome}


def save_session(session: GameSession) -> Path:
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    _log(session, f"\n## Session Ended — {datetime.now().strftime('%H:%M:%S')}")
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

    # Fallback — should not normally be reached
    return "Respond to the player's action using the reference context above."


def _process_generate_block(body: str, session: GameSession) -> None:
    """Create a new NPC stub from a %%GENERATE%% block body.

    Silently skipped if the NPC is already in the index or if the name field
    is missing.  Resets the NPC index after creation so the new entry is
    findable immediately on the same turn's %%DELTAS%% write.
    """
    fields   = _parse_delta_fields(body)

    # Skip location blocks — no stub created for locations.
    if fields.get("type", "").lower() == "location":
        _log(session, f"\n> *[Location block skipped: {fields.get('name', '?')}]*\n")
        return

    # New format uses name:, old format used npc: — accept both.
    npc_name = (fields.get("name") or fields.get("npc", "")).strip()
    if not npc_name:
        return

    # Already known — nothing to do.
    if _get_npc_index().npc_dir_for(npc_name) is not None:
        return

    npc_slug = _slugify(npc_name)
    # Dot-prefix marks this as a session NPC (temporary, purgeable from the UI).
    npc_dir  = _REPO_ROOT / "adventure_path" / "05_npcs" / f".{npc_slug}"
    npc_dir.mkdir(parents=True, exist_ok=True)

    loc_str   = fields.get("location", "")
    locations = [l.strip() for l in loc_str.split(",") if l.strip()] if loc_str else []

    base_md = generate_base_md(
        npc_name,
        role        = fields.get("role", ""),
        appearance  = fields.get("appearance", ""),
        personality = fields.get("personality", ""),
        locations   = locations or None,
        session_number = session.session_number,
    )
    (npc_dir / "base.md").write_text(base_md, encoding="utf-8")
    _invalidate_npc_index()

    _log(session, f"\n> *[New NPC stub created: {npc_name} → {npc_dir.name}/base.md]*\n")


def list_session_npcs() -> list[str]:
    """Return the slug names of all session NPCs (dot-prefixed directories)."""
    npc_base = _REPO_ROOT / "adventure_path" / "05_npcs"
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
    npc_base = _REPO_ROOT / "adventure_path" / "05_npcs"
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
    _END_MARKERS     = ("\n%%ROLL%%", "\n%%DELTAS%%", "\n%%GENERATE%%")
    _HOLDBACK        = 16   # ≥ len("%%GENERATE%%\n") = 14

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
    """Scan completed narrative text for unrecognised proper names.

    Adds candidates to session.scene_npcs so the NEXT turn's directive requests
    a %%DELTAS%% block.  Layer 2 then creates the stub when the model writes
    that delta block.  No stub is created here — detection and creation are
    intentionally separated to avoid false-positive junk folders.
    """
    for _m in _NARRATIVE_NAME_RE.finditer(text):
        _first, _last = _m.group(1), _m.group(2)
        if _first.lower() in _NAME_EXCLUDE_WORDS or _last.lower() in _NAME_EXCLUDE_WORDS:
            continue
        _full_name = f"{_first} {_last}"
        # Already tracked or already in the index — nothing to add
        if _full_name in session.scene_npcs:
            continue
        if _get_npc_index().npc_dir_for(_full_name) is not None:
            continue
        session.scene_npcs.append(_full_name)
        _log(session, f"\n> *[Suspected NPC detected in narrative: {_full_name} — added to scene tracking]*\n")


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
    else:
        max_hist = _FULL_MAX_HISTORY
    history = session.messages[-max_hist:] if len(session.messages) > max_hist else session.messages

    system_content = session.system_prompt
    if session.provider == "groq" and len(system_content) > _GROQ_MAX_SYSTEM_CHARS:
        system_content = system_content[:_GROQ_MAX_SYSTEM_CHARS] + "\n\n…[later context omitted to stay within payload limit]"

    last_user = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )
    injected: list[str] = []

    npc_match = _get_npc_index().detect(last_user)
    if npc_match:
        injected.append(_get_npc_index().format_context(npc_match))
        _log(session, f"\n> *[NPC context injected: {npc_match.canonical_name} (alias: \"{npc_match.matched_alias}\")]*\n")

    skill_match = _get_skill_index().detect(last_user)
    if skill_match:
        injected.append(_get_skill_index().format_context(skill_match))
        _log(session, f"\n> *[Skill context injected: {skill_match.skill_name} (trigger: \"{skill_match.matched_trigger}\")]*\n")

    already_injected = {npc_match.canonical_name} if npc_match else set()
    location_matches = _get_npc_index().detect_by_location(last_user)
    location_matches = [m for m in location_matches if m.canonical_name not in already_injected]
    for loc_match in location_matches:
        injected.append(_get_npc_index().format_context(loc_match))
        _log(session, f"\n> *[Location context injected: {loc_match.canonical_name} at \"{loc_match.matched_location}\"]*\n")

    if npc_match and npc_match.canonical_name not in session.scene_npcs:
        session.scene_npcs.append(npc_match.canonical_name)
    for _loc in location_matches:
        if _loc.canonical_name not in session.scene_npcs:
            session.scene_npcs.append(_loc.canonical_name)

    if injected:
        block = "\n\n---\n".join(injected)
        directive = _build_turn_directive(npc_match, skill_match, location_matches, session.scene_npcs)
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

    context_info: dict = {
        "npc":           npc_match.canonical_name    if npc_match else None,
        "npc_trigger":   npc_match.matched_alias     if npc_match else None,
        "skill":         skill_match.skill_name      if skill_match else None,
        "skill_trigger": skill_match.matched_trigger if skill_match else None,
        "location":      location_matches[0].matched_location if location_matches else None,
        "location_npcs": [m.canonical_name for m in location_matches] if location_matches else [],
        "history":       history,
    }

    return system_content, context_info


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

    # Build the exact payload that will be posted — mirrored from _stream_groq / _stream_ollama
    if session.provider == "groq":
        _raw_request: dict = {
            "model":          session.model,
            "messages":       messages,
            "stream":         True,
            "temperature":    session.temperature,
            "max_tokens":     1024,
            "stream_options": {"include_usage": True},
        }
    else:
        _raw_request = {
            "model":    session.model,
            "messages": messages,
            "stream":   True,
            "options":  options,
        }

    _llm_start = _time.monotonic()
    _llm_error: Optional[str] = None
    _usage: dict = {}
    try:
        _raw = (
            _stream_groq(session, messages, accumulated, _usage)
            if session.provider == "groq"
            else _stream_ollama(session, messages, options, accumulated)
        )
        yield from _stream_with_narrative_filter(_raw, session.dev_mode)
    except Exception as _llm_exc:
        _llm_error = str(_llm_exc)
        raise
    finally:
        _llm_ms = int((_time.monotonic() - _llm_start) * 1000)
        write_api_log(
            provider=session.provider,
            session_id=session.id,
            session_number=session.session_number,
            turn=session.turn_number,
            raw_request=_raw_request,
            response_text="".join(accumulated),
            duration_ms=_llm_ms,
            status="error" if _llm_error else "ok",
            error=_llm_error,
            usage=_usage or None,
        )

    # Emit rate limit info captured from Groq response headers (Groq only; None for Ollama).
    # The UI uses this to show remaining requests/tokens in the header.
    if _usage.get("rate_limits"):
        yield f"data: {json.dumps({'type': 'rate_limits', **_usage['rate_limits']})}\n\n"

    response_text = "".join(accumulated)
    roll_data: Optional[dict] = None

    # ── Parse response sections ───────────────────────────────────────────────
    # Primary path: section-based format (%%NARRATIVE%% / %%ROLL%% / %%DELTAS%% / %%GENERATE%%)
    # Fallback path: old flat-block format (%%DELTA%%…%%END%% etc.) for small models
    # that ignore the template instruction.
    _use_sections = bool(_HAS_SECTION_MARKERS_RE.search(response_text))

    if _use_sections:
        _sections = _parse_response_sections(response_text)
        display_text = _sections.get("NARRATIVE", "").strip() or response_text.strip()

        # ── %%ROLL%% ──────────────────────────────────────────────────────────
        _roll_section = _sections.get("ROLL", "")
        if _roll_section:
            _roll_blocks = _parse_bracket_blocks(_roll_section)
            if _roll_blocks:
                _rf = _roll_blocks[0]
                try:
                    roll_data = {
                        "skill":   _rf.get("skill", "").strip(),
                        "dc":      int(_rf.get("dc", 0)),
                        "success": _rf.get("success", "").strip(),
                        "failure": _rf.get("failure", "").strip(),
                    }
                    session.pending_roll = roll_data
                    _log(session, f"\n> *[Roll requested: {roll_data['skill']} DC {roll_data['dc']}]*\n")
                except (ValueError, KeyError):
                    pass

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

    else:
        # ── Fallback: old flat-block format ───────────────────────────────────
        display_text = response_text

        # %%ROLL%%
        _roll_m = _ROLL_BLOCK_RE.search(display_text)
        if _roll_m:
            try:
                roll_data = {
                    "skill":   _roll_m.group("skill").strip(),
                    "dc":      int(_roll_m.group("dc")),
                    "success": _roll_m.group("success").strip(),
                    "failure": _roll_m.group("failure").strip(),
                }
                session.pending_roll = roll_data
                display_text = _ROLL_BLOCK_RE.sub("", display_text).rstrip()
                _log(session, f"\n> *[Roll requested: {roll_data['skill']} DC {roll_data['dc']}]*\n")
            except (ValueError, AttributeError):
                pass

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
                    # Promote knowledge to list so _write_npc_delta handles it uniformly
                    _fields["knowledge"] = _extract_knowledge_items(_dm.group(1))
                    _write_npc_delta(_fields, session)
                except Exception as _e:
                    _log(session, f"\n> *[%%DELTA%% processing error: {_e}]*\n")

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
                accumulated.append(content)
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            if chunk.get("done"):
                break


def _stream_groq(
    session: GameSession,
    messages: list,
    accumulated: list[str],
    usage_out: dict,
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
                accumulated.append(content)
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"


# ── Session-end recap generation ──────────────────────────────────────────────

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
    """Single non-streaming LLM call dispatched by provider. Used for recap generation."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    if session.provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set.")
        payload = {
            "model": session.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.5,
            "max_tokens": 2048,
        }
        resp = _groq_post(api_key, payload, stream=False)
        return (resp.json()["choices"][0]["message"] or {}).get("content", "").strip()
    else:
        resp = _requests.post(
            f"{session.host}/api/chat",
            json={
                "model": session.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "num_ctx": 4096,
                    "num_gpu": session.num_gpu,
                },
            },
            timeout=300,
        )
        resp.raise_for_status()
        return (resp.json().get("message") or {}).get("content", "").strip()


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

    boot_path = sessions_dir / f"session_{next_n:03d}" / "boot.md"
    boot_path.parent.mkdir(parents=True, exist_ok=True)
    boot_path.write_text(boot_text, encoding="utf-8")

    _log(session, f"\n## Recap generated → {recap_path.relative_to(_REPO_ROOT)}")
    _log(session, f"## Boot generated  → {boot_path.relative_to(_REPO_ROOT)}\n")

    # ── 5. Save session ───────────────────────────────────────────────────────
    yield _status("Saving session…")
    saved_to = save_session(session)

    yield f"data: {json.dumps({'type': 'done', 'recap_path': str(recap_path), 'boot_path': str(boot_path), 'saved_to': str(saved_to)})}\n\n"
