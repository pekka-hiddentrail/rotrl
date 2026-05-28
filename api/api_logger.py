"""API call logger — writes one JSON file per LLM request to outputs/api_log/.

Each file contains:
  - "raw_request"  : the exact JSON body posted to the API (Groq or Ollama)
  - "raw_response" : the full text that came back (assembled from the stream)
  - metadata       : session/turn info, timing, status

File naming:
  YYYYMMDD_HHMMSS_mmm_{provider}_s{session}_t{turn}_{session_id[:8]}.json

Example:
  20260527_113201_042_groq_s001_t003_a1b2c3d4.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

_API_LOG_DIR = Path(__file__).resolve().parent.parent / "outputs" / "api_log"


def write_api_log(
    *,
    provider: str,
    session_id: str,
    session_number: int,
    turn: int,
    raw_request: dict,       # the exact payload posted to the API — nothing added or removed
    response_text: str,
    duration_ms: int,
    status: str = "ok",
    error: Optional[str] = None,
    usage: Optional[dict] = None,  # token counts from Groq (prompt/completion/total)
) -> Path:
    """Write a single API call log file.  Returns the path written."""
    _API_LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    ts  = now.strftime("%Y%m%d_%H%M%S_") + f"{now.microsecond // 1000:03d}"
    sid = session_id[:8]
    filename = f"{ts}_{provider}_s{session_number:03d}_t{turn:03d}_{sid}.json"

    messages = raw_request.get("messages", [])

    # Quick-scan summary — lets you skim without reading the full system prompt
    message_summary = []
    for m in messages:
        content = m.get("content", "")
        message_summary.append({
            "role":    m.get("role", "?"),
            "chars":   len(content),
            "preview": (content[:200] + "…") if len(content) > 200 else content,
        })

    data = {
        "timestamp":      now.isoformat(timespec="milliseconds"),
        "provider":       provider,
        "session_id":     session_id,
        "session_number": session_number,
        "turn":           turn,
        "status":         status,
        "duration_ms":    duration_ms,
        "usage":          usage,  # None for Ollama; {prompt_tokens, completion_tokens, total_tokens} for Groq

        # ── Exact payload sent to the API ─────────────────────────────────────
        # This is identical to what Groq / Ollama received.  Nothing added.
        "raw_request": raw_request,

        # ── Quick-scan summary (spare yourself scrolling past the full prompt) ─
        "summary": {
            "model":         raw_request.get("model", ""),
            "message_count": len(messages),
            "total_chars":   sum(len(m.get("content", "")) for m in messages),
            "messages":      message_summary,
        },

        # ── Full response text (assembled from the streamed chunks) ───────────
        "raw_response": response_text,

        "error": error,
    }

    path = _API_LOG_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
