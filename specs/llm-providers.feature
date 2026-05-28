# FEATURE — LLM Providers

**ID:** llm-providers
**Status:** Approved
**Area:** Backend | Frontend
**Tags:** @llm @groq @ollama @provider

---

## Story

> As a **player**,
> I want to choose between Groq (cloud, fast) and Ollama (local, private),
> so that I can play with the best model available to me at the time.

The provider is selected in the UI before boot and sent to the backend. Groq and Ollama have different payload limits, history sizes, and retry behaviour. Switching provider auto-updates the model dropdown to show the correct options.

---

## Background

- Given the UI is showing the pre-boot header controls

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — Provider switch updates model dropdown
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Player toggles between Groq and Ollama

```gherkin
Given the provider is set to Groq
When  the player switches to Ollama
Then  the model dropdown shows only Ollama models (qwen3:4b, qwen2.5:1.5b)
And   the selected model changes to qwen3:4b

When  the player switches back to Groq
Then  the model dropdown shows only Groq models
And   the selected model changes to llama-3.3-70b-versatile
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — Groq rate limit is retried automatically with a human-readable error
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Groq API returns HTTP 429 (rate limited)

```gherkin
Given the provider is Groq
And   the Groq API returns a 429 response with a retry-after header
When  a turn is submitted
Then  the backend waits the specified retry-after duration (max 60 seconds)
And   retries the request up to 4 times
And   on success the turn streams normally

When  all 4 retries are exhausted
Then  the backend parses the 429 response body
And   the error SSE event contains the Groq error message verbatim
     (e.g. "Groq rate limit: Rate limit reached for model … on tokens per day (TPD):
            Limit 50000, Used 50000 … Please try again after 2026-05-29T00:00:00Z.")
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Groq system prompt is capped at 30,000 chars
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** System prompt exceeds Groq's practical payload limit

```gherkin
Given the provider is Groq
And   the assembled system prompt exceeds 30,000 characters
When  a turn is submitted
Then  the system prompt is truncated to 30,000 characters before sending
And   the turn still completes normally
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Ollama uses num_ctx and num_gpu options
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Session is booted with Ollama provider

```gherkin
Given the provider is Ollama
And   the BootRequest contains num_ctx=4096 and num_gpu=999
When  a turn is submitted
Then  the Ollama API request includes options.num_ctx=4096 and options.num_gpu=999
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Groq per-minute rate limits are surfaced after each turn
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A Groq turn completes successfully

```gherkin
Given the provider is Groq
When  a turn completes and Groq returns x-ratelimit-* response headers
Then  the backend reads: x-ratelimit-{limit,remaining,reset}-{requests,tokens}
And   emits an SSE event: { type: "rate_limits", rpm_limit, rpm_remaining, rpm_reset,
                                                  tpm_limit, tpm_remaining, tpm_reset }
And   if none of those headers are present no rate_limits event is emitted

Given the rate_limits event is received by the frontend
Then  the header displays a compact badge (e.g. "⚡ 4,500/6,000 TPM · 28/30 RPM")
And   hovering the badge shows a tooltip with reset times
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — stream_options degrades gracefully on older Groq models
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Model does not support stream_options (e.g. llama3-8b-8192, mixtral-8x7b-32768)

```gherkin
Given the provider is Groq
And   the selected model does not support stream_options
When  a turn is submitted
Then  Groq returns HTTP 400
And   the backend detects stream_options in the payload
And   retries immediately with stream_options removed (does not sleep, does not consume a retry slot)
And   the turn completes normally
And   the api_log entry has usage: null for that turn
And   no rate_limits SSE event is emitted for that turn

Given the same model receives a 400 for a different reason (stream_options absent)
Then  the backend raises immediately without retrying
```

---

## Out of Scope

- Model quality comparison
- Adding new providers (requires new backend implementation)

---

## Notes

- See: [INDEX.md §3 — LLM Providers](INDEX.md)
- Default model: `llama-3.3-70b-versatile` (Groq), `qwen3:4b` (Ollama)
- History trimmed to 10 messages for Groq, 30 for Ollama
- Per-day limits only appear in the 429 error body — per-minute limits surface via headers on every successful response
- Models confirmed to support `stream_options`: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`
- Models confirmed NOT to support `stream_options`: `llama3-8b-8192`, `mixtral-8x7b-32768`
