"""Token count benchmark — tracks LLM prompt size across code changes.

Hits the real Anthropic API (claude-haiku-4-5-*). Automatically skipped when
ANTHROPIC_API_KEY is not set.

Run explicitly:
    pytest tests/test_token_benchmark.py -v -s
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from tests.conftest import parse_sse

_REAL_OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"
_BENCHMARK_CSV = _REAL_OUTPUTS / "token_benchmarks.csv"
_CSV_FIELDS = [
    "timestamp", "provider", "model", "session", "turn",
    "prompt_tokens", "completion_tokens", "total_tokens", "system_chars", "log_file",
]

_PROVIDER = "anthropic"
_MODEL = "claude-haiku-4-5-20251001"


def _latest_api_log_for_session(session_id: str) -> dict | None:
    """Return parsed contents of the most recent API log for *session_id*."""
    log_dir = _REAL_OUTPUTS / "api_log"
    if not log_dir.exists():
        return None
    # Filename format: YYYYMMDD_HHMMSS_mmm_{provider}_s{NNN}_t{TTT}_{sid8}.json
    sid8 = session_id[:8]
    candidates = list(log_dir.glob(f"*_{sid8}.json"))
    if not candidates:
        return None
    # Filenames sort chronologically — pick the last (most recent turn).
    latest = max(candidates, key=lambda f: f.name)
    data = json.loads(latest.read_text(encoding="utf-8"))
    data["_filename"] = latest.name
    return data


def _append_benchmark_row(row: dict) -> None:
    """Append one row to the persistent benchmark CSV, writing headers if needed."""
    _REAL_OUTPUTS.mkdir(parents=True, exist_ok=True)
    write_header = not _BENCHMARK_CSV.exists()
    with _BENCHMARK_CSV.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in _CSV_FIELDS})


def _extract_token_row(log_data: dict, run_ts: str, turn_num: int) -> dict:
    usage = log_data.get("usage") or {}
    raw_req = log_data.get("raw_request", {})
    # Anthropic puts system prompt at top level; Groq/Ollama use the system message role.
    system_text = raw_req.get("system", "")
    if not system_text:
        system_text = next(
            (m.get("content", "") for m in raw_req.get("messages", []) if m.get("role") == "system"),
            "",
        )
    prompt_tok = int(usage.get("prompt_tokens") or 0)
    compl_tok = int(usage.get("completion_tokens") or 0)
    total_tok = int(usage.get("total_tokens") or (prompt_tok + compl_tok))
    return {
        "timestamp": run_ts,
        "provider": log_data.get("provider", _PROVIDER),
        "model": (log_data.get("summary") or {}).get("model") or _MODEL,
        "session": log_data.get("session_id", "")[:8],
        "turn": turn_num,
        "prompt_tokens": prompt_tok,
        "completion_tokens": compl_tok,
        "total_tokens": total_tok,
        "system_chars": len(system_text),
        "log_file": log_data.get("_filename", ""),
    }


@pytest.mark.benchmark
def test_token_counts_three_turns(benchmark_client):
    """Boot an Anthropic Haiku session and record token counts for three benchmark turns.

    Turn 1 — scene arrival (Swallowtail festival)
    Turn 2 — social interaction (convince Hemlock)
    Turn 3 — after a dice roll, movement (Rusty Dragon)

    Results are appended to outputs/token_benchmarks.csv (never deleted).
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set — skipping real-API benchmark")

    run_ts = datetime.now().isoformat(timespec="seconds")

    # ── Boot ─────────────────────────────────────────────────────────────────
    resp = benchmark_client.post("/api/sessions", json={
        "session_number": 1,
        "model": _MODEL,
        "provider": _PROVIDER,
        "temperature": 0.3,
        "dev_mode": False,
    })
    assert resp.status_code == 200, f"Boot failed: {resp.text}"
    events = parse_sse(resp)
    done_evt = next((e for e in events if e.get("type") == "done"), None)
    assert done_evt and done_evt.get("session_id"), "Boot did not return a session_id"
    session_id: str = done_evt["session_id"]

    rows: list[dict] = []

    def _send_turn(input_text: str, benchmark_turn: int) -> None:
        r = benchmark_client.post(
            f"/api/sessions/{session_id}/turn",
            json={"input": input_text},
        )
        assert r.status_code == 200, f"Turn {benchmark_turn} failed: {r.text}"
        evts = parse_sse(r)
        assert any(e.get("type") == "done" for e in evts), \
            f"Turn {benchmark_turn} stream did not complete"
        log_data = _latest_api_log_for_session(session_id)
        assert log_data, f"No API log found for turn {benchmark_turn}"
        rows.append(_extract_token_row(log_data, run_ts, benchmark_turn))

    # ── Turn 1: scene arrival ─────────────────────────────────────────────────
    _send_turn("We arrive to the Swallowtail festival.", 1)

    # ── Turn 2: social interaction ────────────────────────────────────────────
    _send_turn("I try to convince Belor Hemlock to join me for a pint.", 2)

    # ── Dice roll then turn 3: movement ──────────────────────────────────────
    roll_resp = benchmark_client.post(
        f"/api/sessions/{session_id}/roll",
        json={"expr": "1d20", "rolls": [14], "total": 14},
    )
    assert roll_resp.status_code == 200, f"Roll failed: {roll_resp.text}"
    _send_turn("We head inside the Rusty Dragon.", 3)

    # ── Persist to CSV ────────────────────────────────────────────────────────
    for row in rows:
        _append_benchmark_row(row)
        print(
            f"\n[benchmark] turn={row['turn']}  "
            f"prompt={row['prompt_tokens']}  "
            f"completion={row['completion_tokens']}  "
            f"total={row['total_tokens']}  "
            f"sys_chars={row['system_chars']}"
        )
