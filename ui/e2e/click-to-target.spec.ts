import { expect, test, type Page } from '@playwright/test'

/**
 * E2E — click-to-target.feature
 *
 * Covers:
 *   AC-001 — clicking enemy row selects it as target
 *   AC-002 — target badge appears near InputBar showing "🎯 <name>"
 *   AC-003 — clicking same row again deselects
 *   AC-004 — target_hint sent in POST body
 *   AC-007 — selection only active during PC turn
 *   AC-008 — selection clears after submit
 *   AC-009 — dead enemies cannot be targeted
 *
 * Strategy: mocked backend, deterministic SSE responses.
 */

// ── Fixtures ──────────────────────────────────────────────────────────────────

const AniCharacter = {
  id: 'ani', name: 'Ani', portrait: '/portraits/ani.png', color: '#f0a060', rune: 'A',
  player: '', race: 'Human', subrace: '', class: 'Fighter', archetype: '', alignment: 'LN',
  deity: '', level: 1, appearance: '',
  hp:    { current: 11, max: 11, hitDie: 'd10', baseDieRoll: 10, conBonus: 1 },
  ac:    { total: 17, touch: 12, flatFooted: 14, components: [] },
  initiative: '+1', speed: '30 ft', bab: '+1', abilities: [], saves: [], skills: [], feats: [],
  weapons: [{ name: 'longsword', atk: '+4', dmg: '1d8+2', type: 'melee', special: '' }],
  spells: { concentration: '+0', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

const PcCombatState = {
  round: 1,
  current_actor: 'Ani',
  combatants: [
    { name: 'Ani',             hp_current: 11, hp_max: 11, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
    { name: 'Goblin Warrior 2',hp_current: 5,  hp_max: 5,  ac: 16, initiative: 7,  status: 'active', conditions: [] },
    { name: 'Goblin Dog',      hp_current: 0,  hp_max: 8,  ac: 13, initiative: 5,  status: 'dead',   conditions: [] },
  ],
}

const EnemyCombatState = { ...PcCombatState, current_actor: 'Goblin Warrior 1' }

function sse(events: unknown[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function setupRoutes(page: Page) {
  await page.route('**/api/characters', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([AniCharacter]) }))
  await page.route('**/api/intro?session=1', r =>
    r.fulfill({ status: 200, contentType: 'text/plain', body: '# Session 1' }))
  await page.route('**/api/sessions', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'done', session_id: 'sess-ctt' }]) }))
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function enterCombat(page: Page, state = PcCombatState) {
  await page.route('**/api/sessions/sess-ctt/turn', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'combat_update', combat_state: state }, { type: 'done' }]) }))
  await page.getByRole('textbox').fill('combat begins!')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-round-badge').first()).toBeVisible({ timeout: 10_000 })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Find a combatant row by partial text */
function combatantRow(page: Page, name: string) {
  return page.locator('.combatant-row', { hasText: name })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('click-to-target', () => {

  test('CTT-E2E-001 — clicking an enemy row selects it and applies targeted class (AC-001)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    const row = combatantRow(page, 'Goblin Warrior 1')
    await row.click()

    await expect(row).toHaveClass(/combatant-targeted/, { timeout: 3_000 })
  })

  test('CTT-E2E-002 — target badge appears showing the selected name (AC-002)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    await combatantRow(page, 'Goblin Warrior 1').click()

    // Badge shows 🎯 + enemy name near the InputBar
    await expect(page.locator('.target-badge')).toContainText('Goblin Warrior 1', { timeout: 3_000 })
  })

  test('CTT-E2E-003 — clicking same row again deselects the target (AC-003)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    const row = combatantRow(page, 'Goblin Warrior 1')
    await row.click()
    await expect(row).toHaveClass(/combatant-targeted/)

    // Second click deselects
    await row.click()
    await expect(row).not.toHaveClass(/combatant-targeted/, { timeout: 3_000 })
    await expect(page.locator('.target-badge')).not.toBeVisible()
  })

  test('CTT-E2E-004 — target_hint included in POST body when a target is selected (AC-004)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    // Capture /pc_turn POST body
    let capturedBody: Record<string, unknown> | null = null
    await page.route('**/api/sessions/sess-ctt/pc_turn', async route => {
      capturedBody = JSON.parse(route.request().postData() ?? '{}')
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse([{ type: 'done' }]) })
    })

    // Select a target then submit
    await combatantRow(page, 'Goblin Warrior 2').click()
    await page.getByRole('textbox').fill('I strike!')
    await page.getByRole('button', { name: 'Send' }).click()

    await expect.poll(() => capturedBody, { timeout: 5_000 }).not.toBeNull()
    expect((capturedBody as Record<string, unknown>).target_hint).toBe('Goblin Warrior 2')
  })

  test('CTT-E2E-005 — target clears after submit (AC-008)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    await page.route('**/api/sessions/sess-ctt/pc_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse([{ type: 'done' }]) }))

    await combatantRow(page, 'Goblin Warrior 1').click()
    await expect(page.locator('.target-badge')).toBeVisible()

    await page.getByRole('textbox').fill('attack!')
    await page.getByRole('button', { name: 'Send' }).click()

    // Badge must disappear after submit
    await expect(page.locator('.target-badge')).not.toBeVisible({ timeout: 5_000 })
  })

  test('CTT-E2E-006 — rows are not clickable during enemy turn (AC-007)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page, EnemyCombatState)  // enemy is current actor

    // Click on a live enemy row — should NOT gain targeted class
    const row = combatantRow(page, 'Goblin Warrior 1')
    await row.click()
    await expect(row).not.toHaveClass(/combatant-targeted/, { timeout: 2_000 })
    await expect(page.locator('.target-badge')).not.toBeVisible()
  })

  test('CTT-E2E-007 — dead enemies cannot be targeted (AC-009)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    // Goblin Dog has status: dead
    const deadRow = combatantRow(page, 'Goblin Dog')
    await deadRow.click()
    await expect(deadRow).not.toHaveClass(/combatant-targeted/, { timeout: 2_000 })
  })

})
