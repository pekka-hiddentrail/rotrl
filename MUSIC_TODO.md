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

Status snapshot (2026-06-10): Tier 0 backend/API/tests and frontend playback controls are complete.
Tier 1 prefetch pipeline, stop fade, and audio quality fixes are complete.
Bar-level Intent indicator implemented (AC-014).

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

- [x] **M0-F1 - TypeScript types**
  - [x] Add `NoteEvent`, `PhraseState`, `CalmPhrase`, `NextPhraseRequest` types to `ui/src/api.ts` using snake_case field names

- [x] **M0-F2 - Music API client**
  - [x] Add `fetchCalmPhrase(session_id, seed, previous_state)` to `ui/src/api.ts`
  - [x] Handle 422 `generation_failed` error gracefully

- [x] **M0-F3 - Tone.js dependency**
  - [x] `npm install tone` in `ui/`
  - [x] Create `ui/src/music/synth.ts`: Tone.js bootstrap, AudioContext resume, synth factory
  - [x] Synth type: `Tone.Synth` with `oscillator.type = "triangle"`
  - [x] Expose `startAudioContext()` to be called on first user gesture

- [x] **M0-F4 - Phrase playback engine**
  - [x] Create `ui/src/music/player.ts`
  - [x] Implement `schedulePhrase(phrase: CalmPhrase)`: sort events by (bar, beat), schedule each via `Tone.getTransport()`
  - [x] Map duration strings: `"8n"` → 0.5 beats, `"4n"` → 1 beat, `"2n"` → 2 beats
  - [x] Convert MIDI to frequency: `Tone.Frequency(midi, "midi").toFrequency()`
  - [x] Set `transport.bpm.value = phrase.bpm` per phrase
  - [x] Implement `stop()`: cancel all scheduled events, stop Transport

- [x] **M0-F5 - Music player UI component**
  - [x] Create `ui/src/components/MusicPlayer.tsx`
  - [x] Start / Stop buttons (no separate "Music Off" toggle — Stop is sufficient)
  - [x] Volume slider 0–100, persisted to localStorage, mapped to `Tone.getDestination().volume` with +12 dB boost
  - [x] Require user gesture before starting AudioContext (AC-001)
  - [x] Show Playing / Stopped status badge
  - [x] Wire up `fetchCalmPhrase` → `schedulePhrase`
  - [x] Pass `previousState` from last phrase into next request
  - [x] Added to `App.tsx`
  - [x] Fix: capture `nowMs` after fetch so `startDelayMs` is not stale
  - [x] Fix: reset phrase clock when scheduler drifts behind real time (late fetch or backgrounded tab)
  - [x] Fix: `Tone.Destination` (deprecated) → `Tone.getDestination()`
  - [x] Bar-level Intent indicator: "Intent: B1 B2 B3 B4" row — active chip highlighted when Transport bar callback fires
  - [x] Per-bar highlighting in detailed note list (mirrors active bar from Intent row)

- [x] **M0-F6 - Debug phrase view**
  - [x] "Generate Phrase (Debug)" button — fetch without playing, gated behind `devMode` prop
  - [x] Display compact note list: `B1: C5-4n E5-4n D5-2n | B2: ...`
  - [x] Display `motif_id`, `cadence_degree`, `bpm`

---

## Tier 1 — Smooth Looping

Improve continuity so music loops without gaps or jarring cuts.

- [x] **M1-1 + M1-2 - Pre-fetch pipeline and seamless bar-boundary switching**
  - [x] Add `prefetchedRef: CalmPhrase | null` — holds a fetched phrase not yet scheduled
  - [x] Add `prefetchingRef: boolean` — prevents duplicate in-flight fetches
  - [x] `triggerPrefetch()` — starts background fetch into `prefetchedRef`; called immediately after each `scheduleAndContinue()`, no timer delay
  - [x] Replace single-fetch timer cascade with swap timer: fires `SWAP_BUFFER_MS = 500 ms` before phrase end
  - [x] Swap timer handler (`handleSwap`): takes `prefetchedRef`, schedules at exact `nextScheduleAtMsRef`, calls `triggerPrefetch()` for next phrase
  - [x] On start: schedule phrase 1, immediately call `triggerPrefetch()` for phrase 2 (no wait)
  - [x] `previous_state` snapshotted at fetch time via `previousStateRef` set in `scheduleAndContinue` (motif continuity across pipeline)
  - [x] Handle `prefetchedRef === null` at swap time: poll every `PREFETCH_POLL_MS = 50 ms` up to `PREFETCH_TIMEOUT_MS = 3000 ms`
  - [x] Fallback: if timeout exceeded, replay `lastScheduledPhraseRef` from bar boundary — never go silent; show error in UI
  - [x] `schedulePhrase` guards minimum ahead time (`MIN_SCHEDULE_AHEAD_S = 0.15 s`) to prevent past-scheduling

- [x] **M1-3 - Stop fade-out**
  - [x] `stop(fadeSecs = 0)` on `CalmPhrasePlayer` — ramps `Tone.getDestination().volume` to −60 dB over `fadeSecs`, then cancels events and stops Transport
  - [x] User Stop button: `stop(0.5)` — 0.5 s fade; UI transitions to Stopped immediately
  - [x] Error stop and unmount cleanup: `stop(0)` — hard stop, no fade
  - [x] Volume restored to saved level 600 ms after fade so next Start is not silent
  - [x] Global `tone` mock added to `ui/src/test/setup.ts` — prevents tone errors in all App tests
  - [x] Fix: snapshot `scheduledIds` immediately in `stop(fadeSecs)` — prevents fade timer from cancelling next phrase's notes
  - [x] Fix: cancel pending fade timer in `schedulePhrase` — prevents stale fade from stopping Transport mid-new-phrase
  - [x] Fix: `MIN_SCHEDULE_AHEAD_S` raised 0.05 → 0.15 s — prevents first beat being scheduled in Tone.js past on slower systems
  - [x] Fix: grace note at phrase boundary — `triggerRelease` scheduled 1 ms before each phrase start; synth `release` reduced 0.2 → 0.05 s
  - [x] `schedulePhrase` accepts optional `onBarChange: (bar: number) => void` — bar callbacks scheduled on Transport at each bar start

- [ ] **M1-4 - Transport improvements** *(deferred — not part of next step)*
  - [ ] BPM changes between phrases should be glide-rate limited
  - [ ] Expose tempo as a visible control (±10 BPM trim)

- [ ] **M1-5 - Debugging improvements** *(deferred)*
  - [ ] Phrase history panel: last N phrases with motifId, seed, cadence
  - [ ] Export last phrase as JSON for regression testing

---

## Next Phase — Calm Track 2: Bass

Add a second generated symbolic track (bass) to the calm mood phrase.
Spec: [specs/music-calm-bass-track.feature](specs/music-calm-bass-track.feature)

The bass is the first step toward the eventual 4-track arrangement. Only bass is added here.
Percussion and harmony remain deferred to Tier 2.

- [ ] **MB-1 - Update phrase model to support multiple tracks**
  - [ ] Replace flat `events: NoteEvent[]` field in `CalmPhrase` with `tracks: TrackEvents[]`
  - [ ] Add `TrackEvents` dataclass/type: `track_id`, `role`, `events`
  - [ ] Add `bass_pattern_id` and `bass_final_degree` to `PhraseState`
  - [ ] Update Pydantic response model in `api/main.py`
  - [ ] Update `CalmPhrase` TypeScript type in `ui/src/api.ts`

- [ ] **MB-2 - Bass generator — backend**
  - [ ] Define `CalmBassConfig`: register C2–G3 (MIDI 36–55), degrees {1,3,5,6}, durations {1n,2n,4n}, max 3 events/bar, velocity 0.35–0.55
  - [ ] Implement bar-root weight table (see AC-004 in spec): bar 1 C/G, bar 2 G/E/C, bar 3 A/G/E, bar 4 C/G/E
  - [ ] Implement bass bar filler: choose root, fill bar to 4.0 beats using allowed durations
  - [ ] Enforce phrase arc: bar 1 home → bar 2 away → bar 3 lift → bar 4 return
  - [ ] Enforce phrase ending: ≥75% end on degree 1 / C (AC-005)
  - [ ] Enforce density coordination with lead: if lead ≥5 events in bar, bass ≤2 (AC-007)
  - [ ] Enforce movement limit: no consecutive bass notes >12 semitones apart (AC-008)
  - [ ] Generate `bass_pattern_id` from seed; carry `bass_final_degree` in state (AC-012)

- [ ] **MB-3 - Bass validation and repair**
  - [ ] All MIDI values 36–55 (AC-002)
  - [ ] All degrees in {1, 3, 5, 6} (AC-003)
  - [ ] No 8n or shorter durations; max 3 events/bar (AC-006)
  - [ ] Final degree is 1, 3, or 5 — not A / degree 6 (AC-005, AC-011)
  - [ ] No consecutive jump >12 semitones (AC-008)
  - [ ] Lead and bass never both at maximum density in same bar (AC-007, AC-011)
  - [ ] Bass note always below simultaneous lead note (AC-010)
  - [ ] Repair / regenerate up to MAX_RETRIES; return 422 on exhaustion (AC-011)

- [ ] **MB-4 - Backend tests**
  - [ ] Unit: all bass MIDI values within 36–55
  - [ ] Unit: no bass duration is 8n or shorter
  - [ ] Unit: each bass bar sums to exactly 4.0 beats
  - [ ] Unit: final bass note is degree 1, 3, or 5
  - [ ] Unit: bar-root degree distribution within ±10% of target weights (1000 samples)
  - [ ] Unit: phrase ends on degree 1 ≥75% of time (1000 samples)
  - [ ] Unit: no consecutive bass jump >12 semitones
  - [ ] Unit: density coordination — lead-busy bars have ≤2 bass events
  - [ ] Integration: POST /api/music/calm/next_phrase returns tracks array with lead + bass
  - [ ] Integration: state includes bass_pattern_id and bass_final_degree

- [ ] **MB-5 - Frontend: separate bass synth**
  - [ ] Add `getBasssynth()` to `ui/src/music/synth.ts`
  - [ ] Bass synth: triangle, volume 55–70% of lead, envelope attack 0.01/decay 0.08/sustain 0.4/release 0.1
  - [ ] Update `schedulePhrase` in `player.ts` to accept `tracks: TrackEvents[]` and schedule each track to its own synth
  - [ ] Lead events → lead synth (existing behaviour preserved)
  - [ ] Bass events → bass synth (new)
  - [ ] Both synths share same Transport clock and route to `Tone.getDestination()`

- [ ] **MB-6 - Frontend: UI and debug updates**
  - [ ] Intent row and notes row already support per-bar data — extend to show both tracks if needed
  - [ ] No separate bass volume slider at this phase (master volume applies to both)
  - [ ] Update debug phrase display to show bass notes per bar alongside lead notes

- [ ] **MB-7 - Update all specs and docs**
  - [x] Create `specs/music-calm-bass-track.feature` (14 ACs — planning complete)
  - [x] Update `specs/music-api-contract.feature` (AC-008 multi-track shape — planning complete)
  - [x] Update `specs/music-calm-generation.feature` (out-of-scope note updated)
  - [x] Update `specs/INDEX.md` (new row added)
  - [ ] Update `specs/music-calm-playback.feature` with multi-track synth AC when implementation begins
  - [ ] Update README.md music section when implementation begins

---

## Tier 2 — Multi-Track Chiptune Arrangement

Complete the 4-track calm arrangement. The eventual track lineup:

```
Track 1: lead melody    ← Tier 0 (complete)
Track 2: bass           ← Next phase (spec complete, implementation pending)
Track 3: harmony        ← Tier 2
Track 4: noise/percussion ← Tier 2
```

- [ ] **M2-1 - Lead voice (Tier 0 melody promoted)**
  - [ ] Separate lead generator config from the monophonic prototype
  - [ ] Add slight velocity variation per phrase for expression

- [ ] **M2-2 - Harmony voice**
  - [ ] Generate a harmony line that is 3rds or 6ths below the lead (within C major pentatonic)
  - [ ] Harmony starts at Tier 2 — no harmony in Tier 0 or bass phase

- [ ] **M2-3 - Bass line promotion**
  - [ ] Bass phase (Next Phase above) is prerequisite — must be complete before Tier 2 work starts
  - [ ] At Tier 2: extend bass to use richer root motion informed by harmony track
  - [ ] Register: C2–G3 (established in bass phase)

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

- [ ] Where should the music UI live long-term — Header, sidebar, or floating panel? *(currently rendered in App.tsx)*
- [ ] Should phrase state be stored in backend session state or remain frontend-only?
- [x] API request/response casing: snake_case (matches existing convention)
- [x] Triangle or square oscillator default: triangle shipped
- [x] Volume slider at Tier 0: yes — 0–100 linear, +12 dB boost, persisted to localStorage
- [x] Separate "Music Off" toggle: removed — Stop Music button is sufficient
- [ ] Should generated phrases be persisted to `outputs/` for replay and debugging?
- [ ] Should BPM be fixed for a session or vary phrase-by-phrase within the allowed range?
- [x] `session_id` is optional in Tier 0 request
