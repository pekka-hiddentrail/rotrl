"""Tests for api/api_logger.py — write_api_log()."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import api.api_logger as logger_mod
from api.api_logger import write_api_log


@pytest.fixture(autouse=True)
def redirect_log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(logger_mod, "_API_LOG_DIR", tmp_path / "api_log")


def _req(msgs=None) -> dict:
    return {
        "model": "llama-3.3-70b-versatile",
        "messages": msgs or [
            {"role": "system", "content": "You are a GM."},
            {"role": "user", "content": "Hello!"},
        ],
        "stream": True,
        "temperature": 0.3,
    }


def test_creates_file():
    path = write_api_log(
        provider="groq", session_id="abc12345-xxxx",
        session_number=1, turn=1,
        raw_request=_req(), response_text="Narrative.", duration_ms=500,
    )
    assert path.exists()


def test_returns_path_object():
    result = write_api_log(
        provider="groq", session_id="path-test",
        session_number=1, turn=1,
        raw_request=_req(), response_text="", duration_ms=0,
    )
    assert isinstance(result, Path)


def test_filename_format():
    path = write_api_log(
        provider="groq", session_id="abc12345-xxxx",
        session_number=2, turn=3,
        raw_request=_req(), response_text="Text.", duration_ms=100,
    )
    assert re.match(r"\d{8}_\d{6}_\d{3}_groq_s002_t003_abc12345\.json", path.name)


def test_session_id_truncated_to_8():
    path = write_api_log(
        provider="groq", session_id="abcdefgh-ijkl-mnop",
        session_number=1, turn=1,
        raw_request=_req(), response_text="", duration_ms=0,
    )
    assert "abcdefgh" in path.name
    assert "ijkl" not in path.name


def test_json_structure():
    path = write_api_log(
        provider="groq", session_id="test-id-xx",
        session_number=1, turn=2,
        raw_request=_req(), response_text="Response.", duration_ms=750, status="ok",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["provider"] == "groq"
    assert data["session_number"] == 1
    assert data["turn"] == 2
    assert data["status"] == "ok"
    assert data["duration_ms"] == 750
    assert data["raw_response"] == "Response."
    assert data["error"] is None
    assert "raw_request" in data
    assert "summary" in data
    assert "timestamp" in data


def test_error_field_written():
    path = write_api_log(
        provider="groq", session_id="err-test",
        session_number=1, turn=1,
        raw_request=_req(), response_text="", duration_ms=50,
        status="error", error="Connection refused",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "error"
    assert data["error"] == "Connection refused"


def test_summary_message_count():
    msgs = [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "Player input."},
        {"role": "assistant", "content": "GM response."},
    ]
    path = write_api_log(
        provider="ollama", session_id="sum-test",
        session_number=1, turn=1,
        raw_request=_req(msgs), response_text="Done.", duration_ms=200,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["summary"]["message_count"] == 3
    assert data["summary"]["model"] == "llama-3.3-70b-versatile"
    assert data["summary"]["total_chars"] == sum(len(m["content"]) for m in msgs)


def test_summary_preview_truncated():
    long_content = "X" * 300
    msgs = [{"role": "system", "content": long_content}]
    path = write_api_log(
        provider="groq", session_id="trunc-test",
        session_number=1, turn=1,
        raw_request=_req(msgs), response_text="", duration_ms=10,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    preview = data["summary"]["messages"][0]["preview"]
    assert preview.endswith("…")
    assert len(preview) == 201  # 200 chars + ellipsis


def test_summary_short_content_not_truncated():
    msgs = [{"role": "user", "content": "Short."}]
    path = write_api_log(
        provider="groq", session_id="short-test",
        session_number=1, turn=1,
        raw_request=_req(msgs), response_text="", duration_ms=10,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    preview = data["summary"]["messages"][0]["preview"]
    assert preview == "Short."
    assert not preview.endswith("…")


def test_usage_field_written():
    usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    path = write_api_log(
        provider="groq", session_id="usage-test",
        session_number=1, turn=1,
        raw_request=_req(), response_text="Ok.", duration_ms=300,
        usage=usage,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["usage"] == usage


def test_usage_field_none_when_omitted():
    path = write_api_log(
        provider="ollama", session_id="no-usage",
        session_number=1, turn=1,
        raw_request=_req(), response_text="Ok.", duration_ms=100,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["usage"] is None


def test_chars_field_correct():
    msgs = [{"role": "user", "content": "ABCDE"}]
    path = write_api_log(
        provider="groq", session_id="chars-test",
        session_number=1, turn=1,
        raw_request=_req(msgs), response_text="", duration_ms=0,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["summary"]["messages"][0]["chars"] == 5
