#!/usr/bin/env python3
"""
Bootstrap script for RotRL with Ollama.

This script:
1. Checks if Ollama is running
2. Provides instructions to start it if not
3. Runs a test query to verify setup
4. Prints the LLM response
"""

import requests
import subprocess
import sys
import time
from pathlib import Path


def check_ollama_running(host="http://localhost:11434") -> bool:
    """Check if Ollama is running and accessible."""
    try:
        response = requests.get(f"{host}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def get_available_models(host="http://localhost:11434") -> list:
    """Get list of available models from Ollama."""
    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m.get("name") for m in data.get("models", [])]
    except:
        pass
    return []


def query_ollama(prompt: str, model: str, host="http://localhost:11434") -> str:
    """Send a query to Ollama and get the response."""
    try:
        response = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.0,
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        raise RuntimeError(f"Query failed: {e}")


def main():
    """Run the bootstrap."""
    print("[BOOTSTRAP] RotRL Ollama Bootstrap")
    print("=" * 60)
    print()
    
    # Check if Ollama is running
    print("[CHECK] Is Ollama running?")
    if not check_ollama_running():
        print("[WARN] Ollama is NOT running at http://localhost:11434")
        print()
        print("To start Ollama, run in a new terminal:")
        print("  ollama serve")
        print()
        print("Then come back and run this script again.")
        return 1
    
    print("[OK] Ollama is running!")
    print()
    
    # Get available models
    print("[CHECK] Available models:")
    models = get_available_models()
    if not models:
        print("[ERROR] No models found!")
        print("Pull a model first:")
        print("  ollama pull qwen2")
        print("  ollama pull llama2")
        return 1
    
    for model in models:
        print(f"  - {model}")
    
    # Use first available model
    model = models[0]
    print()
    print(f"[SELECT] Using model: {model}")
    print()
    
    # Run test query
    print("[QUERY] Sending test query...")
    prompt = "Say only the words: hello world"
    
    try:
        print(f"  Prompt: '{prompt}'")
        print(f"  Model: {model}")
        print()
        print("[WAITING] Calling Ollama (this may take a moment)...")
        
        response = query_ollama(prompt, model)
        
        print("[OK] Response received!")
        print()
        print("=" * 60)
        print(f"RESPONSE:\n{response}")
        print("=" * 60)
        print()
        
        # Check if response is what we expected
        if response.lower().strip() == "hello world":
            print("[SUCCESS] Got expected response!")
            return 0
        else:
            print("[INFO] Got response (may differ from strict test)")
            return 0
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
