#!/usr/bin/env python3
"""Save the current code_coverage.json as the baseline for delta tracking.

Run this BEFORE running `pytest --cov` to capture a "before" snapshot.
After the next coverage run the Code Lines tab will show per-file deltas.

Usage:
  python scripts/snapshot_coverage.py
"""
import shutil
from pathlib import Path

_OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"
_SRC = _OUTPUTS / "code_coverage.json"
_DST = _OUTPUTS / "code_coverage_prev.json"

if not _SRC.exists():
    print("No code_coverage.json found — run `pytest --cov --cov-report=json` first.")
else:
    shutil.copy2(_SRC, _DST)
    print(f"Snapshot saved → {_DST}")
    print("Now run `pytest --cov --cov-report=json` to generate fresh coverage.")
    print("Reload the Coverage modal to see deltas.")
