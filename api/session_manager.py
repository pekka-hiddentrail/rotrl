from __future__ import annotations

import json
import os
import re
import sys
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

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MAX_RETRIES = 4
_GROQ_RETRY_BASE = 5.0  # seconds — doubled each attempt


def _groq_post(api_key: str, payload: dict, stream: bool = False) -> _requests.Response:
    """POST to Groq with automatic retry on 429 (rate-limit).

    Reads the ``retry-after`` or ``x-ratelimit-reset-requests`` response header
    when present; otherwise falls back to exponential back-off starting at
    ``_GROQ_RETRY_BASE`` seconds.  Raises on any non-retryable error.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
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
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        if attempt == _GROQ_MAX_RETRIES:
            resp.raise_for_status()  # will raise a 429 HTTPError after all retries

        # Parse the header-suggested wait time if available
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
# All fields except npc: and summary: are optional.
# findall is used — there can be multiple delta blocks per response (one per NPC).
#
# Format:
#   %%DELTA%%
#   npc: Kendra Deverin
#   disposition: neutral → suspicious   (optional)
#   location: Festival Square           (optional)
#   knowledge: Ani tried to deceive her (optional)
#   summary: One sentence of what happened.
#   %%END%%
_DELTA_BLOCK_RE = re.compile(
    r'\s*%%DELTA%%\s*\n'
    r'npc:\s*(?P<npc>[^\n]+)\n'
    r'(?:disposition:\s*(?P<disposition>[^\n]+)\n)?'
    r'(?:location:\s*(?P<location>[^\n]+)\n)?'
    r'(?:knowledge:\s*(?P<knowledge>[^\n]+)\n)?'
    r'summary:\s*(?P<summary>[^\n]+)\n'
    r'%%END%%',
    re.IGNORECASE,
)

_ROLL_BLOCK_RE = re.compile(
    r'\s*%%ROLL%%\s*\n'
    r'(?:skill:\s*)?(?P<skill>[^\n:]+?)(?:\s*:\s*\d+)?\s*\n'
    r'dc:\s*(?P<dc>\d+)\s*\n'
    r'success:\s*(?P<success>[^\n]+)\n'
    r'failure:\s*(?P<failure>[^\n]+)\n'
    r'%%END%%\s*',
    re.IGNORECASE,
)

# context_queue removed — system prompt is fixed at boot.
# All dynamic context is injected per-turn via keyword detection (NPC, skill, location).


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

DICE ROLLS
- Do NOT request rolls on your own. Rolls are requested only when the system explicitly instructs you to via a GM DIRECTIVE section below.
- When no GM DIRECTIVE is present: narrate outcomes directly. Do not append any %%ROLL%% block.
- When a GM DIRECTIVE orders a roll: follow its instructions exactly."""


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
    if dev_mode:
        system_prompt = _DEV_SYSTEM_PROMPT
    else:
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

    # Delete any delta files left over from a previous run of this session number.
    # Delta files are session-scoped: session_NNN.md lives next to each NPC's base.md.
    _npcs_root = _REPO_ROOT / "adventure_path" / "05_npcs"
    if _npcs_root.exists():
        _delta_filename = f"session_{session_number:03d}.md"
        for _npc_dir in _npcs_root.iterdir():
            if _npc_dir.is_dir():
                _old_delta = _npc_dir / _delta_filename
                if _old_delta.exists():
                    _old_delta.unlink()

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


def _build_turn_directive(npc_match, skill_match, location_matches=None) -> str:
    """Return an explicit GM instruction for the current turn based on what was detected.

    This is injected as the last section of the system prompt so the model
    sees a clear, unambiguous action item rather than having to infer from
    the reference data above.
    """
    has_npc   = npc_match   is not None
    has_skill = skill_match is not None
    loc_npc_names = [m.canonical_name for m in (location_matches or [])]

    # All NPCs active this turn (for delta block instruction)
    active_npc_names: list[str] = []
    if has_npc:
        active_npc_names.append(npc_match.canonical_name)
    for n in loc_npc_names:
        if n not in active_npc_names:
            active_npc_names.append(n)

    roll_template = (
        "%%ROLL%%\n"
        "skill: {skill}\n"
        "dc: [DC as a plain integer — nothing else on this line]\n"
        "success: [one sentence — what happens if the roll meets or exceeds DC]\n"
        "failure: [one sentence — what happens if the roll falls below DC]\n"
        "%%END%%\n"
        "IMPORTANT: 'skill:' must be exactly the skill name only — no numbers, no modifiers."
    )

    # Delta block instruction — appended to every directive that involves NPCs.
    # The GM must write one %%DELTA%% block per NPC after the narrative.
    # The backend strips these blocks before display and writes them to delta files.
    _delta_block_instructions = ""
    if active_npc_names:
        npc_list_str = ", ".join(active_npc_names)
        _delta_block_instructions = (
            f"\n\nNPC STATE TRACKING (MANDATORY)\n"
            f"After your narrative (and after any %%ROLL%% block), append one %%DELTA%% block "
            f"for EACH of these NPCs: {npc_list_str}.\n"
            "Use this exact format — include only fields that changed or are relevant:\n\n"
            "%%DELTA%%\n"
            "npc: [exact canonical NPC name]\n"
            "disposition: [change description, e.g. 'neutral → suspicious']  ← omit if unchanged\n"
            "location: [current location]  ← omit if not mentioned\n"
            "knowledge: [what the NPC learned about the party]  ← omit if nothing\n"
            "summary: [one sentence — what happened with this NPC this turn]\n"
            "%%END%%\n\n"
            "These blocks are stripped by the system before display. The player never sees them."
        )

    if has_skill and has_npc:
        npc_name   = npc_match.canonical_name
        skill_name = skill_match.skill_name
        template   = roll_template.format(skill=skill_name)
        return (
            f"THIS TURN: the player is attempting a {skill_name} check against {npc_name}.\n\n"
            "STEP 1 — Write 1–2 sentences of scene setup (what the character attempts). Do not reveal the outcome.\n\n"
            f"STEP 2 — Decide: is the outcome genuinely uncertain?\n"
            f"  YES → Stop the narrative. Copy the block below EXACTLY as the final lines of your response, replacing only the bracketed values:\n\n"
            f"{template}\n\n"
            f"  NO (auto-fail / impossible) → Narrate the immediate failure. No roll block.\n\n"
            "Do NOT write 'What do you do?' if you output the roll block — the roll IS the next action."
            + _delta_block_instructions
        )

    elif has_skill:
        skill_name = skill_match.skill_name
        template   = roll_template.format(skill=skill_name)
        return (
            f"THIS TURN: the player is attempting a {skill_name} check.\n\n"
            "STEP 1 — Write 1–2 sentences of scene setup. Do not reveal the outcome.\n\n"
            f"STEP 2 — Decide: is the outcome genuinely uncertain?\n"
            f"  YES → Stop the narrative. Copy the block below EXACTLY as the final lines of your response, replacing only the bracketed values:\n\n"
            f"{template}\n\n"
            f"  NO (auto-succeed / impossible) → Narrate the result directly. No roll block.\n\n"
            "Do NOT write 'What do you do?' if you output the roll block."
            + _delta_block_instructions
        )

    elif has_npc:
        npc_name = npc_match.canonical_name
        # NPC only: softer but still instructive — social checks handled by keyword detection above;
        # this catches edge cases like "talk to / approach / ask" without a skill keyword.
        return (
            f"THIS TURN: the player is interacting with {npc_name}.\n"
            f"Use the {npc_name} profile above.\n"
            "If this interaction requires a skill check (Diplomacy, Bluff, Intimidate, Sense Motive):\n"
            "  → Write a 1–2 sentence setup, then output the %%ROLL%% block as described in the SYSTEM ROLL PROTOCOL.\n"
            "If no check is needed: narrate the NPC's reaction based on their profile and current state.\n"
            + _delta_block_instructions
        )

    elif location_matches:
        loc_keyword = location_matches[0].matched_location
        npc_names = ", ".join(m.canonical_name for m in location_matches)
        return (
            f"THIS TURN: the player is at or heading to '{loc_keyword}'.\n"
            f"NPCs present at this location: {npc_names}.\n"
            "Use the NPC profiles above to describe who the party finds there and how they react.\n"
            "If the player interacts with an NPC in a way that requires a skill check, output the %%ROLL%% block.\n"
            + _delta_block_instructions
        )

    # Fallback — should not normally be reached
    return "Respond to the player's action using the reference context above."


def _stream_chat(session: GameSession) -> Generator[str, None, None]:
    session.turn_number += 1

    if session.dev_mode:
        max_hist = _DEV_MAX_HISTORY
    elif session.provider == "groq":
        max_hist = _GROQ_MAX_HISTORY
    else:
        max_hist = _FULL_MAX_HISTORY
    history = session.messages[-max_hist:] if len(session.messages) > max_hist else session.messages

    # For Groq: if the system prompt has grown too large (many injected chunks),
    # keep the *beginning* (base prompt + earliest/most critical rules) and drop
    # later injected chunks.  Base prompt is always the most important part.
    system_content = session.system_prompt
    if session.provider == "groq" and len(system_content) > _GROQ_MAX_SYSTEM_CHARS:
        system_content = system_content[:_GROQ_MAX_SYSTEM_CHARS] + "\n\n…[later context omitted to stay within payload limit]"

    # ── Context lookup — NPC and/or skill detected in player input ────────────
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

    # Location detection — inject NPCs found at the mentioned location
    # Skip any NPC already injected by name above (de-duplicate by canonical name)
    already_injected = {npc_match.canonical_name} if npc_match else set()
    location_matches = _get_npc_index().detect_by_location(last_user)
    location_matches = [m for m in location_matches if m.canonical_name not in already_injected]
    for loc_match in location_matches:
        injected.append(_get_npc_index().format_context(loc_match))
        _log(session, f"\n> *[Location context injected: {loc_match.canonical_name} at \"{loc_match.matched_location}\")]*\n")


    if injected:
        block = "\n\n---\n".join(injected)
        directive = _build_turn_directive(npc_match, skill_match, location_matches)
        system_content = (
            system_content
            + f"\n\n---\n[CONTEXT FOR THIS TURN]\n{block}"
            + f"\n\n---\n[GM DIRECTIVE FOR THIS TURN — follow exactly]\n{directive}"
        )

    # ── Context detection event (dev tooling) ─────────────────────────────────
    yield "data: " + json.dumps({
        "type": "context",
        "npc":              npc_match.canonical_name   if npc_match else None,
        "npc_trigger":      npc_match.matched_alias    if npc_match else None,
        "skill":            skill_match.skill_name     if skill_match else None,
        "skill_trigger":    skill_match.matched_trigger if skill_match else None,
        "location":         location_matches[0].matched_location if location_matches else None,
        "location_npcs":    [m.canonical_name for m in location_matches] if location_matches else [],
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
            "model":       session.model,
            "messages":    messages,
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
    _llm_error: Optional[str] = None
    try:
        if session.provider == "groq":
            yield from _stream_groq(session, messages, accumulated)
        else:
            yield from _stream_ollama(session, messages, options, accumulated)
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
        )

    response_text = "".join(accumulated)

    # ── Roll block detection ───────────────────────────────────────────────────
    roll_m = _ROLL_BLOCK_RE.search(response_text)
    if roll_m:
        clean_text = _ROLL_BLOCK_RE.sub("", response_text).rstrip()
        roll_data = {
            "skill":   roll_m.group("skill").strip(),
            "dc":      int(roll_m.group("dc")),
            "success": roll_m.group("success").strip(),
            "failure": roll_m.group("failure").strip(),
        }
        session.pending_roll = roll_data
        # Patch the already-streamed message to remove the raw block tokens
        yield f"data: {json.dumps({'type': 'patch_last', 'content': clean_text})}\n\n"
        yield f"data: {json.dumps({'type': 'roll_request', **roll_data})}\n\n"
        _log(session, f"\n> *[Roll requested: {roll_data['skill']} DC {roll_data['dc']}]*\n")
        history_text = clean_text  # store without block in LLM history
    else:
        history_text = response_text

    # ── Delta block extraction ────────────────────────────────────────────────
    # The GM is instructed to append %%DELTA%%…%%END%% blocks for every NPC
    # involved in the turn.  Parse them all, strip from display text, write to
    # per-NPC delta files.  Errors are silently swallowed — delta writes are
    # best-effort and must never crash the main flow.
    _delta_matches = list(_DELTA_BLOCK_RE.finditer(history_text))
    if _delta_matches:
        # Strip ALL delta blocks from the text shown to the player and
        # always send a patch_last so the already-streamed text is updated.
        history_text = _DELTA_BLOCK_RE.sub("", history_text).strip()
        yield f"data: {json.dumps({'type': 'patch_last', 'content': history_text})}\n\n"

        for _dm in _delta_matches:
            try:
                _npc_name  = (_dm.group("npc") or "").strip()
                _npc_dir   = _get_npc_index().npc_dir_for(_npc_name)
                if _npc_dir is None:
                    continue
                _delta_path = _npc_dir / f"session_{session.session_number:03d}.md"
                _ts_now     = datetime.now().strftime("%H:%M:%S")
                _lines      = [f"## Turn {session.turn_number} — {_ts_now}"]
                if _dm.group("disposition"):
                    _lines.append(f"**Disposition:** {_dm.group('disposition').strip()}")
                if _dm.group("location"):
                    _lines.append(f"**Location:** {_dm.group('location').strip()}")
                if _dm.group("knowledge"):
                    _lines.append(f"**Knowledge:** {_dm.group('knowledge').strip()}")
                if _dm.group("summary"):
                    _lines.append(f"**Summary:** {_dm.group('summary').strip()}")
                _lines.append("")  # trailing blank line between entries
                with _delta_path.open("a", encoding="utf-8") as _df:
                    _df.write("\n".join(_lines) + "\n")
                _log(session, f"\n> *[Delta written: {_npc_name} → {_delta_path.name}]*\n")
            except Exception:
                pass  # delta writes are best-effort

    session.messages.append({"role": "assistant", "content": history_text})
    _log(session, f"\n### [{_ts()}] GM")
    _log(session, f"{history_text}\n")
    _log(session, "---\n")


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
    }
    with _groq_post(api_key, payload, stream=True) as resp:
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            if line == "data: [DONE]":
                break
            if not line.startswith("data: "):
                continue
            chunk = json.loads(line[6:])
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
