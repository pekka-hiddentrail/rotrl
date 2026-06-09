from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class CalmConfig:
    mood: str = "calm"
    bpm_min: int = 88
    bpm_max: int = 108
    phrase_bars: int = 4
    register_low_midi: int = 67   # G4
    register_high_midi: int = 81  # A5
    scale_degrees: tuple[int, ...] = (1, 2, 3, 5, 6)
    durations: tuple[str, ...] = ("8n", "4n", "2n")
    cadence_weights: tuple[tuple[int, float], ...] = ((1, 0.60), (5, 0.25), (3, 0.15))
    motif_min_len: int = 3
    motif_max_len: int = 5
    max_retries: int = 5


@dataclass(frozen=True)
class NoteEvent:
    bar: int
    beat: float
    note: str
    midi: int
    duration: str
    velocity: float


@dataclass(frozen=True)
class PhraseState:
    motif_id: str
    motif_degrees: list[int]
    cadence_degree: int
    highest_degree: int
    novelty: int


@dataclass(frozen=True)
class CalmPhrase:
    phrase_id: str
    mood: str
    key: str
    scale: str
    bpm: int
    time_signature: str
    bars: int
    events: list[NoteEvent]
    state: PhraseState


class GenerationFailedError(RuntimeError):
    def __init__(self, attempts: int, detail: str):
        super().__init__(detail)
        self.attempts = attempts
        self.detail = detail


DEFAULT_CALM_CONFIG = CalmConfig()

_DEGREE_TO_NOTE = {
    1: "C",
    2: "D",
    3: "E",
    5: "G",
    6: "A",
}

_NOTE_TO_SEMITONE = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

_DURATION_TO_BEATS = {
    "8n": 0.5,
    "4n": 1.0,
    "2n": 2.0,
}

_SCALE_ORDER = (1, 2, 3, 5, 6)


def note_to_midi(note_name: str) -> int:
    """Convert a natural note name like C5 into MIDI."""
    note_name = note_name.strip().upper()
    if len(note_name) < 2:
        raise ValueError(f"Invalid note: {note_name}")
    note = note_name[0]
    if note not in _NOTE_TO_SEMITONE:
        raise ValueError(f"Unsupported note: {note_name}")
    try:
        octave = int(note_name[1:])
    except ValueError as exc:
        raise ValueError(f"Invalid octave in note: {note_name}") from exc
    return (octave + 1) * 12 + _NOTE_TO_SEMITONE[note]


def midi_to_freq(midi: int) -> float:
    """Convert MIDI pitch to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def degree_to_note(
    degree: int,
    octave_hint: int = 5,
    *,
    config: CalmConfig = DEFAULT_CALM_CONFIG,
) -> tuple[str, int]:
    """Map C-pentatonic degree to note/midi, clamped to the configured register."""
    if degree not in _DEGREE_TO_NOTE:
        raise ValueError(f"Unsupported degree: {degree}")
    base = _DEGREE_TO_NOTE[degree]
    octave = octave_hint
    midi = note_to_midi(f"{base}{octave}")
    while midi < config.register_low_midi:
        octave += 1
        midi = note_to_midi(f"{base}{octave}")
    while midi > config.register_high_midi:
        octave -= 1
        midi = note_to_midi(f"{base}{octave}")
    return f"{base}{octave}", midi


def _duration_beats(duration: str) -> float:
    return _DURATION_TO_BEATS[duration]


def _weighted_pick(rng: random.Random, items: list[tuple[int, float]]) -> int:
    total = sum(w for _, w in items)
    roll = rng.random() * total
    acc = 0.0
    for value, weight in items:
        acc += weight
        if roll <= acc:
            return value
    return items[-1][0]


def _next_scale_degree(degree: int, step: int) -> int:
    idx = _SCALE_ORDER.index(degree)
    return _SCALE_ORDER[(idx + step) % len(_SCALE_ORDER)]


def _all_candidate_midis_for_degree(degree: int, config: CalmConfig) -> list[int]:
    note = _DEGREE_TO_NOTE[degree]
    out: list[int] = []
    for octave in range(1, 8):
        midi = note_to_midi(f"{note}{octave}")
        if config.register_low_midi <= midi <= config.register_high_midi:
            out.append(midi)
    return out


def _pick_midi(
    degree: int,
    prev_midi: Optional[int],
    rng: random.Random,
    *,
    config: CalmConfig,
    allow_a5: bool,
    prefer_high: bool = False,
) -> int:
    candidates = _all_candidate_midis_for_degree(degree, config)
    if degree == 6 and not allow_a5:
        candidates = [m for m in candidates if m != 81]
    if not candidates:
        _, fallback = degree_to_note(degree, 5, config=config)
        return fallback

    target = prev_midi if prev_midi is not None else 74
    if prefer_high:
        target = min(config.register_high_midi, target + 5)

    # Pick nearest candidate to the target, break ties deterministically.
    scored = sorted((abs(m - target), m) for m in candidates)
    best_dist = scored[0][0]
    best = [m for d, m in scored if d == best_dist]
    return rng.choice(best)


def _midi_to_note_name(midi: int) -> str:
    octave = (midi // 12) - 1
    semitone = midi % 12
    note = {0: "C", 2: "D", 4: "E", 7: "G", 9: "A"}.get(semitone)
    if note is None:
        # Should not happen for the constrained pentatonic output.
        note = "C"
    return f"{note}{octave}"


def _bar_duration_pattern(rng: random.Random, bar: int) -> list[str]:
    # Keep Tier-0 calm by defaulting to quarter/half-heavy bars.
    if bar == 4:
        return rng.choice([
            ["4n", "4n", "2n"],
            ["2n", "2n"],
        ])
    if bar == 3:
        return rng.choice([
            ["8n", "8n", "4n", "2n"],
            ["4n", "4n", "4n", "4n"],
            ["2n", "4n", "4n"],
        ])
    return rng.choice([
        ["4n", "4n", "2n"],
        ["4n", "4n", "4n", "4n"],
        ["2n", "4n", "4n"],
    ])


def _build_motif(rng: random.Random, previous_state: Optional[dict], config: CalmConfig) -> list[int]:
    prev = (previous_state or {}).get("motif_degrees")
    if isinstance(prev, list) and prev:
        motif = [d for d in prev if d in config.scale_degrees]
        if motif:
            # Tiny deterministic variation keeps continuity without full repetition.
            if len(motif) >= 2 and rng.random() < 0.5:
                i = rng.randrange(len(motif))
                motif[i] = _next_scale_degree(motif[i], 1)
            return motif[: config.motif_max_len]

    length = rng.randint(config.motif_min_len, config.motif_max_len)
    motif = [rng.choice((1, 3, 5))]
    for _ in range(max(0, length - 2)):
        motif.append(rng.choice(config.scale_degrees))
    motif.append(rng.choice((3, 5, 6)))
    return motif


def _validate_phrase(events: list[NoteEvent], cadence_degree: int, config: CalmConfig) -> None:
    if cadence_degree not in (1, 3, 5):
        raise ValueError("cadence_degree_invalid")

    if not events:
        raise ValueError("empty_phrase")

    by_bar: dict[int, list[NoteEvent]] = {1: [], 2: [], 3: [], 4: []}
    a5_count = 0
    eighth_count = 0

    for e in events:
        if not (config.register_low_midi <= e.midi <= config.register_high_midi):
            raise ValueError("register_out_of_bounds")
        if e.bar not in by_bar:
            raise ValueError("invalid_bar")
        by_bar[e.bar].append(e)
        if e.midi == 81:
            a5_count += 1
        if e.duration == "8n":
            eighth_count += 1

    if a5_count > 1:
        raise ValueError("a5_overuse")

    for bar, items in by_bar.items():
        if not items:
            raise ValueError(f"bar_{bar}_empty")
        total = sum(_duration_beats(i.duration) for i in items)
        if abs(total - 4.0) > 1e-9:
            raise ValueError(f"bar_{bar}_duration_mismatch")

        counts: dict[int, int] = {}
        for i in items:
            counts[i.midi] = counts.get(i.midi, 0) + 1
        if any(v > 4 for v in counts.values()):
            raise ValueError(f"bar_{bar}_pitch_repetition")

    if events[-1].note[0] not in {"C", "E", "G"}:
        raise ValueError("cadence_note_invalid")

    descending = any(events[i + 1].midi < events[i].midi for i in range(len(events) - 1))
    if not descending:
        raise ValueError("no_descending_motion")

    if (eighth_count / len(events)) > 0.60:
        raise ValueError("too_many_eighth_notes")



def _generate_once(
    seed: int,
    previous_state: Optional[dict],
    *,
    config: CalmConfig,
    attempt: int,
) -> CalmPhrase:
    state_key = json.dumps(previous_state or {}, sort_keys=True)
    rng = random.Random(f"{seed}:{state_key}:attempt:{attempt}")

    motif = _build_motif(rng, previous_state, config)
    cadence_degree = _weighted_pick(rng, list(config.cadence_weights))
    bpm = rng.randint(config.bpm_min, config.bpm_max)

    events: list[NoteEvent] = []
    prev_midi: Optional[int] = None
    a5_used = 0

    for bar in range(1, config.phrase_bars + 1):
        durations = _bar_duration_pattern(rng, bar)
        beat = 1.0
        for idx, duration in enumerate(durations):
            if bar == 1:
                degree = motif[idx % len(motif)]
            elif bar == 2:
                degree = _next_scale_degree(motif[idx % len(motif)], 1)
            elif bar == 3:
                degree = motif[(idx + 1) % len(motif)]
                # Bar 3 may peak upward.
                if idx == 0 and rng.random() < 0.45:
                    degree = 6
            else:
                if idx == len(durations) - 1:
                    degree = cadence_degree
                else:
                    # Descend toward the cadence by stepping back in scale order.
                    degree = _next_scale_degree(cadence_degree, -1)

            prefer_high = (bar == 3 and idx == 0)
            midi = _pick_midi(
                degree,
                prev_midi,
                rng,
                config=config,
                allow_a5=(a5_used == 0),
                prefer_high=prefer_high,
            )
            if midi == 81:
                a5_used += 1

            note = _midi_to_note_name(midi)
            velocity = round(0.50 + (rng.random() * 0.18), 2)
            events.append(
                NoteEvent(
                    bar=bar,
                    beat=round(beat, 2),
                    note=note,
                    midi=midi,
                    duration=duration,
                    velocity=velocity,
                )
            )
            prev_midi = midi
            beat += _duration_beats(duration)

    # Force a guaranteed descending pair if needed by nudging one note down in bar 4.
    if not any(events[i + 1].midi < events[i].midi for i in range(len(events) - 1)):
        for i in range(len(events) - 2, 0, -1):
            if events[i].bar == 4 and events[i].midi > config.register_low_midi:
                lowered = events[i].midi - 2
                if lowered >= config.register_low_midi:
                    events[i] = NoteEvent(
                        bar=events[i].bar,
                        beat=events[i].beat,
                        note=_midi_to_note_name(lowered),
                        midi=lowered,
                        duration=events[i].duration,
                        velocity=events[i].velocity,
                    )
                    break

    _validate_phrase(events, cadence_degree, config)

    novelty = 1
    if previous_state and isinstance(previous_state.get("novelty"), int):
        novelty = max(1, previous_state["novelty"] + 1)

    highest_degree = max(_degree_for_note(e.note) for e in events)
    motif_id = _stable_motif_id(seed, motif)
    state = PhraseState(
        motif_id=motif_id,
        motif_degrees=list(motif),
        cadence_degree=cadence_degree,
        highest_degree=highest_degree,
        novelty=novelty,
    )

    phrase_id = _stable_phrase_id(seed, previous_state, bpm, events)
    return CalmPhrase(
        phrase_id=phrase_id,
        mood=config.mood,
        key="C",
        scale="major_pentatonic",
        bpm=bpm,
        time_signature="4/4",
        bars=config.phrase_bars,
        events=events,
        state=state,
    )


def _degree_for_note(note_name: str) -> int:
    letter = note_name[0].upper()
    return {
        "C": 1,
        "D": 2,
        "E": 3,
        "G": 5,
        "A": 6,
    }[letter]


def _stable_motif_id(seed: int, motif: list[int]) -> str:
    raw = f"{seed}:{','.join(str(x) for x in motif)}"
    return f"m_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8]}"


def _stable_phrase_id(seed: int, previous_state: Optional[dict], bpm: int, events: list[NoteEvent]) -> str:
    payload = {
        "seed": seed,
        "previous_state": previous_state or None,
        "bpm": bpm,
        "events": [asdict(e) for e in events],
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:9]
    return f"calm_s{seed}_h{digest}"


def generate_calm_phrase(
    seed: int,
    previous_state: Optional[dict] = None,
    session_id: Optional[str] = None,
    *,
    config: CalmConfig = DEFAULT_CALM_CONFIG,
) -> CalmPhrase:
    """Generate one deterministic calm phrase.

    session_id is accepted for future compatibility but not used in Tier 0 generation.
    """
    _ = session_id
    last_error = "unknown"
    for attempt in range(1, config.max_retries + 1):
        try:
            return _generate_once(seed, previous_state, config=config, attempt=attempt)
        except ValueError as exc:
            last_error = str(exc)
            continue
    raise GenerationFailedError(config.max_retries, last_error)
