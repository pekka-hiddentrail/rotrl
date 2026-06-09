# Music System Backlog

All adaptive music work lives here. [TODO.md](TODO.md) links here.

Same markup rules as TODO.md apply.

- [ ] Item text - open task
- [x] Item text - completed task
- ~~[ ] Item text~~ - obsolete / cancelled task
- Sub-bullets use the same - [ ] format, indented two spaces
- Never use plain - bullets for tasks - everything actionable must have a checkbox
- Bold the item title when it has a longer description below it

---

## Goal

Build a procedural adaptive music system for the GM app.

Current focus: **Tier 0 only** — calm mood, monophonic chiptune melody, symbolic JSON output,
browser-side synthesis with Tone.js. No audio files generated on the server.

The system is designed to grow from a single melody line to a multi-track arrangement while
keeping each tier independently shippable.

Status snapshot (2026-06-09): Tier 0 backend/API/tests and frontend playback controls are complete.
Music Off toggle behavior is implemented in the UI and persists via localStorage.

---

## Current MVP (Tier 0 scope)

What we are building right now:

- [x] Calm mood only — no other moods yet
- [x] Monophonic symbolic melody generation — one voice, no chords
- [x] C major pentatonic scale — {C, D, E, G, A}
- [x] 4-bar generated phrases in 4/4 at 88–108 BPM
- [x] Register G4–A5
- [x] JSON API contract (`POST /api/music/calm/next_phrase`)
- [x] Browser playback via Tone.js (triangle oscillator)

---

## Tier 0 — Backend

Minimum backend to make calm playback work end-to-end.

- [x] **M0-1 - Music models and config**
  - [x] Define `CalmConfig` dataclass: mood, bpm_range, phrase_bars, register, scale, durations, cadence_weights, motif config, max_retries
  - [x] Define `NoteEvent` dataclass: bar, beat, note, midi, duration, velocity
  - [x] Define `PhraseState` dataclass: motif_id, motif_degrees, cadence_degree, highest_degree, novelty
  - [x] Define `CalmPhrase` dataclass: phrase_id, mood, key, scale, bpm, time_signature, bars, events, state

- [x] **M0-2 - Scale and degree utilities**
  - [x] Implement `degree_to_note(degree, octave_hint)` → note name + MIDI
  - [x] Implement `note_to_midi(note_name)` and `midi_to_freq(midi)` helpers
  - [x] Enforce register clamp: ensure output stays within G4–A5

- [x] **M0-3 - Phrase generator**
  - [x] Implement seeded RNG wrapper so same seed + state → same output
  - [x] Implement motif generation: 3–5 degrees, start degree from {1, 3, 5}, end from {3, 5, 6}
  - [x] Implement bar filling: choose notes and durations to total exactly 4 beats per bar
  - [x] Implement 4-bar arc: bar 1 introduces motif, bar 2 answers, bar 3 varies/peaks, bar 4 settles
  - [x] Implement cadence weighting: degree 1 → 60%, degree 5 → 25%, degree 3 → 15%
  - [x] Implement motif carry-forward from previous_state

- [x] **M0-4 - Phrase validation and repair**
  - [x] Check: phrase ends on degree 1, 3, or 5
  - [x] Check: all notes within G4–A5 (MIDI 67–81)
  - [x] Check: each bar sums to exactly 4.0 beats
  - [x] Check: no pitch appears more than 4 times in one bar
  - [x] Check: A5 appears at most once in the phrase
  - [x] Check: phrase has at least one descending note pair
  - [x] Check: ≤60% eighth notes across the phrase
  - [x] Repair strategy: regenerate up to MAX_RETRIES=5 times with modified seed
  - [x] On exhausted retries: raise `GenerationFailedError` with attempt count

- [x] **M0-5 - `/api/music/calm/next_phrase` endpoint**
  - [x] Add `POST /api/music/calm/next_phrase` to `api/main.py`
  - [x] Pydantic request model: `session_id`, `seed`, `previous_state` (nullable)
  - [x] Pydantic response model: full `CalmPhrase` shape
  - [x] Wire up generator with config, seed, and previous_state
  - [x] Handle `GenerationFailedError` → HTTP 422 with structured body
  - [x] Add endpoint to specs/INDEX.md

- [x] **M0-T - Tests**
  - [x] Unit: scale degree → correct note name and MIDI
  - [x] Unit: bar duration totals exactly 4 beats
  - [x] Unit: cadence note is always degree 1, 3, or 5
  - [x] Unit: same seed + null state produces identical phrase twice
  - [x] Unit: same seed + previous_state produces identical phrase twice
  - [x] Unit: all notes within G4–A5
  - [x] Unit: no pitch > 4 times per bar
  - [x] Unit: A5 appears ≤1 time per phrase
  - [x] Unit: phrase has at least one descending interval
  - [x] Unit: eighth-note proportion ≤60%
  - [x] Unit: motif state is carried into phrase 2 when previous_state is supplied
  - [x] Integration: POST /api/music/calm/next_phrase returns 200 with valid schema
  - [x] Integration: POST with invalid request returns 422
  - [x] Integration: exhausted retries returns 422 with `generation_failed` error code

---

## Tier 0 — Frontend

Minimum frontend to play a calm phrase end-to-end.

- [ ] **M0-F1 - TypeScript types**
  - [x] Add `NoteEvent`, `PhraseState`, `CalmPhrase`, `NextPhraseRequest` types to `ui/src/api.ts` using snake_case field names

- [ ] **M0-F2 - Music API client**
  - [x] Add `fetchCalmPhrase(session_id, seed, previous_state)` to `ui/src/api.ts`
  - [x] Handle 422 `generation_failed` error gracefully

- [ ] **M0-F3 - Tone.js dependency**
  - [x] `npm install tone` in `ui/`
  - [x] Create `ui/src/music/synth.ts`: Tone.js bootstrap, AudioContext resume, synth factory
  - [x] Synth type: `Tone.Synth` with `oscillator.type = "triangle"` (or `"square"` — TBD)
  - [x] Expose `startAudioContext()` to be called on first user gesture

- [ ] **M0-F4 - Phrase playback engine**
  - [x] Create `ui/src/music/player.ts`
  - [x] Implement `schedulePhrase(phrase: CalmPhrase)`: sort events by (bar, beat), schedule each via `Tone.Transport`
  - [x] Map duration strings: `"8n"` → 0.5 beats, `"4n"` → 1 beat, `"2n"` → 2 beats
  - [x] Convert MIDI to frequency: `Tone.Frequency(midi, "midi").toFrequency()`
  - [x] Set `Tone.Transport.bpm.value = phrase.bpm` on first phrase
  - [x] Implement `stop()`: cancel all scheduled events, stop Transport

- [ ] **M0-F5 - Music player UI component**
  - [x] Create `ui/src/components/MusicPlayer.tsx`
  - [x] Start / Stop buttons
  - [x] Add a persistent `Music Off` toggle that blocks playback and phrase fetching
  - [x] Require user gesture before starting AudioContext (AC-001)
  - [x] Show Playing / Stopped status badge
  - [x] Wire up `fetchCalmPhrase` → `schedulePhrase`
  - [x] Pass `previousState` from last phrase into next request
  - [x] Add to appropriate location in layout (TBD — Header or sidebar)

- [ ] **M0-F6 - Debug phrase view**
  - [x] "Generate Phrase (Debug)" button — fetch without playing
  - [x] Display compact note list: `B1: C5-4n E5-4n D5-2n | B2: ...`
  - [x] Display `motif_id`, `cadence_degree`, `bpm`
  - [x] Gate behind `dev_mode` or always visible TBD

---

## Tier 1 — Smooth Looping

Improve continuity so music loops without gaps or jarring cuts.

- [ ] **M1-1 - Phrase queue**
  - [ ] Pre-fetch next phrase while current is still playing (look-ahead buffer)
  - [ ] Keep 2 phrases queued at all times when playing
  - [ ] Handle fetch failures gracefully (replay last phrase rather than silence)

- [ ] **M1-2 - Scheduled loop switching**
  - [ ] Switch to next phrase at the exact bar boundary, not when the last note ends
  - [ ] Pass motif state from completed phrase to queued phrase request

- [ ] **M1-3 - Stop/start without clicks or pops**
  - [ ] Fade out over 0.5 s on Stop
  - [ ] Fade in over 0.25 s on Start
  - [ ] Do not cut notes mid-sustain

- [ ] **M1-4 - Transport improvements**
  - [ ] BPM changes between phrases should be glide-rate limited
  - [ ] Expose tempo as a visible control (±10 BPM trim)

- [ ] **M1-5 - Debugging improvements**
  - [ ] Phrase history panel: last N phrases with motifId, seed, cadence
  - [ ] Export last phrase as JSON for regression testing

---

## Tier 2 — Multi-Track Chiptune Arrangement

Expand from a single melody to a 4-part arrangement.

- [ ] **M2-1 - Lead voice (Tier 0 melody promoted)**
  - [ ] Separate lead generator config from the monophonic prototype
  - [ ] Add slight velocity variation per phrase for expression

- [ ] **M2-2 - Harmony voice**
  - [ ] Generate a harmony line that is 3rds or 6ths below the lead (within C major pentatonic)
  - [ ] Harmony starts at Tier 2 — no harmony in Tier 0 or Tier 1

- [ ] **M2-3 - Bass line**
  - [ ] Bass follows chord roots: C–Am–F–G (or pentatonic-safe root motion)
  - [ ] Register: C2–G3
  - [ ] Square or triangle oscillator with more attack

- [ ] **M2-4 - Noise / percussion**
  - [ ] Simple chiptune drum pattern: kick on 1 and 3, snare on 2 and 4, hi-hat 8n fills
  - [ ] Tone.js `NoiseSynth` or sampled one-shot
  - [ ] Optional — can be toggled off per-session

- [ ] **M2-5 - Multi-track voicing rules**
  - [ ] Lead and harmony never overlap in frequency at the same beat
  - [ ] Bass does not cross above lead

- [ ] **M2-6 - Density controls**
  - [ ] Per-track mute / solo in debug panel
  - [ ] Overall density slider: sparse → full (affects note count per bar)

- [ ] **M2-7 - Simple mixer**
  - [ ] Per-track volume control
  - [ ] Master volume control
  - [ ] Persist volume preferences in localStorage

---

## Later / Future

Ideas not scoped to any current tier.

- [ ] **Tense mood** — minor pentatonic, faster tempo, denser rhythm
- [ ] **Combat mood** — driving bass, shorter phrases, high urgency
- [ ] **Transition stingers** — 2-bar stinger when mood changes (calm → tense, etc.)
- [ ] **Mood recognition from game state** — detect combat, NPC emotion from session state
- [ ] **Cue selection** — pick stinger based on event type (encounter, discovery, NPC reaction)
- [ ] **MIDI export** — download last phrase or session as MIDI file for debugging
- [ ] **Generated music test corpus** — golden-file regression suite for phrase output

---

## Known Limitations

- [ ] **No generated audio files** — Tier 0 is symbolic only; browser synth produces all sound
- [ ] **No persistence** — phrase state is frontend-managed; refreshing the page resets music
- [ ] **No real adaptive mood detection** — GM manually controls mood at Tier 0
- [ ] **No multi-track** — single monophonic melody until Tier 2
- [ ] **Generated quality depends on validation rules** — phrase shape is rule-driven, not ML;
      edge-case phrases may sound mechanical until motif logic is refined

---

## Open Questions

- [ ] Where should the music debug UI live — Header, sidebar, or floating panel?
- [ ] Should phrase state be stored in backend session state or remain frontend-only?
- [x] API request/response casing decided: snake_case for Tier 0
- [x] Triangle or square oscillator as the Tier 0 default?
- [ ] Should generated phrases be persisted to `outputs/` for replay and debugging?
- [ ] Should BPM be fixed for a session or vary phrase-by-phrase within the allowed range?
- [x] `session_id` is optional in Tier 0 request
