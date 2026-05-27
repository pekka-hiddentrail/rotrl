"""Tests for GET /api/intro — intro card file resolution."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def intro_client(tmp_path, monkeypatch):
    """Client with _REPO_ROOT in main.py redirected to tmp_path
    so we can control which session files exist."""
    import api.main as main_mod
    import api.session_manager as sm
    monkeypatch.setattr(main_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    from api.main import app
    with TestClient(app) as c:
        yield c, tmp_path


def _make_session_file(base: Path, session: int, filename: str, content: str):
    d = base / "sessions" / f"session_{session:03d}"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(content, encoding="utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_intro_returns_intro_md(intro_client):
    client, tmp = intro_client
    _make_session_file(tmp, 1, "intro.md", "# Session 1\n\nWelcome to Sandpoint.")
    resp = client.get("/api/intro?session=1")
    assert resp.status_code == 200
    assert "Welcome to Sandpoint" in resp.text


def test_intro_session2_falls_back_to_recap(intro_client):
    """Session 2 has no intro.md — should serve session_001/recap.md."""
    client, tmp = intro_client
    _make_session_file(tmp, 1, "recap.md", "# Session 1 — Recap\n\nLast time…")
    resp = client.get("/api/intro?session=2")
    assert resp.status_code == 200
    assert "Last time" in resp.text


def test_intro_fallback_to_session1_intro(intro_client):
    """No session-specific files — falls back to session_001/intro.md."""
    client, tmp = intro_client
    _make_session_file(tmp, 1, "intro.md", "# Session 1\n\nCampaign opener.")
    resp = client.get("/api/intro?session=3")
    assert resp.status_code == 200
    assert "Campaign opener" in resp.text


def test_intro_prefers_own_intro_over_recap(intro_client):
    """session_002/intro.md should beat session_001/recap.md."""
    client, tmp = intro_client
    _make_session_file(tmp, 1, "recap.md", "# Recap\n\nOld recap.")
    _make_session_file(tmp, 2, "intro.md", "# Session 2\n\nHand-crafted intro.")
    resp = client.get("/api/intro?session=2")
    assert resp.status_code == 200
    assert "Hand-crafted intro" in resp.text


def test_intro_404_when_nothing_exists(intro_client):
    client, _ = intro_client
    resp = client.get("/api/intro?session=5")
    assert resp.status_code == 404
