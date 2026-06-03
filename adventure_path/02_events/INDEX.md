# Event Index — `adventure_path/02_events/`

Events are injected into the LLM at runtime when triggered. Each file is self-contained — it includes everything the GM needs for that event.

---

## How Events Work

- The `<!-- INJECT -->` marker in each file is the injection boundary. Everything below it is sent to the LLM.
- Events chain via `%%EVENT%% event_name` written by the LLM at the end of each scene.
- Type determines which template was used: **combat** or **social/aftermath**.

---

## Act I — The Swallowtail Festival

The complete event chain for Act I, from the opening ceremony through the goblin raid and aftermath.

### Pre-Combat: The Festival

| File | Type | Trigger | Leads to |
|------|------|---------|----------|
| [welcoming_speeches.md](welcoming_speeches.md) | social | Act start — Autumnal Equinox, morning | `festival_social_phase` |
| [festival_social_phase.md](festival_social_phase.md) | social | Speeches complete, festival open | `cathedral_alarm` |
| [cathedral_alarm.md](cathedral_alarm.md) | narrative | Sunset — consecration begins | `goblin_attack_begins` |

### The Goblin Raid

| File | Type | Trigger | Leads to |
|------|------|---------|----------|
| [goblin_attack_begins.md](goblin_attack_begins.md) | combat | Thunderstone crack / alarm bell | `first_wave_repelled` |
| [first_wave_repelled.md](first_wave_repelled.md) | social | All first-wave goblins dead/fled | `fire_phase_begins` |
| [fire_phase_begins.md](fire_phase_begins.md) | combat | After the first-wave breather | `second_wave_repelled` |
| [second_wave_repelled.md](second_wave_repelled.md) | social | All fire-phase goblins dead/fled | `goblin_cavalry_attack_begins` |
| [goblin_cavalry_attack_begins.md](goblin_cavalry_attack_begins.md) | combat | After the second-wave breather | `attack_repelled` |
| [attack_repelled.md](attack_repelled.md) | aftermath | Goblin commando killed | — end of act — |

### Key NPCs across the full chain

| NPC | First appears | Notes |
|-----|--------------|-------|
| Mayor Kendra Deverin | `welcoming_speeches` | Opens the festival; available during social phase |
| Sheriff Hemlock | `welcoming_speeches` | On duty throughout; warm to PCs after raid |
| Father Zantus | `welcoming_speeches` | Tells the Desna parable at noon; offers healing after wave 1 |
| Cyrdak Drokkus | `welcoming_speeches` | Substitutes for absent Lonjiku; easy social contact |
| Ameiko Kaijitsu | `festival_social_phase` | Lunch beat; offers lodging after raid |
| Aldern Foxglove | `festival_social_phase` (afternoon) + `goblin_cavalry_attack_begins` | First met at festival; gratitude seeds Act II hook |

### Civilian family

The family of four (Center zone, `goblin_attack_begins`) is the moral pressure point of Wave 1. Rescue outcome feeds the `CIVILIAN_DEATHS` delta in `attack_repelled`.

### Bestiary references

| Creature | File |
|----------|------|
| Goblin Warrior | `adventure_path/09_bestiary/goblin.md` |
| Goblin Warchanter | `adventure_path/09_bestiary/goblin_warchanter.md` |
| Goblin Commando | `adventure_path/09_bestiary/goblin_commando.md` |
| Goblin Dog | `adventure_path/09_bestiary/goblin_dog.md` |

---

## Templates

| File | Use for |
|------|---------|
| [_EVENT_TEMPLATE.md](_EVENT_TEMPLATE.md) | Combat events — zones, combatants, tactics, appearance, taunts |
| [_SOCIAL_TEMPLATE.md](_SOCIAL_TEMPLATE.md) | Social / narrative / aftermath events — scene, NPCs, branches |
