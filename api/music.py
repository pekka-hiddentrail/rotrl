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
class CalmBassConfig:
    register_low_midi: int = 36   # C2
    register_high_midi: int = 55  # G3
    allowed_degrees: tuple[int, ...] = (1, 3, 5, 6)
    allowed_durations: tuple[str, ...] = ("1n", "2n", "4n")
    max_events_per_bar: int = 3
    velocity_min: float = 0.35
    velocity_max: float = 0.55
    max_jump_semitones: int = 12


@dataclass(frozen=True)
class NoteEvent:
    bar: int
    beat: float
    note: str
    midi: int
    duration: str
    velocity: float


@dataclass(frozen=True)
class TrackEvents:
    track_id: str
    role: str
    events: list[NoteEvent]


@dataclass(frozen=True)
class PhraseState:
    motif_id: str
    motif_degrees: list[int]
    cadence_degree: int
    highest_degree: int
    novelty: int
    bass_pattern_id: str
    bass_final_degree: int


@dataclass(frozen=True)
class CalmPhrase:
    phrase_id: str
    mood: str
    key: str
    scale: str
    bpm: int
    time_signature: str
    bars: int
    tracks: list[TrackEvents]
    state: PhraseState


class GenerationFailedError(RuntimeError):
    def __init__(self, attempts: int, detail: str):
        super().__init__(detail)
        self.attempts = attempts
        self.detail = detail


DEFAULT_CALM_CONFIG = CalmConfig()
DEFAULT_CALM_BASS_CONFIG = CalmBassConfig()

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
    "1n": 4.0,
}

_SCALE_ORDER = (1, 2, 3, 5, 6)

_BASS_ALLOWED_DEGREES: tuple[int, ...] = (1, 3, 5, 6)

# Bar-root degree weights: bar 1 anchors on tonic, bar 4 resolves to tonic.
_BASS_BAR_ROOT_WEIGHTS: dict[int, list[tuple[int, float]]] = {
    1: [(1, 0.80), (5, 0.20)],
    2: [(5, 0.50), (3, 0.30), (1, 0.20)],
    3: [(6, 0.40), (5, 0.35), (3, 0.25)],
    4: [(1, 0.75), (5, 0.20), (3, 0.05)],
}

# Duration patterns that sum to exactly 4.0 beats, keyed by event count.
_BASS_BAR_PATTERNS: dict[int, list[list[str]]] = {
    1: [["1n"]],
    2: [["2n", "2n"]],
    3: [
        ["2n", "4n", "4n"],
        ["4n", "4n", "2n"],
        ["4n", "2n", "4n"],
    ],
}


def note_to_midi(note_name: str) -> int:
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
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def degree_to_note(
    degree: int,
    octave_hint: int = 5,
    *,
    config: CalmConfig = DEFAULT_CALM_CONFIG,
) -> tuple[str, int]:
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

    scored = sorted((abs(m - target), m) for m in candidates)
    best_dist = scored[0][0]
    best = [m for d, m in scored if d == best_dist]
    return rng.choice(best)


def _midi_to_note_name(midi: int) -> str:
    octave = (midi // 12) - 1
    semitone = midi % 12
    note = {0: "C", 2: "D", 4: "E", 7: "G", 9: "A"}.get(semitone)
    if note is None:
        note = "C"
    return f"{note}{octave}"


def _bar_duration_pattern(rng: random.Random, bar: int) -> list[str]:
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


# ─── Bass generation ──────────────────────────────────────────────────────────


def _bass_degree_midis(degree: int, config: CalmBassConfig) -> list[int]:
    note = _DEGREE_TO_NOTE.get(degree, "C")
    result: list[int] = []
    for octave in range(0, 6):
        midi = note_to_midi(f"{note}{octave}")
        if config.register_low_midi <= midi <= config.register_high_midi:
            result.append(midi)
    return result


def _pick_bass_midi(
    degree: int,
    prev_midi: Optional[int],
    rng: random.Random,
    *,
    config: CalmBassConfig,
) -> int:
    candidates = _bass_degree_midis(degree, config)
    if not candidates:
        return config.register_low_midi

    if prev_midi is None:
        return rng.choice(candidates)

    reachable = [m for m in candidates if abs(m - prev_midi) <= config.max_jump_semitones]
    if not reachable:
        # No candidate within max_jump — take the absolute closest.
        return min(candidates, key=lambda m: abs(m - prev_midi))

    # Among reachable, prefer closest; allow ±7 semitone window for variety.
    pool_sorted = sorted(reachable, key=lambda m: abs(m - prev_midi))
    best_dist = abs(pool_sorted[0] - prev_midi)
    top = [m for m in pool_sorted if abs(m - prev_midi) <= best_dist + 7]
    return rng.choice(top)


def _bass_step_degree(root: int, rng: random.Random) -> int:
    """Stay on root 70% of the time; otherwise step to an adjacent allowed degree."""
    if rng.random() < 0.70:
        return root
    idx = _BASS_ALLOWED_DEGREES.index(root) if root in _BASS_ALLOWED_DEGREES else 0
    direction = rng.choice([-1, 1])
    return _BASS_ALLOWED_DEGREES[(idx + direction) % len(_BASS_ALLOWED_DEGREES)]


def _generate_bass_track(
    seed: int,
    previous_state: Optional[dict],
    lead_events: list[NoteEvent],
    *,
    attempt: int,
    config: CalmBassConfig,
) -> tuple[list[NoteEvent], str, int]:
    """Generate one 4-bar bass track. Returns (events, bass_pattern_id, bass_final_degree)."""
    state_key = json.dumps(previous_state or {}, sort_keys=True)
    rng = random.Random(f"{seed}:{state_key}:bass:attempt:{attempt}")

    # Count lead events per bar for density coordination.
    lead_by_bar: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    for e in lead_events:
        if e.bar in lead_by_bar:
            lead_by_bar[e.bar] += 1

    events: list[NoteEvent] = []
    prev_midi: Optional[int] = None

    for bar in range(1, 5):
        root_degree = _weighted_pick(rng, _BASS_BAR_ROOT_WEIGHTS[bar])

        lead_count = lead_by_bar[bar]
        if lead_count >= 5:
            event_count = rng.choice([1, 2])
        elif lead_count <= 2:
            event_count = rng.randint(2, 3)
        else:
            event_count = rng.randint(1, 3)

        durations = rng.choice(_BASS_BAR_PATTERNS[event_count])
        beat = 1.0

        for i, duration in enumerate(durations):
            degree = root_degree if i == 0 else _bass_step_degree(root_degree, rng)
            midi = _pick_bass_midi(degree, prev_midi, rng, config=config)
            note = _midi_to_note_name(midi)
            velocity = round(
                config.velocity_min + rng.random() * (config.velocity_max - config.velocity_min), 2
            )
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
            beat += _DURATION_TO_BEATS[duration]

    # Ensure final note lands on a cadence degree (1, 3, or 5).
    last = events[-1]
    if _degree_for_note(last.note) not in (1, 3, 5):
        target_midi = _pick_bass_midi(1, last.midi, rng, config=config)
        events[-1] = NoteEvent(
            bar=last.bar,
            beat=last.beat,
            note=_midi_to_note_name(target_midi),
            midi=target_midi,
            duration=last.duration,
            velocity=last.velocity,
        )

    bass_final_degree = _degree_for_note(events[-1].note)
    bass_pattern_id = _stable_bass_pattern_id(seed, [e.note for e in events])
    return events, bass_pattern_id, bass_final_degree


def _validate_bass_track(
    bass_events: list[NoteEvent],
    lead_events: list[NoteEvent],
    config: CalmBassConfig,
) -> None:
    if not bass_events:
        raise ValueError("bass_empty")

    lead_by_bar: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    for e in lead_events:
        if e.bar in lead_by_bar:
            lead_by_bar[e.bar] += 1

    for e in bass_events:
        if not (config.register_low_midi <= e.midi <= config.register_high_midi):
            raise ValueError("bass_register_out_of_bounds")
        if e.duration not in config.allowed_durations:
            raise ValueError("bass_invalid_duration")

    for bar in range(1, 5):
        bar_events = [e for e in bass_events if e.bar == bar]
        if not bar_events:
            raise ValueError(f"bass_bar_{bar}_empty")
        if len(bar_events) > config.max_events_per_bar:
            raise ValueError(f"bass_bar_{bar}_too_many_events")
        total = sum(_DURATION_TO_BEATS[e.duration] for e in bar_events)
        if abs(total - 4.0) > 1e-9:
            raise ValueError(f"bass_bar_{bar}_duration_mismatch")
        if lead_by_bar[bar] >= 5 and len(bar_events) > 2:
            raise ValueError(f"bass_bar_{bar}_too_dense_vs_lead")

    if _degree_for_note(bass_events[-1].note) not in (1, 3, 5):
        raise ValueError("bass_cadence_invalid")

    for i in range(len(bass_events) - 1):
        jump = abs(bass_events[i + 1].midi - bass_events[i].midi)
        if jump > config.max_jump_semitones:
            raise ValueError(f"bass_jump_too_large_{jump}")


# ─── Lead generation ──────────────────────────────────────────────────────────


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
                if idx == 0 and rng.random() < 0.45:
                    degree = 6
            else:
                if idx == len(durations) - 1:
                    degree = cadence_degree
                else:
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

    bass_config = DEFAULT_CALM_BASS_CONFIG
    bass_events, bass_pattern_id, bass_final_degree = _generate_bass_track(
        seed=seed,
        previous_state=previous_state,
        lead_events=events,
        attempt=attempt,
        config=bass_config,
    )
    _validate_bass_track(bass_events, events, bass_config)

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
        bass_pattern_id=bass_pattern_id,
        bass_final_degree=bass_final_degree,
    )

    phrase_id = _stable_phrase_id(seed, previous_state, bpm, events)
    lead_track = TrackEvents(track_id="lead", role="lead", events=events)
    bass_track_obj = TrackEvents(track_id="bass", role="bass", events=bass_events)
    return CalmPhrase(
        phrase_id=phrase_id,
        mood=config.mood,
        key="C",
        scale="major_pentatonic",
        bpm=bpm,
        time_signature="4/4",
        bars=config.phrase_bars,
        tracks=[lead_track, bass_track_obj],
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


def _stable_bass_pattern_id(seed: int, note_names: list[str]) -> str:
    raw = f"bass:{seed}:{','.join(note_names)}"
    return f"bp_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8]}"


def _stable_phrase_id(
    seed: int,
    previous_state: Optional[dict],
    bpm: int,
    events: list[NoteEvent],
) -> str:
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
