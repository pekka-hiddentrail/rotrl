#!/usr/bin/env python3
"""
dev.py — one-command local development startup for RotRL.

Usage:
    python dev.py               # run tests, then start API + UI
    python dev.py --skip-tests  # skip tests, start immediately

What it does:
  1. Runs pytest (--tb=short) — aborts if any test fails
  2. Starts the FastAPI backend on port 8000  (uvicorn, --reload)
  3. Starts the Vite UI dev server on port 5173
  4. Streams both outputs to the terminal with colour-coded prefixes
  5. Ctrl-C shuts both down cleanly
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent

# ANSI colour helpers
_R  = "\033[0m"
_BOLD  = "\033[1m"
_RED   = "\033[31m"
_GREEN = "\033[32m"
_CYAN  = "\033[36m"
_DIM   = "\033[2m"


def _stream(proc: subprocess.Popen, label: str, color: str) -> None:
    """Forward every output line from *proc* to stdout with a coloured label."""
    for line in proc.stdout:
        sys.stdout.write(f"{color}[{label}]{_R} {line}")
        sys.stdout.flush()


def run_tests() -> bool:
    print(f"{_BOLD}▶  Running tests…{_R}", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=short"],
        cwd=REPO,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="RotRL dev startup")
    parser.add_argument(
        "--skip-tests", action="store_true",
        help="Skip pytest and start API + UI immediately",
    )
    args = parser.parse_args()

    if not args.skip_tests:
        ok = run_tests()
        if not ok:
            print(
                f"\n{_RED}✗  Tests failed. "
                f"Fix them or run:  python dev.py --skip-tests{_R}",
                flush=True,
            )
            sys.exit(1)
        print(f"\n{_GREEN}✓  All tests passed.{_R}\n", flush=True)

    # ── Launch processes ──────────────────────────────────────────────────────
    # On Windows, executables like `npm` resolve to `npm.cmd`, so shell=True
    # is required for the UI command.  The Python/uvicorn command doesn't need it.
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    ui_proc = subprocess.Popen(
        "npm run dev",
        cwd=REPO / "ui",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True,
    )

    threading.Thread(target=_stream, args=(api_proc, "API", _GREEN), daemon=True).start()
    threading.Thread(target=_stream, args=(ui_proc,  "UI",  _CYAN),  daemon=True).start()

    print(
        f"{_BOLD}▶  API on http://127.0.0.1:8000  |  UI on http://localhost:5173{_R}\n"
        f"{_DIM}   Press Ctrl-C to stop both.{_R}\n",
        flush=True,
    )

    try:
        while True:
            if api_proc.poll() is not None:
                print(f"\n{_RED}[API] process exited unexpectedly.{_R}")
                break
            if ui_proc.poll() is not None:
                print(f"\n{_RED}[UI]  process exited unexpectedly.{_R}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n{_BOLD}Shutting down…{_R}")
    finally:
        for proc in (api_proc, ui_proc):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        print(f"{_GREEN}Done.{_R}")


if __name__ == "__main__":
    main()
