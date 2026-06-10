# FEATURE — Calm Music: Bass Track (Backend + Frontend)

**ID:** music-calm-bass-track
**Status:** Planning / Spec — not yet implemented
**Area:** Backend | Frontend
**Tags:** @music @generation @calm @bass @symbolic @multi-track

---

## Story

> As a **GM using the app**,
> I want the calm music to include a simple bass track alongside the lead melody,
> so that the atmosphere feels more grounded and game-like without becoming dramatic or busy.

The bass is a second generated symbolic track returned in the same phrase response as the lead
melody. The frontend synthesises it separately with a lower-register synth. The bass is sparse,
warm, and supportive — it should not compete with or distract from the lead.

This is the first step toward the eventual 4-track calm arrangement (lead, harmony, bass,
percussion). Only bass is added in this phase.

---

## Background

- Given the calm music generator is configured and running (see `music-calm-generation.feature`)
- And the API endpoint `POST /api/music/calm/next_phrase` is reachable
- And the Tone.js frontend playback is active (see `music-calm-playback.feature`)
- And the phrase scope is still: calm mood, C major pentatonic, 4/4, 4 bars, 88–108 BPM

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Phrase response contains two tracks: lead and bass
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The phrase API returns both tracks in a single response object.

```gherkin
Given a valid phrase request is made to POST /api/music/calm/next_phrase
When  the response is returned
Then  the response contains a "tracks" array with exactly two elements
And   one element has track_id="lead" and role="lead"
And   one element has track_id="bass" and role="bass"
And   each track element contains an "events" array
And   the lead track events are the same lead melody as today's single-track response
And   the bass track events are non-empty (at least one note per phrase)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Bass register is C2–G3
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** All bass notes stay within the calm bass register.

```gherkin
Given a bass track has been generated
When  every bass event is inspected
Then  every bass note's MIDI value is between 36 (C2) and 55 (G3) inclusive
And   no bass note appears above C4 (MIDI 60)
And   no bass note appears below C2 (MIDI 36)
```

**Preferred bass note set:**

| Note | MIDI |
|------|------|
| C2   | 36   |
| E2   | 40   |
| G2   | 43   |
| A2   | 45   |
| C3   | 48   |
| E3   | 52   |
| G3   | 55   |

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Bass uses only stable support degrees
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bass avoids dissonant or unstable scale degrees.

```gherkin
Given a bass track has been generated
When  every bass event is inspected
Then  every bass note is one of: C (degree 1), E (degree 3), G (degree 5), A (degree 6)
And   no bass note is D (degree 2) unless it is an explicitly permitted passing tone
And   no chromatic notes, sharps, or flats appear in the bass
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Bass bar-root degree follows weighted choices
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Each bar's bass root is drawn from a weighted distribution that creates a gentle
4-bar arc: establish home → move gently → mild lift → return home.

```gherkin
Given 1000 phrases are generated with distinct seeds
When  the first (lowest-beat) bass note in each bar is inspected across all phrases
Then  bar 1 root distribution is approximately:
        degree 1 / C: 80%
        degree 5 / G: 20%
And   bar 2 root distribution is approximately:
        degree 5 / G: 50%
        degree 3 / E: 30%
        degree 1 / C: 20%
And   bar 3 root distribution is approximately:
        degree 6 / A: 40%
        degree 5 / G: 35%
        degree 3 / E: 25%
And   bar 4 root distribution is approximately:
        degree 1 / C: 75%
        degree 5 / G: 20%
        degree 3 / E: 5%
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Bass phrase ends on degree 1 / C most of the time
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The last bass note of bar 4 resolves to C at least 75% of the time.

```gherkin
Given 1000 phrases are generated with distinct seeds
When  the final bass note of bar 4 is inspected across all phrases
Then  at least 750 phrases end the bass on a C pitch (C2 or C3)
And   the remainder may end on G (degree 5) or E (degree 3)
And   no phrase ends the bass on A (degree 6)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Bass uses sparse rhythms only
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bass is never rhythmically busy. Eighth notes are forbidden.

```gherkin
Given a bass track has been generated
When  every bass event's duration is inspected
Then  every duration is one of: "1n" (whole), "2n" (half), "4n" (quarter)
And   no event has duration "8n" or shorter
And   each bar has between 1 and 3 bass events (inclusive)
And   the sum of bass event durations in any bar equals exactly 4.0 beats
```

**Allowed bar rhythm patterns (examples — not an exhaustive fixed set):**

```
1n                    → whole note
2n, 2n                → two halves
2n, 4n, 4n            → half + two quarters
4n, 4n, 2n            → two quarters + half
4n, 4n, 4n, 4n        → four quarters (maximum density)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Bass density adapts to lead activity
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** When the lead is busy the bass backs off; when the lead holds long notes the bass
may add gentle movement.

```gherkin
Given a phrase has been generated
When  the event count per bar is compared between lead and bass
Then  for any bar where the lead has 5 or more events:
        the bass has at most 2 events in that bar
And   for any bar where the lead has 2 or 3 events:
        the bass may use up to 3 events in that bar
And   lead and bass are never both at maximum density in the same bar
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Bass movement stays within safe intervals
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bass does not make large, random leaps between consecutive notes.

```gherkin
Given a bass track has been generated
When  consecutive bass note pairs are inspected across the entire phrase
Then  no two consecutive bass notes differ by more than 12 semitones (one octave)
And   bass movement consists primarily of: repeated notes, fifths (7 semitones),
      and small steps within {C, E, G, A}
And   bass never uses chromatic or walking-bass stepwise patterns
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Bass phrase contour follows the 4-bar arc
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The bass supports the same gentle arc as the lead melody.

```gherkin
Given a phrase has been generated
Then  bar 1 bass establishes the home degree (usually C)
And   bar 2 bass moves gently away (usually G or E)
And   bar 3 bass may introduce mild harmonic lift (A or G)
And   bar 4 bass returns toward home (usually C)
And   the overall bass motion feels calm and loop-safe rather than developmental
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Lead and bass do not clash in the same octave
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The two tracks occupy distinct registers so they do not crowd each other.

```gherkin
Given a phrase has been generated
When  lead and bass events at the same beat position are compared
Then  the bass note is always lower in pitch than the lead note at that beat
And   the bass note is always below C4 (MIDI 60)
And   lead and bass do not share the same MIDI number on the same beat
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Validation rejects or repairs an invalid bass track
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bad bass phrases are never returned to the caller.

```gherkin
Given a candidate bass track has been generated
When  any of the following are true:
        - any bass note is outside C2–G3 (MIDI 36–55)
        - any bar has more than 3 bass events
        - any bass event has duration "8n" or shorter
        - bass phrase final note is not degree 1, 3, or 5
        - bass phrase final note is A (degree 6)
        - two consecutive bass notes differ by more than 12 semitones
        - lead and bass are both at maximum density in the same bar
Then  the generator repairs or regenerates the bass track (up to MAX_RETRIES attempts)
And   if all retries fail, the endpoint returns HTTP 422 with error "generation_failed"
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Extended phrase state includes bass fields
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The state object carries bass-specific continuity fields for subsequent phrases.

```gherkin
Given a two-track phrase has been returned
When  the state object is inspected
Then  it contains the existing lead fields:
        motif_id, motif_degrees, cadence_degree, highest_degree, novelty
And   it also contains new bass fields:
        bass_pattern_id   : string  (identifier for the bass pattern used)
        bass_final_degree : integer from {1, 3, 5}  (last bass degree — used for smooth transitions)
And   when the next phrase request includes this state as previous_state
Then  the bass generator uses bass_final_degree to choose a smooth opening bass note
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — Frontend creates a separate synth for the bass track
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bass and lead each have their own Tone.js synth with appropriate settings.

```gherkin
Given the music player starts and receives a two-track phrase
When  the phrase is scheduled for playback
Then  the lead events are sent to a "lead synth":
        - oscillator: "triangle" or "square"
        - volume: nominal (100% of master)
        - register: G4–A5
And   the bass events are sent to a "bass synth":
        - oscillator: "triangle" or "square"
        - volume: 55–70% of lead volume (softer, warmer)
        - register: C2–G3
        - envelope attack: very short (≤0.01 s)
        - envelope release: short-medium (≤0.15 s)
And   both synths schedule their events against the same Tone.js Transport clock
And   both synths route to Tone.getDestination() so the master volume slider applies to both
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — Bass does not repeat the exact same 4-bar pattern too many times
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Looping music should not produce an obviously mechanical repeating bass line.

```gherkin
Given a session plays more than 4 consecutive phrases
When  the bass root sequence across consecutive phrases is examined
Then  the exact same sequence of 4 bass roots (bar1, bar2, bar3, bar4) does not repeat
      more than 3 times consecutively
And   bass_pattern_id changes at least once every 4 phrases when seed varies
```

---

## Out of Scope (this phase)

- Harmony / chord pad track — Tier 2
- Percussion / noise track — Tier 2
- Walking bass or passing tones other than the four stable degrees — later refinement
- Bass velocity dynamics beyond a fixed calm range (0.35–0.55) — later refinement
- Separate bass volume control in UI — use master volume slider for now
- Bass register below C2 — too low for browser synthesis to be audible

---

## Notes

**Bass generator configuration (proposed `CalmBassConfig`):**

```
register:         C2–G3 (MIDI 36–55)
allowed_degrees:  [1, 3, 5, 6]   (C, E, G, A)
allowed_durations: [1n, 2n, 4n]
max_events_per_bar: 3
velocity_range:   (0.35, 0.55)   (softer than lead; lead is 0.45–0.75)
```

**Bar-root weights (see AC-004):**

| Bar | Degree 1 / C | Degree 3 / E | Degree 5 / G | Degree 6 / A |
|-----|-------------|-------------|-------------|-------------|
| 1   | 80%         | 0%          | 20%         | 0%          |
| 2   | 20%         | 30%         | 50%         | 0%          |
| 3   | 0%          | 25%         | 35%         | 40%         |
| 4   | 75%         | 5%          | 20%         | 0%          |

**Multi-track API shape** (snake_case, consistent with existing convention):

```json
{
  "phrase_id": "calm_s12345_h9f0a1c2d",
  "mood": "calm",
  "key": "C",
  "scale": "major_pentatonic",
  "bpm": 96,
  "time_signature": "4/4",
  "bars": 4,
  "tracks": [
    {
      "track_id": "lead",
      "role": "lead",
      "events": [
        { "bar": 1, "beat": 1.0, "note": "C5",  "midi": 72, "duration": "4n", "velocity": 0.6  },
        { "bar": 1, "beat": 2.0, "note": "E5",  "midi": 76, "duration": "4n", "velocity": 0.55 },
        { "bar": 1, "beat": 3.0, "note": "D5",  "midi": 74, "duration": "2n", "velocity": 0.5  }
      ]
    },
    {
      "track_id": "bass",
      "role": "bass",
      "events": [
        { "bar": 1, "beat": 1.0, "note": "C2",  "midi": 36, "duration": "2n", "velocity": 0.45 },
        { "bar": 1, "beat": 3.0, "note": "G2",  "midi": 43, "duration": "2n", "velocity": 0.4  },
        { "bar": 2, "beat": 1.0, "note": "G2",  "midi": 43, "duration": "1n", "velocity": 0.42 },
        { "bar": 3, "beat": 1.0, "note": "A2",  "midi": 45, "duration": "2n", "velocity": 0.4  },
        { "bar": 3, "beat": 3.0, "note": "G2",  "midi": 43, "duration": "2n", "velocity": 0.38 },
        { "bar": 4, "beat": 1.0, "note": "C3",  "midi": 48, "duration": "1n", "velocity": 0.45 }
      ]
    }
  ],
  "state": {
    "motif_id": "m_12345_001",
    "motif_degrees": [1, 3, 2],
    "cadence_degree": 1,
    "highest_degree": 3,
    "novelty": 1,
    "bass_pattern_id": "bp_12345_001",
    "bass_final_degree": 1
  }
}
```

**Migration note:** The existing flat `events` field on `CalmPhrase` is the lead track at Tier 0.
When the multi-track response is introduced, the `events` field should be replaced by `tracks`.
This is a breaking change to the API contract and TypeScript types — the migration must update:
- `api/music/calm/` generator
- `api/main.py` response model
- `ui/src/api.ts` `CalmPhrase` type
- `ui/src/music/player.ts` scheduling (now iterates tracks)
- `ui/src/components/MusicPlayer.tsx` (pass track-specific callbacks)

**Synth envelope for bass (proposed):**

```
oscillator: triangle
envelope:
  attack:  0.01
  decay:   0.08
  sustain: 0.4
  release: 0.1
```

Keep release short (≤0.15 s) to prevent bass note tails from muddying phrase transitions.

**Related specs:**
- [music-calm-generation.feature](music-calm-generation.feature) — lead melody rules this extends
- [music-api-contract.feature](music-api-contract.feature) — HTTP contract (AC-008 covers multi-track shape)
- [music-calm-playback.feature](music-calm-playback.feature) — frontend playback this extends

**Open questions:**
- Should `bass_pattern_id` be seeded from the phrase seed or independently?
- Should bass velocity be adjustable relative to lead via a hidden UI slider at this phase?
- Should the generator skip the bass track if the session has been playing for fewer than N seconds (to let the lead establish itself first)?
