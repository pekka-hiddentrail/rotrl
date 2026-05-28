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
### AC-002 — Groq rate limit is retried automatically
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Groq API returns HTTP 429 (rate limited)

```gherkin
Given the provider is Groq
And   the Groq API returns a 429 response with a retry-after header
When  a turn is submitted
Then  the backend waits the specified retry-after duration (max 60 seconds)
And   retries the request up to 4 times
And   on success the turn streams normally
And   on exhausted retries an error event is emitted
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

## Out of Scope

- Model quality comparison
- Adding new providers (requires new backend implementation)

---

## Notes

- See: [INDEX.md §3 — LLM Providers](INDEX.md)
- Default model: `llama-3.3-70b-versatile` (Groq), `qwen3:4b` (Ollama)
- History trimmed to 10 messages for Groq, 30 for Ollama
