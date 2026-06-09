# FEATURE — Calm Music Generation (Backend)

**ID:** music-calm-generation
**Status:** Draft
**Area:** Backend
**Tags:** @music @generation @calm @symbolic @backend

---

## Story

> As the **GM engine**,
> I want a rule-based backend generator that produces symbolic calm-mood melody phrases,
> so that the frontend can synthesise them in the browser without any audio file I/O on the server.

The generator produces symbolic note events — pitch name, MIDI number, bar, beat, duration, velocity — for a
single monophonic melody line. It does not render audio. Tier 0 scope: calm mood only, C major pentatonic,
4/4 at 88–108 BPM, 4 bars, register G4–A5. The generator is seeded so the same seed + motif state always
returns the same phrase.

---

## Background

- Given a session is active (or the endpoint is called in isolation)
- And the `mood` parameter is `"calm"`
- And the generator is configured with the calm profile (see Notes)
- And `event_scheduler` state is not required — this feature is independent of the event system

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Generate a 4-bar calm phrase
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A caller requests a new calm phrase; the generator returns exactly 4 bars of note events.

```gherkin
Given the calm generator is configured with phrase_bars=4 and time_signature="4/4"
When  a caller requests a new calm phrase
Then  the response contains exactly 4 bars worth of note events
And   every event has a "bar" field with value 1, 2, 3, or 4
And   no event has a bar value outside 1–4
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Use C major pentatonic scale exclusively
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Every generated note is a member of the C major pentatonic scale.

```gherkin
Given the scale is configured as C major pentatonic {C, D, E, G, A}
When  a phrase is generated
Then  every note event's pitch name is one of: C4, D4, E4, G4, A4, C5, D5, E5, G5, A5
And   no chromatic or diatonic non-pentatonic pitch appears (F, B, and all sharps/flats are forbidden)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Monophonic output only — no simultaneous notes
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The generator never produces chords or overlapping events.

```gherkin
Given a phrase has been generated
When  the events for any single bar are examined
Then  no two events share the same bar + beat start position
And   the cumulative duration of events within any bar does not exceed 4 beats
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Notes stay within the G4–A5 register
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** All generated pitches are within the calm melody register.

```gherkin
Given the register is configured as low=G4 (MIDI 67), high=A5 (MIDI 81)
When  a phrase is generated
Then  every note event has a "midi" value between 67 and 81 inclusive
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Each bar totals exactly 4 beats
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Duration bookkeeping is exact; bars never under- or over-fill.

```gherkin
Given allowed durations are: 8n (0.5 beat), 4n (1 beat), 2n (2 beats)
And   16n notes are not permitted at Tier 0
When  a phrase is generated
Then  for every bar the sum of event durations equals exactly 4.0 beats
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Phrase ends on a cadence note with weighted probability
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The last note of bar 4 resolves to a calm cadence degree.

```gherkin
Given cadence weights: degree 1 / C → 60%, degree 5 / G → 25%, degree 3 / E → 15%
When  1000 phrases are generated with distinct seeds
Then  roughly 60% end on a C pitch (any octave within register)
And   roughly 25% end on a G pitch
And   roughly 15% end on an E pitch
And   no phrase ends on D or A
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Seeded generation is deterministic
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The same seed + previous state always produces identical output.

```gherkin
Given seed=12345 and previousState=null
When  the calm phrase endpoint is called twice with the same inputs
Then  both responses contain identical events (same notes, durations, beats, bars)
And   both responses return the same phraseId prefix
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Motif state is carried between phrases
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Phrase N+1 references the motif extracted from phrase N, creating continuity.

```gherkin
Given phrase 1 was generated and returned state.motifDegrees=[1, 2, 3, 5]
When  phrase 2 is requested with previousState from phrase 1
Then  phrase 2 begins with a note derived from or related to motifDegrees
And   the state returned by phrase 2 carries a non-null motifId
And   calling again with the same previousState returns the same phrase 2 (seeded)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Phrase shape follows the 4-bar arc
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bar roles are distinguishable — bar 4 is calmer and less busy than bar 3.

```gherkin
Given a phrase has been generated
When  the event density per bar is counted
Then  bar 4 has fewer or equal events compared to bar 3
And   bar 4 ends on a cadence note (degree 1, 3, or 5)
And   bar 3 is permitted to reach a higher pitch than bars 1 and 2
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Anti-annoyance: pitch repetition limit
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The same pitch does not dominate a single bar.

```gherkin
Given a phrase has been generated
When  each bar is examined
Then  no single pitch appears more than 4 times in one bar
And   the high note A5 appears at most once across the entire phrase
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Anti-annoyance: phrase must contain downward motion
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Purely ascending phrases are rejected or repaired.

```gherkin
Given a candidate phrase has been computed
When  the sequence of MIDI values is inspected
Then  at least one consecutive note pair has a lower pitch than its predecessor
And   if the candidate has no downward motion it is repaired or regenerated before being returned
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Anti-annoyance: excess eighth-notes rejected or repaired
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A phrase driven mostly by 8n notes feels too busy for a calm mood.

```gherkin
Given a candidate phrase has been computed
When  the proportion of 8n events across all 4 bars is calculated
Then  if more than 60% of events are 8n, the phrase is repaired or regenerated
And   the returned phrase contains a mix of 8n, 4n, and at least one 2n event
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — Invalid phrase is never returned to the caller
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Validation is a hard gate before the response is sent.

```gherkin
Given the generator has produced a candidate phrase
When  any of these conditions are true:
        - phrase does not end on degree 1, 3, or 5
        - any note is outside G4–A5
        - any bar total ≠ 4.0 beats
        - same pitch > 4 times in one bar
        - A5 appears more than once
        - no downward motion
        - > 60% eighth notes
Then  the generator repairs or regenerates the phrase (up to MAX_RETRIES attempts)
And   if all retries fail, the endpoint returns HTTP 422 with error code "generation_failed"
And   the error body includes "attempts" with the retry count
```

---

## Out of Scope

- Audio file generation (WAV, MP3, MIDI) — Tier 0 is symbolic only
- Harmony, chords, or simultaneous voices — single monophonic line only
- Percussion or bass — no rhythm track at Tier 0
- Scale modes other than C major pentatonic — all other keys/modes are Tier 2+
- Tempo other than 88–108 BPM
- Mood detection or automatic mood switching — see [music-calm-playback.feature](music-calm-playback.feature) notes
- Motif mutation / evolution algorithms — basic carry-forward only at Tier 0
- Combat or tension moods — see MUSIC_TODO.md Tier 2+

---

## Notes

**Calm generator configuration (proposed `CalmConfig` dataclass):**

```
mood:            calm
meter:           4/4
bpm_range:       (88, 108)          # default pick: 96
phrase_bars:     4
register:        G4–A5 (MIDI 67–81)
scale:           C major pentatonic {C, D, E, G, A}
scale_degrees:   [1, 2, 3, 5, 6]
allowed_durations: [8n, 4n, 2n]     # 16n excluded at Tier 0
events_per_bar:  2–6 (soft target)
cadence_weights: {1: 0.60, 5: 0.25, 3: 0.15}
motif_length:    3–5 degrees
motif_start:     preferred degrees 1, 3, or 5
motif_end:       preferred degrees 3, 5, or 6
max_retries:     5
```

**Motif degree → note name mapping (octave chosen by register rule):**

| Degree | Note | Preferred MIDI in register |
|--------|------|---------------------------|
| 1      | C    | C5 (72)                   |
| 2      | D    | D5 (74)                   |
| 3      | E    | E5 (76)                   |
| 5      | G    | G4 (67) or G5 (79)        |
| 6      | A    | A4 (69) or A5 (81)        |

**Related specs:**
- [music-api-contract.feature](music-api-contract.feature) — HTTP contract for this generator
- [music-calm-playback.feature](music-calm-playback.feature) — frontend consumption

**Open questions:**
- Should the generator live in `api/music/` or `api/session_manager.py`?
- Should `MAX_RETRIES` be configurable per mood?
- Should repaired phrases be logged for quality monitoring?
