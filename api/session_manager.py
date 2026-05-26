from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests as _requests
from src.agents.gm_boot_agent import GMAgent, GMConfig

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTPUTS_DIR = _REPO_ROOT / "outputs"

_BOOT_USER_PROMPT = (
    "Begin the Session Boot now. Follow the boot protocol in the system message. "
    "Produce the opening narration and end with exactly: What do you do?"
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


@dataclass
class GameSession:
    id: str
    session_number: int
    model: str
    host: str
    temperature: float
    dev_mode: bool = False
    system_prompt: str = ""
    messages: list = field(default_factory=list)
    log_path: Optional[Path] = None


_sessions: dict[str, GameSession] = {}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _log(session: GameSession, text: str) -> None:
    if session.log_path is None:
        return
    with session.log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def create_session(
    session_number: int,
    model: str,
    host: str = "http://localhost:11434",
    temperature: float = 0.3,
    dev_mode: bool = False,
) -> GameSession:
    if dev_mode:
        system_prompt = _DEV_SYSTEM_PROMPT
    else:
        config = GMConfig(
            ollama_host=host,
            ollama_model=model,
            temperature=temperature,
        )
        agent = GMAgent(config)
        agent.load_boot_contexts()
        system_prompt = agent.build_boot_system_prompt(session_number=session_number)

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
        system_prompt=system_prompt,
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
    prompt = _DEV_BOOT_USER_PROMPT if session.dev_mode else _BOOT_USER_PROMPT
    session.messages.append({"role": "user", "content": prompt})
    try:
        yield from _stream_chat(session)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return
    yield f"data: {json.dumps({'type': 'done', 'session_id': session.id})}\n\n"


def stream_turn(session: GameSession, user_input: str) -> Generator[str, None, None]:
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
    max_hist = _DEV_MAX_HISTORY if session.dev_mode else _FULL_MAX_HISTORY
    history = session.messages[-max_hist:] if len(session.messages) > max_hist else session.messages
    messages = [{"role": "system", "content": session.system_prompt}] + history
    options: dict = {"temperature": session.temperature}
    if session.dev_mode:
        options["num_predict"] = _DEV_MAX_TOKENS
    accumulated: list[str] = []

    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    _log(session, f"\n### [{_ts()}] PLAYER")
    _log(session, f"{last_user}\n")

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
