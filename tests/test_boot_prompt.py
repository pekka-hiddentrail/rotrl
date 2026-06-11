"""
Tests for boot prompt assembly and session-start context resolution.

Covers:
  - _build_slim_system_prompt structure and required sections
  - Situation block: boot.md > previous recap.md > fallback notice
  - Party block extracted from ui/public/data/player_NN.json files
  - Boot delta cleanup: session_NNN.md files deleted for current session only
  - _DELTA_BLOCK_RE: parsing full and minimal %%DELTA%% blocks, stripping from text
  - validate_turn_input
  - validate_generated_text
"""
from __future__ import annotations

from pathlib import Path

import pytest

import json

from api.session_manager import (
    _build_slim_system_prompt,
    _build_pc_profiles,
    validate_turn_input,
    validate_generated_text,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session_dir(base: Path, n: int) -> Path:
    d = base / "sessions" / f"session_{n:03d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_player(base: Path, slot: int, name: str, cls: str) -> None:
    d = base / "ui" / "public" / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"player_{slot:02d}.json").write_text(
        json.dumps({"name": name, "class": cls}),
        encoding="utf-8",
    )


# ── Boot prompt structure ─────────────────────────────────────────────────────

def test_prompt_contains_core_behavior(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_session_dir(tmp_path, 1)
    prompt = _build_slim_system_prompt.__wrapped__(1) if hasattr(_build_slim_system_prompt, "__wrapped__") else _build_slim_system_prompt(1)
    assert "CORE BEHAVIOR" in prompt


def test_prompt_contains_response_structure(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "RESPONSE STRUCTURE" in prompt
    assert "%%NARRATIVE%%" in prompt
    assert "%%DELTAS%%" in prompt
    assert "%%GENERATE%%" in prompt


def test_prompt_contains_party_section(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "PARTY" in prompt


def test_prompt_contains_situation_section(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "CURRENT SITUATION" in prompt


def test_prompt_mentions_roll_marker(tmp_path, monkeypatch):
    """Static prompt lists %%ROLL%% in the marker list but does NOT contain
    the full spec (dc:, success:, failure:) — that is injected dynamically."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "%%ROLL%%" in prompt
    assert "dc:" not in prompt


# ── Situation block resolution ────────────────────────────────────────────────

def test_reads_own_boot_md(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = _make_session_dir(tmp_path, 2)
    (d / "boot.md").write_text("Session 2 boot content.", encoding="utf-8")

    prompt = _build_slim_system_prompt(2)
    assert "Session 2 boot content." in prompt


def test_falls_back_to_previous_recap(tmp_path, monkeypatch):
    """Session 2 has no boot.md — should use session_001/recap.md."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_session_dir(tmp_path, 2)
    prev = _make_session_dir(tmp_path, 1)
    (prev / "recap.md").write_text("Recap from session 1.", encoding="utf-8")

    prompt = _build_slim_system_prompt(2)
    assert "Recap from session 1." in prompt


def test_does_not_use_recap_when_own_boot_exists(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = _make_session_dir(tmp_path, 2)
    (d / "boot.md").write_text("Correct boot.", encoding="utf-8")
    prev = _make_session_dir(tmp_path, 1)
    (prev / "recap.md").write_text("Should not appear.", encoding="utf-8")

    prompt = _build_slim_system_prompt(2)
    assert "Correct boot." in prompt
    assert "Should not appear." not in prompt


def test_fallback_notice_when_no_files(tmp_path, monkeypatch):
    """No session files at all — prompt should contain the fallback string."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    prompt = _build_slim_system_prompt(1)
    assert "No boot context found" in prompt


def test_session1_does_not_look_for_session0_recap(tmp_path, monkeypatch):
    """Session 1 should never try to read session_000/recap.md."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    bogus = _make_session_dir(tmp_path, 0)
    (bogus / "recap.md").write_text("Should never load this.", encoding="utf-8")

    prompt = _build_slim_system_prompt(1)
    assert "Should never load this." not in prompt


# ── Party block extraction ────────────────────────────────────────────────────

def test_party_names_appear_in_prompt(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_player(tmp_path, 1, "Aldric", "Fighter / Two-Handed Fighter")
    _make_player(tmp_path, 2, "Sylara", "Wizard / Diviner")

    prompt = _build_slim_system_prompt(1)
    assert "Aldric" in prompt
    assert "Sylara" in prompt
    assert "Fighter" in prompt
    assert "Wizard" in prompt


def test_party_fallback_when_no_players_dir(tmp_path, monkeypatch):
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    prompt = _build_slim_system_prompt(1)
    assert "no character files found" in prompt


def test_party_sorted_by_slot(tmp_path, monkeypatch):
    """Players should appear in slot order (01, 02, 03)."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    _make_player(tmp_path, 3, "Charlie", "Rogue")
    _make_player(tmp_path, 1, "Alice",   "Paladin")
    _make_player(tmp_path, 2, "Bob",     "Ranger")

    prompt = _build_slim_system_prompt(1)
    alice_pos  = prompt.index("Alice")
    bob_pos    = prompt.index("Bob")
    charlie_pos = prompt.index("Charlie")
    assert alice_pos < bob_pos < charlie_pos


# ── Boot delta cleanup ────────────────────────────────────────────────────────

def test_boot_deletes_session_delta_files(tmp_path, monkeypatch):
    """create_session() must delete the session's own delta files on boot."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    npc_dir = tmp_path / "adventure_path" / "01_npcs" / "test_npc"
    npc_dir.mkdir(parents=True)
    delta = npc_dir / "session_001.md"
    delta.write_text("## Turn 1 — 12:00:00\n**Summary:** old data\n", encoding="utf-8")
    assert delta.exists()

    sm.create_session(1, "qwen3:4b", dev_mode=True)

    assert not delta.exists(), "session_001.md should be deleted when booting session 1"


def test_boot_does_not_delete_other_session_deltas(tmp_path, monkeypatch):
    """Boot for session 1 must not touch delta files from other sessions."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    npc_dir = tmp_path / "adventure_path" / "01_npcs" / "test_npc"
    npc_dir.mkdir(parents=True)
    other = npc_dir / "session_002.md"
    other.write_text("## Turn 1 — 12:00:00\n**Summary:** session 2 data\n", encoding="utf-8")

    sm.create_session(1, "qwen3:4b", dev_mode=True)

    assert other.exists(), "session_002.md must not be touched when booting session 1"


def test_boot_session_1_resets_knowledge_file(tmp_path, monkeypatch):
    """Booting session 1 should clear existing NPC knowledge.md content."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    npc_dir = tmp_path / "adventure_path" / "01_npcs" / "test_npc"
    npc_dir.mkdir(parents=True)
    (npc_dir / "knowledge.md").write_text(
        "- [pcs] Old campaign memory — S005 T010\n",
        encoding="utf-8",
    )

    sm.create_session(1, "qwen3:4b", dev_mode=True)

    assert (npc_dir / "knowledge.md").read_text(encoding="utf-8") == ""


def test_boot_non_session_1_keeps_knowledge_file(tmp_path, monkeypatch):
    """Booting sessions other than 1 must preserve knowledge.md content."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})

    npc_dir = tmp_path / "adventure_path" / "01_npcs" / "test_npc"
    npc_dir.mkdir(parents=True)
    original = "- [pcs] Keep this memory — S001 T003\n"
    (npc_dir / "knowledge.md").write_text(original, encoding="utf-8")

    sm.create_session(2, "qwen3:4b", dev_mode=True)

    assert (npc_dir / "knowledge.md").read_text(encoding="utf-8") == original


# ── Delta block regex ─────────────────────────────────────────────────────────

def test_delta_block_re_parses_full_block():
    """_DELTA_BLOCK_RE + _parse_delta_fields extracts status fields; knowledge extracted separately."""
    import api.session_manager as sm
    text = (
        "Some GM narrative.\n\n"
        "%%DELTA%%\n"
        "npc: Kendra Deverin\n"
        "disposition: neutral → suspicious\n"
        "location: Festival Square\n"
        "knowledge: [pcs] Ani tried to deceive her\n"
        "knowledge: [quest] The party is investigating the fireworks\n"
        "summary: Kendra grew wary after the failed Bluff attempt.\n"
        "%%END%%\n"
    )
    m = sm._DELTA_BLOCK_RE.search(text)
    assert m is not None
    # Status fields
    fields = sm._parse_delta_fields(m.group(1))
    assert fields["npc"] == "Kendra Deverin"
    assert "suspicious" in fields["disposition"]
    assert "Festival Square" in fields["location"]
    assert "wary" in fields["summary"]
    # Knowledge extracted separately (multiple lines)
    items = sm._extract_knowledge_items(m.group(1))
    assert len(items) == 2
    assert any("deceive" in i for i in items)
    assert any("fireworks" in i for i in items)


def test_delta_block_re_parses_minimal_block():
    """_DELTA_BLOCK_RE matches a block with only npc + summary."""
    import api.session_manager as sm
    text = (
        "%%DELTA%%\n"
        "npc: Ameiko Kaijitsu\n"
        "summary: Ameiko offered the party a free room at the Rusty Dragon.\n"
        "%%END%%\n"
    )
    m = sm._DELTA_BLOCK_RE.search(text)
    assert m is not None
    fields = sm._parse_delta_fields(m.group(1))
    assert fields["npc"] == "Ameiko Kaijitsu"
    assert "disposition" not in fields
    assert "location" not in fields
    assert "knowledge" not in fields
    assert "free room" in fields["summary"]


def test_delta_block_re_tolerates_extra_fields_and_reordered_fields():
    """_DELTA_BLOCK_RE matches even when the LLM adds extra fields or reorders them."""
    import api.session_manager as sm
    text = (
        "%%DELTA%%\n"
        "npc: Abstalar Zantus\n"
        "location: Cathedral\n"          # location before disposition
        "goals: Wants to bless the festival\n"   # extra field
        "disposition: warm\n"
        "summary: Zantus welcomed the party.\n"
        "%%END%%\n"
    )
    m = sm._DELTA_BLOCK_RE.search(text)
    assert m is not None
    fields = sm._parse_delta_fields(m.group(1))
    assert fields["npc"] == "Abstalar Zantus"
    assert fields["location"] == "Cathedral"
    assert fields["disposition"] == "warm"
    assert fields["summary"] == "Zantus welcomed the party."


def test_delta_block_re_strips_from_text():
    """Substituting out the delta block leaves only the narrative."""
    import api.session_manager as sm
    text = (
        "Father Zantus smiled warmly.\n\n"
        "%%DELTA%%\n"
        "npc: Abstalar Zantus\n"
        "summary: Zantus answered Ani's question about Desna.\n"
        "%%END%%\n"
    )
    clean = sm._DELTA_BLOCK_RE.sub("", text).strip()
    assert "%%DELTA%%" not in clean
    assert "%%END%%" not in clean
    assert "Father Zantus smiled warmly." in clean


# ── Missing %%END%% tolerance ─────────────────────────────────────────────────

def test_delta_block_re_tolerates_missing_end_marker():
    """%%DELTA%% block with no %%END%% is still parsed and stripped."""
    import api.session_manager as sm
    text = (
        "Kendra turned to greet him.\n\n"
        "%%DELTA%%\n"
        "npc: Kendra Deverin\n"
        "disposition: neutral\n"
        "location: cathedral steps\n"
        "summary: Kendra greeted Yanyeeku warmly.\n"
        # no %%END%%
    )
    m = sm._DELTA_BLOCK_RE.search(text)
    assert m is not None
    fields = sm._parse_delta_fields(m.group(1))
    assert fields["npc"] == "Kendra Deverin"
    assert fields["disposition"] == "neutral"
    assert "warmly" in fields["summary"]

    clean = sm._DELTA_BLOCK_RE.sub("", text).strip()
    assert "%%DELTA%%" not in clean
    assert "Kendra turned to greet him." in clean


def test_delta_block_re_two_blocks_without_end_markers():
    """Two consecutive %%DELTA%% blocks with no %%END%% are both found."""
    import api.session_manager as sm
    text = (
        "The scene unfolds.\n\n"
        "%%DELTA%%\n"
        "npc: Kendra Deverin\n"
        "summary: Kendra greeted the party.\n"
        "\n"
        "%%DELTA%%\n"
        "npc: Abstalar Zantus\n"
        "summary: Zantus offered a blessing.\n"
    )
    matches = list(sm._DELTA_BLOCK_RE.finditer(text))
    assert len(matches) == 2
    f1 = sm._parse_delta_fields(matches[0].group(1))
    f2 = sm._parse_delta_fields(matches[1].group(1))
    assert f1["npc"] == "Kendra Deverin"
    assert f2["npc"] == "Abstalar Zantus"

    clean = sm._DELTA_BLOCK_RE.sub("", text).strip()
    assert "%%DELTA%%" not in clean
    assert "The scene unfolds." in clean


def test_roll_block_re_tolerates_missing_end_marker():
    """%%ROLL%% block with no %%END%% is still parsed and stripped."""
    import api.session_manager as sm
    text = (
        "Yanyeeku steps forward to speak with the mayor.\n\n"
        "%%ROLL%%\n"
        "skill: Diplomacy\n"
        "dc: 12\n"
        "success: The mayor smiles warmly.\n"
        "failure: The mayor looks distracted.\n"
        # no %%END%%
    )
    m = sm._ROLL_BLOCK_RE.search(text)
    assert m is not None
    assert m.group("skill").strip() == "Diplomacy"
    assert int(m.group("dc")) == 12
    assert "warmly" in m.group("success")
    assert "distracted" in m.group("failure")

    clean = sm._ROLL_BLOCK_RE.sub("", text).strip()
    assert "%%ROLL%%" not in clean
    assert "Yanyeeku steps forward" in clean


def test_roll_then_delta_both_without_end_markers():
    """%%ROLL%% followed by %%DELTA%%, neither has %%END%% — both stripped cleanly."""
    import api.session_manager as sm
    text = (
        "Yanyeeku approaches the mayor on the cathedral steps.\n\n"
        "%%ROLL%%\n"
        "skill: Diplomacy\n"
        "dc: 12\n"
        "success: Kendra's expression turns genuinely interested.\n"
        "failure: Kendra's smile falters for a moment.\n"
        "\n"
        "%%DELTA%%\n"
        "npc: Kendra Deverin\n"
        "disposition: neutral\n"
        "location: cathedral steps\n"
        "knowledge: [pcs] Yanyeeku is a visitor interested in local citizens\n"
        "summary: Yanyeeku approaches the mayor and she greets him warmly.\n"
    )
    # Roll stripped first
    after_roll = sm._ROLL_BLOCK_RE.sub("", text).rstrip()
    assert "%%ROLL%%" not in after_roll
    assert "Yanyeeku approaches the mayor" in after_roll
    assert "%%DELTA%%" in after_roll  # delta still present

    # Delta stripped second
    after_delta = sm._DELTA_BLOCK_RE.sub("", after_roll).strip()
    assert "%%DELTA%%" not in after_delta
    assert "Yanyeeku approaches the mayor" in after_delta

    # Roll was parseable
    roll_m = sm._ROLL_BLOCK_RE.search(text)
    assert roll_m is not None
    assert roll_m.group("skill").strip() == "Diplomacy"
    assert int(roll_m.group("dc")) == 12

    # Delta was parseable (from intermediate text)
    delta_m = sm._DELTA_BLOCK_RE.search(after_roll)
    assert delta_m is not None
    fields = sm._parse_delta_fields(delta_m.group(1))
    assert fields["npc"] == "Kendra Deverin"
    items = sm._extract_knowledge_items(delta_m.group(1))
    assert len(items) == 1
    assert "visitor" in items[0]


# ── Section-based response parser ────────────────────────────────────────────

def test_parse_response_sections_all_sections():
    """_parse_response_sections splits a full templated response into named sections."""
    import api.session_manager as sm
    text = (
        "%%NARRATIVE%%\n"
        "Hannah smiles at Vanx.\n\n"
        "%%ROLL%%\n"
        "[\n"
        "skill: Diplomacy\n"
        "dc: 12\n"
        "success: She opens up warmly.\n"
        "failure: She stays guarded.\n"
        "]\n\n"
        "%%DELTAS%%\n"
        "[\n"
        "npc: Hannah\n"
        "summary: Greeted Vanx.\n"
        "]\n\n"
        "%%GENERATE%%\n"
        "[\n"
        "npc: Hannah\n"
        "role: fruit shop owner\n"
        "]\n"
    )
    sections = sm._parse_response_sections(text)
    assert "NARRATIVE" in sections
    assert "ROLL" in sections
    assert "DELTAS" in sections
    assert "GENERATE" in sections
    assert "Hannah smiles" in sections["NARRATIVE"]
    assert "Diplomacy" in sections["ROLL"]
    assert "fruit shop owner" in sections["GENERATE"]


def test_parse_response_sections_fallback_no_markers():
    """Without section markers the whole text is returned as NARRATIVE."""
    import api.session_manager as sm
    text = "Kendra smiles at you warmly. What do you do?"
    sections = sm._parse_response_sections(text)
    assert sections == {"NARRATIVE": text.strip()}


def test_parse_response_sections_narrative_only():
    """A response with only %%NARRATIVE%% returns just that section."""
    import api.session_manager as sm
    text = "%%NARRATIVE%%\nThe festival continues.\n"
    sections = sm._parse_response_sections(text)
    assert sections.get("NARRATIVE") == "The festival continues."
    assert "DELTAS" not in sections


def test_parse_bracket_blocks_single():
    """A single bracket block is parsed into one field dict."""
    import api.session_manager as sm
    text = "[\nnpc: Kendra Deverin\nlocation: steps\nsummary: She waved.\n]"
    blocks = sm._parse_bracket_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["npc"] == "Kendra Deverin"
    assert blocks[0]["location"] == "steps"


def test_parse_bracket_blocks_multiple():
    """Multiple bracket blocks in one section are all returned."""
    import api.session_manager as sm
    text = (
        "[\nnpc: Kendra Deverin\nsummary: Greeted party.\n]\n\n"
        "[\nnpc: Garridan Vashin\nsummary: Showed fireworks.\n]\n"
    )
    blocks = sm._parse_bracket_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["npc"] == "Kendra Deverin"
    assert blocks[1]["npc"] == "Garridan Vashin"


def test_parse_bracket_blocks_multiple_knowledge_lines():
    """Multiple knowledge: lines in one block are collected into a list."""
    import api.session_manager as sm
    text = (
        "[\n"
        "npc: Kendra Deverin\n"
        "knowledge: [pcs] Yanyeeku asked about fireworks\n"
        "knowledge: [world] The festival is going well\n"
        "summary: Spoke with Yanyeeku.\n"
        "]\n"
    )
    blocks = sm._parse_bracket_blocks(text)
    assert len(blocks) == 1
    k = blocks[0]["knowledge"]
    assert isinstance(k, list)
    assert len(k) == 2
    assert any("fireworks" in item for item in k)
    assert any("festival" in item for item in k)


def test_parse_bracket_blocks_knowledge_tag_not_confused_with_delimiter():
    """[pcs] tags inside knowledge lines do not confuse the bracket parser."""
    import api.session_manager as sm
    text = (
        "[\n"
        "npc: Kendra Deverin\n"
        "knowledge: [persistent] Always friendly to newcomers\n"
        "summary: Welcomed the party.\n"
        "]\n"
    )
    blocks = sm._parse_bracket_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["npc"] == "Kendra Deverin"


# ── B2: malformed character sheet robustness ─────────────────────────────────

def test_party_name_without_class_does_not_crash(tmp_path, monkeypatch):
    """Character sheet with Name but no Class line must not raise UnboundLocalError."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = tmp_path / "players" / "player_01"
    d.mkdir(parents=True)
    (d / "character_sheet.md").write_text("**Name:** Ghostface\n", encoding="utf-8")

    prompt = _build_slim_system_prompt(1)
    assert isinstance(prompt, str)


def test_party_class_before_name_does_not_crash(tmp_path, monkeypatch):
    """Class line appearing before Name in character_sheet.md must not raise UnboundLocalError."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = tmp_path / "players" / "player_01"
    d.mkdir(parents=True)
    (d / "character_sheet.md").write_text(
        "**Class / Archetype:** Fighter\n**Name:** Brak\n",
        encoding="utf-8",
    )

    prompt = _build_slim_system_prompt(1)
    assert isinstance(prompt, str)


def test_party_mixed_good_and_malformed_sheets(tmp_path, monkeypatch):
    """A JSON entry without class must not prevent valid entries from appearing."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)

    d = tmp_path / "ui" / "public" / "data"
    d.mkdir(parents=True)
    # player_01 has no class — should be omitted from the party block
    (d / "player_01.json").write_text(json.dumps({"name": "Ghostface"}), encoding="utf-8")
    # player_02 has full identity — must appear
    (d / "player_02.json").write_text(json.dumps({"name": "Aldric", "class": "Paladin"}), encoding="utf-8")

    prompt = _build_slim_system_prompt(1)
    assert "Aldric" in prompt


# ── Input validation ──────────────────────────────────────────────────────────

def test_validate_empty_input():
    assert validate_turn_input("") is not None
    assert validate_turn_input("   ") is not None


def test_validate_too_long_input():
    assert validate_turn_input("x" * 4001) is not None


def test_validate_normal_input():
    assert validate_turn_input("We look around the square.") is None


def test_validate_max_length_boundary():
    assert validate_turn_input("x" * 4000) is None


# ── Output validation ─────────────────────────────────────────────────────────

def test_validate_empty_output():
    assert validate_generated_text("", "Recap") is not None
    assert validate_generated_text("   ", "Recap") is not None


def test_validate_too_short_output():
    assert validate_generated_text("Short.", "Recap", min_length=80) is not None


def test_validate_acceptable_output():
    text = "A" * 200
    assert validate_generated_text(text, "Recap", min_length=80) is None


def test_validate_uses_stripped_length():
    """Padding with whitespace should not fool the length check."""
    text = "   " + "x" * 10 + "   "
    assert validate_generated_text(text, "Boot", min_length=80) is not None


# ── Dynamic prompt sections not in static base ────────────────────────────────

def test_static_prompt_does_not_contain_format_example(tmp_path, monkeypatch):
    """Format example (Gerhard Pickle) must NOT be in the static prompt —
    it is injected per-turn only on the first player turn."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "Gerhard Pickle" not in prompt
    assert "EXAMPLE OF A CORRECT FULL RESPONSE" not in prompt


def test_static_prompt_does_not_contain_combat_tracker_rules(tmp_path, monkeypatch):
    """Verbose combat rules must NOT be in the static prompt —
    they are injected per-turn only when combat is active."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    # The compact one-liner stays; the rule prose must not be present.
    assert "Increment round when all combatants have acted" not in prompt
    assert "Valid statuses: active" not in prompt


def test_static_prompt_contains_compact_combat_reference(tmp_path, monkeypatch):
    """A compact %%COMBAT%% reference must still appear in the static prompt
    so the model knows the marker exists and when to use it."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "%%COMBAT%%" in prompt


def test_format_example_constant_contains_required_sections():
    """_FORMAT_EXAMPLE must include all three section markers the model
    needs to learn the format from."""
    from api.session_manager import _FORMAT_EXAMPLE
    assert "%%NARRATIVE%%" in _FORMAT_EXAMPLE
    assert "%%GENERATE%%" in _FORMAT_EXAMPLE
    assert "%%DELTAS%%" in _FORMAT_EXAMPLE
    assert "Gerhard Pickle" in _FORMAT_EXAMPLE


def test_combat_full_spec_constant_contains_format_and_rules():
    """Round-1 spec has HP init fields; ongoing spec carries the round-0 rule."""
    from api.session_manager import _COMBAT_SPEC_ROUND1, _COMBAT_SPEC_ONGOING
    assert "%%COMBAT%%" in _COMBAT_SPEC_ROUND1
    assert "hp:" in _COMBAT_SPEC_ROUND1        # round-1: LLM must supply HP for init
    assert "round: 0" in _COMBAT_SPEC_ONGOING  # ongoing spec has the clear-combat rule


def test_static_prompt_section_specs_absent(tmp_path, monkeypatch):
    """Verbose section specs (dc:, type: npc|location, Tags:) must NOT be in
    the static prompt — they are injected per-turn by _inject_context."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    prompt = _build_slim_system_prompt(1)
    assert "dc: <N>" not in prompt
    assert "type: npc|location" not in prompt
    assert "Tags: [persistent]" not in prompt


# ── _build_pc_profiles ────────────────────────────────────────────────────────

def _make_player_json(data_dir: Path, filename: str, data: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / filename).write_text(json.dumps(data), encoding="utf-8")


_SAMPLE_PC_JSON = {
    "name": "Aldric",
    "race": "Human",
    "class": "Fighter",
    "archetype": "Two-Handed Fighter",
    "appearance": "A broad-shouldered man with a scarred jaw and close-cropped grey hair.",
    "hp": {"current": 12, "max": 12},
    "ac": {"total": 16},
    "initiative": "+1",
    "speed": "30 ft.",
    "abilities": [
        {"name": "STR", "mod": "+3"},
        {"name": "DEX", "mod": "+1"},
        {"name": "CON", "mod": "+2"},
        {"name": "INT", "mod": "+0"},
        {"name": "WIS", "mod": "+1"},
        {"name": "CHA", "mod": "-1"},
    ],
    "saves": [
        {"name": "Fortitude", "total": "+4"},
        {"name": "Reflex",    "total": "+1"},
        {"name": "Will",      "total": "+2"},
    ],
    "spells": {"list": []},
}


class TestBuildPcProfiles:
    def test_returns_empty_dict_when_dir_absent(self, tmp_path):
        result = _build_pc_profiles(tmp_path / "nonexistent")
        assert result == {}

    def test_returns_empty_dict_when_no_json_files(self, tmp_path):
        (tmp_path / "data").mkdir()
        result = _build_pc_profiles(tmp_path / "data")
        assert result == {}

    def test_name_becomes_lowercase_key(self, tmp_path):
        _make_player_json(tmp_path, "player_01.json", _SAMPLE_PC_JSON)
        result = _build_pc_profiles(tmp_path)
        assert "aldric" in result

    def test_narrative_contains_name_and_appearance(self, tmp_path):
        _make_player_json(tmp_path, "player_01.json", _SAMPLE_PC_JSON)
        result = _build_pc_profiles(tmp_path)
        narr = result["aldric"]["narrative"]
        assert "Aldric" in narr
        assert "scarred jaw" in narr

    def test_narrative_contains_class_and_archetype(self, tmp_path):
        _make_player_json(tmp_path, "player_01.json", _SAMPLE_PC_JSON)
        result = _build_pc_profiles(tmp_path)
        narr = result["aldric"]["narrative"]
        assert "Fighter" in narr
        assert "Two-Handed Fighter" in narr

    def test_mechanical_contains_hp_ac_init_speed(self, tmp_path):
        _make_player_json(tmp_path, "player_01.json", _SAMPLE_PC_JSON)
        result = _build_pc_profiles(tmp_path)
        mech = result["aldric"]["mechanical"]
        assert "HP: 12" in mech
        assert "AC: 16" in mech
        assert "Init: +1" in mech
        assert "Speed: 30 ft." in mech

    def test_mechanical_contains_saves(self, tmp_path):
        _make_player_json(tmp_path, "player_01.json", _SAMPLE_PC_JSON)
        result = _build_pc_profiles(tmp_path)
        mech = result["aldric"]["mechanical"]
        assert "Fort +4" in mech
        assert "Ref +1" in mech
        assert "Will +2" in mech

    def test_multiple_pcs_keyed_separately(self, tmp_path):
        _make_player_json(tmp_path, "player_01.json", _SAMPLE_PC_JSON)
        second = dict(_SAMPLE_PC_JSON, name="Sylara", race="Elf", **{"class": "Wizard"})
        _make_player_json(tmp_path, "player_02.json", second)
        result = _build_pc_profiles(tmp_path)
        assert "aldric" in result
        assert "sylara" in result

    def test_invalid_json_skipped_gracefully(self, tmp_path):
        (tmp_path / "player_01.json").write_text("not valid json", encoding="utf-8")
        _make_player_json(tmp_path, "player_02.json", _SAMPLE_PC_JSON)
        result = _build_pc_profiles(tmp_path)
        assert "aldric" in result
        assert len(result) == 1

    def test_missing_name_skipped(self, tmp_path):
        nameless = dict(_SAMPLE_PC_JSON)
        del nameless["name"]
        _make_player_json(tmp_path, "player_01.json", nameless)
        result = _build_pc_profiles(tmp_path)
        assert result == {}

    def test_spells_included_in_mechanical(self, tmp_path):
        with_spells = dict(_SAMPLE_PC_JSON)
        with_spells["spells"] = {"list": [
            {"name": "Magic Missile"}, {"name": "Shield"}, {"name": "Sleep"}
        ]}
        _make_player_json(tmp_path, "player_01.json", with_spells)
        result = _build_pc_profiles(tmp_path)
        mech = result["aldric"]["mechanical"]
        assert "Magic Missile" in mech
        assert "Shield" in mech
