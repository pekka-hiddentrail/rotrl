"""Prompt token trend tracker.

Reads all api_log JSON files, appends new entries to outputs/prompt_trend.csv,
and prints a summary so you can spot growth over time.

Usage:
    python prompt_trend.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_LOG_DIR   = _REPO_ROOT / "outputs" / "api_log"
_TREND_CSV = _REPO_ROOT / "outputs" / "prompt_trend.csv"

_FIELDS = [
    "timestamp", "provider", "model",
    "session", "turn",
    "prompt_tokens", "completion_tokens", "total_tokens",
    "system_chars",
]

# Warn if prompt_tokens exceeds this on a single turn.
_WARN_TOKENS = 2_500


def _system_chars(raw_request: dict) -> int:
    """Return the char length of the system message in the raw request."""
    if "system" in raw_request:          # Anthropic format
        return len(raw_request["system"])
    msgs = raw_request.get("messages", [])
    if msgs and msgs[0].get("role") == "system":
        return len(msgs[0].get("content", ""))
    return 0


def _load_existing_timestamps() -> set[str]:
    if not _TREND_CSV.exists():
        return set()
    with _TREND_CSV.open(encoding="utf-8") as f:
        return {row["timestamp"] for row in csv.DictReader(f)}


def _collect_new_entries(existing: set[str]) -> list[dict]:
    entries = []
    for path in sorted(_LOG_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        ts = data.get("timestamp", "")
        if not ts or ts in existing:
            continue
        if data.get("status") != "ok":
            continue

        usage = data.get("usage", {})
        prompt  = usage.get("prompt_tokens",     0)
        compl   = usage.get("completion_tokens", 0)
        total   = usage.get("total_tokens",      prompt + compl)
        raw_req = data.get("raw_request", {})

        entries.append({
            "timestamp":         ts,
            "provider":          data.get("provider", ""),
            "model":             data.get("raw_request", {}).get("model", ""),
            "session":           data.get("session_number", ""),
            "turn":              data.get("turn", ""),
            "prompt_tokens":     prompt,
            "completion_tokens": compl,
            "total_tokens":      total,
            "system_chars":      _system_chars(raw_req),
        })
    return entries


def _ensure_csv() -> None:
    """Create the CSV with headers if it doesn't exist yet."""
    if not _TREND_CSV.exists():
        _TREND_CSV.parent.mkdir(parents=True, exist_ok=True)
        with _TREND_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_FIELDS).writeheader()
        print(f"Created {_TREND_CSV}")


def _append(entries: list[dict]) -> None:
    with _TREND_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_FIELDS).writerows(entries)


def _read_all() -> list[dict]:
    if not _TREND_CSV.exists():
        return []
    with _TREND_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _print_summary(all_rows: list[dict], new_count: int) -> None:
    if not all_rows:
        print("No data yet.")
        return

    recent = all_rows[-20:]
    col_w  = [12, 10, 26, 7, 4, 13, 11, 12, 12]
    header = ["timestamp", "provider", "model", "session", "turn",
              "prompt_tok", "compl_tok", "total_tok", "sys_chars"]

    sep = "  ".join("-" * w for w in col_w)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_w)

    print()
    print(fmt.format(*header))
    print(sep)

    warnings = []
    for row in recent:
        pt = int(row["prompt_tokens"] or 0)
        flag = " ⚠" if pt > _WARN_TOKENS else ""
        print(fmt.format(
            row["timestamp"][:19],
            row["provider"][:10],
            row["model"][:26],
            row["session"],
            row["turn"],
            str(pt) + flag,
            row["completion_tokens"],
            row["total_tokens"],
            row["system_chars"],
        ))
        if pt > _WARN_TOKENS:
            warnings.append(f"  turn {row['turn']} ({row['provider']}/{row['model']}): {pt} prompt tokens")

    print()
    print(f"Total entries: {len(all_rows)}  |  New this run: {new_count}  |  Showing last {len(recent)}")
    print(f"Trend CSV: {_TREND_CSV}")

    if warnings:
        print(f"\n⚠  Turns over {_WARN_TOKENS} prompt tokens:")
        for w in warnings:
            print(w)


def main() -> int:
    if not _LOG_DIR.exists():
        print(f"No api_log directory found at {_LOG_DIR}")
        return 1

    _ensure_csv()
    existing    = _load_existing_timestamps()
    new_entries = _collect_new_entries(existing)

    if new_entries:
        _append(new_entries)

    all_rows = _read_all()
    _print_summary(all_rows, len(new_entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
