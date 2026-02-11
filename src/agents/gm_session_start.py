#!/usr/bin/env python3
"""
Session start loader for RotRL.

Loads:
- Player character files
- World setting files
- Campaign setting files
- Previous session notes
- Active adventure state files (book + act)
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AdventureState:
    session_number: int
    book: int
    act: int
    book_dir: Optional[Path]
    act_dir: Optional[Path]


class SessionStartLoader:
    def __init__(self, repo_root: Optional[Path] = None):
        # src/agents/gm_session_start.py -> parents[2] == repo root
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.players_root = self.repo_root / "players"
        self.adventure_root = self.repo_root / "adventure_path"
        self.outputs_root = self.repo_root / "outputs"

    def _read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def _read_json(self, path: Path) -> Dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_markdown_files(self, root: Path, recursive: bool = True) -> Dict[str, str]:
        if not root.exists():
            return {}
        pattern = "**/*.md" if recursive else "*.md"
        files = sorted(p for p in root.glob(pattern) if p.is_file())
        return {str(p.relative_to(self.repo_root)): self._read_text(p) for p in files}

    def load_player_context(self) -> Dict[str, str]:
        context: Dict[str, str] = {}

        top_level_players = ("PLAYER_CHARACTERS.md", "PLAYER_LIMITS_AND_EXPECTATIONS.md")
        for name in top_level_players:
            path = self.players_root / name
            if path.exists():
                context[str(path.relative_to(self.repo_root))] = self._read_text(path)

        if self.players_root.exists():
            for player_dir in sorted(p for p in self.players_root.iterdir() if p.is_dir()):
                for filename in ("character_sheet.md", "player_knowledge.md"):
                    file_path = player_dir / filename
                    if file_path.exists():
                        context[str(file_path.relative_to(self.repo_root))] = self._read_text(file_path)

        return context

    def load_world_settings(self) -> Dict[str, str]:
        return self._load_markdown_files(self.adventure_root / "01_world_setting", recursive=True)

    def load_campaign_settings(self) -> Dict[str, str]:
        return self._load_markdown_files(self.adventure_root / "02_campaign_setting", recursive=True)

    def _latest_output_notes_file(self) -> Optional[Path]:
        if not self.outputs_root.exists():
            return None
        candidates = sorted(self.outputs_root.glob("session_*_notes.json"))
        return candidates[-1] if candidates else None

    def _infer_from_text_notes(self, text: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        session_match = re.search(r"session(?:\s+number)?\s*[:=]\s*(\d+)", text, flags=re.IGNORECASE)
        book_match = re.search(r"book\s*[:=]\s*(\d+)", text, flags=re.IGNORECASE)
        act_match = re.search(r"act\s*[:=]\s*(\d+)", text, flags=re.IGNORECASE)
        session_number = int(session_match.group(1)) if session_match else None
        book = int(book_match.group(1)) if book_match else None
        act = int(act_match.group(1)) if act_match else None
        return session_number, book, act

    def load_previous_session_notes(self) -> Dict[str, object]:
        result: Dict[str, object] = {
            "source": None,
            "content": None,
            "session_number": None,
            "book": None,
            "act": None,
        }

        preferred = self.adventure_root / "SESSION_NOTES_LAST.md"
        if preferred.exists():
            text = self._read_text(preferred)
            session_number, book, act = self._infer_from_text_notes(text)
            result.update(
                {
                    "source": str(preferred.relative_to(self.repo_root)),
                    "content": text,
                    "session_number": session_number,
                    "book": book,
                    "act": act,
                }
            )
            return result

        latest_json = self._latest_output_notes_file()
        if latest_json and latest_json.exists():
            payload = self._read_json(latest_json)
            result.update(
                {
                    "source": str(latest_json.relative_to(self.repo_root)),
                    "content": payload,
                    "session_number": payload.get("session_number"),
                    "book": payload.get("book"),
                    "act": payload.get("act"),
                }
            )
            return result

        return result

    def _first_available_book(self) -> Optional[Tuple[int, Path]]:
        books_root = self.adventure_root / "03_books"
        if not books_root.exists():
            return None

        candidates: List[Tuple[int, Path]] = []
        for p in books_root.iterdir():
            if not p.is_dir():
                continue
            m = re.match(r"BOOK_(\d+)_", p.name)
            if m:
                candidates.append((int(m.group(1)), p))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0]

    def _resolve_book_dir(self, book_number: int) -> Optional[Path]:
        books_root = self.adventure_root / "03_books"
        if not books_root.exists():
            return None
        matches = sorted(books_root.glob(f"BOOK_{book_number:02d}_*"))
        return matches[0] if matches else None

    def _resolve_act_dir(self, book_dir: Path, act_number: int) -> Optional[Path]:
        matches = sorted(book_dir.glob(f"act_{act_number:02d}"))
        return matches[0] if matches else None

    def resolve_adventure_state(self, requested_session: Optional[int] = None) -> AdventureState:
        notes = self.load_previous_session_notes()
        previous_session = notes.get("session_number")
        previous_book = notes.get("book")
        previous_act = notes.get("act")

        session_number = requested_session or (int(previous_session) + 1 if isinstance(previous_session, int) else 1)

        if isinstance(previous_book, int):
            book = previous_book
        else:
            first = self._first_available_book()
            book = first[0] if first else 1

        act = int(previous_act) if isinstance(previous_act, int) else 1

        book_dir = self._resolve_book_dir(book)
        if book_dir is None:
            first = self._first_available_book()
            if first:
                book = first[0]
                book_dir = first[1]

        act_dir = self._resolve_act_dir(book_dir, act) if book_dir else None
        if book_dir and act_dir is None:
            fallback = sorted(p for p in book_dir.glob("act_*") if p.is_dir())
            if fallback:
                act_dir = fallback[0]
                m = re.match(r"act_(\d+)", act_dir.name)
                if m:
                    act = int(m.group(1))

        return AdventureState(
            session_number=session_number,
            book=book,
            act=act,
            book_dir=book_dir,
            act_dir=act_dir,
        )

    def load_adventure_state_files(self, state: AdventureState) -> Dict[str, str]:
        files: Dict[str, str] = {}
        if not state.book_dir:
            return files

        # Load top-level book files.
        for p in sorted(state.book_dir.glob("*.md")):
            if p.is_file():
                files[str(p.relative_to(self.repo_root))] = self._read_text(p)

        # Load current act subtree, including encounters.
        if state.act_dir and state.act_dir.exists():
            for p in sorted(state.act_dir.glob("**/*.md")):
                if p.is_file():
                    files[str(p.relative_to(self.repo_root))] = self._read_text(p)

        return files

    def load_all(self, requested_session: Optional[int] = None) -> Dict[str, object]:
        previous_notes = self.load_previous_session_notes()
        state = self.resolve_adventure_state(requested_session=requested_session)

        bundle = {
            "resolved_state": {
                "session_number": state.session_number,
                "book": state.book,
                "act": state.act,
                "book_dir": str(state.book_dir.relative_to(self.repo_root)) if state.book_dir else None,
                "act_dir": str(state.act_dir.relative_to(self.repo_root)) if state.act_dir else None,
            },
            "players": self.load_player_context(),
            "world_settings": self.load_world_settings(),
            "campaign_settings": self.load_campaign_settings(),
            "previous_session_notes": previous_notes,
            "adventure_state_files": self.load_adventure_state_files(state),
        }
        return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Load RotRL session-start context and resolve adventure state.")
    parser.add_argument("--session", type=int, default=None, help="Override session number.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON file path for the loaded context bundle.",
    )
    args = parser.parse_args()

    loader = SessionStartLoader()
    bundle = loader.load_all(requested_session=args.session)

    summary = bundle["resolved_state"]
    print("SESSION START CONTEXT")
    print("=" * 80)
    print(f"session_number: {summary['session_number']}")
    print(f"book:           {summary['book']}")
    print(f"act:            {summary['act']}")
    print(f"book_dir:       {summary['book_dir']}")
    print(f"act_dir:        {summary['act_dir']}")
    print("-" * 80)
    print(f"players loaded:          {len(bundle['players'])}")
    print(f"world settings loaded:   {len(bundle['world_settings'])}")
    print(f"campaign settings loaded:{len(bundle['campaign_settings'])}")
    print(f"adventure files loaded:  {len(bundle['adventure_state_files'])}")
    print(f"notes source:            {bundle['previous_session_notes']['source']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"written: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
