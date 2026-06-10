# FEATURE — Calm Music Playback (Frontend)

**ID:** music-calm-playback
**Status:** Tier 0 + Tier 1 M1-1/M1-2/M1-3 implemented; AC-014 (bar indicator) implemented
**Area:** Frontend
**Tags:** @music @playback @calm @ui @webaudio

---

## Story

> As a **GM using the app**,
> I want calm ambient music to play in the background while running a social scene,
> so that the atmosphere is enhanced without distracting from gameplay.

The frontend fetches symbolic note events from the backend and synthesises them in the browser
using Tone.js. No audio files are downloaded. The synth is a triangle oscillator (chiptune
aesthetic). Playback is phrase-based: the frontend pre-fetches the next phrase immediately after
scheduling the current one, so the swap at each bar boundary is instantaneous with no silence.

---

## Background

- Given the app is loaded in a browser that supports Web Audio API
- And a session is active (or a dev-mode "music only" path is available)
- And the backend `POST /api/music/calm/next_phrase` endpoint is reachable

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Audio does not start before a user gesture
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Web Audio autoplay policy requires a user interaction before the AudioContext can
start. Violating this causes a silent or error state in most browsers.

```gherkin
Given the page has just loaded
When  no user interaction has occurred
Then  the AudioContext is not started
And   no notes are played
And   no HTTP requests to /music are made

When  the user clicks "Start Music"
Then  the AudioContext is resumed or created
And   phrase fetching and playback begin
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Start calm music from a UI control
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The user explicitly starts the music player.

```gherkin
Given the app is in a session
And   the music player is stopped
When  the user activates the "Start Music" control
Then  the frontend calls POST /api/music/calm/next_phrase with seed and previous_state=null
And   the returned events are scheduled into Tone.js Transport (or Web Audio clock)
And   the first note plays within one beat of the scheduled start time
And   the music player UI transitions to "Playing" state
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Stop calm music from a UI control
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The user explicitly stops the music player.

```gherkin
Given the music player is in "Playing" state
When  the user activates the "Stop Music" control
Then  all scheduled note events are cancelled
And   the Tone.js Transport (or Web Audio clock) is paused or stopped
And   the music player UI transitions to "Stopped" state
And   no further HTTP requests to /music are made until restarted
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Play symbolic events in bar/beat order
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Events are scheduled by bar + beat position, not by array index.

```gherkin
Given a phrase response with events in arbitrary array order
When  the frontend schedules the phrase
Then  events are sorted by (bar, beat) before scheduling
And   event at bar=1, beat=1 plays first
And   event at bar=4, beat=4 (or last beat of bar 4) plays last
And   each note's duration maps correctly: "4n"→quarter, "2n"→half, "8n"→eighth
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Phrase-level scheduling — no per-note API calls
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The frontend fetches one full phrase at a time, not individual notes.

```gherkin
Given the music player is playing
When  a 4-bar phrase is being synthesised
Then  exactly one HTTP request was made to /api/music/calm/next_phrase for that phrase
And   no HTTP request is made per note event
And   the next phrase prefetch begins immediately after the current phrase is scheduled
      (not on a timer — fetch and schedule are decoupled)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Browser-side synthesis — triangle or square oscillator
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The synth is a simple chiptune-style oscillator; no audio assets are loaded.

```gherkin
Given the music player starts
When  a note event is played
Then  the sound is produced by a Tone.js Synth (or equivalent Web Audio OscillatorNode)
      configured with oscillator type "triangle" or "square"
And   no audio files (WAV, MP3, OGG) are fetched from the network for synthesis
And   the note's MIDI value is converted to frequency before being sent to the oscillator
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Debug: generate one phrase without playback
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A developer wants to inspect phrase output without hearing it.

```gherkin
Given a "Generate Phrase (Debug)" button or action is available in dev mode
When  the developer activates it
Then  the frontend calls POST /api/music/calm/next_phrase
And   the response JSON is displayed in a debug panel or browser console
And   no audio is played unless playback is separately enabled
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Debug view: display current phrase as compact note list
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The current phrase is human-readable in the UI during development.

```gherkin
Given a phrase has been generated and is playing (or was last generated in debug mode)
When  the debug music panel is open
Then  the panel shows either:
        (a) the raw phrase JSON from the backend, or
        (b) a compact note list: e.g. "B1: C5-4n E5-4n D5-2n | B2: G4-2n A4-8n ..."
And   the motif_id and cadence_degree are visible
And   bpm is displayed
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-009 — Phrase motif state is passed between consecutive requests
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The frontend maintains a rolling previous_state so each phrase is musically
connected to the last.

```gherkin
Given phrase N has finished playing
And   the frontend stored phrase N's state.motif_id and state.motif_degrees
When  the frontend requests phrase N+1
Then  the request body includes previous_state = { phrase N's state }
And   the seed for phrase N+1 is derived or incremented from the session seed
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-010 — Volume control
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The GM can adjust playback volume without stopping music.

```gherkin
Given the music player is visible
When  the user moves the volume slider
Then  the output volume changes immediately via Tone.getDestination().volume
And   the volume persists across page reloads (stored in localStorage)
And   the slider range is 0 (silent) to 100 (maximum, +12 dB above nominal)

Given the page reloads
And   a volume level was previously saved
When  the MusicPlayer mounts
Then  the slider restores to the saved value
And   Tone.getDestination().volume is set to the corresponding dB level before any playback
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-011 — Seamless bar-boundary phrase switching (Tier 1)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Phrases transition without audible silence between them.

```gherkin
Given the music player is playing
And   phrase N is currently scheduled on the Transport
When  the swap timer fires (~500 ms before phrase N ends)
Then  phrase N+1 is already pre-fetched and waiting in the prefetch buffer
And   phrase N+1 is scheduled onto the Transport immediately at the exact bar boundary
      (nextScheduleAtMs = phraseN.startMs + phraseN.durationMs)
And   there is no gap between the last note of phrase N and the first note of phrase N+1
And   the prefetch for phrase N+2 starts immediately after phrase N+1 is scheduled
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-012 — Fetch failure fallback: replay last phrase (Tier 1)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A slow or failed network request must not produce silence.

```gherkin
Given phrase N+1 prefetch is in flight when the swap timer fires
When  the prefetch has not returned within 3000 ms of the swap time
Then  the last successfully played phrase is rescheduled from the bar boundary
And   playback continues without silence
And   an error indicator is shown in the UI

Given the prefetch returns a non-2xx response or network error
Then  the same fallback replay applies
And   the next prefetch attempt is started immediately after the fallback is scheduled
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-013 — Stop fade-out: no hard cut (Tier 1)
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Stopping music fades out smoothly instead of cutting mid-note.

```gherkin
Given the music player is in "Playing" state
When  the user activates the "Stop Music" control
Then  Tone.getDestination().volume ramps to -Infinity dB over 0.5 seconds
And   all scheduled note events are cancelled after the fade completes
And   the Transport is stopped after the fade completes
And   the music player UI transitions to "Stopped" state immediately on click
      (UI is responsive; audio fades in background)

Given the player is stopped due to an error (not user action)
Then  a hard stop is used instead of fade (no further audio output is desired)
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-014 — Active bar indicator: Intent row
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The GM can see which bar of the current phrase is playing, and follow the
note list without getting lost.

```gherkin
Given a phrase has been scheduled and is playing
Then  the music player shows an Intent row: "Intent: B1  B2  B3  B4"
      (one chip per bar in the phrase, in order)
And   the chip for the currently playing bar is visually highlighted
And   the detailed note row below mirrors the same highlighting on its bar labels

When  bar N starts playing (Transport callback fires for that bar)
Then  the chip for BN becomes active and all other chips become inactive

When  the music player is stopped (fade or hard stop)
Then  no bar chip is highlighted
```

---

## Out of Scope

- Harmony, second voice, bass line, or percussion — single monophonic synth only
- Audio file download or offline caching of phrases
- Mood detection — the GM manually selects mood for now
- Automatic mood switching on combat or NPC events — Tier 2+
- Volume normalisation, EQ, or reverb — keep it raw at Tier 0
- A separate "Music Off" toggle — Stop Music button is sufficient
- MIDI output or export
- Mobile PWA background audio
- Phrase queue lookahead beyond 1 (keep 2–3 pre-fetched simultaneously) — Tier 2+
- BPM glide rate limiting between phrases — Tier 1 M1-4 (deferred)
- ±10 BPM tempo trim control — Tier 1 M1-4 (deferred)

---

## Notes

**Library:** Tone.js (`npm install tone`) — implemented.

- `Tone.Synth` with `oscillator.type = "triangle"` — triangle chosen as default
- `Tone.getTransport().bpm.value = phrase.bpm` — set per phrase
- Schedule events: `transport.schedule(time => synth.triggerAttackRelease(freq, dur), at)`
- MIDI → frequency: `Tone.Frequency(midi, "midi").toFrequency()`
- Volume: `Tone.getDestination().volume.value` — mapped from linear 0–100 slider with +12 dB boost
  so the full range is −∞ to +12 dB; default slider position is 70 (~+9 dB)

**Scheduling timing note (Tier 0):** `nowMs` is captured *after* the phrase fetch completes so that
`startDelayMs` reflects actual remaining lookahead time. If the scheduler falls behind real time,
the clock resets to `now + 100ms` rather than scheduling notes into the past.

**Tier 1 scheduling architecture:** Fetching and scheduling are decoupled.
- `prefetchedRef: CalmPhrase | null` holds a phrase that has been fetched but not yet scheduled
- `triggerPrefetch()` — fires immediately after each `schedulePhrase()` call, no timer delay
- Swap timer fires `SWAP_BUFFER_MS` (500 ms) before phrase N ends
- On swap: take `prefetchedRef`, call `schedulePhrase` at the exact next bar boundary, call `triggerPrefetch()` for N+2
- `nextScheduleAtMs` is tracked in Transport seconds (not wall-clock ms) to stay locked to the audio clock
- Fallback: if `prefetchedRef` is null at swap time, poll every 50 ms up to `PREFETCH_TIMEOUT_MS` (3000 ms), then replay last phrase
- Stop path: `player.stop(fadeSecs = 0.5)` — snapshots current `scheduledIds` immediately, ramps `Tone.getDestination().volume` to −∞ dB, then cancels only the snapshotted IDs and stops Transport; `schedulePhrase` called during a fade cancels the fade timer so new-phrase notes are never affected

**Minimum schedule lookahead:** `MIN_SCHEDULE_AHEAD_S = 0.15 s` — 150 ms minimum gap between the
current Transport position and the first note of a newly scheduled phrase. Prevents the first beat
from being treated as already-past on slower systems.

**Grace note / phrase-boundary fix:** A `triggerRelease()` is scheduled 1 ms before each phrase's
first note fires. This flushes any lingering release tail from the previous phrase before the new
attack starts. The synth `release` envelope is set to `0.05 s` (down from `0.2 s`) so tails are
inaudible even if the boundary callback is slightly late.

**Bar indicator (AC-014):** `schedulePhrase` accepts an optional `onBarChange?: (bar: number) => void`
callback. It schedules a Transport callback at the start of each bar that fires the callback with the
bar number. `MusicPlayer` passes `setCurrentBar` and renders:
- Intent row: compact chips "B1 B2 B3 B4" — active chip highlighted green
- Notes row: same highlighting on bar labels in the detailed note list
Both reset to `currentBar = 0` (no highlight) when music stops.

**Duration mapping:**

| Symbol | Tone.js value | Beats |
|--------|--------------|-------|
| `8n`   | `"8n"`       | 0.5   |
| `4n`   | `"4n"`       | 1.0   |
| `2n`   | `"2n"`       | 2.0   |

**Music UI location:** `ui/src/components/MusicPlayer.tsx`, rendered in `App.tsx`.

**Related specs:**
- [music-calm-generation.feature](music-calm-generation.feature) — generator rules
- [music-api-contract.feature](music-api-contract.feature) — endpoint this component calls

**Open questions:**
- Triangle or square oscillator — triangle shipped; square still an option
- Where does the music player control live long-term — Header, sidebar, or floating?
- Should the debug phrase view be gated behind `dev_mode`?
