from __future__ import annotations

from api.music import (
    DEFAULT_CALM_CONFIG,
    degree_to_note,
    generate_calm_phrase,
    midi_to_freq,
    note_to_midi,
)


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
    totals = _bar_totals(phrase.events)
    assert totals == {1: 4.0, 2: 4.0, 3: 4.0, 4: 4.0}


def test_cadence_degree_always_valid():
    phrase = generate_calm_phrase(seed=4321)
    assert phrase.state.cadence_degree in {1, 3, 5}
    assert phrase.events[-1].note[0] in {"C", "E", "G"}


def test_deterministic_with_same_seed_and_null_state():
    p1 = generate_calm_phrase(seed=2222)
    p2 = generate_calm_phrase(seed=2222)
    assert p1.phrase_id == p2.phrase_id
    assert p1.events == p2.events
    assert p1.state == p2.state


def test_deterministic_with_same_seed_and_previous_state():
    p1 = generate_calm_phrase(seed=9001)
    prev = {
        "motif_id": p1.state.motif_id,
        "motif_degrees": p1.state.motif_degrees,
        "cadence_degree": p1.state.cadence_degree,
        "highest_degree": p1.state.highest_degree,
        "novelty": p1.state.novelty,
    }
    p2 = generate_calm_phrase(seed=9002, previous_state=prev)
    p3 = generate_calm_phrase(seed=9002, previous_state=prev)
    assert p2.phrase_id == p3.phrase_id
    assert p2.events == p3.events
    assert p2.state == p3.state


def test_all_notes_within_register():
    phrase = generate_calm_phrase(seed=777)
    for e in phrase.events:
        assert DEFAULT_CALM_CONFIG.register_low_midi <= e.midi <= DEFAULT_CALM_CONFIG.register_high_midi


def test_no_pitch_repeats_more_than_four_times_per_bar():
    phrase = generate_calm_phrase(seed=888)
    by_bar = {1: {}, 2: {}, 3: {}, 4: {}}
    for e in phrase.events:
        by_bar[e.bar][e.midi] = by_bar[e.bar].get(e.midi, 0) + 1
    for counts in by_bar.values():
        assert max(counts.values()) <= 4


def test_a5_appears_at_most_once_per_phrase():
    phrase = generate_calm_phrase(seed=999)
    a5_count = sum(1 for e in phrase.events if e.midi == 81)
    assert a5_count <= 1


def test_phrase_contains_descending_interval():
    phrase = generate_calm_phrase(seed=13579)
    assert any(phrase.events[i + 1].midi < phrase.events[i].midi for i in range(len(phrase.events) - 1))


def test_eighth_note_ratio_is_calm_safe():
    phrase = generate_calm_phrase(seed=24680)
    eighth = sum(1 for e in phrase.events if e.duration == "8n")
    ratio = eighth / len(phrase.events)
    assert ratio <= 0.60


def test_motif_state_carries_forward_to_next_phrase():
    p1 = generate_calm_phrase(seed=111)
    p2 = generate_calm_phrase(
        seed=112,
        previous_state={
            "motif_id": p1.state.motif_id,
            "motif_degrees": p1.state.motif_degrees,
            "cadence_degree": p1.state.cadence_degree,
            "highest_degree": p1.state.highest_degree,
            "novelty": p1.state.novelty,
        },
    )
    assert p2.state.novelty == p1.state.novelty + 1
    assert len(p2.state.motif_degrees) >= 3
