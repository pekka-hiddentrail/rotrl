Feature: Zone-based Combat — PoC (M1-PoC)

  Combatants have a named zone read from the event file. The zone is stored on
  the Combatant, serialized in combat state, and displayed in the CombatPanel.
  No adjacency or range enforcement in this tier — data flow only.

  Background:
    Given the event file contains a ## Combatants table with a Zone column

  # ── Backend: data model ──────────────────────────────────────────────────────

  Scenario: ZC-001 — Combatant.zone defaults to "default"
    When a Combatant is created without specifying a zone
    Then combatant.zone equals "default"

  Scenario: ZC-002 — Zone column parsed from Combatants table
    Given an event file table row "| Goblin Warrior 1 | 5 | 16 | +6 | Center |"
    When _parse_event_combatants processes the table
    Then the parsed entry for "goblin warrior 1" has zone "Center"

  Scenario: ZC-002b — Missing Zone column falls back to "default"
    Given an event file table with no Zone column
    When _parse_event_combatants processes the table
    Then every parsed entry has zone "default"

  Scenario: ZC-002c — Parenthetical zone value "(random)" falls back to "default"
    Given an event file table row with zone "(random)"
    When _parse_event_combatants processes the table
    Then the parsed entry has zone "default"

  Scenario: ZC-003 — Zone serialized in combat state
    Given a CombatState with a Combatant whose zone is "Alleyway"
    When _serialize_combat_state is called
    Then the combatant dict in the result contains "zone": "Alleyway"

  Scenario: ZC-003b — Zone "default" serialized as "default"
    Given a CombatState with a Combatant whose zone is "default"
    When _serialize_combat_state is called
    Then the combatant dict in the result contains "zone": "default"

  Scenario: ZC-004 — Zone seeded from event file at round 1
    Given pending_combatants contains an entry with zone "Market Stalls"
    When _seed_round1_combatants runs
    Then the resulting Combatant has zone "Market Stalls"

  # ── Frontend: display ────────────────────────────────────────────────────────

  Scenario: ZC-005 — CombatPanel renders zone badge when zone is set
    Given a combatant with zone "Cathedral Stairs"
    When the CombatPanel renders that combatant row
    Then a zone badge with text "Cathedral Stairs" is visible below the HP bar

  Scenario: ZC-006 — CombatPanel omits zone badge when zone is "default"
    Given a combatant with zone "default"
    When the CombatPanel renders that combatant row
    Then no zone badge is rendered for that combatant
