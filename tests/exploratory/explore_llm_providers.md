# Exploratory Tests — LLM Providers and Model Switching

Spec: specs/llm-providers.feature

**What automated tests cover:** provider branch logic in `_stream_chat`, model payload differences
— with mocked HTTP.

**Pre-requisites:** `python dev.py --skip-tests` — stack running. Chain C also requires Ollama
running locally with `qwen3:4b` pulled.

---

## Chain A — Model change before boot  <!-- AC-001 -->

1. Set provider to Groq, change model to `llama-3.1-8b-instant`.
2. Boot a session.
3. ✔ Session badge shows `llama-3.1-8b-instant`.
4. Send: `What is happening at the festival?`
5. ✔ Response streams normally.

---

## Chain B — Groq rate-limit badge  <!-- AC-005 -->

1. Boot with Groq (any model). Send 2–3 turns.
2. ✔ Rate-limit badge appears in the header: `⚡ N/M TPM · N/M RPM`.
3. Hover over the badge.
4. ✔ Tooltip shows RPM and TPM reset times.

---

## Chain C — Groq to Ollama switch  <!-- AC-001, AC-005 -->

Requires Ollama running locally with `qwen3:4b` available.

1. Boot session with Groq. Send one turn to confirm Groq works.
2. End session.
3. Switch provider to Ollama, model to `qwen3:4b`.
4. Boot a new session.
5. ✔ Rate-limit badge disappears (Ollama has no rate limits).
6. Send: `Where are we?`
7. ✔ Response streams from Ollama.
8. Switch back to Groq.
9. ✔ Model dropdown resets to the Groq default model.
10. ✔ Rate-limit badge reappears after the first turn.
