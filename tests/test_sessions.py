"""Tests for session lifecycle: boot, info, roll, delete."""
from __future__ import annotations

from .conftest import parse_sse


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_boot_returns_session_id(client):
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "model": "qwen3:4b",
        "dev_mode": True,
    })
    assert resp.status_code == 200
    events = parse_sse(resp)
    done = next((e for e in events if e["type"] == "done"), None)
    assert done is not None
    assert "session_id" in done
    assert len(done["session_id"]) == 36  # UUID


def test_boot_creates_log_file(client, tmp_path):
    import api.session_manager as sm
    # _OUTPUTS_DIR is already pointed at tmp_path/outputs by the client fixture
    resp = client.post("/api/sessions", json={
        "session_number": 1,
        "dev_mode": True,
    })
    assert resp.status_code == 200
    log_files = list((tmp_path / "outputs").glob("*.log.md"))
    assert len(log_files) == 1


def test_get_session_info(booted_session):
    client, session_id = booted_session
    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session_id
    assert data["session_number"] == 1


def test_get_unknown_session_404(client):
    resp = client.get("/api/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_log_endpoint_returns_text(booted_session):
    client, session_id = booted_session
    resp = client.get(f"/api/sessions/{session_id}/log")
    assert resp.status_code == 200
    assert "Session" in resp.text     # log header written at boot


def test_log_404_for_unknown_session(client):
    resp = client.get("/api/sessions/bad-id/log")
    assert resp.status_code == 404


def test_roll_logged(booted_session):
    client, session_id = booted_session
    resp = client.post(f"/api/sessions/{session_id}/roll", json={
        "expr": "1d20",
        "rolls": [14],
        "total": 14,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify the roll appears in the log
    log_resp = client.get(f"/api/sessions/{session_id}/log")
    assert "1d20" in log_resp.text
    assert "14" in log_resp.text


def test_delete_session_saves_and_removes(booted_session, tmp_path):
    client, session_id = booted_session
    resp = client.delete(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert "saved_to" in resp.json()

    # Session should no longer exist in memory
    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 404


def test_delete_unknown_session_404(client):
    resp = client.delete("/api/sessions/nonexistent")
    assert resp.status_code == 404


def test_boot_invalid_session_returns_400(client, tmp_path, monkeypatch):
    """Booting a session number with no boot/recap context returns 400."""
    import api.main as main_mod
    monkeypatch.setattr(main_mod, "_REPO_ROOT", tmp_path)
    # tmp_path has no sessions/ directory, so session 99 has no context files.
    resp = client.post("/api/sessions", json={"session_number": 99, "model": "qwen3:4b"})
    assert resp.status_code == 400
    assert "99" in resp.json()["detail"]


# ── Purge session NPCs ────────────────────────────────────────────────────────

def test_purge_session_npcs_removes_dot_dirs(client, monkeypatch, tmp_path):
    import api.session_manager as sm
    npc_base = tmp_path / "adventure_path" / "01_npcs"
    (npc_base / ".temp_guard").mkdir(parents=True)
    (npc_base / ".unnamed_merchant").mkdir()
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_npc_index", None)

    resp = client.delete("/api/npcs/session")
    assert resp.status_code == 200
    assert resp.json()["purged"] == 2
    assert not (npc_base / ".temp_guard").exists()
    assert not (npc_base / ".unnamed_merchant").exists()


def test_purge_session_npcs_keeps_canonical_dirs(client, monkeypatch, tmp_path):
    import api.session_manager as sm
    npc_base = tmp_path / "adventure_path" / "01_npcs"
    (npc_base / "ameiko_kaijitsu").mkdir(parents=True)
    (npc_base / ".temp_guard").mkdir()
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_npc_index", None)

    resp = client.delete("/api/npcs/session")
    assert resp.json()["purged"] == 1
    assert (npc_base / "ameiko_kaijitsu").exists()


def test_purge_session_npcs_returns_zero_when_none(client, monkeypatch, tmp_path):
    import api.session_manager as sm
    npc_base = tmp_path / "adventure_path" / "01_npcs"
    npc_base.mkdir(parents=True)
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    resp = client.delete("/api/npcs/session")
    assert resp.status_code == 200
    assert resp.json()["purged"] == 0


def test_list_session_npcs(client, monkeypatch, tmp_path):
    import api.session_manager as sm
    npc_base = tmp_path / "adventure_path" / "01_npcs"
    (npc_base / ".temp_guard").mkdir(parents=True)
    (npc_base / ".unnamed_merchant").mkdir()
    (npc_base / "ameiko_kaijitsu").mkdir()
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    resp = client.get("/api/npcs/session")
    assert resp.status_code == 200
    slugs = resp.json()["npcs"]
    assert sorted(slugs) == ["temp_guard", "unnamed_merchant"]  # dot stripped
