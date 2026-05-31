from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_load_spec_acs_scans_nested_specs_and_flexible_headings(tmp_path, monkeypatch):
    import scripts.build_coverage as bc

    specs = tmp_path / "specs"
    nested = specs / "api"
    nested.mkdir(parents=True)
    (specs / "top-level.feature").write_text(
        """# FEATURE - Top Level

**ID:** top-level

### AC-001 - Hyphen heading
### AC-002 Second heading without dash
""",
        encoding="utf-8",
    )
    (nested / "new-api.feature").write_text(
        """# FEATURE - New API

**ID:** new-api

### AC-001: Colon heading
### AC-002 — Em dash heading
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(bc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bc, "SPECS_DIR", specs)

    acs = bc.load_spec_acs()

    assert set(acs) == {
        ("top-level", "AC-001"),
        ("top-level", "AC-002"),
        ("new-api", "AC-001"),
        ("new-api", "AC-002"),
    }
    assert acs[("new-api", "AC-001")].feature_file == "specs/api/new-api.feature"
    assert acs[("top-level", "AC-002")].title == "Second heading without dash"


def test_build_coverage_finds_new_ac_inventory_each_run(tmp_path, monkeypatch):
    import scripts.build_coverage as bc

    specs = tmp_path / "specs"
    tests = tmp_path / "tests"
    specs.mkdir()
    tests.mkdir()
    (specs / "fresh.feature").write_text(
        """# FEATURE - Fresh

**ID:** fresh

### AC-001 — First behavior
### AC-002 — Second behavior
### AC-003 — Newly added behavior
""",
        encoding="utf-8",
    )
    (tests / "test_fresh.py").write_text(
        '"""Spec: specs/fresh.feature\nAC-001 through AC-002"""\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(bc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bc, "SPECS_DIR", specs)
    monkeypatch.setattr(bc, "TESTS_DIR", tests)
    monkeypatch.setattr(bc, "UI_TESTS_DIR", tmp_path / "ui" / "src")
    monkeypatch.setattr(bc, "E2E_DIR", tmp_path / "ui" / "e2e")
    monkeypatch.setattr(bc, "EXPLORATORY_DIR", tmp_path / "tests" / "exploratory")

    data = bc.build_coverage()
    rows = {(r["feature_id"], r["ac_id"]): r for r in data["rows"]}

    assert data["summary"] == {"total": 3, "covered": 2, "gap": 1}
    assert rows[("fresh", "AC-001")]["pytest"] == ["test_fresh.py"]
    assert rows[("fresh", "AC-002")]["pytest"] == ["test_fresh.py"]
    assert rows[("fresh", "AC-003")]["status"] == "gap"


def test_coverage_endpoint_rebuilds_and_persists_matrix(tmp_path, monkeypatch):
    import scripts.build_coverage as bc
    from api.main import app

    output_path = tmp_path / "outputs" / "coverage.json"
    data = {
        "generated": "2026-05-31T00:00:00+00:00",
        "summary": {"total": 1, "covered": 0, "gap": 1},
        "rows": [
            {
                "feature_id": "fresh",
                "feature_file": "specs/fresh.feature",
                "ac_id": "AC-001",
                "title": "Fresh behavior",
                "pytest": [],
                "vitest": [],
                "playwright": [],
                "exploratory": [],
                "status": "gap",
            }
        ],
    }

    monkeypatch.setattr(bc, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(bc, "build_coverage", lambda: data)

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get("/api/coverage")

    assert resp.status_code == 200
    assert resp.json() == data
    assert json.loads(output_path.read_text(encoding="utf-8")) == data
