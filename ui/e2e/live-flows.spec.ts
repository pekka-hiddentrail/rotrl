import { existsSync, readdirSync, readFileSync, rmSync } from 'node:fs'
import path from 'node:path'
import { test, expect, type Locator, type Page } from '@playwright/test'

const repoRoot = path.resolve(process.cwd(), '..')
const sessionNpcRoot = path.join(repoRoot, 'adventure_path', '01_npcs')
const locationRoot = path.join(repoRoot, 'adventure_path', '03_locations')

function dotNpcDirs() {
  return readdirSync(sessionNpcRoot, { withFileTypes: true })
    .filter(entry => entry.isDirectory() && entry.name.startsWith('.'))
    .map(entry => entry.name)
    .sort()
}

function dotNpcPath(dirName: string) {
  return path.join(sessionNpcRoot, dirName)
}

function readNpcBase(dirName: string) {
  const basePath = path.join(dotNpcPath(dirName), 'base.md')
  return existsSync(basePath) ? readFileSync(basePath, 'utf8') : ''
}

function locationDirs() {
  return readdirSync(locationRoot, { withFileTypes: true })
    .filter(entry => entry.isDirectory())
    .map(entry => entry.name)
    .sort()
}

function locationPath(dirName: string) {
  return path.join(locationRoot, dirName)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Switch to Anthropic / Haiku / Dev mode before booting. */
async function configureHaiku(page: Page) {
  await page.locator('.provider-btn', { hasText: 'Claude' }).click()
  await page.getByLabel('Dev').check()
  await page.getByLabel('Model').selectOption('claude-haiku-4-5-20251001')
}

/** Click Boot and wait for the session badge to appear. */
async function bootSession(page: Page) {
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible({ timeout: 20_000 })
}

/** Fill the input, send, then wait until the textbox re-enables (stream done). */
async function sendTurnAndWait(page: Page, text: string) {
  const input = page.getByRole('textbox')
  await input.fill(text)
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(input).toBeEnabled({ timeout: 90_000 })
}

async function visibleBox(locator: Locator, label: string) {
  await expect(locator, `${label} should be visible`).toBeVisible()
  const box = await locator.boundingBox()
  expect(box, `${label} should have a layout box`).not.toBeNull()
  return box!
}

// ---------------------------------------------------------------------------
// L1–L4  — shared session: boot once, send one turn, run all format checks
//
// Dev mode is ON so every %%SECTION%% marker streams through to the GM bubble,
// making them directly assertable in the DOM without log scraping.
// ---------------------------------------------------------------------------

test.describe.serial('L1-L4 — live session and response format', () => {
  let page: Page
  let sessionId = ''

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()

    // Capture the session ID from the outgoing /turn request URL before any
    // response arrives — no mocking, pure observation.
    page.on('request', req => {
      const m = req.url().match(/\/api\/sessions\/([^/]+)\/turn/)
      if (m && !sessionId) sessionId = m[1]
    })

    await page.goto('/')
    await configureHaiku(page)
    await bootSession(page)
    await sendTurnAndWait(
      page,
      'I approach Father Abstalar Zantus at the cathedral and tell him I will help watch the crowd during the ceremony.',
    )
  })

  test.afterAll(async () => {
    await page.close()
  })

  // L1 — session badge confirms Haiku is active and no errors surfaced
  // Covers: session-boot.feature AC-001, AC-002
  test('L1 — session badge shows Haiku, no error bar', async () => {
    await expect(page.getByText(/haiku/i)).toBeVisible()
    await expect(page.locator('.error-bar')).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'End Session' })).toBeVisible()
  })

  // L2 — LLM followed the format: %%NARRATIVE%% must appear in the GM bubble
  // Covers: response-parsing.feature AC-001
  test('L2 — GM bubble contains %%NARRATIVE%%', async () => {
    await expect(
      page.locator('.bubble-gm').filter({ hasText: '%%NARRATIVE%%' }),
    ).toBeVisible()
  })

  // L3 — %%DELTAS%% section also present (both required headers = format intact)
  // Covers: response-parsing.feature AC-001
  test('L3 — GM bubble contains %%DELTAS%%', async () => {
    await expect(
      page.locator('.bubble-gm').filter({ hasText: '%%DELTAS%%' }),
    ).toBeVisible()
  })

  // L4 — session log written to disk and accessible via API; contains the markers
  // Covers: session-logging.feature AC-001, AC-002
  test('L4 — log API returns 200 and contains %%NARRATIVE%%', async () => {
    expect(sessionId, 'session ID was not captured from /turn request').toBeTruthy()
    const response = await page.request.get(`/api/sessions/${sessionId}/log`)
    expect(response.status()).toBe(200)
    const body = await response.text()
    expect(body).toContain('%%NARRATIVE%%')
    expect(body.length).toBeGreaterThan(50)
  })
})

// ---------------------------------------------------------------------------
// L5 — full end-session lifecycle with real LLM recap
//
// Sends one turn then triggers "Generate recap" from the dev-mode dialog.
// Asserts the session closes cleanly and the session number increments.
// ---------------------------------------------------------------------------

// Covers: session-end-recap.feature AC-001, AC-002, AC-003
test('L5 — end session writes recap and returns to pre-boot', async ({ page }) => {
  await page.goto('/')
  await configureHaiku(page)
  await bootSession(page)
  await sendTurnAndWait(page, 'I greet the innkeeper.')

  // Dev mode: End Session shows a confirmation dialog
  await page.getByRole('button', { name: 'End Session' }).click()
  await expect(page.getByText('End session?')).toBeVisible()
  await page.getByRole('button', { name: 'Generate recap' }).click()

  // Recap LLM call — give it generous time
  await expect(page.getByText(/Session saved/)).toBeVisible({ timeout: 90_000 })

  // After the 1.8 s pause the app clears state and returns to pre-boot
  await expect(page.getByRole('button', { name: 'Boot Session' })).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('.error-bar')).not.toBeVisible()

  // Session number must have incremented
  await expect(page.getByLabel('Session')).toHaveValue('2')
})

// ---------------------------------------------------------------------------
// L6 — character sidebar rendered from real /api/characters (no LLM needed)
//
// Validates that the backend serves valid character JSON and the sidebar
// renders it — HP bar and party label visible on page load.
// ---------------------------------------------------------------------------

// Covers: character-system.feature AC-001
test('L6 — character sidebar renders from real /api/characters', async ({ page }) => {
  await page.goto('/')

  // At least one character avatar must appear
  await expect(page.locator('.char-icon-btn').first()).toBeVisible({ timeout: 10_000 })

  // HP bar rendered (colour driven by real HP values from the JSON)
  await expect(page.locator('.char-hp-bar').first()).toBeVisible()

  // Sidebar label present
  await expect(page.locator('.sidebar-label')).toHaveText('Party')
})

// ---------------------------------------------------------------------------
// L7-L8 - generated NPC lifecycle
//
// Uses the live app and real backend side effects: one test asks the model to
// create a new named NPC, then the next test purges that session NPC directory.
// ---------------------------------------------------------------------------

test.describe.serial('L7-L8 - live generated NPC lifecycle', () => {
  let generatedNpcDir = ''
  let initialLocationDirs = new Set<string>()

  test.afterAll(() => {
    if (generatedNpcDir && existsSync(dotNpcPath(generatedNpcDir))) {
      rmSync(dotNpcPath(generatedNpcDir), { recursive: true, force: true })
    }
    for (const dirName of locationDirs()) {
      if (!initialLocationDirs.has(dirName)) {
        rmSync(locationPath(dirName), { recursive: true, force: true })
      }
    }
  })

  // Covers: npc-system.feature AC-003, AC-004, AC-005
  test('L7 - %%GENERATE%% creates a dot-prefixed NPC directory', async ({ page }) => {
    const before = new Set(dotNpcDirs())
    initialLocationDirs = new Set(locationDirs())
    const newNpcName = 'Tavra Quillmark'

    await page.goto('/')
    await configureHaiku(page)
    await bootSession(page)
    await sendTurnAndWait(
      page,
      [
        `At the festival map stall, I meet a nervous local seller who introduces herself as ${newNpcName}.`,
        `${newNpcName} offers me a hand-drawn map of the Lost Coast, and I ask which landmark she recommends visiting first.`,
      ].join(' '),
    )

    await expect(page.locator('.bubble-gm').filter({ hasText: '%%GENERATE%%' })).toBeVisible({
      timeout: 60_000,
    })

    await expect
      .poll(
        () => dotNpcDirs().filter(dirName => !before.has(dirName)).length,
        { timeout: 15_000, message: 'waiting for generated NPC directory' },
      )
      .toBeGreaterThan(0)

    const createdDirs = dotNpcDirs().filter(dirName => !before.has(dirName))
    const matchingDirs = createdDirs.filter(dirName => readNpcBase(dirName).includes('Tavra Quillmark'))

    expect(matchingDirs, `created session NPC dirs: ${createdDirs.join(', ')}`).toHaveLength(1)
    generatedNpcDir = matchingDirs[0]

    const listed = await page.request.get('/api/npcs/session')
    expect(listed.status()).toBe(200)
    await expect(listed.json()).resolves.toMatchObject({
      npcs: expect.arrayContaining([generatedNpcDir.slice(1)]),
    })

    await page.getByRole('button', { name: 'End Session' }).click()
    await expect(page.getByText('End session?')).toBeVisible()
    await page.getByRole('button', { name: 'End without recap' }).click()
    await expect(page.getByRole('button', { name: 'Boot Session' })).toBeVisible({ timeout: 15_000 })
  })

  // Covers: npc-system.feature AC-006
  test('L8 - Purge NPCs removes the generated NPC directory', async ({ page }) => {
    test.skip(!generatedNpcDir, 'L7 did not create a generated NPC directory')

    const unrelatedSessionDirs = dotNpcDirs().filter(dirName => dirName !== generatedNpcDir)
    test.skip(
      unrelatedSessionDirs.length > 0,
      `Refusing to purge unrelated session NPC dirs: ${unrelatedSessionDirs.join(', ')}`,
    )

    await page.goto('/')
    await page.getByRole('button', { name: /Tools/ }).click()
    await expect(page.getByRole('button', { name: /Purge Session NPCs/ })).toBeVisible()
    await page.getByRole('button', { name: /Purge Session NPCs/ }).click()
    await expect(page.getByText('Purge session NPCs?')).toBeVisible()
    await page.getByRole('button', { name: 'Yes' }).click()

    await expect(page.getByText('1 session NPC directory removed.')).toBeVisible({ timeout: 10_000 })
    await expect
      .poll(() => existsSync(dotNpcPath(generatedNpcDir)), { timeout: 10_000 })
      .toBe(false)

    const listed = await page.request.get('/api/npcs/session')
    expect(listed.status()).toBe(200)
    await expect(listed.json()).resolves.toEqual({ npcs: [] })
  })
})

// ---------------------------------------------------------------------------
// L9-L12 - live event, combat, roll, and attack lifecycle
//
// Drives the goblin raid from event trigger through combat tracker, skill roll,
// and full PC attack-resolution flow (NPC auto-resolve → PC to-hit banner →
// optional damage roll → resume_combat LLM narrative).
// ---------------------------------------------------------------------------

test.describe.serial('L9-L12 - live goblin event, combat, roll, and attack flow', () => {
  let page: Page
  let initialSessionNpcDirs = new Set<string>()
  let initialLocationDirs = new Set<string>()

  test.beforeAll(async ({ browser }) => {
    initialSessionNpcDirs = new Set(dotNpcDirs())
    initialLocationDirs = new Set(locationDirs())
    page = await browser.newPage()
    await page.goto('/')
    await configureHaiku(page)
    await bootSession(page)
  })

  test.afterAll(async () => {
    if (!page.isClosed()) {
      await page.getByRole('button', { name: 'End Session' }).click().catch(() => undefined)
      await page.getByRole('button', { name: 'End without recap' }).click().catch(() => undefined)
      await page.close()
    }
    for (const dirName of dotNpcDirs()) {
      if (!initialSessionNpcDirs.has(dirName)) {
        rmSync(dotNpcPath(dirName), { recursive: true, force: true })
      }
    }
    for (const dirName of locationDirs()) {
      if (!initialLocationDirs.has(dirName)) {
        rmSync(locationPath(dirName), { recursive: true, force: true })
      }
    }
  })

  // Covers: event-injection.feature AC-001, session-state.feature AC-008
  test('L9 - live turn triggers goblin_attack_starts event', async () => {
    await sendTurnAndWait(
      page,
      [
        'The cathedral alarm bell rings and goblins become visible at the north edge of the festival square.',
        'This is the exact trigger for the goblin_attack_starts event.',
        'Write the event line exactly as %%EVENT%% goblin_attack_starts after the narrative and deltas.',
        'Do not start combat until my next action.',
      ].join(' '),
    )

    const gmBubble = page.locator('.bubble-gm').last()
    await expect(gmBubble).toContainText('%%EVENT%%', { timeout: 60_000 })
    await expect(gmBubble).toContainText('goblin_attack_starts')

    // session-state AC-008: state.json reflects the active event
    const statePath = path.join(repoRoot, 'sessions', 'session_001', 'state.json')
    await expect.poll(() => {
      try {
        const s = JSON.parse(readFileSync(statePath, 'utf8'))
        return s.events ?? []
      } catch { return [] }
    }, { timeout: 5_000 }).toContain('goblin_attack_starts')
  })

  // Covers: combat-tracker.feature AC-001, AC-004, AC-005, AC-006, session-state.feature AC-004
  // Covers: roll-initiatives.feature AC-008 (initiative_pending → banner → roll → CombatPanel)
  test('L10 - spotting goblins produces %%COMBAT%% round 1', async () => {
    await sendTurnAndWait(
      page,
      [
        'Do I spot any goblins?',
        'The goblin_attack_starts event is active, so start Wave 1 combat now if goblins are visible.',
        'Write a %%COMBAT%% block with round: 1 and the Wave 1 goblin combatants.',
        'Do not write a %%ATTACK%% block yet.',
      ].join(' '),
    )

    await expect(page.locator('.bubble-gm').last()).toContainText(/%%COMBAT%%\s*round:\s*1/, { timeout: 60_000 })

    // New flow (roll-initiatives.feature AC-008):
    // The goblin_attack_starts combat event is active, so the backend emits
    // "initiative_pending" instead of "combat_update". The CombatPanel stays
    // hidden until the player clicks "Roll for all combatants" in the DicePanel.
    await expect(page.locator('.initiative-banner')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.combat-panel')).not.toBeVisible()

    // Player triggers the initiative roll — DicePanel is still in right column at this point
    await page.getByRole('button', { name: /Roll for all combatants/i }).click()

    // After rolling, CombatPanel appears and DicePanel shifts left
    await expect(page.locator('.combat-panel')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('.initiative-banner')).not.toBeVisible()
    await expect(page.locator('.combat-round-badge')).toContainText(/Round\s+1/)
    await expect(page.locator('.combatant-name').filter({ hasText: /goblin/i }).first()).toBeVisible()

    const viewport = page.viewportSize()
    expect(viewport, 'viewport should be available for layout assertions').not.toBeNull()
    const combatBox = await visibleBox(page.locator('.combat-panel'), 'combat tracker')
    const diceBox = await visibleBox(page.locator('.dice-panel'), 'dice panel')
    const characterBox = await visibleBox(page.locator('.char-sidebar'), 'character sidebar')

    expect(combatBox.x + combatBox.width / 2, 'combat tracker should be on the right side').toBeGreaterThan(viewport!.width / 2)
    expect(characterBox.x + characterBox.width, 'character sidebar should be left of combat tracker').toBeLessThan(combatBox.x)
    expect(diceBox.x + diceBox.width, 'dice panel should be left of combat tracker').toBeLessThan(combatBox.x)
    expect(characterBox.x, 'character sidebar should start on the left side').toBeLessThan(viewport!.width / 2)
    expect(diceBox.x, 'dice panel should start on the left side').toBeLessThan(viewport!.width / 2)

    // session-state AC-004: state.json switches to combat mode at round 1
    const statePath = path.join(repoRoot, 'sessions', 'session_001', 'state.json')
    await expect.poll(() => {
      try { return JSON.parse(readFileSync(statePath, 'utf8')) } catch { return {} }
    }, { timeout: 5_000 }).toMatchObject({ mode: 'combat', round: 1 })
  })

  // Covers: dice-panel.feature AC-001, AC-002, AC-004
  test('L11 - %%ROLL%% prompt can be answered from the dice panel', async () => {
    await sendTurnAndWait(
      page,
      [
        'I scan the chaos to locate the goblin warchanter before anyone attacks.',
        'This requires a Perception check. Write a %%ROLL%% section.',
        'The %%ROLL%% marker must be on its own line; write each field on its own line beneath it, exactly like this:',
        '%%ROLL%%',
        'skill: Perception',
        'dc: 15',
        'success: You spot the warchanter.',
        'failure: You cannot locate the warchanter.',
        'Do not add a second %%ROLL%% marker. Do not resolve the roll yourself. Do not write a %%ATTACK%% block.',
      ].join('\n'),
    )

    await expect(page.locator('.bubble-gm').last()).toContainText('%%ROLL%%', { timeout: 60_000 })

    // The dice panel activates only if the backend parsed the %%ROLL%% block and emitted
    // a roll_request SSE.  If not, the LLM deviated from the required format — fail with
    // a plain assertion (not test.fail(), which produces a counter-intuitive "unexpected
    // pass" result in Playwright when no exception is thrown).
    const panelActive = page.locator('.dice-panel-active')
    const panelVisible = await panelActive.isVisible().catch(() => false) ||
      await panelActive.waitFor({ state: 'visible', timeout: 15_000 }).then(() => true).catch(() => false)

    expect(
      panelVisible,
      'dice-panel-active did not appear — roll_request SSE not emitted; LLM deviated from %%ROLL%% format',
    ).toBe(true)
    if (!panelVisible) return

    await expect(page.locator('.roll-request-skill')).toContainText('Perception')
    await expect(page.locator('.roll-request-dc')).toContainText('DC 15')

    await page.locator('.roll-request-prompt').click()

    await expect(page.locator('.history-row').first()).toContainText(/PASSED|FAILED/, { timeout: 15_000 })
    await expect(page.getByText(/rolled (?:a )?\d+/i).last()).toBeVisible()
  })

  // L12 — PC attack-resolution: NPC auto-resolves, PC roll prompt, then resume
  // Covers: attack-resolution.feature AC-001, AC-002, AC-003, AC-004, AC-005, AC-007
  test('L12 - attack-resolution: NPC auto-resolves, PC roll prompt then resume_combat', async () => {
    // combat_state is active from L10 (round 1); _COMBAT_SPEC_ONGOING is injected,
    // which includes the %%ATTACK%% format spec. L11 resolved a Perception roll so
    // streaming is idle and we can proceed immediately to round 2.
    await sendTurnAndWait(
      page,
      [
        'Round 2: a goblin warrior charges and swings at Yanyeeku with its dogslicer.',
        'Yanyeeku braces and counter-attacks with her morningstar.',
        'Write %%COMBAT%% round: 2 keeping all existing combatants.',
        'Immediately after the %%COMBAT%% block write a %%ATTACK%% block with exactly two lines',
        '(one NPC attack, one PC attack) in this exact format:',
        '- attacker: [goblin name] · target: Yanyeeku · bonus: +2 · damage: 1d4 · type: melee',
        '- attacker: Yanyeeku · target: [goblin name] · bonus: +2 · damage: 1d8 · type: melee',
        'Replace [goblin name] with the actual name of the lead goblin warrior from the current combat.',
        'Do NOT write a %%ROLL%% block.',
        'Do not resolve attack outcomes or dice yourself.',
      ].join(' '),
    )

    // AC-001: %%ATTACK%% block was present in the GM response (dev mode shows markers)
    await expect(page.locator('.bubble-gm').last()).toContainText('%%ATTACK%%', { timeout: 60_000 })

    // AC-002: NPC attack auto-resolved → attack_result SSE → HP bar(s) visible in CombatPanel
    await expect(page.locator('.combat-panel')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('.combatant-hp-row').first()).toBeVisible()

    // AC-002 + AC-003: PC attack queued → attack_request SSE → DicePanel shows to-hit banner
    await expect(page.locator('.dice-panel-active')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('.attack-banner')).toBeVisible()
    // Banner must identify Yanyeeku as the attacker
    await expect(page.locator('.roll-request-skill')).toContainText('Yanyeeku')

    // AC-003: clicking the to-hit prompt auto-rolls d20 → POST /resolve_attack_roll
    // Set up both listeners before the click to avoid race conditions on the miss path.
    const atkResponsePromise = page.waitForResponse(r => r.url().includes('/resolve_attack_roll'))
    const resumeRequestPromise = page.waitForRequest(
      r => r.url().includes('/resume_combat'),
      { timeout: 30_000 },
    )
    await page.locator('.roll-request-prompt').click()
    const atkResponse = await atkResponsePromise
    const atkData = await atkResponse.json()

    if (atkData.hit) {
      // AC-004: hit path — damage banner appears, player picks a die and rolls
      await expect(page.locator('.attack-banner--damage')).toBeVisible({ timeout: 8_000 })
      await expect(page.locator('.roll-request-skill')).toContainText('HIT!')

      // Pick the d8 die (Yanyeeku morningstar: 1d8)
      await page.locator('.die-btn').filter({ hasText: 'd8' }).click()

      // Click Roll Damage → POST /resolve_damage_roll
      const dmgResponsePromise = page.waitForResponse(r => r.url().includes('/resolve_damage_roll'))
      await page.locator('.attack-damage-roll-btn').click()
      await dmgResponsePromise

      // AC-007: Goblin Warrior HP may be reduced — CombatPanel still visible
      await expect(page.locator('.combat-panel')).toBeVisible()
    }
    // Miss path: banner clears automatically; doResumeCombat fires immediately.

    // AC-005: resume_combat called when queue_remaining === 0 (hit or miss)
    const resumeRequest = await resumeRequestPromise
    expect(resumeRequest.method()).toBe('POST')

    // GM narrative streams; wait for it to finish (textbox re-enables)
    await expect(page.getByRole('textbox')).toBeEnabled({ timeout: 60_000 })
    await expect(page.locator('.bubble-gm').last()).toBeVisible()

    // Attack banner is cleared after full resolution
    await expect(page.locator('.attack-banner')).not.toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// L13-L14 — dice panel integration (App.tsx wiring)
//
// Queue/auto-bonus/history-cap behaviour is already covered by DicePanel
// Vitest tests (DicePanel.test.tsx AC-001, AC-006, AC-007, AC-010).
// Only the two App.tsx integration paths that cannot be tested at component
// level live here:
//
//   L13 — App.tsx sets pendingRoll=null after resolveRoll resolves,
//          clearing the banner and surfacing the PASSED/FAILED badge.
//   L14 — App.tsx keeps streaming=true while the SSE stream is open,
//          keeping the Send button disabled until the stream closes.
//
// /turn and /resolve_roll are mocked via page.route — no LLM call needed.
// ---------------------------------------------------------------------------

test.describe.serial('L13-L14 — dice panel integration', () => {
  let page: Page

  function rollRequestSse(skill: string, dc: number): string {
    const token = JSON.stringify({ type: 'token', content: `%%ROLL%% [ skill: ${skill}  dc: ${dc}  success: ok  failure: fail ]` })
    const rollReq = JSON.stringify({ type: 'roll_request', skill, dc, success: 'ok', failure: 'fail', speaker: null })
    const done = JSON.stringify({ type: 'done' })
    return `data: ${token}\n\ndata: ${rollReq}\n\ndata: ${done}\n\n`
  }

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()
    await page.goto('/')
    await configureHaiku(page)
    await bootSession(page)
  })

  test.afterAll(async () => {
    if (!page.isClosed()) await page.close()
  })

  // App.tsx wiring: setPendingRoll(null) fires after resolveRoll resolves → banner gone.
  // DicePanel unit tests cover badge rendering; this covers the parent callback chain.
  test('L13 — pending roll banner clears after resolve and PASSED/FAILED badge appears', async () => {
    await page.route('**/sessions/*/turn', route =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
        body: rollRequestSse('Stealth', 12),
      }),
    )
    await page.route('**/sessions/*/resolve_roll', route =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passed: true, skill: 'Stealth', dc: 12, rolled: 14, outcome: 'ok', speaker: null }),
      }),
    )

    await page.getByRole('textbox').fill('I try to hide.')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByRole('textbox')).toBeEnabled({ timeout: 10_000 })

    // Banner visible once roll_request SSE arrives
    await expect(page.locator('.roll-request-banner')).toBeVisible({ timeout: 5_000 })
    await page.locator('.roll-request-prompt').click()

    // Banner gone — pendingRoll set to null by App.tsx after resolveRoll resolves
    await expect(page.locator('.roll-request-banner')).not.toBeVisible({ timeout: 5_000 })

    // PASSED/FAILED outcome badge on the newest history row
    const latestRow = page.locator('.history-row').first()
    await expect(latestRow.locator('.hist-outcome')).toBeVisible({ timeout: 5_000 })
    await expect(latestRow).toContainText(/PASSED|FAILED/)

    await page.unroute('**/sessions/*/turn')
    await page.unroute('**/sessions/*/resolve_roll')
  })

  // App.tsx wiring: streaming=true while SSE is open → InputBar disabled prop → Send disabled.
  test('L14 — send button is disabled while GM response is streaming', async () => {
    let releaseStream!: () => void
    const streamHeld = new Promise<void>(resolve => { releaseStream = resolve })

    await page.route('**/sessions/*/turn', async route => {
      await streamHeld
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
        body: `data: ${JSON.stringify({ type: 'token', content: 'ok' })}\n\ndata: ${JSON.stringify({ type: 'done' })}\n\n`,
      })
    })

    await page.getByRole('textbox').fill('A test message.')
    await page.getByRole('button', { name: 'Send' }).click()

    // While stream is held: streaming=true → InputBar disabled prop → textarea disabled.
    // (The button label changes to '…' when disabled, so we assert on the textarea
    //  which uses the same disabled prop but keeps a stable accessible role.)
    await expect(page.getByRole('textbox')).toBeDisabled({ timeout: 5_000 })

    // Release stream → streaming=false → textarea re-enables
    releaseStream()
    await expect(page.getByRole('textbox')).toBeEnabled({ timeout: 15_000 })

    await page.unroute('**/sessions/*/turn')
  })
})
