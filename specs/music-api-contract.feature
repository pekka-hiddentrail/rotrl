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
is `POST /music/calm/next-phrase`. All types in this contract should use the casing convention
already established in the project API (check `api/main.py` for current practice — camelCase vs
snake_case; this spec uses camelCase as placeholder and defers to the project convention).

---

## Background

- Given the FastAPI backend is running
- And no session is required for a basic phrase request (though `sessionId` may be passed for future context)
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
        POST /music/calm/next-phrase
        { "sessionId": "demo", "seed": 12345, "previousState": null }
Then  the backend responds 200 OK
And   the response body matches the phrase schema (see AC-003)
And   response.state.motifId is a non-empty string
And   response.state.novelty equals 1
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Frontend requests a follow-up phrase with previous motif state
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Continuation — passing last phrase's state for musical coherence.

```gherkin
Given phrase 1 was returned with state { motifId: "m001", motifDegrees: [1,2,3,5], ... }
When  the frontend sends:
        POST /music/calm/next-phrase
        { "sessionId": "demo", "seed": 99, "previousState": <phrase1.state> }
Then  the backend responds 200 OK
And   response.state.motifId is non-null
And   the response phrase begins with a note consistent with previousState.motifDegrees
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
        phraseId     : string   (e.g. "calm_20260609_12345")
        mood         : "calm"
        key          : "C"
        scale        : "major_pentatonic"
        bpm          : integer in [88, 108]
        timeSignature: "4/4"
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
        motifId      : string
        motifDegrees : array of integers from {1, 2, 3, 5, 6}
        cadenceDegree: integer from {1, 3, 5}
        highestDegree: integer from {1, 2, 3, 5, 6}
        novelty      : integer >= 1
```

**Example response:**

```json
{
  "phraseId": "calm_20260609_12345",
  "mood": "calm",
  "key": "C",
  "scale": "major_pentatonic",
  "bpm": 96,
  "timeSignature": "4/4",
  "bars": 4,
  "events": [
    { "bar": 1, "beat": 1.0, "note": "C5", "midi": 72, "duration": "4n", "velocity": 0.6 },
    { "bar": 1, "beat": 2.0, "note": "E5", "midi": 76, "duration": "4n", "velocity": 0.55 },
    { "bar": 1, "beat": 3.0, "note": "D5", "midi": 74, "duration": "2n", "velocity": 0.5 }
  ],
  "state": {
    "motifId": "m_12345_001",
    "motifDegrees": [1, 3, 2],
    "cadenceDegree": 1,
    "highestDegree": 3,
    "novelty": 1
  }
}
```

> **Note on casing:** the field names above use camelCase as a placeholder. The final implementation
> should match the casing convention used by existing endpoints in `api/main.py`.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Same seed + same previousState returns identical phrase
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Determinism — essential for debugging and phrase replay.

```gherkin
Given seed=12345 and previousState=null
When  POST /music/calm/next-phrase is called twice with identical request bodies
Then  both responses have identical events arrays
And   both responses have identical state objects
And   both responses have the same phraseId
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
Given a request body with mood="combat" (not yet supported at Tier 0)
When  POST /music/calm/next-phrase is called
Then  the backend responds 422 Unprocessable Entity
And   the error body contains "error" and "detail" fields

Given a request body where seed is a non-integer string
When  POST /music/calm/next-phrase is called
Then  the backend responds 422 Unprocessable Entity
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — Generation failure returns 422 with retry info
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** If the generator exhausts retries it surfaces a structured error, not a 500.

```gherkin
Given the generator configuration forces all validation checks to fail (test-only)
When  POST /music/calm/next-phrase is called
Then  the backend responds 422
And   the error body contains:
        { "error": "generation_failed", "attempts": <int>, "detail": "<reason>" }
And   no 500 Internal Server Error is returned
```

---

## Out of Scope

- `GET /music/calm/phrase/{phraseId}` — phrase persistence and retrieval (future Tier 1)
- `POST /music/transition` — mood stingers and transitions (Tier 2+)
- WebSocket streaming of notes one-by-one — all notes are returned in a single batch
- Audio files or base64 audio in any response field (Tier 0 constraint)
- Session-linked music state persistence — state is passed by the client each call (Tier 0)

---

## Notes

**Planned endpoint summary:**

| Method | Path                         | Tier | Purpose                              |
|--------|------------------------------|------|--------------------------------------|
| POST   | `/music/calm/next-phrase`    | 0    | Generate one 4-bar calm phrase       |
| GET    | `/music/calm/phrase/{id}`    | 1    | Retrieve a previously generated phrase |
| POST   | `/music/transition`          | 2+   | Request a mood-transition stinger    |

**Casing convention:** Defer to whatever `api/main.py` uses for existing POST body fields —
currently a mix. Recommend aligning to `snake_case` for consistency with Python internals and
existing Pydantic models, but this is an open question (see MUSIC_TODO.md).

**Related specs:**
- [music-calm-generation.feature](music-calm-generation.feature) — generator rules this endpoint wraps
- [music-calm-playback.feature](music-calm-playback.feature) — frontend that calls this endpoint

**Open questions:**
- snake_case vs camelCase for request/response fields?
- Should `sessionId` be required or optional?
- Should `bpm` be fixed per session or allowed to vary per phrase?
