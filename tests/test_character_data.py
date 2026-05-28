"""
Smoke tests for UI character JSON data (ui/public/data/).

Validates that:
  - characters.json is valid JSON and lists known player IDs
  - every referenced player file exists and parses
  - each player file contains all fields the CharacterData TypeScript type requires
  - numeric fields are sane (level >= 1, hp.max > 0, etc.)
  - no broken cross-references within a file
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "ui" / "public" / "data"

# Required top-level string fields from CharacterData interface
REQUIRED_STRING_FIELDS = [
    "id", "portrait", "color", "rune",
    "name", "player", "race", "class", "archetype",
    "alignment", "deity", "appearance",
    "initiative", "speed", "bab",
]

# Required top-level object/array fields
REQUIRED_OBJECT_FIELDS = [
    "hp", "ac", "abilities", "saves", "skills",
    "feats", "weapons", "spells", "inventory",
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def character_ids() -> list[str]:
    index = DATA_DIR / "characters.json"
    assert index.exists(), f"Missing {index}"
    ids = json.loads(index.read_text(encoding="utf-8"))
    assert isinstance(ids, list), "characters.json must be a JSON array"
    return ids


@pytest.fixture(scope="module")
def all_characters(character_ids) -> list[dict]:
    chars = []
    for cid in character_ids:
        path = DATA_DIR / f"{cid}.json"
        assert path.exists(), f"characters.json references '{cid}' but {path.name} is missing"
        data = json.loads(path.read_text(encoding="utf-8"))
        chars.append(data)
    return chars


# ── Index file ────────────────────────────────────────────────────────────────

def test_characters_json_exists():
    assert (DATA_DIR / "characters.json").exists()


def test_characters_json_is_non_empty_list(character_ids):
    assert len(character_ids) > 0


def test_character_ids_are_strings(character_ids):
    for cid in character_ids:
        assert isinstance(cid, str) and cid.strip(), \
            f"All entries in characters.json must be non-empty strings, got: {cid!r}"


def test_all_referenced_files_exist(character_ids):
    for cid in character_ids:
        assert (DATA_DIR / f"{cid}.json").exists(), \
            f"Missing file: {cid}.json"


def test_no_duplicate_ids(character_ids):
    assert len(character_ids) == len(set(character_ids)), \
        "characters.json contains duplicate IDs"


# ── Per-character field presence ──────────────────────────────────────────────

@pytest.mark.parametrize("field", REQUIRED_STRING_FIELDS)
def test_required_string_field_present(all_characters, field):
    for char in all_characters:
        assert field in char, \
            f"Character '{char.get('id', '?')}' missing field '{field}'"
        assert isinstance(char[field], str), \
            f"'{field}' in '{char.get('id')}' must be a string"
        assert char[field].strip(), \
            f"'{field}' in '{char.get('id')}' must not be blank"


@pytest.mark.parametrize("field", REQUIRED_OBJECT_FIELDS)
def test_required_object_field_present(all_characters, field):
    for char in all_characters:
        assert field in char, \
            f"Character '{char.get('id', '?')}' missing field '{field}'"


# ── id consistency ────────────────────────────────────────────────────────────

def test_id_matches_filename(character_ids):
    for cid in character_ids:
        data = json.loads((DATA_DIR / f"{cid}.json").read_text(encoding="utf-8"))
        assert data.get("id") == cid, \
            f"{cid}.json has id='{data.get('id')}' but expected '{cid}'"


# ── HP block ─────────────────────────────────────────────────────────────────

def test_hp_fields(all_characters):
    for char in all_characters:
        hp = char["hp"]
        for key in ("current", "max", "hitDie", "baseDieRoll", "conBonus"):
            assert key in hp, f"hp.{key} missing in '{char['id']}'"
        assert hp["max"] > 0, f"hp.max must be > 0 in '{char['id']}'"
        assert hp["current"] <= hp["max"], \
            f"hp.current > hp.max in '{char['id']}'"
        assert hp["hitDie"].startswith("d"), \
            f"hp.hitDie must start with 'd' in '{char['id']}'"


# ── Level ─────────────────────────────────────────────────────────────────────

def test_level_is_positive_integer(all_characters):
    for char in all_characters:
        assert isinstance(char["level"], int) and char["level"] >= 1, \
            f"level must be int >= 1 in '{char['id']}'"


# ── Abilities ────────────────────────────────────────────────────────────────

EXPECTED_ABILITIES = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}

def test_all_six_abilities_present(all_characters):
    for char in all_characters:
        names = {a["name"] for a in char["abilities"]}
        missing = EXPECTED_ABILITIES - names
        assert not missing, \
            f"'{char['id']}' missing abilities: {missing}"


def test_ability_scores_in_range(all_characters):
    for char in all_characters:
        for ab in char["abilities"]:
            score = ab["score"]
            assert 1 <= score <= 30, \
                f"Ability score {ab['name']}={score} out of range in '{char['id']}'"


# ── Saves ────────────────────────────────────────────────────────────────────

EXPECTED_SAVES = {"Fortitude", "Reflex", "Will"}

def test_three_saves_present(all_characters):
    for char in all_characters:
        names = {s["name"] for s in char["saves"]}
        assert names == EXPECTED_SAVES, \
            f"'{char['id']}' has unexpected saves: {names}"


# ── Inventory wealth ─────────────────────────────────────────────────────────

def test_wealth_fields(all_characters):
    for char in all_characters:
        wealth = char["inventory"]["wealth"]
        for coin in ("pp", "gp", "sp", "cp"):
            assert coin in wealth, f"wealth.{coin} missing in '{char['id']}'"
            assert isinstance(wealth[coin], (int, float)) and wealth[coin] >= 0, \
                f"wealth.{coin} must be non-negative number in '{char['id']}'"


# ── Weapons ──────────────────────────────────────────────────────────────────

def test_weapon_required_fields(all_characters):
    required = {"display", "name", "type", "atk", "dmg", "crit"}
    for char in all_characters:
        for w in char["weapons"]:
            missing = required - set(w.keys())
            assert not missing, \
                f"Weapon in '{char['id']}' missing fields: {missing}"


# ── Spells ───────────────────────────────────────────────────────────────────

def test_spells_has_concentration_and_list(all_characters):
    for char in all_characters:
        spells = char["spells"]
        assert "concentration" in spells, f"spells.concentration missing in '{char['id']}'"
        assert "list" in spells, f"spells.list missing in '{char['id']}'"
        assert isinstance(spells["list"], list), \
            f"spells.list must be an array in '{char['id']}'"
