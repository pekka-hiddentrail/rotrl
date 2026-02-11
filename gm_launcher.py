# gm_launcher.py
#!/usr/bin/env python3
"""
Quick launcher for RotRL GM Agent (BOOT TEST).

Usage:
    python gm_launcher.py                        # Boot session 1 and print output
    python gm_launcher.py --session 3            # Boot session 3
    python gm_launcher.py --model qwen3:4b        # Use specific Ollama model
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.gm_boot_agent import GMAgent, GMConfig


def check_ollama_running(host: str) -> bool:
    try:
        import requests
        r = requests.get(f"{host}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch RotRL GM Agent (boot only)")
    parser.add_argument("--session", type=int, default=1, help="Session number to boot (default: 1)")
    parser.add_argument("--model", default="qwen3:4b", help="Ollama model to use (default: qwen3:4b)")
    parser.add_argument("--host", default="http://localhost:11434", help="Ollama server URL")
    parser.add_argument("--temp", type=float, default=0.3, help="LLM temperature (default: 0.3)")
    args = parser.parse_args()

    print("[LAUNCHER] Checking Ollama connection...")
    if not check_ollama_running(args.host):
        print(f"[ERROR] Cannot reach Ollama at {args.host}")
        print("Start Ollama with: ollama serve")
        return 1
    print("[LAUNCHER] ✓ Ollama is running\n")

    config = GMConfig(
        ollama_host=args.host,
        ollama_model=args.model,
        temperature=args.temp
    )

    # Fail fast if boot prompt is missing
    if not config.boot_prompt_path.exists():
        print(f"[ERROR] Missing canonical boot prompt: {config.boot_prompt_path}")
        print("Create it at .agents/GM/SESSION_BOOT_PROMPT.md")
        return 1

    print("[LAUNCHER] Boot configuration:")
    print(f"  - Session: {args.session}")
    print(f"  - Model: {args.model}")
    print(f"  - Host: {args.host}")
    print(f"  - Temperature: {args.temp}\n")

    try:
        gm = GMAgent(config)
        print("[LAUNCHER] Booting GM...\n")
        gm.boot_session(session_number=args.session)
        return 0
    except KeyboardInterrupt:
        print("\n[LAUNCHER] Interrupted by user.")
        return 0
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
