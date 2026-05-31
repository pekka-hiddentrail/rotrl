# Exploratory Tests — Character Sidebar and Sheet

Spec: specs/character-system.feature

**What automated tests cover:** `GET /api/characters` returns 200, list, correct IDs, required
fields, 404 when index missing; sidebar action menu open/close, Set Active / Clear Active, Open
Sheet callbacks, halo class, loading state; JSON files for all three player characters pass full
field-presence and sanity checks.

**Pre-requisites:** `python dev.py --skip-tests` — stack running at http://localhost:5173.

---

## Chain A — Characters load before boot  <!-- AC-001, AC-002 -->

1. Open `http://localhost:5173` without clicking Boot Session.
2. ✔ All three character portraits appear in the left sidebar immediately.
3. ✔ No "Character data:" error bar appears.
4. ✔ Each character's name label is visible below their avatar.
5. ✔ HP bars are visible and coloured (green at full HP).

---

## Chain B — API unavailable at page load  <!-- AC-001 -->

1. Start only Vite (leave the Python API stopped): `cd ui && npm run dev`.
2. Open `http://localhost:5173`.
3. ✔ A "Character data: TypeError: Failed to fetch" error bar appears.
4. Start the API: `python -m uvicorn api.main:app --port 8000`.
5. Refresh the browser.
6. ✔ Characters load correctly; error bar is gone.

---

## Chain C — Live JSON edit reflects on refresh  <!-- AC-001, AC-003 -->

1. Open `ui/public/data/player_01.json`, set `hp.current` to `2`, save.
2. Refresh the browser.
3. ✔ That character's HP bar is red (< 33%).
4. Open the character sheet for that character.
5. ✔ HP shows `2 / <max>`.
6. Restore the original `hp.current` value and refresh again.

---

## Chain D — Malformed character JSON  <!-- AC-001 -->

1. Open `ui/public/data/player_02.json`, break the JSON (e.g. add a stray comma), save.
2. Refresh the browser.
3. ✔ A "Character data: HTTP 500" error bar appears; sidebar is empty.
4. Restore the file and refresh. ✔ All characters load; error bar gone.

---

## Chain E — Sheet completeness  <!-- AC-004, AC-005, AC-006 -->

1. Click a character avatar → click Open Sheet.
2. Scroll through every section: Abilities, Saves, Skills, Weapons, Spells, Inventory.
3. ✔ No section shows `undefined`, `null`, or `[object Object]`.
4. ✔ HP bar is visible and coloured.
5. Press Escape or click the close button.
6. ✔ Sheet closes; background UI is still interactive.

---

## Chain F — Active speaker in chat  <!-- AC-007, AC-008, AC-009, AC-010, AC-011 -->

1. Click a character avatar → click Set Active.
2. ✔ Halo/ring appears on that avatar.
3. ✔ Input bar shows "Speaking as \<Name\>" badge.
4. Type `I ask Ameiko about the raid.` and send.
5. ✔ Player bubble in chat shows `@Yanyeeku: "I ask Ameiko about the raid."`.
6. Click the same avatar → click Clear Active.
7. Type `I look around.` and send.
8. ✔ Player bubble shows `I look around.` with no prefix.

---

## Chain G — Sheet open during streaming  <!-- AC-004 -->

1. Send a turn that will produce a long GM response.
2. Immediately click a character avatar → Open Sheet while tokens are streaming.
3. ✔ Sheet opens normally.
4. ✔ Tokens continue to appear in the background; no freeze or error.

---

## Chain H — HP bar colour (requires JSON edit)  <!-- AC-003 -->

1. Open `ui/public/data/player_01.json`, set `hp.current` to 2 (low HP), save.
2. Refresh the browser, open the character sheet.
3. ✔ HP bar is red.
4. Restore the value.

---

## Chain I — Action menu placement  <!-- AC-012 -->

1. Click a character avatar.
2. ✔ The two-action menu (Set Active / Open Sheet) opens to the right of the avatar,
   not below it and not off-screen.
