# bootstrap_ollama.py
#!/usr/bin/env python3
"""
Bootstrap script for RotRL with Ollama (CHAT + SYSTEM PROMPT BINDING TEST).

This tests what you actually need for the GM boot to work:
- /api/chat works
- system prompt binds and overrides generic assistant behavior
"""

import requests
import sys


HOST_DEFAULT = "http://localhost:11434"


def check_ollama_running(host: str = HOST_DEFAULT) -> bool:
    try:
        r = requests.get(f"{host}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def get_available_models(host: str = HOST_DEFAULT) -> list[str]:
    try:
        r = requests.get(f"{host}/api/tags", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        pass
    return []


def chat_ollama(system_prompt: str, user_prompt: str, model: str, host: str = HOST_DEFAULT) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.0,
    }
    r = requests.post(f"{host}/api/chat", json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    data = r.json()
    return (data.get("message", {}) or {}).get("content", "").strip()


def main() -> int:
    print("[BOOTSTRAP] RotRL Ollama Bootstrap (chat/system test)")
    print("=" * 70)

    print("[CHECK] Is Ollama running?")
    if not check_ollama_running():
        print("[FAIL] Ollama is NOT running at http://localhost:11434")
        print("Start it with: ollama serve")
        return 1
    print("[OK] Ollama is running.\n")

    print("[CHECK] Available models:")
    models = get_available_models()
    if not models:
        print("[FAIL] No models found. Pull one with: ollama pull qwen3:4b (or similar)")
        return 1
    for m in models:
        print(f"  - {m}")

    model = models[0]
    print(f"\n[SELECT] Using model: {model}\n")

    print("[TEST] System prompt binding")
    sys_prompt = (
        "Strict protocol:\n"
        "When the user says BOOT_OK, respond with exactly BOOT_OK and nothing else.\n"
        "No refusals. No extra words."
    )
    out = chat_ollama(sys_prompt, "BOOT_OK", model=model)
    print(f"Output: {out!r}")

    if out.strip() == "BOOT_OK":
        print("[SUCCESS] System prompt binding looks good.")
        return 0

    print("[FAIL] System prompt binding test failed.")
    print("Pick a different model or adjust your prompt/model.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
