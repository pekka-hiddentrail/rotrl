"""Tests for GET /api/log/api and GET /api/log/api/{filename} endpoints."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_log(log_dir: Path, name: str, content: dict = None) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / name
    path.write_text(json.dumps(content or {"test": "data"}), encoding="utf-8")
    return path


@pytest.fixture()
def api_log_dir(tmp_path, monkeypatch, client):
    """Point main._REPO_ROOT at tmp_path so log endpoints use the temp dir."""
    import api.main as main_mod
    monkeypatch.setattr(main_mod, "_REPO_ROOT", tmp_path)
    return tmp_path / "outputs" / "api_log"


# ── GET /api/log/api ──────────────────────────────────────────────────────────

def test_list_logs_empty(client, api_log_dir):
    resp = client.get("/api/log/api")
    assert resp.status_code == 200
    assert resp.json() == {"files": []}


def test_list_logs_shows_files(client, api_log_dir):
    _make_log(api_log_dir, "20260528_120000_000_groq_s001_t001_abc12345.json")
    _make_log(api_log_dir, "20260528_120001_000_groq_s001_t002_abc12345.json")
    data = client.get("/api/log/api").json()
    assert len(data["files"]) == 2


def test_list_logs_has_size_bytes(client, api_log_dir):
    _make_log(api_log_dir, "20260528_120000_000_groq_s001_t001_abc12345.json", {"x": "y"})
    files = client.get("/api/log/api").json()["files"]
    assert "size_bytes" in files[0]
    assert files[0]["size_bytes"] > 0


def test_list_logs_newest_first(client, api_log_dir):
    _make_log(api_log_dir, "20260528_120000_000_groq_s001_t001_aaa.json")
    _make_log(api_log_dir, "20260528_120002_000_groq_s001_t002_bbb.json")
    _make_log(api_log_dir, "20260528_120001_000_groq_s001_t003_ccc.json")
    files = client.get("/api/log/api").json()["files"]
    names = [f["name"] for f in files]
    assert names == sorted(names, reverse=True)


def test_list_logs_limit_param(client, api_log_dir):
    for i in range(5):
        _make_log(api_log_dir, f"20260528_12000{i}_000_groq_s001_t00{i}_abc.json")
    files = client.get("/api/log/api?limit=3").json()["files"]
    assert len(files) == 3


# ── GET /api/log/api/{filename} ───────────────────────────────────────────────

def test_get_log_returns_content(client, api_log_dir):
    content = {"provider": "groq", "turn": 3}
    _make_log(api_log_dir, "20260528_120000_000_groq_s001_t003_abc12345.json", content)
    resp = client.get("/api/log/api/20260528_120000_000_groq_s001_t003_abc12345.json")
    assert resp.status_code == 200
    assert resp.json()["provider"] == "groq"
    assert resp.json()["turn"] == 3


def test_get_log_not_found_returns_404(client, api_log_dir):
    api_log_dir.mkdir(parents=True, exist_ok=True)
    resp = client.get("/api/log/api/20260528_999999_000_groq_s001_t001_missing.json")
    assert resp.status_code == 404


def test_get_log_invalid_filename_rejected(client, api_log_dir):
    # Spaces and special chars — rejected by the regex validator
    resp = client.get("/api/log/api/evil file.json")
    assert resp.status_code in (400, 404, 422)


def test_get_log_semicolon_rejected(client, api_log_dir):
    resp = client.get("/api/log/api/foo;bar.json")
    assert resp.status_code in (400, 404, 422)


def test_get_log_path_traversal_double_dot(client, api_log_dir):
    # FastAPI path parameter with ../ — should be rejected or not match
    resp = client.get("/api/log/api/..%2Fsecret.json")
    assert resp.status_code in (400, 404, 422)
