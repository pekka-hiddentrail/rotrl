# Exploratory Tests — NPC System

Spec: specs/npc-system.feature

**What automated tests cover:** `NpcIndex` singleton, `npc_dir_for`, stub creation, delta write
functions — all with temp directories. Live Playwright coverage in `ui/e2e/live-flows.spec.ts`
boots a real session, asks the LLM to generate a uniquely named NPC, verifies the dot-prefixed
directory, then clicks Purge NPCs and verifies removal.

**Pre-requisites:** `python dev.py --skip-tests` — stack running with real disk state.

---

## Chain A — Delta write to known NPC  <!-- AC-003, AC-004 -->

1. Boot a session.
2. Send: `I find Belor Hemlock at the garrison and ask him about the goblin raids.`
3. Open `adventure_path/01_npcs/belor_hemlock/session_NNN.md`.
4. ✔ A `%%DELTA%%` block was appended with the current session number and a turn count.
5. ✔ The `knowledge:` lines contain readable prose (not garbled JSON).
6. Send a second turn mentioning Belor: `I press Hemlock on whether Nualia is involved.`
7. ✔ A second delta block was appended to the same file (not a new file).

---

## Chain B — Auto-stub creation for new NPC  <!-- AC-006 -->

1. Send: `I walk over to the elderly woman selling amulets near the fountain and introduce myself.
   Her name is Marta Hask.`
2. Wait 5 seconds.
3. ✔ A directory `.marta_hask/` (or similar slug) exists under `adventure_path/01_npcs/`.
4. ✔ `base.md` contains at least `name:`, `role:`, and `appearance:` fields with non-empty values.
5. ✔ Directory has the dot prefix (session NPC).

---

## Chain C — NPC promotion  <!-- AC-001, AC-002 -->

1. After Chain B, rename `.marta_hask/` → `marta_hask/` in the file system.
2. End the session, boot a new one.
3. Send: `I look for Marta Hask at the fountain again.`
4. ✔ Intent bar shows `marta_hask` (or her name) as a detected NPC.
5. ✔ Her profile was injected into the system prompt (visible in dev mode).

---

## Chain D — Purge session NPCs  <!-- AC-005 -->

1. Without an active session, confirm at least one dot-prefixed directory exists under `01_npcs/`.
2. Click Purge NPCs in the header.
3. ✔ Inline confirm appears: "Purge session NPCs? Yes / No".
4. Click Yes.
5. ✔ Toast notification shows e.g. "2 session NPC directories removed."
6. ✔ Dot-prefixed directories are gone; `belor_hemlock/`, `ameiko_kaijitsu/` etc. are untouched.
7. Click Purge NPCs again (nothing to purge).
8. ✔ Toast shows "0 session NPC directories removed." (no error).
