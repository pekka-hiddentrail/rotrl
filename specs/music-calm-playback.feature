# FEATURE — Calm Music Playback (Frontend)

**ID:** music-calm-playback
**Status:** Implemented (Tier 0)
**Area:** Frontend
**Tags:** @music @playback @calm @ui @webaudio

---

## Story

> As a **GM using the app**,
> I want calm ambient music to play in the background while running a social scene,
> so that the atmosphere is enhanced without distracting from gameplay.

The frontend fetches symbolic note events from the backend and synthesises them in the browser
using Tone.js or the Web Audio API directly. No audio files are downloaded. The synth is a simple
triangle or square oscillator (chiptune aesthetic). Playback is phrase-based: the frontend
schedules a full 4-bar phrase, then requests the next one before the current one ends.

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
And   the next phrase request is made while the current phrase is still playing
      (look-ahead scheduling — not after the last note ends)
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

## Out of Scope

- Harmony, second voice, bass line, or percussion — single monophonic synth only
- Audio file download or offline caching of phrases
- Mood detection — the GM manually selects mood for now
- Automatic mood switching on combat or NPC events — Tier 2+
- Volume normalisation, EQ, or reverb — keep it raw at Tier 0
- A separate "Music Off" toggle — Stop Music button is sufficient
- MIDI output or export
- Mobile PWA background audio
- Phrase queue lookahead (2–3 phrases buffered) — Tier 1

---

## Notes

**Library:** Tone.js (`npm install tone`) — implemented.

- `Tone.Synth` with `oscillator.type = "triangle"` — triangle chosen as default
- `Tone.getTransport().bpm.value = phrase.bpm` — set per phrase
- Schedule events: `transport.schedule(time => synth.triggerAttackRelease(freq, dur), at)`
- MIDI → frequency: `Tone.Frequency(midi, "midi").toFrequency()`
- Volume: `Tone.getDestination().volume.value` — mapped from linear 0–100 slider with +12 dB boost
  so the full range is −∞ to +12 dB; default slider position is 70 (~+9 dB)

**Scheduling timing note:** `nowMs` is captured *after* the phrase fetch completes so that
`startDelayMs` reflects actual remaining lookahead time, not stale pre-fetch time. If the
scheduler falls behind real time (late fetch, tab backgrounded), the clock resets to
`now + 100ms` rather than attempting to schedule notes into the past.

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
