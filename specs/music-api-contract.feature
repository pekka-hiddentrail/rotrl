# FEATURE — Music API Contract

**ID:** music-api-contract
**Status:** Draft
**Area:** Backend | Frontend
**Tags:** @music @api @calm @symbolic @contract

---

## Story

> As the **React frontend**,
> I want a stable JSON API that returns symbolic note events for a calm phrase,
> so that I can synthesise music entirely in the browser without the server generating audio.

This spec pins the request/response shape for the music endpoint family. The only Tier 0 endpoint
is `POST /api/music/calm/next_phrase`. Tier 0 uses snake_case request/response fields.

---

## Background

- Given the FastAPI backend is running
- And no session is required for a basic phrase request (though `session_id` may be passed for future context)
- And the `mood` for all Tier 0 requests is `"calm"`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Frontend requests a first phrase with no previous state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Cold-start — no motif history yet.

```gherkin
Given the frontend has no stored phrase state
When  the frontend sends:
        POST /api/music/calm/next_phrase
        { "session_id": "demo", "seed": 12345, "previous_state": null }
Then  the backend responds 200 OK
And   the response body matches the phrase schema (see AC-003)
And   response.state.motif_id is a non-empty string
And   response.state.novelty equals 1
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Frontend requests a follow-up phrase with previous motif state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Continuation — passing last phrase's state for musical coherence.

```gherkin
Given phrase 1 was returned with state { motif_id: "m001", motif_degrees: [1,2,3,5], ... }
When  the frontend sends:
        POST /api/music/calm/next_phrase
        { "session_id": "demo", "seed": 99, "previous_state": <phrase1.state> }
Then  the backend responds 200 OK
And   response.state.motif_id is non-null
And   the response phrase begins with a note consistent with previous_state.motif_degrees
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Response body conforms to the phrase schema
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Shape validation — every required field is present and typed correctly.

```gherkin
Given a phrase has been generated and returned
When  the response body is inspected
Then  it contains these top-level fields with correct types:
        phrase_id     : string   (deterministic for identical request inputs)
        mood         : "calm"
        key          : "C"
        scale        : "major_pentatonic"
        bpm          : integer in [88, 108]
        time_signature: "4/4"
        bars         : 4
        events       : array (min 1 element)
        state        : object
And   each event in events contains:
        bar      : integer 1–4
        beat     : number  1.0–4.0 (1-indexed, fractional for 8n offsets)
        note     : string  e.g. "C5"
        midi     : integer 67–81
        duration : one of "8n", "4n", "2n"
        velocity : number  0.0–1.0
And   state contains:
        motif_id      : string
        motif_degrees : array of integers from {1, 2, 3, 5, 6}
        cadence_degree: integer from {1, 3, 5}
        highest_degree: integer from {1, 2, 3, 5, 6}
        novelty      : integer >= 1
```

**Example response:**

```json
{
        "phrase_id": "calm_s12345_h9f0a1c2d",
  "mood": "calm",
  "key": "C",
  "scale": "major_pentatonic",
  "bpm": 96,
        "time_signature": "4/4",
  "bars": 4,
  "events": [
    { "bar": 1, "beat": 1.0, "note": "C5", "midi": 72, "duration": "4n", "velocity": 0.6 },
    { "bar": 1, "beat": 2.0, "note": "E5", "midi": 76, "duration": "4n", "velocity": 0.55 },
    { "bar": 1, "beat": 3.0, "note": "D5", "midi": 74, "duration": "2n", "velocity": 0.5 }
  ],
  "state": {
                "motif_id": "m_12345_001",
                "motif_degrees": [1, 3, 2],
                "cadence_degree": 1,
                "highest_degree": 3,
    "novelty": 1
  }
}
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Same seed + same previous_state returns identical phrase
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Determinism — essential for debugging and phrase replay.

```gherkin
Given seed=12345 and previous_state=null
When  POST /api/music/calm/next_phrase is called twice with identical request bodies
Then  both responses have identical events arrays
And   both responses have identical state objects
And   both responses have the same phrase_id
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Tier 0 never returns audio data
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** No audio rendering on the server — symbolic only.

```gherkin
Given any valid calm phrase request
When  the response is received
Then  the response Content-Type is "application/json"
And   the response body contains no "audioUrl", "wavBase64", "mp3Base64", or binary audio fields
And   the backend never writes WAV, MP3, OGG, or MIDI files to disk for this endpoint
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — Invalid request returns 422 with a structured error
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Bad input is rejected at the API boundary.

```gherkin
Given a request body where seed is a non-integer string
When  POST /api/music/calm/next_phrase is called
Then  the backend responds 422 Unprocessable Entity
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Generation failure returns 422 with retry info
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** If the generator exhausts retries it surfaces a structured error, not a 500.

```gherkin
Given the generator configuration forces all validation checks to fail (test-only)
When  POST /api/music/calm/next_phrase is called
Then  the backend responds 422
And   the error body contains:
        { "error": "generation_failed", "attempts": <int>, "detail": "<reason>" }
And   no 500 Internal Server Error is returned
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-008 — Planned: multi-track response for lead + bass
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Status:** Planning — not yet implemented. Specifies the target shape when the bass track is
added. See [music-calm-bass-track.feature](music-calm-bass-track.feature) for full rules.

```gherkin
Given the bass track phase is implemented
When  POST /api/music/calm/next_phrase is called
Then  the response contains "tracks" (array) instead of the flat "events" field
And   each element in tracks has: track_id, role, events
And   track_id="lead" carries the existing melody events
And   track_id="bass" carries the new bass events (see music-calm-bass-track.feature)
And   the state object adds: bass_pattern_id (string), bass_final_degree (integer 1|3|5)
And   all other top-level fields (phrase_id, mood, key, bpm, bars, etc.) remain unchanged
And   the response is still Content-Type: application/json with no audio data
```

**Target state object (extended):**

```json
{
  "motif_id": "m_12345_001",
  "motif_degrees": [1, 3, 2],
  "cadence_degree": 1,
  "highest_degree": 3,
  "novelty": 1,
  "bass_pattern_id": "bp_12345_001",
  "bass_final_degree": 1
}
```

**Migration note:** The existing `events` top-level field (flat lead track events) is replaced by
`tracks` — this is a breaking change. Both the Pydantic model and `ui/src/api.ts` `CalmPhrase`
type must be updated atomically. See music-calm-bass-track.feature Notes for the full migration
checklist.

---

## Out of Scope

- `GET /api/music/calm/phrase/{phrase_id}` — phrase persistence and retrieval (future Tier 1)
- `POST /api/music/transition` — mood stingers and transitions (Tier 2+)
- WebSocket streaming of notes one-by-one — all notes are returned in a single batch
- Audio files or base64 audio in any response field (Tier 0 constraint)
- Session-linked music state persistence — state is passed by the client each call (Tier 0)

---

## Notes

**Planned endpoint summary:**

| Method | Path                         | Tier | Purpose                              |
|--------|------------------------------|------|--------------------------------------|
| POST   | `/api/music/calm/next_phrase`    | 0    | Generate one 4-bar calm phrase       |
| GET    | `/api/music/calm/phrase/{id}`    | 1    | Retrieve a previously generated phrase |
| POST   | `/api/music/transition`          | 2+   | Request a mood-transition stinger    |

**Casing convention:** Tier 0 uses snake_case fields in both request and response.

**Related specs:**
- [music-calm-generation.feature](music-calm-generation.feature) — generator rules this endpoint wraps
- [music-calm-playback.feature](music-calm-playback.feature) — frontend that calls this endpoint

**Open questions:**
- Should `session_id` be required or optional?
- Should `bpm` be fixed per session or allowed to vary per phrase?
