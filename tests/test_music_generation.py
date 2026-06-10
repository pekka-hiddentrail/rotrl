from __future__ import annotations

from api.music import (
    DEFAULT_CALM_CONFIG,
    degree_to_note,
    generate_calm_phrase,
    midi_to_freq,
    note_to_midi,
)


def _lead_events(phrase):
    track = next(t for t in phrase.tracks if t.role == "lead")
    return track.events


def _bar_totals(events):
    totals = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    beats = {"8n": 0.5, "4n": 1.0, "2n": 2.0}
    for e in events:
        totals[e.bar] += beats[e.duration]
    return totals


def test_degree_to_note_and_midi_mapping():
    note, midi = degree_to_note(1, 5)
    assert note == "C5"
    assert midi == 72
    assert note_to_midi("G4") == 67
    assert round(midi_to_freq(69), 2) == 440.00


def test_generate_phrase_bar_totals_exactly_four_beats():
    phrase = generate_calm_phrase(seed=12345)
    totals = _bar_totals(_lead_events(phrase))
    assert totals == {1: 4.0, 2: 4.0, 3: 4.0, 4: 4.0}


def test_cadence_degree_always_valid():
    phrase = generate_calm_phrase(seed=4321)
    assert phrase.state.cadence_degree in {1, 3, 5}
    assert _lead_events(phrase)[-1].note[0] in {"C", "E", "G"}


def test_deterministic_with_same_seed_and_null_state():
    p1 = generate_calm_phrase(seed=2222)
    p2 = generate_calm_phrase(seed=2222)
    assert p1.phrase_id == p2.phrase_id
    assert p1.tracks == p2.tracks
    assert p1.state == p2.state


def _full_state_dict(state):
    return {
        "motif_id": state.motif_id,
        "motif_degrees": state.motif_degrees,
        "cadence_degree": state.cadence_degree,
        "highest_degree": state.highest_degree,
        "novelty": state.novelty,
        "bass_pattern_id": state.bass_pattern_id,
        "bass_final_degree": state.bass_final_degree,
    }


def test_deterministic_with_same_seed_and_previous_state():
    p1 = generate_calm_phrase(seed=9001)
    prev = _full_state_dict(p1.state)
    p2 = generate_calm_phrase(seed=9002, previous_state=prev)
    p3 = generate_calm_phrase(seed=9002, previous_state=prev)
    assert p2.phrase_id == p3.phrase_id
    assert p2.tracks == p3.tracks
    assert p2.state == p3.state


def test_all_notes_within_register():
    phrase = generate_calm_phrase(seed=777)
    for e in _lead_events(phrase):
        assert DEFAULT_CALM_CONFIG.register_low_midi <= e.midi <= DEFAULT_CALM_CONFIG.register_high_midi


def test_no_pitch_repeats_more_than_four_times_per_bar():
    phrase = generate_calm_phrase(seed=888)
    by_bar = {1: {}, 2: {}, 3: {}, 4: {}}
    for e in _lead_events(phrase):
        by_bar[e.bar][e.midi] = by_bar[e.bar].get(e.midi, 0) + 1
    for counts in by_bar.values():
        assert max(counts.values()) <= 4


def test_a5_appears_at_most_once_per_phrase():
    phrase = generate_calm_phrase(seed=999)
    a5_count = sum(1 for e in _lead_events(phrase) if e.midi == 81)
    assert a5_count <= 1


def test_phrase_contains_descending_interval():
    phrase = generate_calm_phrase(seed=13579)
    events = _lead_events(phrase)
    assert any(events[i + 1].midi < events[i].midi for i in range(len(events) - 1))


def test_eighth_note_ratio_is_calm_safe():
    phrase = generate_calm_phrase(seed=24680)
    events = _lead_events(phrase)
    eighth = sum(1 for e in events if e.duration == "8n")
    ratio = eighth / len(events)
    assert ratio <= 0.60


def test_motif_state_carries_forward_to_next_phrase():
    p1 = generate_calm_phrase(seed=111)
    p2 = generate_calm_phrase(seed=112, previous_state=_full_state_dict(p1.state))
    assert p2.state.novelty == p1.state.novelty + 1
    assert len(p2.state.motif_degrees) >= 3


def test_phrase_has_lead_and_bass_tracks():
    phrase = generate_calm_phrase(seed=42)
    roles = {t.role for t in phrase.tracks}
    assert "lead" in roles
    assert "bass" in roles


def test_bass_track_events_within_bass_register():
    phrase = generate_calm_phrase(seed=55)
    bass = next(t for t in phrase.tracks if t.role == "bass")
    for e in bass.events:
        assert 36 <= e.midi <= 55, f"bass note {e.midi} outside C2-G3 register"


def test_bass_state_fields_present():
    phrase = generate_calm_phrase(seed=77)
    assert isinstance(phrase.state.bass_pattern_id, str)
    assert isinstance(phrase.state.bass_final_degree, int)
