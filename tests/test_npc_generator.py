"""
Tests for the procedural NPC stub generator (api/npc_generator.py)
and the %%GENERATE%% block pipeline in session_manager.
"""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from api.npc_generator import auto_aliases, generate_base_md, reload_library, slugify


@pytest.fixture(autouse=True)
def clear_library_cache():
    """Flush the in-memory library cache before each test.

    Tests that monkeypatch _LIBRARY_DIR need a clean cache so they don't
    inherit entries loaded from the real library by a previous test.
    """
    reload_library()
    yield
    reload_library()


# ── slugify ───────────────────────────────────────────────────────────────────

def test_slugify_two_words():
    assert slugify("Gorm Hysys") == "gorm_hysys"

def test_slugify_three_words():
    assert slugify("Father Abstalar Zantus") == "father_abstalar_zantus"

def test_slugify_apostrophe():
    assert slugify("Ameiko's Friend") == "ameiko_s_friend"

def test_slugify_extra_spaces():
    assert slugify("  Bo  Bard  ") == "bo_bard"


# ── auto_aliases ──────────────────────────────────────────────────────────────

def test_auto_aliases_standard():
    assert auto_aliases("Gorm Hysys") == ["gorm", "hysys"]

def test_auto_aliases_drops_short_particles():
    # "of", "the", "van" are ≤3 chars — filtered out
    assert "of"  not in auto_aliases("Lord of Sandpoint")
    assert "the" not in auto_aliases("the Wanderer")

def test_auto_aliases_single_short_name():
    assert auto_aliases("Bo") == []

def test_auto_aliases_three_words():
    result = auto_aliases("Father Tobyn Zantus")
    assert "father" in result
    assert "tobyn"  in result
    assert "zantus" in result


# ── library loading ──────────────────────────────────────────────────────────

def test_library_loads_multiple_entries(tmp_path, monkeypatch):
    """A library file with several entries is parsed into a list."""
    import api.npc_generator as gen
    lib = tmp_path / "npc_library"
    lib.mkdir()
    (lib / "appearances.txt").write_text(
        "# comment\nEntry one.\n---\nEntry two.\n---\nEntry three.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gen, "_LIBRARY_DIR", lib)
    reload_library()
    table = gen._get_table("appearances")
    assert len(table) == 3
    assert "Entry one." in table
    assert "Entry three." in table


def test_library_strips_comment_lines(tmp_path, monkeypatch):
    """Lines starting with # are stripped before parsing."""
    import api.npc_generator as gen
    lib = tmp_path / "npc_library"
    lib.mkdir()
    (lib / "personalities.txt").write_text(
        "# This is a header comment\nReal entry.\n---\n# inline comment\nSecond entry.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gen, "_LIBRARY_DIR", lib)
    reload_library()
    table = gen._get_table("personalities")
    assert not any(e.startswith("#") for e in table)
    assert "Real entry." in table


def test_library_falls_back_when_file_missing(tmp_path, monkeypatch):
    """Missing library file returns a non-empty fallback list."""
    import api.npc_generator as gen
    monkeypatch.setattr(gen, "_LIBRARY_DIR", tmp_path / "nonexistent")
    reload_library()
    table = gen._get_table("appearances")
    assert len(table) >= 1  # fallback always returns something


def test_library_falls_back_when_file_empty(tmp_path, monkeypatch):
    """Library file with no valid entries returns the fallback."""
    import api.npc_generator as gen
    lib = tmp_path / "npc_library"
    lib.mkdir()
    (lib / "appearances.txt").write_text("# only comments\n# nothing else\n",
                                         encoding="utf-8")
    monkeypatch.setattr(gen, "_LIBRARY_DIR", lib)
    reload_library()
    table = gen._get_table("appearances")
    assert len(table) >= 1


def test_reload_library_clears_cache():
    """reload_library() flushes the cache so next access re-reads files."""
    import api.npc_generator as gen
    _ = gen._get_table("appearances")        # populate cache
    assert "appearances" in gen._table_cache
    reload_library()
    assert "appearances" not in gen._table_cache


def test_generate_draws_from_library(tmp_path, monkeypatch):
    """generate_base_md uses entries from the library files, not hardcoded text."""
    import api.npc_generator as gen
    lib = tmp_path / "npc_library"
    lib.mkdir()
    unique = "UNIQUE_LIBRARY_APPEARANCE_MARKER"
    (lib / "appearances.txt").write_text(f"{unique}\n", encoding="utf-8")
    (lib / "personalities.txt").write_text("Some personality.\n", encoding="utf-8")
    (lib / "narrative_functions.txt").write_text("Some function.\n", encoding="utf-8")
    (lib / "reactions.txt").write_text("Some reaction.\n", encoding="utf-8")
    monkeypatch.setattr(gen, "_LIBRARY_DIR", lib)
    reload_library()

    md = gen.generate_base_md("Test NPC", rng=random.Random(1))
    assert unique in md


# ── generate_base_md — structure ──────────────────────────────────────────────

@pytest.fixture()
def seeded_rng():
    return random.Random(42)


def test_generate_contains_canonical_name(seeded_rng):
    md = generate_base_md("Gorm Hysys", rng=seeded_rng)
    assert "# Gorm Hysys" in md


def test_generate_session_npc_flag(seeded_rng):
    md = generate_base_md("Gorm Hysys", session_number=1, rng=seeded_rng)
    assert "SESSION NPC" in md
    assert "session_001" in md


def test_generate_session_number_in_flag(seeded_rng):
    md = generate_base_md("Gorm Hysys", session_number=3, rng=seeded_rng)
    assert "session_003" in md


def test_generate_tier_iv(seeded_rng):
    md = generate_base_md("Gorm Hysys", rng=seeded_rng)
    assert "Tier:** IV" in md


def test_generate_all_sections_present(seeded_rng):
    md = generate_base_md("Gorm Hysys", rng=seeded_rng)
    for section in ("Personality", "Appearance", "Narrative Function",
                    "Location & Availability", "Reaction to PCs",
                    "Social Checks", "State Handling"):
        assert section in md, f"Missing section: {section}"


def test_generate_social_checks_present(seeded_rng):
    md = generate_base_md("Gorm Hysys", rng=seeded_rng)
    assert "Diplomacy" in md
    assert "Bluff"     in md
    assert "Intimidate" in md


# ── generate_base_md — caller-supplied fields used verbatim ──────────────────

def test_generate_uses_provided_role(seeded_rng):
    md = generate_base_md("Gorm Hysys", role="pyrotechnician", rng=seeded_rng)
    assert "pyrotechnician" in md


def test_generate_uses_provided_appearance(seeded_rng):
    md = generate_base_md("Gorm Hysys",
                          appearance="A barrel-chested dwarf with singed eyebrows.",
                          rng=seeded_rng)
    assert "barrel-chested dwarf" in md


def test_generate_uses_provided_personality(seeded_rng):
    md = generate_base_md("Gorm Hysys",
                          personality="Boisterous and proud of his craft.",
                          rng=seeded_rng)
    assert "Boisterous" in md


def test_generate_uses_provided_locations(seeded_rng):
    md = generate_base_md("Gorm Hysys",
                          locations=["Gorm's Fireworks", "market street"],
                          rng=seeded_rng)
    assert "Gorm's Fireworks" in md
    assert "market street"    in md


def test_generate_default_location_is_sandpoint(seeded_rng):
    md = generate_base_md("Gorm Hysys", rng=seeded_rng)
    assert "Sandpoint" in md


def test_generate_aliases_from_name(seeded_rng):
    md = generate_base_md("Gorm Hysys", rng=seeded_rng)
    assert "gorm"  in md
    assert "hysys" in md


# ── %%GENERATE%% block — session_manager integration ─────────────────────────

def _make_npc_dir(base: Path, slug: str, content: str = "") -> Path:
    d = base / "adventure_path" / "05_npcs" / slug
    d.mkdir(parents=True, exist_ok=True)
    if content:
        (d / "base.md").write_text(content, encoding="utf-8")
    return d


def test_generate_block_creates_stub(tmp_path, monkeypatch):
    """%%GENERATE%% for an unknown NPC creates a stub base.md."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)
    monkeypatch.setattr(sm, "_skill_index", None)

    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    body = (
        "npc: Gorm Hysys\n"
        "role: pyrotechnician\n"
        "appearance: A stocky dwarf with singed eyebrows.\n"
        "location: Gorm's Fireworks\n"
    )
    sm._process_generate_block(body, session)

    stub = tmp_path / "adventure_path" / "05_npcs" / ".gorm_hysys" / "base.md"
    assert stub.exists(), "base.md should be created"
    text = stub.read_text(encoding="utf-8")
    assert "# Gorm Hysys" in text
    assert "pyrotechnician" in text
    assert "SESSION NPC" in text


def test_generate_block_skips_known_npc(tmp_path, monkeypatch):
    """%%GENERATE%% is ignored when the NPC already exists in the index."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)
    monkeypatch.setattr(sm, "_skill_index", None)

    # Pre-create a known NPC
    existing = _make_npc_dir(tmp_path, "kendra_deverin",
                             "# Kendra Deverin\n**Aliases:** kendra\n")
    original_mtime = existing.stat().st_mtime

    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._process_generate_block("npc: Kendra Deverin\nrole: mayor\n", session)

    # Folder should be unchanged
    assert (existing / "base.md").exists()
    assert not (existing / "base.md").stat().st_mtime > original_mtime + 1


def test_generate_block_resets_npc_index(tmp_path, monkeypatch):
    """After stub creation the NPC index is invalidated for immediate reuse."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)
    monkeypatch.setattr(sm, "_skill_index", None)

    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    # Force index to load (so it will need to be reset)
    _ = sm._get_npc_index()
    assert sm._npc_index is not None

    sm._process_generate_block("npc: Brand New NPC\nrole: blacksmith\n", session)

    assert sm._npc_index is None, "Index must be reset after stub creation"


# ── Boot cleanup — SESSION NPC folders deleted on boot ───────────────────────

def test_boot_deletes_session_npc_folder(tmp_path, monkeypatch):
    """create_session() deletes NPC folders flagged as SESSION NPC."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)

    stub = _make_npc_dir(tmp_path, "gorm_hysys",
                         "# Gorm Hysys\n**Flags:** SESSION NPC — auto-generated session_001\n")
    assert stub.exists()

    sm.create_session(1, "qwen3:4b", dev_mode=True)
    assert not stub.exists(), "SESSION NPC folder must be deleted on boot"


def test_boot_cleanup_invalidates_npc_index(tmp_path, monkeypatch):
    """Boot cleanup must invalidate the in-memory NPC index.

    Regression: without _invalidate_npc_index() at the end of the cleanup loop,
    the stale index still reports the deleted session NPC as 'existing', causing
    _process_generate_block() to skip recreating its directory on the next turn.
    """
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)

    # Warm the index with a session NPC that boot will delete.
    _make_npc_dir(tmp_path, ".marta_hask",
                  "# Marta Hask\n**Flags:** SESSION NPC — auto-generated session_001\n")
    _ = sm._get_npc_index()  # load the stale entry into memory
    assert sm._get_npc_index().npc_dir_for("Marta Hask") is not None

    # Boot: cleanup deletes the directory.
    sm.create_session(1, "qwen3:4b", dev_mode=True)

    # Index must be invalidated — fresh rebuild should NOT find Marta Hask.
    assert sm._get_npc_index().npc_dir_for("Marta Hask") is None, (
        "Stale NPC index not cleared on boot — session NPC will fail to be recreated"
    )


def test_session_npc_recreated_after_reboot(tmp_path, monkeypatch):
    """_process_generate_block() creates a new stub after boot purges the old one.

    Regression: stale index caused _process_generate_block() to silently return
    without creating the directory, leaving Chain B with no NPC stub on second run.
    """
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)

    # Simulate a prior session having created .marta_hask/
    _make_npc_dir(tmp_path, ".marta_hask",
                  "# Marta Hask\n**Flags:** SESSION NPC — auto-generated session_001\n")
    _ = sm._get_npc_index()  # load stale index
    assert sm._get_npc_index().npc_dir_for("Marta Hask") is not None

    # Boot: cleanup purges it.
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)
    assert not (tmp_path / "adventure_path" / "05_npcs" / ".marta_hask").exists()

    # Now simulate the LLM emitting a %%GENERATE%% block for the same NPC.
    sm._process_generate_block(
        "type: npc\nname: Marta Hask\nrole: amulet vendor\n", session
    )

    new_stub = tmp_path / "adventure_path" / "05_npcs" / ".marta_hask" / "base.md"
    assert new_stub.exists(), "Session NPC directory must be recreated after boot purge"


def test_boot_keeps_promoted_npc(tmp_path, monkeypatch):
    """An NPC whose Flags no longer contain SESSION NPC is kept on boot."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)

    promoted = _make_npc_dir(tmp_path, "gorm_hysys",
                             "# Gorm Hysys\n**Flags:** PERSISTENT\n")
    assert promoted.exists()

    sm.create_session(1, "qwen3:4b", dev_mode=True)
    assert promoted.exists(), "Promoted NPC must NOT be deleted on boot"


def test_boot_keeps_permanent_npc_untouched(tmp_path, monkeypatch):
    """Pre-authored NPCs with no SESSION NPC flag are never touched."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)

    kendra = _make_npc_dir(tmp_path, "kendra_deverin",
                           "# Kendra Deverin\n**Flags:** PLOT_CRITICAL, PERSISTENT\n")

    sm.create_session(1, "qwen3:4b", dev_mode=True)
    assert kendra.exists()


# ── Layer 2: delta-loop auto-stub creation ────────────────────────────────────

def _sm_setup(tmp_path, monkeypatch):
    """Common monkeypatching for session_manager integration tests."""
    import api.session_manager as sm
    monkeypatch.setattr(sm, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(sm, "_OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sm, "_sessions", {})
    monkeypatch.setattr(sm, "_npc_index", None)
    monkeypatch.setattr(sm, "_skill_index", None)
    return sm


def test_delta_loop_creates_stub_for_unknown_npc(tmp_path, monkeypatch):
    """Layer 2: %%DELTA%% referencing an unknown NPC triggers stub creation."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)

    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    # Simulate the delta loop receiving a block for an NPC not in the index
    body = (
        "npc: Grimbold Ironfist\n"
        "location: festival square\n"
        "summary: Grimbold showed Yanyeeku fireworks.\n"
    )
    fields = sm._parse_delta_fields(body)
    npc_name = fields.get("npc", "").strip()

    # Nothing in the index yet
    assert sm._get_npc_index().npc_dir_for(npc_name) is None

    # Simulate Layer 2 path (same logic as in the delta loop)
    stub_body = f"npc: {npc_name}\n"
    if fields.get("location"):
        stub_body += f"location: {fields['location']}\n"
    sm._process_generate_block(stub_body, session)

    stub = tmp_path / "adventure_path" / "05_npcs" / ".grimbold_ironfist" / "base.md"
    assert stub.exists(), "Layer 2 must create a stub from delta data"
    text = stub.read_text(encoding="utf-8")
    assert "# Grimbold Ironfist" in text
    assert "SESSION NPC" in text


def test_delta_loop_stub_is_findable_immediately(tmp_path, monkeypatch):
    """After Layer 2 stub creation the index rebuild finds the new NPC."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)

    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._process_generate_block("npc: Grimbold Ironfist\nlocation: market square\n", session)

    # Index was invalidated — rebuilding it should now find the NPC
    npc_dir = sm._get_npc_index().npc_dir_for("Grimbold Ironfist")
    assert npc_dir is not None, "Newly created stub must be findable in rebuilt index"


# ── Narrative name detection (_detect_narrative_npcs) ────────────────────────

def test_detect_adds_unknown_name_to_scene_npcs(tmp_path, monkeypatch):
    """An unrecognised two-word proper name is added to scene_npcs."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._detect_narrative_npcs(
        "Vanx steps inside, where the shopkeeper, Hannah Harvest, welcomes him.",
        session,
    )

    assert "Hannah Harvest" in session.scene_npcs


def test_detect_does_not_create_stub(tmp_path, monkeypatch):
    """Detection must NOT create a stub — that is Layer 2's job."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._detect_narrative_npcs("Hannah Harvest greets Vanx warmly.", session)

    npcs_root = tmp_path / "adventure_path" / "05_npcs"
    assert not npcs_root.exists() or not any(npcs_root.iterdir()), \
        "Detection must not write any NPC folder"


def test_detect_skips_already_tracked_name(tmp_path, monkeypatch):
    """A name already in scene_npcs is not added again."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)
    session.scene_npcs.append("Hannah Harvest")

    sm._detect_narrative_npcs("Hannah Harvest smiles at Vanx.", session)

    assert session.scene_npcs.count("Hannah Harvest") == 1


def test_detect_adds_known_npc_via_single_word(tmp_path, monkeypatch):
    """A known NPC mentioned by single word (alias) IS added to scene_npcs.

    Pass 1 of _detect_narrative_npcs checks single Title Case words against the
    alias table. "Kendra" resolves to "Kendra Deverin", so she is tracked even
    when her full name appears (the word "Kendra" triggers the match first).
    This ensures known NPCs mentioned only by first name are not silently dropped
    from scene tracking.
    """
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    _make_npc_dir(tmp_path, "kendra_deverin",
                  "# Kendra Deverin\n**Aliases:** kendra\n")
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._detect_narrative_npcs("Kendra Deverin smiles from the steps.", session)

    # Kendra resolved to her canonical name via the alias table (Pass 1)
    assert "Kendra Deverin" in session.scene_npcs
    assert session.scene_npcs.count("Kendra Deverin") == 1  # not duplicated by Pass 2


def test_detect_skips_exclude_words(tmp_path, monkeypatch):
    """Pairs containing title/place words are not added."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._detect_narrative_npcs(
        "Mayor Deverin waves. Sheriff Hemlock watches. The Festival Square is full.",
        session,
    )

    assert not any(
        name in session.scene_npcs
        for name in ("Mayor Deverin", "Sheriff Hemlock", "Festival Square")
    )


def test_detect_skips_short_sentence_starters(tmp_path, monkeypatch):
    """2-char capitalised words like 'As', 'He', 'In' never form a match."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._detect_narrative_npcs(
        "As Kendra speaks you notice her bearing. He Smiles warmly.",
        session,
    )

    assert not any("As " in name or "He " in name for name in session.scene_npcs)


def test_detect_no_duplicate_on_second_call(tmp_path, monkeypatch):
    """Calling detection twice with the same name adds it only once."""
    import api.session_manager as sm
    sm = _sm_setup(tmp_path, monkeypatch)
    session = sm.create_session(1, "qwen3:4b", dev_mode=True)

    sm._detect_narrative_npcs("Hannah Harvest greets Vanx.", session)
    sm._detect_narrative_npcs("Hannah Harvest is still here.", session)

    assert session.scene_npcs.count("Hannah Harvest") == 1

