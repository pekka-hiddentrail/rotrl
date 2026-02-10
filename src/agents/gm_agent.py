#!/usr/bin/env python3
"""
GM Agent for RotRL - Bootstraps the Game Master AI.

This module:
1. Loads all necessary adventure_path documents
2. Builds a comprehensive GM context prompt
3. Communicates with Ollama LLM
4. Manages session state and game flow
"""

import requests
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GMConfig:
    """Configuration for GM Agent."""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    adventure_path_root: Optional[Path] = None
    temperature: float = 0.3  # Lower temp for consistency
    
    def __post_init__(self):
        if self.adventure_path_root is None:
            self.adventure_path_root = Path(__file__).parent.parent.parent / "adventure_path"


class FileLoader:
    """Loads and caches adventure_path documents."""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._cache: Dict[str, str] = {}
    
    def load_file(self, relative_path: str) -> str:
        """Load a file from adventure_path, with caching."""
        if relative_path in self._cache:
            return self._cache[relative_path]
        
        file_path = self.root_path / relative_path
        if not file_path.exists():
            return f"[FILE NOT FOUND: {relative_path}]"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._cache[relative_path] = content
            return content
        except Exception as e:
            return f"[ERROR LOADING {relative_path}: {e}]"
    
    def load_multiple(self, relative_paths: List[str]) -> Dict[str, str]:
        """Load multiple files at once."""
        return {path: self.load_file(path) for path in relative_paths}


class GMAgent:
    """The Game Master AI Agent."""
    
    # Core files for GM behavior constraints
    SYSTEM_AUTHORITY_FILES = [
        "00_system_authority/GM_OPERATING_RULES.md",
        "00_system_authority/ADJUDICATION_PRINCIPLES.md",
        "00_system_authority/COMBAT_AND_POSITIONING.md",
        "00_system_authority/PF1E_RULES_SCOPE.md",
        "00_system_authority/SESSION_NOTES_PROTOCOL.md",
    ]
    
    # Campaign context files
    CAMPAIGN_FILES = [
        "01_world_setting/WORLD_OPERATING_RULES.md",
        "01_world_setting/WORLD_CANON.md",
        "02_campaign_setting/CAMPAIGN_OVERVIEW.md",
        "02_campaign_setting/THEME_AND_TONE.md",
        "02_campaign_setting/PLAYER_AGENCY_RULES.md",
        "02_campaign_setting/NPC_MEMORY_AND_CONTINUITY.md",
    ]
    
    # Book I specific files
    BOOK_I_FILES = [
        "03_books/BOOK_01_BURNT_OFFERINGS/BOOK_OVERVIEW.md",
        "03_books/BOOK_01_BURNT_OFFERINGS/NPCS.md",
        "03_books/BOOK_01_BURNT_OFFERINGS/LOCATIONS.md",
        "03_books/BOOK_01_BURNT_OFFERINGS/EVENTS_AND_TRIGGERS.md",
        "03_books/BOOK_01_BURNT_OFFERINGS/ACT_STRUCTURE.md",
    ]
    
    def __init__(self, config: GMConfig):
        self.config = config
        self.loader = FileLoader(config.adventure_path_root)
        self.system_context: str = ""
        self.campaign_context: str = ""
        self.book_context: str = ""
        self.session_state: Dict = {}
    
    def load_contexts(self, book: int = 1, act: int = 1):
        """Load all required contexts for the GM."""
        print("[GM-AGENT] Loading system authority files...")
        system_files = self.loader.load_multiple(self.SYSTEM_AUTHORITY_FILES)
        self.system_context = self._merge_documents("SYSTEM AUTHORITY", system_files)
        
        print("[GM-AGENT] Loading campaign context files...")
        campaign_files = self.loader.load_multiple(self.CAMPAIGN_FILES)
        self.campaign_context = self._merge_documents("CAMPAIGN CONTEXT", campaign_files)
        
        if book == 1:
            print("[GM-AGENT] Loading Book I files...")
            book_files = self.loader.load_multiple(self.BOOK_I_FILES)
            self.book_context = self._merge_documents("BOOK I - BURNT OFFERINGS", book_files)
        
        print("[GM-AGENT] Contexts loaded successfully")
    
    def _merge_documents(self, section_name: str, files: Dict[str, str]) -> str:
        """Merge multiple documents into a single context section."""
        merged = f"\n{'='*80}\n{section_name}\n{'='*80}\n\n"
        for filename, content in files.items():
            merged += f"\n--- {filename} ---\n{content}\n"
        return merged
    
    def build_gm_prompt(self, session_number: int = 1, book: int = 1, act: int = 1) -> str:
        """Build the complete GM system prompt."""
        prompt = f"""# RotRL GM Agent - Session Boot Prompt

You are the Game Master AI for Rise of the Runelords in Pathfinder 1st Edition.

## YOUR ROLE

You are a **neutral rules arbiter and world simulator**, not a storyteller or guide.

Your explicit responsibilities:
1. Apply Pathfinder 1e rules RAW (as written)
2. Maintain strict impartiality (no favoring players or outcomes)
3. Enforce consequences rigorously
4. Simulate the world state accurately
5. Present information only what characters can perceive
6. Never fudge dice, adjust DCs after rolling, or protect player characters

## SESSION BOOT INFORMATION

Session Number: {session_number}
Book: {book}
Act: {act}
Campaign Status: FRESH BOOT (no prior session state)

## HOW TO PROCEED

1. **Acknowledge Context**: Confirm you have read and understood all system authority, campaign rules, and Book I guidelines
2. **State Game State**: What is the current in-world date/time? Where are the PCs? What is known?
3. **Ask for Player Input**: Request the player/PC information to begin play
4. **Wait for Scene**: Do not advance the game until you receive explicit player declarations

## MANDATORY CONSTRAINTS

- No speculation or prediction
- No soft-magic or narrative shortcuts
- No inventing rules, spells, or abilities
- All mechanics resolved strictly per PF1e rules
- Combat uses explicit spatial state (grid positioning)
- Time always advances; world continues off-screen per event triggers

## SYSTEM AUTHORITY (CRITICAL - HIGHEST PRIORITY)

You MUST operate within these constraints at all times:

{self.system_context}

## CAMPAIGN CONTEXT (HIGH PRIORITY)

These rules govern campaign scope, player agency, NPC behavior, and tone:

{self.campaign_context}

## BOOK I: BURNT OFFERINGS (OPERATIONAL CONTEXT)

This is your current operational guide for encounters, NPCs, locations, and events:

{self.book_context}

---

## READY TO BEGIN

Once you have confirmed you understand all above, ask:
1. "Has Session {session_number} been run before? (If yes, provide session notes for context)"
2. "How many player characters are present, and what are their names/classes/levels?"
3. "Are you ready to begin play?"

Then wait for player input before advancing the game.
"""
        return prompt
    
    def query_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a query to Ollama and return the response."""
        try:
            payload = {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "temperature": self.config.temperature,
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(
                f"{self.config.ollama_host}/api/generate",
                json=payload,
                timeout=180
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            raise RuntimeError(f"Ollama query failed: {e}")
    
    def boot_session(self, session_number: int = 1) -> None:
        """Boot a new game session."""
        print("\n" + "="*80)
        print("ROTR] GM AGENT SESSION BOOT")
        print("="*80 + "\n")
        
        # Load all contexts
        self.load_contexts(book=1, act=1)
        
        # Build boot prompt
        print("[GM-AGENT] Building boot prompt...")
        boot_prompt = self.build_gm_prompt(session_number=session_number)
        
        # Query Ollama to initialize GM
        print("[GM-AGENT] Initializing GM Agent with Ollama...")
        print("[OLLAMA] Sending boot prompt (this may take 30-60 seconds)...")
        
        gm_response = self.query_ollama(boot_prompt)
        
        print("\n" + "="*80)
        print("GM AGENT INITIALIZED")
        print("="*80 + "\n")
        print(gm_response)
        print("\n" + "-"*80 + "\n")
        
        # Store boot state
        self.session_state = {
            "session_number": session_number,
            "book": 1,
            "act": 1,
            "boot_timestamp": datetime.now().isoformat(),
            "gm_initialized": True,
        }
    
    def session_loop(self) -> None:
        """Main session game loop."""
        if not self.session_state.get("gm_initialized"):
            print("[ERROR] GM not initialized. Call boot_session() first.")
            return
        
        print("[SESSION] Entering game loop. Type 'quit' to exit.\n")
        
        session_buffer = []
        turn_count = 0
        
        while True:
            try:
                user_input = input(">>> ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("[SESSION] Ending session...")
                    break
                
                if not user_input:
                    continue
                
                turn_count += 1
                
                # Build context for this turn
                context_prompt = f"""Current Game State:
Session {self.session_state['session_number']}, Turn {turn_count}

Player/GM Input:
{user_input}

Respond as the GM. Apply rules, adjudicate outcomes, and describe results.
Remember: You are a neutral rules arbiter, not a storyteller. Present mechanical outcomes."""
                
                # Query Ollama
                gm_output = self.query_ollama(context_prompt)
                print(f"\n[GM] {gm_output}\n")
                
                # Buffer for session notes
                session_buffer.append({
                    "turn": turn_count,
                    "player_input": user_input,
                    "gm_output": gm_output
                })
                
            except KeyboardInterrupt:
                print("\n[SESSION] Interrupted by user.")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                continue
        
        # Save session notes
        print("[SESSION] Saving session notes...")
        self._save_session_notes(session_buffer)
    
    def _save_session_notes(self, turns: List[Dict]) -> None:
        """Save session notes to file."""
        session_num = self.session_state.get("session_number", 1)
        output_dir = Path(__file__).parent.parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        
        notes_file = output_dir / f"session_{session_num:03d}_notes.json"
        
        session_data = {
            "session_number": session_num,
            "book": self.session_state.get("book", 1),
            "act": self.session_state.get("act", 1),
            "turns": turns,
        }
        
        with open(notes_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)
        
        print(f"[SESSION] Notes saved to {notes_file}")


def main():
    """Entry point for GM Agent."""
    config = GMConfig()
    
    # Check Ollama is running
    try:
        response = requests.get(f"{config.ollama_host}/api/tags", timeout=2)
        if response.status_code != 200:
            print("[ERROR] Ollama is not responding. Start with: ollama serve")
            return 1
    except:
        print("[ERROR] Cannot reach Ollama at {config.ollama_host}")
        print("Start Ollama with: ollama serve")
        return 1
    
    # Create and boot GM agent
    gm = GMAgent(config)
    
    try:
        gm.boot_session(session_number=1)
        gm.session_loop()
    except KeyboardInterrupt:
        print("\n[GM-AGENT] Shutting down...")
        return 0
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
