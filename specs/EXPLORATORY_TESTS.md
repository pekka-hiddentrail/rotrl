# Exploratory Test Notes

**Features**: action-economy, click-to-target, enemy-action-type, enemy-turn, pc-combat-turn, magic-spell-system
**Test type**: Manual / exploratory (pre-release checklist)

---

## How to use

Run these checks manually against a live dev session (`./start_backend.ps1` + `./start_ui.ps1`).
Tick each item once verified. Flag unexpected behaviour as a new bug.

---

## 1 — action-economy

| # | Scenario | Expected |
|---|----------|----------|
| AE-EX-001 | Open app outside combat | Standard/Move/Full-Round/Swift/Free buttons are NOT visible |
| AE-EX-002 | Enter combat; PC's turn | All five action-type buttons appear above the text input |
| AE-EX-003 | Click "Standard" | Button lights up (active style); Move and Full-Round stay unlit |
| AE-EX-004 | Click "Standard" again | Button unlit (toggle off) |
| AE-EX-005 | Click "Standard", then "Move" | Both are lit; Full-Round is NOT lit |
| AE-EX-006 | Click "Full-Round" with Standard+Move active | Full-Round lights up; Standard and Move unlight |
| AE-EX-007 | Click "Swift" while "Full-Round" is active | Both Full-Round and Swift are lit |
| AE-EX-008 | Click "Free" while "Standard" and "Move" are active | All three are lit |
| AE-EX-009 | Select "Standard", type "I attack the goblin", submit | Network payload contains `"action_type_hints":["standard"]` |
| AE-EX-010 | After submitting, check buttons | All buttons are unlit (reset) |
| AE-EX-011 | PC submits; turn advances to enemy | Buttons disappear |
| AE-EX-012 | Select "Standard" with "use ability: inspire" text → submit | Backend narrates `use_ability`, NOT overridden to `attack` |
| AE-EX-013 | Select "Move", type a zone destination → submit | PC zone updates in combat tracker; no attack queued |

---

## 2 — click-to-target

| # | Scenario | Expected |
|---|----------|----------|
| CTT-EX-001 | It is the PC's turn; click a live enemy row | Row highlights with targeted style; 🎯 badge appears |
| CTT-EX-002 | Click the same row again | Row un-highlights; badge disappears |
| CTT-EX-003 | With target selected, submit action | Network payload `target_hint` == selected enemy name |
| CTT-EX-004 | After submit | Target badge is gone; no lingering selection |
| CTT-EX-005 | Click a dead/unconscious enemy row | Nothing happens; no badge |
| CTT-EX-006 | It is the enemy's turn; click any enemy row | Nothing happens; no badge |
| CTT-EX-007 | PC submits with no target selected | `target_hint` is null in payload; backend infers target |
| CTT-EX-008 | Turn advances to next PC | Previous target selection is cleared |

---

## 3 — enemy-action-type

| # | Scenario | Expected |
|---|----------|----------|
| EAT-EX-001 | Enemy executes a standard attack | Action card in chat shows attack card with attacker/target/roll |
| EAT-EX-002 | Enemy delays (no attack) | Narrative appears, no attack result card |
| EAT-EX-003 | Dev mode ON, trigger enemy turn | Raw `%%ACTION%%` block visible with `action_type:` field |
| EAT-EX-004 | Enemy uses an ability | Narrative appears; action card has appropriate `action_type` |

---

## 4 — enemy-turn

| # | Scenario | Expected |
|---|----------|----------|
| ET-EX-001 | Click "Enemy Turn" during enemy's turn | Streaming dots appear; narrative populates in chat |
| ET-EX-002 | HP loss on enemy hit | CombatPanel HP bar updates; HP number changes |
| ET-EX-003 | Click "Enemy Turn" while PC attack is pending | Button is disabled / 409 error shown |
| ET-EX-004 | Enemy attack kills a PC | PC row shows "dying" status |
| ET-EX-005 | Click "End Combat" | Closing narrative streams; CombatPanel disappears after stream |
| ET-EX-006 | Nauseated enemy's turn | Enemy narration reflects limitation; single move only |
| ET-EX-007 | LLM hallucinates a weapon | Warning log entry; resolved attack uses profile weapon |

---

## 5 — pc-combat-turn

| # | Scenario | Expected |
|---|----------|----------|
| PCT-EX-001 | PC's turn; type "I attack the goblin" → submit | Dice tray banner appears (attack_request); no narrative yet |
| PCT-EX-002 | Roll the d20 in dice tray | Input field shows roll; confirm resolves the attack |
| PCT-EX-003 | After dice resolution | Narrative populates; action card shows hit/miss |
| PCT-EX-004 | After narration | Turn auto-advances; CombatPanel updates current actor |
| PCT-EX-005 | Type ambiguous text "I attack!" | Backend falls back to first weapon, random enemy |
| PCT-EX-006 | Type weapon name not in profile | Falls back to equipped weapon; attack proceeds |
| PCT-EX-007 | PC HP drops below 33% | HP descriptor "badly wounded" in briefing (check dev logs) |

---

## 6 — magic-spell-system

| # | Scenario | Expected |
|---|----------|----------|
| MSS-EX-001 | Caster PC's turn; type "I cast Force Bolt at the goblin" | Damage roll banner appears (damage_request, NOT attack_request) |
| MSS-EX-002 | Roll damage dice | Damage applied; goblin HP decreases in CombatPanel |
| MSS-EX-003 | After damage resolved | Narrative streams; action card has `is_spell: true` |
| MSS-EX-004 | After narration | Turn auto-advances |
| MSS-EX-005 | Type "Force Bolt the goblin" (no "cast" keyword) | Still detected as spell; damage_request emitted |
| MSS-EX-006 | Non-caster PC types "Force Bolt" | Treated as text; no spell intent; weapon attack queued |
| MSS-EX-007 | Buff/utility spell with no damage (e.g. Shield) | No attack_request or damage_request; narrates as use_ability |
| MSS-EX-008 | Select "Standard" action button then type spell name | action_type NOT overridden to "attack"; spell cast proceeds |
