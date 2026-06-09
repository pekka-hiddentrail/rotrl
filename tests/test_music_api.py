from __future__ import annotations

from api.music import GenerationFailedError


def test_post_music_calm_next_phrase_returns_valid_schema(client):
    resp = client.post(
        "/api/music/calm/next_phrase",
        json={"session_id": "demo", "seed": 12345, "previous_state": None},
    )
    assert resp.status_code == 200
    data = resp.json()

    for key in (
        "phrase_id",
        "mood",
        "key",
        "scale",
        "bpm",
        "time_signature",
        "bars",
        "events",
        "state",
    ):
        assert key in data

    assert data["mood"] == "calm"
    assert data["key"] == "C"
    assert data["scale"] == "major_pentatonic"
    assert 88 <= data["bpm"] <= 108
    assert data["time_signature"] == "4/4"
    assert data["bars"] == 4
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0

    sample = data["events"][0]
    assert set(sample.keys()) == {"bar", "beat", "note", "midi", "duration", "velocity"}

    state = data["state"]
    assert set(state.keys()) == {
        "motif_id",
        "motif_degrees",
        "cadence_degree",
        "highest_degree",
        "novelty",
    }


def test_post_music_calm_next_phrase_invalid_request_returns_422(client):
    resp = client.post(
        "/api/music/calm/next_phrase",
        json={"session_id": "demo", "seed": "not-an-int", "previous_state": None},
    )
    assert resp.status_code == 422


def test_post_music_calm_next_phrase_generation_failed_returns_structured_422(client, monkeypatch):
    import api.main as main

    def _raise(*_args, **_kwargs):
        raise GenerationFailedError(5, "validation_failed")

    monkeypatch.setattr(main, "generate_calm_phrase", _raise)

    resp = client.post(
        "/api/music/calm/next_phrase",
        json={"session_id": "demo", "seed": 12345, "previous_state": None},
    )
    assert resp.status_code == 422
    assert resp.json() == {
        "error": "generation_failed",
        "detail": "validation_failed",
        "attempts": 5,
    }
