# Persistence Handling Rules

## Authority

This document defines **mandatory rules** for how persistence is recorded, interpreted, and applied in the campaign world.

These rules are **binding** for the GM agent and override improvisation where conflicts arise.

Persistence exists to ensure:

* World continuity
* Consequence without railroading
* Player agency with lasting impact


## Core Definitions

### Persistence Entry

A persistence entry is a **single, atomic record** of a change to the world state caused by player action, inaction, or collateral consequence.

### Persistent State

The accumulated result of all persistence entries affecting a location, NPC, faction, or belief.


## When to Create a Persistence Entry

A persistence entry **MUST** be created when ANY of the following occur:

1. An NPC with a name **dies, disappears, or is publicly discredited**
2. A settlement suffers **civilian harm, destruction, or public fear**
3. A threat is **partially resolved** or **left unresolved**
4. PCs gain or lose **public trust**
5. A location is **changed, damaged, sanctified, or corrupted**
6. Information that *could have been learned* is missed or ignored

If uncertain, **create the entry**.


## When NOT to Create a Persistence Entry

Do NOT create entries for:

* Routine combat victories with no witnesses
* Temporary conditions resolved within the same session
* Purely mechanical gains (XP, gold, items)
* Private PC-only knowledge unless it leaks later


## Entry Atomicity Rule

Each persistence entry must represent **one change**.

Do NOT:

* Bundle multiple causes
* Track multiple domains unless directly linked

If multiple effects occur, create **multiple entries**.


## Temporal Scope

Persistence entries are:

* **Permanent** unless explicitly resolved by later play
* **Non-retroactive** (never rewritten)
* **Forward-propagating** into future books

Entries may be *superseded*, never erased.


## Resolution Rules

A persistence entry is considered **resolved** only when:

* PCs take deliberate action addressing it
* The narrative explicitly closes the consequence

Resolution creates a **new entry** referencing the old one.


## GM Application Rules

* Never explain persistence mechanically to players
* Show persistence through behavior, absence, cost, or resistance
* Prefer callbacks over exposition
* Review relevant entries before revisiting a location

Persistence is not punishment.

Persistence is memory.

* **PERSISTENCE_LEDGER.md** → [adventure_path/04_persistence/](adventure_path/04_persistence/)

