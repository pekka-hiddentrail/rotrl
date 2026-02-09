#!/usr/bin/env python3
"""
Hello World test for Ollama LLM integration.

This script tests that we can:
1. Connect to Ollama
2. Send a prompt
3. Receive and parse a response
4. Validate the response matches expected format
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:4b"  # Using detected model
PROMPT_FILE = Path(__file__).parent.parent.parent / ".agents" / "hello" / "PROMPT.md"


def read_prompt() -> str:
    """Read the hello world prompt from file."""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt file not found: {PROMPT_FILE}")
    
    with open(PROMPT_FILE, "r") as f:
        content = f.read()
    
    # Extract just the instruction part (after the headers)
    lines = content.split("\n")
    instruction_start = None
    for i, line in enumerate(lines):
        if "Input" in line:
            instruction_start = i + 1
            break
    
    if instruction_start:
        instruction = "\n".join(lines[instruction_start:]).strip()
        return instruction
    
    return content


def call_ollama(prompt: str) -> str:
    """Call Ollama API with prompt and return response."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.0,  # Deterministic for testing
            },
            timeout=120  # Longer timeout for LLM inference
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_HOST}. "
            f"Make sure Ollama is running: ollama serve"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama API error: {e}")


def validate_response(response: str) -> bool:
    """
    Validate that response is exactly 'hello world'.
    
    Args:
        response: The response text from Ollama
        
    Returns:
        True if response matches exactly, False otherwise
    """
    expected = "hello world"
    cleaned = response.lower().strip()
    
    # Exact match
    if cleaned == expected:
        return True
    
    # Check if it's embedded in extra text (less strict but still useful for debugging)
    if expected in cleaned:
        print(f"[WARN] Response contains 'hello world' but with extra text: {response}")
        return False
    
    return False


def main():
    """Run the hello world test."""
    print("[TEST] RotRL Hello World Test")
    print("=" * 50)
    
    try:
        # Load prompt
        print(f"[LOAD] Loading prompt from: {PROMPT_FILE}")
        prompt = read_prompt()
        print(f"[OK] Prompt loaded ({len(prompt)} characters)")
        print()
        
        # Call Ollama
        print(f"[LLM] Calling Ollama ({OLLAMA_MODEL}) at {OLLAMA_HOST}...")
        response = call_ollama(prompt)
        print(f"[OK] Response received: '{response}'")
        print()
        
        # Validate
        print("[CHECK] Validating response...")
        is_valid = validate_response(response)
        
        if is_valid:
            print("[OK] PASS: Response is exactly 'hello world'")
            print()
            print("=" * 50)
            print("[SUCCESS] Hello World test PASSED!")
            return 0
        else:
            print(f"[FAIL] Response does not match expected output")
            print(f"   Expected: 'hello world'")
            print(f"   Got:      '{response}'")
            print()
            print("=" * 50)
            print("[FAILED] Hello World test FAILED!")
            return 1
            
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}")
        return 1
    except ConnectionError as e:
        print(f"[ERROR] Connection Error: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
