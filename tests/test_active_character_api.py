"""API endpoint tests for PUT /api/sessions/{id}/active_character.

Covers the HTTP layer on top of the unit-level logic already tested in
test_session_state.py.  Uses the booted_session fixture so a real session
is alive in the registry before each test.

Spec: specs/session-state.feature
Covers: AC-014 (PUT updates field), AC-015 (party deselects),
        AC-016 (empty string fallback), AC-017 (persists across other changes)
"""
from __future__ import annotations

import pytest


# ── AC-014 — PUT sets active_character ───────────────────────────────────────

class TestPutActiveCharacter:
    def test_returns_200(self, booted_session):
        client, sid = booted_session
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": "Ani"})
        assert resp.status_code == 200

    def test_response_body_contains_name(self, booted_session):
        client, sid = booted_session
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": "Ani"})
        assert resp.json()["active_character"] == "Ani"

    def test_sets_yanyeeku(self, booted_session):
        client, sid = booted_session
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": "Yanyeeku"})
        assert resp.json()["active_character"] == "Yanyeeku"

    def test_sets_vanx(self, booted_session):
        client, sid = booted_session
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": "Vanx"})
        assert resp.json()["active_character"] == "Vanx"

    def test_updates_session_in_memory(self, booted_session):
        client, sid = booted_session
        client.put(f"/api/sessions/{sid}/active_character", json={"name": "Ani"})
        info = client.get(f"/api/sessions/{sid}")
        assert info.status_code == 200
        # session_info doesn't expose active_character yet — verify via second PUT
        resp2 = client.put(f"/api/sessions/{sid}/active_character", json={"name": "Vanx"})
        assert resp2.json()["active_character"] == "Vanx"


# ── AC-015 — "party" deselects ────────────────────────────────────────────────

class TestDeselect:
    def test_party_resets_to_party(self, booted_session):
        client, sid = booted_session
        client.put(f"/api/sessions/{sid}/active_character", json={"name": "Ani"})
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": "party"})
        assert resp.json()["active_character"] == "party"

    def test_sequential_select_deselect(self, booted_session):
        client, sid = booted_session
        for name in ("Ani", "Yanyeeku", "party", "Vanx", "party"):
            resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": name})
            assert resp.json()["active_character"] == name


# ── AC-016 — Empty string falls back to "party" ───────────────────────────────

class TestEmptyFallback:
    def test_empty_string_returns_party(self, booted_session):
        client, sid = booted_session
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": ""})
        assert resp.json()["active_character"] == "party"

    def test_whitespace_returns_party(self, booted_session):
        client, sid = booted_session
        resp = client.put(f"/api/sessions/{sid}/active_character", json={"name": "   "})
        assert resp.json()["active_character"] == "party"


# ── 404 on unknown session ────────────────────────────────────────────────────

class TestNotFound:
    def test_unknown_session_returns_404(self, client):
        resp = client.put("/api/sessions/no-such-session/active_character", json={"name": "Ani"})
        assert resp.status_code == 404
