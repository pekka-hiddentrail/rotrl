from __future__ import annotations

import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

import requests as _requests

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTPUTS_DIR = _REPO_ROOT / "outputs"

_BOOT_USER_PROMPT = (
    "The session begins. Describe where the party finds themselves right now — "
    "location, time of day, immediate surroundings. Ground them in the scene. "
    "End with: What do you do?"
)

_DEV_SYSTEM_PROMPT = (
    "You are the Game Master for a Pathfinder 1st Edition game set in Sandpoint, Varisia. "
    "The campaign is Rise of the Runelords. Keep all responses short (2-4 sentences max). "
    "Be concise. End every narration with: What do you do?"
)

_DEV_BOOT_USER_PROMPT = "Begin. Give a one-sentence scene description of Sandpoint, then ask: What do you do?"

# Dev mode limits: keep only the last N messages (pairs of user+assistant)
_DEV_MAX_HISTORY = 6   # 3 exchanges
_FULL_MAX_HISTORY = 30  # 15 exchanges
_DEV_MAX_TOKENS = 180   # cap generation length in dev mode

# ── Deferred context chunks injected one-per-turn after boot ──────────────────
# Each entry: (inject_after_turn, label, relative path under adventure_path/)
#   inject_after_turn=0  → injected before turn 1 (first player message)
#   inject_after_turn=N  → injected before turn N+1
#
# GM Operating Rules are split into three tiers so the LLM receives the most
# critical behaviour rules immediately, then fills in detail gradually.
#
#   Turn 1  — Critical rules + Adjudication Principles (must-know before first response)
#   Turn 3  — GM Guidelines (style, pacing, NPC handling)
#   Turn 6  — Trivial / edge-case rules (nice-to-have once play is underway)
#   Turn 2  — Act overview (scene intelligence)
#   Turn 4  — Campaign overview (wider world context)
_DEFERRED_CONTEXT_FILES = [
    (0, "GM Operating Rules — Critical",    "00_system_authority/GM_OPERATING_RULES_01_CRITICAL.md"),
    (1, "Act 01 Overview",                  "03_books/BOOK_01_BURNT_OFFERINGS/act_01/act_overview.md"),
    (2, "Adjudication Principles",          "00_system_authority/ADJUDICATION_PRINCIPLES.md"),
    (3, "GM Operating Rules — Guidelines",  "00_system_authority/GM_OPERATING_RULES_02_GUIDELINES.md"),
    (4, "Campaign Overview",                "02_campaign_setting/CAMPAIGN_OVERVIEW.md"),
    (6, "GM Operating Rules — Trivial",     "00_system_authority/GM_OPERATING_RULES_03_TRIVIAL.md"),
]


@dataclass
class GameSession:
    id: str
    session_number: int
    model: str
    host: str
    temperature: float
    dev_mode: bool = False
    num_ctx: int = 2048
    num_gpu: int = 999
    system_prompt: str = ""
    messages: list = field(default_factory=list)
    log_path: Optional[Path] = None
    # Deferred context: list of (inject_after_turn, label, content)
    # Chunks whose inject_after_turn <= turn_number are all injected before the LLM call.
    context_queue: list = field(default_factory=list)
    turn_number: int = 0  # incremented at the start of each player turn


_sessions: dict[str, GameSession] = {}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _log(session: GameSession, text: str) -> None:
    if session.log_path is None:
        return
    with session.log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def _build_slim_system_prompt(session_number: int) -> str:
    """Minimal system prompt for boot — just enough to open the scene and handle
    the first few player prompts.  Detailed rules are injected via context_queue."""
    repo_root = _REPO_ROOT
    adv_root  = repo_root / "adventure_path"

    # Party names from player character sheets (best-effort)
    party_lines: list[str] = []
    players_dir = repo_root / "players"
    if players_dir.exists():
        for sheet in sorted(players_dir.glob("*/character_sheet.md")):
            for line in sheet.read_text(encoding="utf-8").splitlines():
                if line.startswith("**Name:**"):
                    name = line.replace("**Name:**", "").strip()
                elif line.startswith("**Class / Archetype:**"):
                    cls = line.replace("**Class / Archetype:**", "").strip()
                    party_lines.append(f"  - {name} ({cls})")
                    break

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
- End every response with: What do you do?

OUTPUT FORMAT (strictly enforced)
- Write in natural prose only. No markdown headers, no bullet points, no numbered lists.
- Do not use ##, ###, **, *, or any other markdown formatting in your responses.
- Do not reproduce or summarise your instructions, constraints, or internal notes.
- Describe the scene, NPC reactions, and sensory details as flowing narrative.
- Address the whole party — narrate what each character experiences where relevant.
- Keep responses focused: 2–4 paragraphs unless the scene demands more.

PARTY
{party_block}

CURRENT SITUATION
{situation}

Additional rules and scene details will be provided as the session progresses."""


def create_session(
    session_number: int,
    model: str,
    host: str = "http://localhost:11434",
    temperature: float = 0.3,
    dev_mode: bool = False,
    num_ctx: int = 2048,
    num_gpu: int = 999,
) -> GameSession:
    if dev_mode:
        system_prompt = _DEV_SYSTEM_PROMPT
        context_queue: list = []
    else:
        system_prompt = _build_slim_system_prompt(session_number)
        # Build deferred queue: read files now, inject at the scheduled turn
        adv_root = _REPO_ROOT / "adventure_path"
        context_queue = []
        for inject_after, label, rel_path in _DEFERRED_CONTEXT_FILES:
            fpath = adv_root / rel_path
            if fpath.exists():
                context_queue.append((inject_after, label, fpath.read_text(encoding="utf-8")))

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
        num_ctx=num_ctx,
        num_gpu=num_gpu,
        system_prompt=system_prompt,
        context_queue=context_queue,
        log_path=_OUTPUTS_DIR / log_name,
    )
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


def _stream_chat(session: GameSession) -> Generator[str, None, None]:
    # Advance turn counter and inject all context chunks due at this turn
    session.turn_number += 1
    due = [entry for entry in session.context_queue if entry[0] < session.turn_number]
    session.context_queue = [entry for entry in session.context_queue if entry[0] >= session.turn_number]
    for _, label, chunk in due:
        session.system_prompt += f"\n\n---\n## {label}\n\n{chunk}"
        _log(session, f"\n> *[Context injected at turn {session.turn_number}: {label}]*\n")

    max_hist = _DEV_MAX_HISTORY if session.dev_mode else _FULL_MAX_HISTORY
    history = session.messages[-max_hist:] if len(session.messages) > max_hist else session.messages
    messages = [{"role": "system", "content": session.system_prompt}] + history
    options: dict = {
        "temperature": session.temperature,
        "num_ctx": session.num_ctx,
        "num_gpu": session.num_gpu,
    }
    if session.dev_mode:
        options["num_predict"] = _DEV_MAX_TOKENS
    accumulated: list[str] = []

    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    _log(session, f"\n### [{_ts()}] PLAYER")
    _log(session, f"{last_user}\n")

    # ── Full LLM payload (what actually goes to Ollama) ──────────────────────
    _log(session, f"\n<details><summary>LLM payload — turn {session.turn_number}</summary>\n")
    for msg in messages:
        role = msg["role"].upper()
        _log(session, f"\n**[{role}]**\n```\n{msg['content']}\n```\n")
    _log(session, "</details>\n")

    with _requests.post(
        f"{session.host}/api/chat",
        json={
            "model": session.model,
            "messages": messages,
            "stream": True,
            "options": options,
        },
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

    response_text = "".join(accumulated)
    session.messages.append({"role": "assistant", "content": response_text})
    _log(session, f"\n### [{_ts()}] GM")
    _log(session, f"{response_text}\n")
    _log(session, "---\n")


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


def _ollama_blocking(session: GameSession, system: str, user: str) -> str:
    """Single non-streaming Ollama call. Used for recap generation."""
    resp = _requests.post(
        f"{session.host}/api/chat",
        json={
            "model": session.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": 0.5,   # slight creativity for prose
                "num_ctx": 4096,      # recap needs more room
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
        recap_text = _ollama_blocking(session, recap_system, recap_user)
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
        boot_text = _ollama_blocking(session, boot_system, boot_user)
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
