#!/usr/bin/env python3
"""
Quick launcher for RotRL GM Agent.

Usage:
    python gm_launcher.py                    # Boot session 1
    python gm_launcher.py --session 3        # Boot session 3
    python gm_launcher.py --model qwen2      # Use specific Ollama model
    python gm_launcher.py --help             # Show options
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.gm_agent import GMAgent, GMConfig


def check_ollama_running(host: str) -> bool:
    """Verify Ollama is running."""
    try:
        import requests
        response = requests.get(f"{host}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Launch RotRL GM Agent for interactive play"
    )
    parser.add_argument(
        "--session",
        type=int,
        default=1,
        help="Session number to boot (default: 1)"
    )
    parser.add_argument(
        "--model",
        default="qwen3:4b",
        help="Ollama model to use (default: qwen3:4b)"
    )
    parser.add_argument(
        "--host",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--temp",
        type=float,
        default=0.3,
        help="LLM temperature (default: 0.3, lower=more consistent)"
    )
    
    args = parser.parse_args()
    
    # Check Ollama is running
    print("[LAUNCHER] Checking Ollama connection...")
    if not check_ollama_running(args.host):
        print(f"[ERROR] Cannot reach Ollama at {args.host}")
        print("Start Ollama with: ollama serve")
        return 1
    
    print("[LAUNCHER] ✓ Ollama is running")
    
    # Create GM config
    config = GMConfig(
        ollama_host=args.host,
        ollama_model=args.model,
        temperature=args.temp
    )
    
    print(f"[LAUNCHER] GM Configuration:")
    print(f"  - Session: {args.session}")
    print(f"  - Model: {args.model}")
    print(f"  - Host: {args.host}")
    print(f"  - Temperature: {args.temp}")
    
    # Create and boot GM
    try:
        print("\n[LAUNCHER] Initializing GM Agent...\n")
        gm = GMAgent(config)
        gm.boot_session(session_number=args.session)
        
        # Run session loop
        print("\n[LAUNCHER] Entering game loop...")
        gm.session_loop()
        
        print("\n[LAUNCHER] Session ended.")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n[LAUNCHER] Interrupted by user.")
        return 0
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
