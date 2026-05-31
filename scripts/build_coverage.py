#!/usr/bin/env python3
"""Build the feature AC coverage matrix.

Reads:
  specs/*.feature              → all AC IDs and titles
  tests/test_*.py              → pytest coverage
  ui/src/**/*.test.{ts,tsx}   → Vitest coverage
  ui/e2e/*.spec.ts             → Playwright coverage

Writes:
  outputs/coverage.json

Run with:
  python scripts/build_coverage.py

AC reference detection (in order):
  - Range:    "AC-NNN through AC-NNN"  → expands to every AC in range
  - Explicit: "AC-NNN" anywhere in text (comments, docstrings, describe names)

Feature attribution — how a test file is linked to a spec feature:
  - "Spec: specs/<id>.feature"        → all ACs in file belong to this feature
  - "Covers <id>.feature AC-…"        → same
  - Without a feature hint, an AC-NNN is matched only when exactly one spec
    file defines that ID (unambiguous). Most features share AC-001/AC-002/…
    so many backend tests without headers will show as gaps until annotated.

This script is read-only and never modifies any source file.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SPECS_DIR        = REPO_ROOT / "specs"
TESTS_DIR        = REPO_ROOT / "tests"
UI_TESTS_DIR     = REPO_ROOT / "ui" / "src"
E2E_DIR          = REPO_ROOT / "ui" / "e2e"
EXPLORATORY_DIR  = REPO_ROOT / "tests" / "exploratory"
OUTPUT_PATH      = REPO_ROOT / "outputs" / "coverage.json"

# ── Spec file parsing ─────────────────────────────────────────────────────────

_AC_HEADING_RE  = re.compile(r"^### (AC-\d{3}) — (.+)$", re.MULTILINE)
_FEATURE_ID_RE  = re.compile(r"^\*\*ID:\*\*\s+(\S+)", re.MULTILINE)


@dataclass
class AcEntry:
    feature_id:   str
    feature_file: str        # "specs/foo.feature"
    ac_id:        str
    title:        str
    pytest:       list[str] = field(default_factory=list)
    vitest:       list[str] = field(default_factory=list)
    playwright:   list[str] = field(default_factory=list)
    exploratory:  list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "covered" if (self.pytest or self.vitest or self.playwright or self.exploratory) else "gap"


def load_spec_acs() -> dict[tuple[str, str], AcEntry]:
    """Return {(feature_id, ac_id): AcEntry} for all *.feature files."""
    entries: dict[tuple[str, str], AcEntry] = {}
    for path in sorted(SPECS_DIR.glob("*.feature")):
        text = path.read_text(encoding="utf-8")
        m = _FEATURE_ID_RE.search(text)
        feature_id   = m.group(1) if m else path.stem
        feature_file = f"specs/{path.name}"
        for ac_m in _AC_HEADING_RE.finditer(text):
            ac_id = ac_m.group(1)
            title = ac_m.group(2).strip()
            entries[(feature_id, ac_id)] = AcEntry(
                feature_id=feature_id,
                feature_file=feature_file,
                ac_id=ac_id,
                title=title,
            )
    return entries


# ── AC reference extraction from test file text ───────────────────────────────

_AC_RANGE_RE  = re.compile(r"AC-(\d{3})\s+through\s+AC-(\d{3})")
_AC_BARE_RE   = re.compile(r"\bAC-(\d{3})\b")
_SPEC_HDR_RE  = re.compile(r"Spec:\s+specs/([\w\-]+)\.feature")
_COVERS_RE    = re.compile(r"[Cc]overs?\s+([\w\-]+)\.feature")


def _extract_acs(text: str) -> list[str]:
    """Return all AC IDs mentioned in *text*, with ranges expanded."""
    ids: list[str] = []
    range_spans: list[tuple[int, int]] = []

    for m in _AC_RANGE_RE.finditer(text):
        lo, hi = int(m.group(1)), int(m.group(2))
        ids.extend(f"AC-{n:03d}" for n in range(lo, hi + 1))
        range_spans.append((m.start(), m.end()))

    for m in _AC_BARE_RE.finditer(text):
        if not any(lo <= m.start() < hi for lo, hi in range_spans):
            ids.append(f"AC-{int(m.group(1)):03d}")

    return list(dict.fromkeys(ids))  # deduplicate, preserve order


def _feature_hint(text: str) -> str | None:
    m = _SPEC_HDR_RE.search(text) or _COVERS_RE.search(text)
    return m.group(1) if m else None


# Matches inline per-test annotations, e.g.:
#   // Covers: attack-resolution.feature AC-001, AC-002, AC-003
_INLINE_COVERS_RE = re.compile(
    r"[Cc]overs:\s+([\w\-]+)\.feature\s+((?:AC-\d{3}[,\s]*)+)",
    re.MULTILINE,
)


def _attach_inline_covers(
    text: str,
    name: str,
    all_acs: dict[tuple[str, str], AcEntry],
    suite: str,
) -> set[tuple[str, str]]:
    """Process per-line 'Covers: feature.feature AC-NNN, ...' annotations.

    Returns a set of (feature_id, ac_id) pairs that were explicitly attributed
    via inline annotations, so the caller can skip them in the fallback loop.
    """
    handled: set[tuple[str, str]] = set()
    for m in _INLINE_COVERS_RE.finditer(text):
        feature_id = m.group(1)
        ac_ids = re.findall(r"AC-\d{3}", m.group(0))
        for ac_id in ac_ids:
            entry = all_acs.get((feature_id, ac_id))
            if entry is not None:
                target: list[str] = getattr(entry, suite)
                if name not in target:
                    target.append(name)
            handled.add((feature_id, ac_id))
    return handled


def _attach_coverage(
    test_files: list[Path],
    suite: str,
    all_acs: dict[tuple[str, str], AcEntry],
) -> None:
    """Find AC references in each test file and attach to matching AcEntry objects."""
    for path in test_files:
        text  = path.read_text(encoding="utf-8", errors="replace")
        name  = path.name
        hint  = _feature_hint(text)

        # Process inline per-test annotations first (highest priority).
        inline_handled = _attach_inline_covers(text, name, all_acs, suite)

        found = _extract_acs(text)

        for ac_id in found:
            entry: AcEntry | None = None

            if hint:
                key = (hint, ac_id)
                # Skip if already attributed via an inline Covers: annotation
                if key in inline_handled:
                    continue
                entry = all_acs.get(key)

            if entry is None:
                # Fallback: match if exactly one spec file defines this AC ID.
                # (Most features share AC-001 etc., so this usually stays None
                #  until the test file gets a Spec: header.)
                candidates = [e for (fid, aid), e in all_acs.items() if aid == ac_id]
                if len(candidates) == 1:
                    # Skip if already attributed via inline annotation
                    if (candidates[0].feature_id, ac_id) in inline_handled:
                        continue
                    entry = candidates[0]

            if entry is not None:
                target: list[str] = getattr(entry, suite)
                if name not in target:
                    target.append(name)


# ── Main ──────────────────────────────────────────────────────────────────────

def build_coverage() -> dict:
    all_acs = load_spec_acs()

    _attach_coverage(sorted(TESTS_DIR.glob("test_*.py")), "pytest", all_acs)
    _attach_coverage(
        sorted(UI_TESTS_DIR.rglob("*.test.tsx")) + sorted(UI_TESTS_DIR.rglob("*.test.ts")),
        "vitest",
        all_acs,
    )
    _attach_coverage(sorted(E2E_DIR.glob("*.spec.ts")), "playwright", all_acs)
    _attach_coverage(sorted(EXPLORATORY_DIR.glob("*.md")), "exploratory", all_acs)

    rows = [
        {
            "feature_id":   e.feature_id,
            "feature_file": e.feature_file,
            "ac_id":        e.ac_id,
            "title":        e.title,
            "pytest":       e.pytest,
            "vitest":       e.vitest,
            "playwright":   e.playwright,
            "exploratory":  e.exploratory,
            "status":       e.status,
        }
        for e in all_acs.values()
    ]

    total   = len(rows)
    covered = sum(1 for r in rows if r["status"] == "covered")

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary":   {"total": total, "covered": covered, "gap": total - covered},
        "rows":      rows,
    }


def main() -> None:
    data = build_coverage()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    s = data["summary"]
    print(f"Coverage matrix written → {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  {s['covered']}/{s['total']} ACs covered  ({s['gap']} gaps)")


if __name__ == "__main__":
    main()
