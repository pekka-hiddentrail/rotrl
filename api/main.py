from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.session_manager import create_session, get_session, save_session, stream_boot, stream_turn

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


class TurnRequest(BaseModel):
    input: str


@app.post("/api/sessions")
def post_sessions(req: BootRequest):
    try:
        session = create_session(req.session_number, req.model, req.host, req.temperature, req.dev_mode)
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


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    saved_to = save_session(session)
    return {"saved_to": str(saved_to)}
