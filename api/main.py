from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from api.session_manager import create_session, get_session, list_session_npcs, log_roll, purge_session_npcs, resolve_attack_roll, resolve_damage_roll, resolve_roll, save_session, stream_boot, stream_end_session, stream_resume_combat, stream_turn

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
    model: str = "llama-3.3-70b-versatile"
    host: str = "http://localhost:11434"
    temperature: float = 0.3
    dev_mode: bool = False
    provider: str = "ollama"  # "ollama" | "groq" | "anthropic"
    num_ctx: int = 2048       # context window — smaller = faster (Ollama only)
    num_gpu: int = 999        # GPU layers — 999 = push everything to GPU (Ollama only)


class TurnRequest(BaseModel):
    input: str


class RollRequest(BaseModel):
    expr: str
    rolls: list[int]
    total: int


@app.get("/api/health")
def get_health():
    """Liveness check — the UI hits this before boot to confirm the backend is up."""
    return {"status": "ok"}


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
    if req.session_number > 1:
        sessions_dir = _REPO_ROOT / "sessions"
        boot = sessions_dir / f"session_{req.session_number:03d}" / "boot.md"
        recap = sessions_dir / f"session_{req.session_number - 1:03d}" / "recap.md"
        if not boot.exists() and not recap.exists():
            raise HTTPException(
                status_code=400,
                detail=f"No boot context found for session {req.session_number}. "
                       f"Expected sessions/session_{req.session_number:03d}/boot.md "
                       f"or sessions/session_{req.session_number - 1:03d}/recap.md.",
            )
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


class ResolveRollRequest(BaseModel):
    rolled: int


@app.post("/api/sessions/{session_id}/resolve_roll")
def post_resolve_roll(session_id: str, req: ResolveRollRequest):
    """Resolve a pending dice roll: compare against DC, record outcome in history."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.pending_roll:
        raise HTTPException(status_code=409, detail="No pending roll for this session")
    try:
        result = resolve_roll(session, req.rolled)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return result


class ResolveAttackRollRequest(BaseModel):
    rolled: int


class ResolveDamageRollRequest(BaseModel):
    rolls: list[int]
    total: int


@app.post("/api/sessions/{session_id}/resolve_attack_roll")
def post_resolve_attack_roll(session_id: str, req: ResolveAttackRollRequest):
    """Process a player's to-hit roll for the first queued PC attack."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.attack_queue:
        raise HTTPException(status_code=409, detail="No pending attack roll")
    try:
        return resolve_attack_roll(session, req.rolled)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/sessions/{session_id}/resolve_damage_roll")
def post_resolve_damage_roll(session_id: str, req: ResolveDamageRollRequest):
    """Process a player's damage roll for the current hit PC attack."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.attack_queue or not session.attack_queue[0].hit:
        raise HTTPException(status_code=409, detail="No pending damage roll")
    try:
        return resolve_damage_roll(session, req.rolls, req.total)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/sessions/{session_id}/resume_combat")
def post_resume_combat(session_id: str):
    """Inject resolved attack results into history and call LLM to narrate outcomes."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.attack_queue:
        raise HTTPException(status_code=409, detail="Attack queue not empty — resolve all PC attacks first")
    return StreamingResponse(stream_resume_combat(session), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.delete("/api/sessions/{session_id}/combat")
def delete_combat(session_id: str):
    """Clear the active combat state (End Combat button in UI)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.combat_state = None
    return {"combat_state": None}


@app.post("/api/sessions/{session_id}/end")
def end_session(session_id: str):
    """Generate recap + boot files for the next session, then save and close."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(stream_end_session(session), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.get("/api/log/api")
def list_api_logs(limit: int = 50):
    """List the most recent API call log files (newest first)."""
    log_dir = _REPO_ROOT / "outputs" / "api_log"
    if not log_dir.exists():
        return JSONResponse({"files": []})
    files = sorted(log_dir.glob("*.json"), key=lambda p: p.name, reverse=True)[:limit]
    return JSONResponse({
        "files": [
            {"name": f.name, "size_bytes": f.stat().st_size}
            for f in files
        ]
    })


@app.get("/api/log/api/{filename}")
def get_api_log(filename: str):
    """Return a single API call log file as JSON."""
    # Sanitise: only allow filenames with safe characters (no path traversal)
    import re as _re
    if not _re.fullmatch(r"[\w.\-]+\.json", filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    log_dir = (_REPO_ROOT / "outputs" / "api_log").resolve()
    path = (log_dir / filename).resolve()
    if not path.is_relative_to(log_dir):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    import json as _json
    return JSONResponse(_json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/characters")
def get_characters():
    """Return all character data from ui/public/data/ as a list."""
    data_dir = (_REPO_ROOT / "ui" / "public" / "data").resolve()
    index_path = data_dir / "characters.json"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="characters.json not found")
    import json as _json
    ids: list[str] = _json.loads(index_path.read_text(encoding="utf-8"))
    characters = []
    for cid in ids:
        if not isinstance(cid, str):
            raise HTTPException(status_code=400, detail="Invalid character ID")
        path = (data_dir / f"{cid}.json").resolve()
        if not path.is_relative_to(data_dir):
            raise HTTPException(status_code=400, detail="Invalid character ID")
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"{cid}.json not found")
        characters.append(_json.loads(path.read_text(encoding="utf-8")))
    return characters


@app.get("/api/npcs/session")
def get_session_npcs():
    """List all auto-created session NPC slugs (dot-prefixed directories)."""
    return {"npcs": list_session_npcs()}


@app.delete("/api/npcs/session")
def delete_session_npcs():
    """Purge all session NPC directories and invalidate the NPC index."""
    count = purge_session_npcs()
    return {"purged": count}


@app.get("/api/benchmarks")
def get_benchmarks():
    """Return all token benchmark rows from outputs/token_benchmarks.csv as JSON."""
    import csv as _csv
    csv_path = _REPO_ROOT / "outputs" / "token_benchmarks.csv"
    if not csv_path.exists():
        return JSONResponse({"rows": []})
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            for k in ("prompt_tokens", "completion_tokens", "total_tokens", "system_chars"):
                try:
                    row[k] = int(row[k])
                except (ValueError, KeyError):
                    row[k] = 0
            rows.append(row)
    return JSONResponse({"rows": rows})


@app.get("/api/coverage")
def get_coverage():
    """Return the feature AC coverage matrix built by scripts/build_coverage.py.

    Returns an empty matrix if outputs/coverage.json does not exist yet.
    Run `python scripts/build_coverage.py` to generate it.
    """
    import json as _json
    path = _REPO_ROOT / "outputs" / "coverage.json"
    if not path.exists():
        return JSONResponse({"generated": None, "summary": {"total": 0, "covered": 0, "gap": 0}, "rows": []})
    return JSONResponse(_json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/code-coverage")
def get_code_coverage():
    """Return pytest-cov line coverage data with optional delta from previous run.

    Generate with: pytest --cov --cov-report=json
    The .coveragerc [json] section writes to outputs/code_coverage.json.
    Create a baseline for delta tracking with: python scripts/snapshot_coverage.py
    """
    import json as _json
    path      = _REPO_ROOT / "outputs" / "code_coverage.json"
    prev_path = _REPO_ROOT / "outputs" / "code_coverage_prev.json"
    if not path.exists():
        return JSONResponse({
            "generated": None, "files": [], "has_prev": False,
            "total_stmts": 0, "total_miss": 0, "total_pct": 0, "total_pct_delta": None,
        })
    raw = _json.loads(path.read_text(encoding="utf-8"))

    # Build per-file pct lookup from the previous run (if snapshot exists)
    prev_pct: dict[str, int] = {}
    if prev_path.exists():
        try:
            prev_raw = _json.loads(prev_path.read_text(encoding="utf-8"))
            for fname, fdata in prev_raw.get("files", {}).items():
                norm = fname.replace("\\", "/")
                prev_pct[norm] = round(fdata.get("summary", {}).get("percent_covered", 0))
        except Exception:
            pass
    has_prev = bool(prev_pct)

    files = []
    for fname, fdata in raw.get("files", {}).items():
        summary = fdata.get("summary", {})
        stmts = summary.get("num_statements", 0)
        miss  = summary.get("missing_lines", 0)
        pct   = round(summary.get("percent_covered", 0))
        norm  = fname.replace("\\", "/")
        delta = (pct - prev_pct[norm]) if norm in prev_pct else None
        files.append({
            "name": norm,
            "stmts": stmts,
            "miss": miss,
            "covered": stmts - miss,
            "pct": pct,
            "delta": delta,
            "missing_lines": fdata.get("missing_lines", []),
        })
    files.sort(key=lambda f: f["pct"])

    totals     = raw.get("totals", {})
    total_pct  = round(totals.get("percent_covered", 0))
    prev_total = round(sum(prev_pct.values()) / len(prev_pct)) if prev_pct else None
    total_delta = (total_pct - prev_total) if prev_total is not None else None

    return JSONResponse({
        "generated":        raw.get("meta", {}).get("timestamp"),
        "files":            files,
        "has_prev":         has_prev,
        "total_stmts":      totals.get("num_statements", 0),
        "total_miss":       totals.get("missing_lines", 0),
        "total_pct":        total_pct,
        "total_pct_delta":  total_delta,
    })


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Discard session without generating recap (emergency close)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    saved_to = save_session(session)
    return {"saved_to": str(saved_to)}
