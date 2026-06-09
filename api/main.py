from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from api.session_manager import advance_combat_turn, create_session, get_session, list_session_npcs, log_roll, purge_session_npcs, resolve_attack_roll, resolve_damage_roll, resolve_roll, roll_combat_initiatives, save_session, set_active_character, stream_boot, stream_close_combat, stream_end_session, stream_enemy_turn, stream_pc_turn, stream_resume_combat, stream_turn, write_session_state

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
    event_scheduler: bool = False
    provider: str = "ollama"  # "ollama" | "groq" | "anthropic"
    num_ctx: int = 2048       # context window — smaller = faster (Ollama only)
    num_gpu: int = 999        # GPU layers — 999 = push everything to GPU (Ollama only)


class TurnRequest(BaseModel):
    input: str


class PcTurnRequest(BaseModel):
    input: str
    action_type_hint: str | None = None          # legacy single-hint (kept for compat)
    action_type_hints: list[str] | None = None   # multi-action hints (takes priority)
    target_hint: str | None = None


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
    if req.session_number > 1 and not req.dev_mode:
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
        session = create_session(req.session_number, req.model, req.host, req.temperature, req.dev_mode, req.num_ctx, req.num_gpu, req.provider, req.event_scheduler)
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


@app.get("/api/sessions/{session_id}/event_status")
def get_event_status(session_id: str):
    """Return event scheduler runtime state for the Event Status debug panel."""
    import dataclasses as _dc
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    rt = session.event_runtime
    return JSONResponse({
        "scheduler_enabled": session.event_scheduler,
        "turn_number": session.turn_number,
        "active_event_id": rt.active_event_id,
        "warm_events": {
            eid: _dc.asdict(we) for eid, we in rt.warm_events.items()
        },
        "completed_events": list(rt.completed_events),
        "cooldowns": dict(rt.cooldowns),
    })


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


@app.post("/api/sessions/{session_id}/pc_turn")
def post_pc_turn(session_id: str, req: PcTurnRequest):
    """Handle a PC combat turn: extract intent, queue attack from profile, emit attack_request.

    Routes the player's free-text action through backend intent extraction rather than
    relying on the LLM to write %%ATTACK%% blocks. No LLM call is made at this stage.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.combat_state is None:
        raise HTTPException(status_code=409, detail="No active combat")
    return StreamingResponse(stream_pc_turn(session, req.input, req.action_type_hint, req.target_hint, req.action_type_hints), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.post("/api/sessions/{session_id}/enemy_turn")
def post_enemy_turn(session_id: str):
    """Run the current enemy actor's turn using a focused LLM call."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.combat_state is None:
        raise HTTPException(status_code=409, detail="No active combat")
    if session.attack_queue:
        raise HTTPException(status_code=409, detail="Attack queue not empty - resolve PC attacks first")
    return StreamingResponse(stream_enemy_turn(session), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.post("/api/sessions/{session_id}/close_combat")
def post_close_combat(session_id: str):
    """Narrate combat closure, then clear the active combat state."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.combat_state is None:
        raise HTTPException(status_code=409, detail="No active combat")
    return StreamingResponse(stream_close_combat(session), media_type="text/event-stream", headers=_SSE_HEADERS)


@app.delete("/api/sessions/{session_id}/combat")
def delete_combat(session_id: str):
    """Clear the active combat state (End Combat button in UI)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.combat_state = None
    write_session_state(session)
    return {"combat_state": None}


@app.post("/api/sessions/{session_id}/combat/advance_turn")
def post_advance_combat_turn(session_id: str):
    """Advance the initiative to the next active combatant and write state.json.

    Returns { current_actor, is_pc, position, combatant_count, round, round_incremented }.
    round_incremented is true when the last combatant in the order wraps back to the first
    (end of round).  409 when no combat is active; 404 when session not found.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.combat_state is None:
        raise HTTPException(status_code=409, detail="No active combat")
    result = advance_combat_turn(session)
    return result


@app.post("/api/sessions/{session_id}/combat/roll_initiatives")
def post_roll_initiatives(session_id: str):
    """Roll d20 + modifier for every combatant and update initiative order.

    PCs use their initiative modifier from pc_profiles; enemies use +0 until
    SA-2 event-file seeding is implemented.  Returns the updated combat_state.
    409 when no combat is active; 404 when session not found.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.combat_state is None:
        raise HTTPException(status_code=409, detail="No active combat")
    combat_state = roll_combat_initiatives(session)
    return {"combat_state": combat_state}


class ActiveCharacterRequest(BaseModel):
    name: str  # PC name, or "party" to deselect


@app.put("/api/sessions/{session_id}/active_character")
def put_active_character(session_id: str, req: ActiveCharacterRequest):
    """Set the active character for the session (syncs UI selection to state.json)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    set_active_character(session, req.name)
    return {"active_character": session.active_character}


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


def _character_data_dir():
    return (_REPO_ROOT / "ui" / "public" / "data").resolve()


def _read_character_ids(data_dir):
    index_path = data_dir / "characters.json"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="characters.json not found")
    import json as _json
    ids: list[str] = _json.loads(index_path.read_text(encoding="utf-8"))
    for cid in ids:
        if not isinstance(cid, str):
            raise HTTPException(status_code=400, detail="Invalid character ID")
    return ids


def _read_character_file(data_dir, cid: str):
    if not isinstance(cid, str):
        raise HTTPException(status_code=400, detail="Invalid character ID")
    path = (data_dir / f"{cid}.json").resolve()
    if not path.is_relative_to(data_dir):
        raise HTTPException(status_code=400, detail="Invalid character ID")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{cid}.json not found")
    import json as _json
    return _json.loads(path.read_text(encoding="utf-8"))


def _character_summary(char: dict) -> dict:
    keys = (
        "id", "portrait", "color", "rune", "name", "player", "race",
        "subrace", "class", "archetype", "level", "hp",
    )
    return {k: char[k] for k in keys if k in char}


@app.get("/api/characters")
def get_characters():
    """Return lightweight character summaries for sidebar/splash UI."""
    data_dir = _character_data_dir()
    ids = _read_character_ids(data_dir)
    return [_character_summary(_read_character_file(data_dir, cid)) for cid in ids]


@app.get("/api/characters/{character_id}")
def get_character(character_id: str):
    """Return one full character sheet from ui/public/data/."""
    data_dir = _character_data_dir()
    ids = _read_character_ids(data_dir)
    if character_id not in ids:
        raise HTTPException(status_code=404, detail=f"{character_id}.json not found")
    return _read_character_file(data_dir, character_id)

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


@app.get("/api/benchmarks/combat")
def get_combat_benchmarks():
    """Return all combat benchmark rows from outputs/token_benchmarks_combat.csv as JSON."""
    import csv as _csv
    csv_path = _REPO_ROOT / "outputs" / "token_benchmarks_combat.csv"
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
            for k in ("combat_started", "attack_requested", "roll_requested"):
                try:
                    row[k] = int(row[k])
                except (ValueError, KeyError):
                    row[k] = 0
            rows.append(row)
    return JSONResponse({"rows": rows})


@app.get("/api/coverage")
def get_coverage():
    """Return a freshly rebuilt feature AC coverage matrix.

    The JSON file is still written to outputs/coverage.json for CLI/users, but
    the GUI does not depend on a stale file. If rebuilding fails, fall back to
    the last generated file and include refresh_error for visibility.
    """
    import json as _json
    empty = {"generated": None, "summary": {"total": 0, "covered": 0, "gap": 0}, "rows": []}
    path = _REPO_ROOT / "outputs" / "coverage.json"
    try:
        from scripts.build_coverage import OUTPUT_PATH as _COVERAGE_OUTPUT_PATH
        from scripts.build_coverage import build_coverage as _build_coverage

        data = _build_coverage()
        _COVERAGE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _COVERAGE_OUTPUT_PATH.write_text(_json.dumps(data, indent=2), encoding="utf-8")
        return JSONResponse(data)
    except Exception as e:
        if path.exists():
            data = _json.loads(path.read_text(encoding="utf-8"))
        else:
            data = empty
        data["refresh_error"] = str(e)
        return JSONResponse(data)


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
