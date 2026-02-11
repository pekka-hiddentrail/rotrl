# src/agents/gm_boot_agent.py
#!/usr/bin/env python3
"""
RotRL GM Agent (BOOT-FIRST, CANONICAL PROMPT FILE)

Design constraints:
- Do NOT invent the boot protocol prompt in code.
- Treat .agents/GM/SESSION_BOOT_PROMPT.md as canonical and inject loaded docs into it.
- BOOT loads only: System Authority + (optional) Player identity + (optional) Last session notes.
- Uses Ollama /api/chat so system prompt binding works reliably.

Boot compliance:
- Extract the checklist from SESSION_BOOT_PROMPT.md (# Session Boot Output section)
- Run deterministic checks in Python
- Print checklist with ✅/❌
- If any check fails, raise RuntimeError (fail-fast)
"""

import requests
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
import json  # add at top of file
from src.tools.prompt_verification import (
    VerificationResult,
    extract_checklist_items as extract_prompt_checklist_items,
    summarize_results,
    verify_prompt,
)



@dataclass
class GMConfig:
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    temperature: float = 0.3

    repo_root: Optional[Path] = None
    adventure_path_root: Optional[Path] = None
    boot_prompt_path: Optional[Path] = None

    def __post_init__(self):
        if self.repo_root is None:
            # repo_root/src/agents/gm_boot_agent.py -> parents[2] == repo_root
            self.repo_root = Path(__file__).resolve().parents[2]
        if self.adventure_path_root is None:
            self.adventure_path_root = self.repo_root / "adventure_path"
        if self.boot_prompt_path is None:
            self.boot_prompt_path = self.repo_root / ".agents" / "GM" / "SESSION_BOOT_PROMPT.md"


class FileLoader:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._cache: Dict[str, str] = {}

    def load_path(self, file_path: Path) -> str:
        key = str(file_path.resolve())
        if key in self._cache:
            return self._cache[key]

        if not file_path.exists():
            return f"[FILE NOT FOUND: {file_path}]"

        try:
            content = file_path.read_text(encoding="utf-8")
            self._cache[key] = content
            return content
        except Exception as e:
            return f"[ERROR LOADING {file_path}: {e}]"

    def load_file(self, relative_path: str) -> str:
        return self.load_path((self.root_path / relative_path).resolve())

    def load_multiple(self, relative_paths: List[str]) -> Dict[str, str]:
        return {path: self.load_file(path) for path in relative_paths}


class GMAgent:
    # BOOT-only minimal set
    BOOT_SYSTEM_AUTHORITY_FILES = [
        "00_system_authority/GM_OPERATING_RULES.md",
        "00_system_authority/ADJUDICATION_PRINCIPLES.md",
        "00_system_authority/COMBAT_AND_POSITIONING.md",
        "00_system_authority/PF1E_RULES_SCOPE.md",
        "00_system_authority/SESSION_NOTES_PROTOCOL.md",
    ]

    def __init__(self, config: GMConfig):
        self.config = config

        # Loader rooted at repo_root so we can read .agents/...
        self.repo_loader = FileLoader(config.repo_root)

        # Loader rooted at adventure_path_root so we can read authority files
        self.adv_loader = FileLoader(config.adventure_path_root)

        # Cached contexts for prompt injection
        self.system_context: str = ""
        self.player_context: str = ""
        self.continuity_context: str = ""

        # Boot instrumentation for deterministic checks
        self._boot_loaded_files: List[str] = []
        self._boot_only_system_authority_loaded: bool = False

    # ---------- context loading ----------
    def _merge_documents(self, section_name: str, files: Dict[str, str]) -> str:
        merged = f"\n{'='*80}\n{section_name}\n{'='*80}\n\n"
        for filename, content in files.items():
            merged += f"\n--- {filename} ---\n{content}\n"
        return merged

    def load_boot_contexts(self) -> None:
        """Load minimal contexts needed for boot and record what was loaded."""
        self._boot_loaded_files = []

        # Load system authority (required)
        system_files = self.adv_loader.load_multiple(self.BOOT_SYSTEM_AUTHORITY_FILES)
        self._boot_loaded_files.extend(self.BOOT_SYSTEM_AUTHORITY_FILES)
        self.system_context = self._merge_documents("SYSTEM AUTHORITY", system_files)

        # Optional: player file
        player_char_path = self.config.adventure_path_root / "PLAYER_CHARACTERS.md"
        if player_char_path.exists():
            player_content = self.adv_loader.load_path(player_char_path)
            self.player_context = self._merge_documents("PLAYER IDENTITY", {"PLAYER_CHARACTERS.md": player_content})
            self._boot_loaded_files.append("PLAYER_CHARACTERS.md")

        # Optional: limits/expectations file
        limits_path = self.config.adventure_path_root / "PLAYER_LIMITS_AND_EXPECTATIONS.md"
        if limits_path.exists():
            limits_content = self.adv_loader.load_path(limits_path)
            if self.player_context:
                # append as second file in same block
                self.player_context += self._merge_documents("PLAYER LIMITS (ALIGNMENT ONLY)", {"PLAYER_LIMITS_AND_EXPECTATIONS.md": limits_content})
            else:
                self.player_context = self._merge_documents("PLAYER LIMITS (ALIGNMENT ONLY)", {"PLAYER_LIMITS_AND_EXPECTATIONS.md": limits_content})
            self._boot_loaded_files.append("PLAYER_LIMITS_AND_EXPECTATIONS.md")

        # Optional: last session notes
        session_notes_path = self.config.adventure_path_root / "SESSION_NOTES_LAST.md"
        if session_notes_path.exists():
            notes_content = self.adv_loader.load_path(session_notes_path)
            self.continuity_context = self._merge_documents("CONTINUITY ANCHOR", {"SESSION_NOTES_LAST.md": notes_content})
            self._boot_loaded_files.append("SESSION_NOTES_LAST.md")

        # Deterministic gate: during boot we only load system authority + minimal identity + last notes
        disallowed_prefixes = (
            "01_world_setting/",
            "02_campaign_setting/",
            "03_books/",
        )
        self._boot_only_system_authority_loaded = not any(
            f.startswith(disallowed_prefixes) for f in self._boot_loaded_files
        )

    # ---------- boot prompt assembly ----------
    def _inject_context(self, boot_md: str, session_number: int) -> str:
        """Inject loaded contexts into boot prompt placeholders."""
        rendered = boot_md.replace("{{SESSION_NUMBER}}", str(session_number))

        if "{{SYSTEM_AUTHORITY}}" in rendered:
            rendered = rendered.replace("{{SYSTEM_AUTHORITY}}", self.system_context.strip())

        if "{{PLAYER_IDENTITY}}" in rendered:
            rendered = rendered.replace(
                "{{PLAYER_IDENTITY}}",
                self.player_context.strip() if self.player_context else "[NO PLAYER FILES LOADED]"
            )

        if "{{CONTINUITY_ANCHOR}}" in rendered:
            rendered = rendered.replace(
                "{{CONTINUITY_ANCHOR}}",
                self.continuity_context.strip() if self.continuity_context else "[NO SESSION_NOTES_LAST.md FOUND]"
            )

        return rendered

    def build_boot_system_prompt(self, session_number: int) -> str:
        """Build the system prompt for boot from canonical boot prompt file."""
        boot_md = self.repo_loader.load_path(self.config.boot_prompt_path)
        return self._inject_context(boot_md, session_number=session_number)

    # ---------- ollama chat ----------
    def query_ollama_chat(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.config.ollama_model,
            "messages": messages,
            "stream": False,
            "temperature": self.config.temperature,
        }

        resp = requests.post(f"{self.config.ollama_host}/api/chat", json=payload, timeout=180)
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama /api/chat failed: HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        return (data.get("message", {}) or {}).get("content", "").strip()

    # ---------- checklist extraction ----------
    def get_boot_output_section(self) -> str:
        """
        Extract the "# Session Boot Output" section from SESSION_BOOT_PROMPT.md.
        Returns the section text (or a clear message if missing).
        """
        boot_prompt_content = self.repo_loader.load_path(self.config.boot_prompt_path)

    
        header = "# Session Boot Output"
        if header not in boot_prompt_content:
            return "[No Session Boot Output section found in boot prompt file]"

        start = boot_prompt_content.find(header)
        return boot_prompt_content[start:].strip()

    def semantic_audit_narration(self, narration: str) -> Dict:
        """
        Ask the LLM to audit the narration against BOOT constraints.
        Returns a dict parsed from strict JSON.
        If parsing fails or required keys are missing, raise.
        """
        # Keep this SYSTEM prompt minimal and extremely strict.
        audit_system = (
            "You are a strict verifier. You must return ONLY valid JSON. "
            "No markdown, no prose, no extra keys beyond the schema. "
            "If uncertain, set the verdict to false and explain briefly in 'notes'."
        )

        # The schema is intentionally simple for robust parsing.
        audit_user = {
            "task": "BOOT_NARRATION_AUDIT",
            "requirements": [
                "Narration is based only on established, on-screen facts (no invented history, no unseen causes).",
                "No forming/resolving plans, triggers, or outcomes.",
                "No implication of future threats/events (no foreshadowing).",
                "No escalation, dialogue, rolls, or time advancement.",
                "Ends exactly with: What do you do?"
            ],
            "narration": narration
        }

        # Force JSON response: ask model to output the exact structure.
        audit_instruction = (
            "Return JSON exactly in this format:\n"
            "{\n"
            '  "on_screen_facts_only": {"pass": <true/false>, "notes": "<short>"},\n'
            '  "no_plans_triggers_outcomes": {"pass": <true/false>, "notes": "<short>"},\n'
            '  "no_future_implication": {"pass": <true/false>, "notes": "<short>"},\n'
            '  "no_escalation_dialogue_rolls_time": {"pass": <true/false>, "notes": "<short>"},\n'
            '  "ends_with_what_do_you_do": {"pass": <true/false>, "notes": "<short>"}\n'
            "}\n"
            "Return ONLY JSON."
        )

        # We send the instruction plus the payload as plain text to avoid model confusion.
        user_prompt = audit_instruction + "\n\n" + json.dumps(audit_user, ensure_ascii=False)

        raw = self.query_ollama_chat(user_prompt, system_prompt=audit_system)

        try:
            data = json.loads(raw)
        except Exception as e:
            raise RuntimeError(f"Semantic audit returned non-JSON. Error: {e}. Raw: {raw[:300]!r}")

        required = [
            "on_screen_facts_only",
            "no_plans_triggers_outcomes",
            "no_future_implication",
            "no_escalation_dialogue_rolls_time",
            "ends_with_what_do_you_do",
        ]
        for k in required:
            if k not in data or "pass" not in data[k] or "notes" not in data[k]:
                raise RuntimeError(f"Semantic audit JSON missing required field(s): {k}. JSON: {data}")

        return data


    def extract_checklist_items(self, boot_output_section: str) -> List[str]:
        return extract_prompt_checklist_items(boot_output_section)

    def evaluate_boot_checklist(
        self,
        checklist_items: List[str],
        narration: str,
        audit: Optional[Dict] = None,
    ) -> List[VerificationResult]:
        return verify_prompt(
            checklist_items,
            narration,
            prompt_source="SESSION_BOOT_PROMPT",
            audit=audit,
            loaded_files=self._boot_loaded_files,
            required_system_authority_files=self.BOOT_SYSTEM_AUTHORITY_FILES,
        )

    def print_checklist_report(self, evaluated: List[VerificationResult]) -> None:
        print("\n" + "=" * 80)
        print("BOOT CHECKLIST VERIFICATION")
        print("=" * 80)
        summary = summarize_results(evaluated)
        all_ok = bool(summary["ok"])

        print("-" * 80)
        if all_ok:
            print("[PASS] ALL CHECKS PASSED")
        else:
            print("[FAIL] ONE OR MORE CHECKS FAILED")
        print("=" * 80 + "\n")

        if not all_ok:
            raise RuntimeError("Boot checklist verification failed. See report above.")

    # ---------- BOOT public API ----------
    def boot_once(self, session_number: int = 1) -> str:
        """Runs boot and returns the GM opening narration (string)."""
        if not self.config.boot_prompt_path.exists():
            raise FileNotFoundError(f"Missing canonical boot prompt: {self.config.boot_prompt_path}")

        print("[GM-AGENT] Loading boot contexts...")
        self.load_boot_contexts()

        print("[GM-AGENT] Building system prompt from canonical boot file...")
        system_prompt = self.build_boot_system_prompt(session_number=session_number)

        print("[GM-AGENT] Querying Ollama for opening narration...")
        user_prompt = (
            "Begin the Session Boot now. Follow the boot protocol in the system message. "
            "Produce the opening narration and end with exactly: What do you do?"
        )
        return self.query_ollama_chat(user_prompt, system_prompt=system_prompt)

    def boot_session(self, session_number: int = 1) -> None:
        """Boots, prints narration, then prints and enforces checklist verification."""
        print("\n" + "=" * 80)
        print("GM AGENT BOOT SEQUENCE")
        print("=" * 80 + "\n")

        narration = self.boot_once(session_number=session_number)

        print("\n" + "=" * 80)
        print("OPENING NARRATION")
        print("=" * 80 + "\n")
        print(narration)
        print("\n" + "-" * 80 + "\n")

        # Extract checklist from boot prompt file
        # Extract checklist from boot prompt file
        boot_output_section = self.get_boot_output_section()
        checklist_items = self.extract_checklist_items(boot_output_section)

        if not checklist_items:
            raise RuntimeError(
                "No checklist items found in '# Session Boot Output' section of SESSION_BOOT_PROMPT.md. "
                "Ensure it contains lines like '* [ ] ...'."
            )

        # Run semantic audit (strict JSON). If it fails to return JSON, boot fails.
        audit = self.semantic_audit_narration(narration)

        # Evaluate checklist items (deterministic + audit)
        evaluated = self.evaluate_boot_checklist(checklist_items, narration, audit=audit)

        self.print_checklist_report(evaluated)
