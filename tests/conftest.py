"""Shared fixtures and helpers for RotRL API tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

_REAL_OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_outputs():
    """Safety-net fixture — kept as a no-op.

    The client fixture redirects all writes to tmp_path so the real
    outputs/ directory is never touched during test runs.  Real api_log
    and session log files are intentionally preserved for post-run
    inspection; this fixture no longer deletes them.
    """
    yield


# ── SSE helper ────────────────────────────────────────────────────────────────

def parse_sse(response) -> list[dict]:
    """Parse a streaming SSE response into a list of event dicts."""
    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ── Ollama mock helpers ───────────────────────────────────────────────────────

def make_stream_response(tokens: list[str]) -> MagicMock:
    """Build a mock requests response that streams the given tokens."""
    lines = [
        json.dumps({"message": {"content": t}, "done": False}).encode()
        for t in tokens
    ]
    lines.append(json.dumps({"message": {"content": ""}, "done": True}).encode())

    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.iter_lines = MagicMock(return_value=iter(lines))
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def make_blocking_response(content: str) -> MagicMock:
    """Build a mock requests response for a non-streaming Ollama call."""
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json = MagicMock(return_value={"message": {"content": content}})
    return mock


# ── Core fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with outputs redirected to tmp_path.
    Starts fresh — no leftover sessions or cached indexes between tests.
    """
    import api.session_manager as sm
    import api.api_logger as api_logger

    # Redirect outputs to a temp directory
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(api_logger, "_API_LOG_DIR", tmp_path / "outputs" / "api_log")
    # Clear in-memory session registry between tests
    monkeypatch.setattr(sm, "_sessions", {})
    # Reset lazy-loaded NPC/skill indexes so tests that monkeypatch _REPO_ROOT
    # don't get the real repo's index from a previous test run.
    monkeypatch.setattr(sm, "_npc_index", None)
    monkeypatch.setattr(sm, "_skill_index", None)
    monkeypatch.setattr(sm, "_location_index", None)
    monkeypatch.setattr(sm, "_event_index", None)

    from api.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def booted_session(client, monkeypatch):
    """Boot a session and return (client, session_id).
    Ollama is NOT called during boot — this is purely in-memory setup.
    """
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "host": "http://localhost:11434",
        "temperature": 0.3,
        "dev_mode": True,   # dev mode: no file reads, minimal prompt
    })
    assert resp.status_code == 200
    events = parse_sse(resp)
    done = next(e for e in events if e["type"] == "done")
    return client, done["session_id"]


@pytest.fixture()
def sample_log(tmp_path) -> Path:
    """Write a minimal but realistic session log to tmp_path and return its path."""
    log = tmp_path / "session_001_test.log.md"
    log.write_text(
        """\
# Session 001 — 2026-05-26 19:46:04
Model: `qwen3:4b` | Mode: full | Temp: 0.3

## System Prompt

```
You are the Game Master...
```

---


## Boot complete — waiting for first player input


> *[Context injected at turn 1: GM Operating Rules — Critical]*


### [19:47:08] PLAYER
Ani wants to talk to father Zantus. Vanx looks at the cathedral.


<details><summary>LLM payload — turn 1</summary>

**[SYSTEM]**
```
(system prompt here)
```

**[USER]**
```
Ani wants to talk to father Zantus.
```

</details>


### [19:49:49] GM
Father Zantus turns from the altar as Ani approaches, his expression calm and welcoming.
The cathedral smells of fresh timber and candle wax.

---


> *[Context injected at turn 2: Act 01 Overview]*


### [19:52:00] PLAYER
Ani asks Zantus about Desna.


<details><summary>LLM payload — turn 2</summary>

**[SYSTEM]**
```
(longer system prompt)
```

</details>


### [19:54:10] GM
Zantus smiles and speaks of Desna as the goddess of dreams and stars.
He says the festival honours her role as protector of travellers.

---


## Session Ended — 19:55:00
Total exchanges: 2
""",
        encoding="utf-8",
    )
    return log
