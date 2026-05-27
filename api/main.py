from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from api.session_manager import create_session, get_session, log_roll, save_session, stream_boot, stream_end_session, stream_turn

_REPO_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="RotRL GM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class BootRequest(BaseModel):
    session_number: int = 1
    model: str = "qwen3:4b"
    host: str = "http://localhost:11434"
    temperature: float = 0.3
    dev_mode: bool = False
    provider: str = "ollama"  # "ollama" | "groq"
    num_ctx: int = 2048       # context window — smaller = faster (Ollama only)
    num_gpu: int = 999        # GPU layers — 999 = push everything to GPU (Ollama only)


class TurnRequest(BaseModel):
    input: str


class RollRequest(BaseModel):
    expr: str
    rolls: list[int]
    total: int


@app.get("/api/intro")
def get_intro(session: int = 1):
    """Return the player-facing intro markdown for a given session number.
    Lookup order:
      1. sessions/session_NNN/intro.md           (hand-written or generated)
      2. sessions/session_NNN-1/recap.md          (generated at end of prior session)
      3. sessions/session_001/intro.md            (fallback to campaign opener)
    """
    sessions_dir = _REPO_ROOT / "sessions"
    candidates = [
        sessions_dir / f"session_{session:03d}" / "intro.md",
    ]
    if session > 1:
        candidates.append(sessions_dir / f"session_{session - 1:03d}" / "recap.md")
    candidates.append(sessions_dir / "session_001" / "intro.md")

    for path in candidates:
        if path.exists():
            return PlainTextResponse(path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="No intro file found")


@app.post("/api/sessions")
def post_sessions(req: BootRequest):
    try:
        session = create_session(req.session_number, req.model, req.host, req.temperature, req.dev_mode, req.num_ctx, req.num_gpu, req.provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return StreamingResponse(stream_boot(session), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.post("/api/sessions/{session_id}/turn")
def post_turn(session_id: str, req: TurnRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(stream_turn(session, req.input), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.get("/api/sessions/{session_id}")
def get_session_info(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "session_number": session.session_number,
        "model": session.model,
        "message_count": len(session.messages),
    }


@app.get("/api/sessions/{session_id}/log")
def get_log(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.log_path is None or not session.log_path.exists():
        raise HTTPException(status_code=404, detail="No log file for this session")
    content = session.log_path.read_text(encoding="utf-8")
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")


@app.post("/api/sessions/{session_id}/roll")
def post_roll(session_id: str, req: RollRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    log_roll(session, req.expr, req.rolls, req.total)
    return {"ok": True}


@app.post("/api/sessions/{session_id}/end")
def end_session(session_id: str):
    """Generate recap + boot files for the next session, then save and close."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(stream_end_session(session), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Discard session without generating recap (emergency close)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    saved_to = save_session(session)
    return {"saved_to": str(saved_to)}
