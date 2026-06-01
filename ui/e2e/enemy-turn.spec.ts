import { expect, test, type Page } from '@playwright/test'

// Spec: specs/enemy-turn.feature
// Covers: enemy-turn.feature AC-010, AC-011, AC-014
// Covers: combat-tracker.feature AC-016, AC-017, AC-018

const combatState = {
  round: 1,
  current_actor: 'Goblin Warrior 1',
  combatants: [
    { name: 'Vanx', hp_current: 10, hp_max: 10, ac: 18, initiative: 14, status: 'active' },
    { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 10, status: 'active' },
  ],
}

const damagedCombatState = {
  ...combatState,
  combatants: [
    { ...combatState.combatants[0], hp_current: 7 },
    combatState.combatants[1],
  ],
}

function sse(events: unknown[]) {
  return events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('')
}

async function routeJson(page: Page, url: string, body: unknown) {
  await page.route(url, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }))
}

async function routeSse(page: Page, url: string, events: unknown[]) {
  await page.route(url, route => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: sse(events),
  }))
}

async function setupCommonRoutes(page: Page) {
  await routeJson(page, '**/api/characters', [])
  await page.route('**/api/intro?session=1', route => route.fulfill({
    status: 200,
    contentType: 'text/plain',
    body: '# Test Intro',
  }))
  await routeSse(page, '**/api/sessions', [{ type: 'done', session_id: 'sess-e2e' }])
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function sendCombatTurn(page: Page) {
  await page.getByRole('textbox').fill('Do I spot any goblins?')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByRole('button', { name: 'Enemy Turn' })).toBeVisible()
}

test.describe('Enemy turn UI flow', () => {
  test('boots, triggers combat, runs one enemy turn, and updates CombatPanel', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-e2e/turn', [
      { type: 'combat_update', combat_state: combatState },
      { type: 'done' },
    ])
    await routeSse(page, '**/api/sessions/sess-e2e/enemy_turn', [
      { type: 'token', content: 'The goblin slashes Vanx.' },
      { type: 'attack_result', attacker: 'Goblin Warrior 1', target: 'Vanx', roll: 15, bonus: 4, total: 19, ac: 18, hit: true, damage_rolls: [3], damage_total: 3, attack_type: 'melee', is_pc: false },
      { type: 'combat_update', combat_state: damagedCombatState },
      { type: 'done' },
    ])

    await boot(page)
    await sendCombatTurn(page)
    await page.getByRole('button', { name: 'Enemy Turn' }).click()

    await expect(page.locator('.bubble-gm', { hasText: 'The goblin slashes Vanx.' })).toBeVisible()
    await expect(page.locator('.combatant-row', { hasText: 'Vanx' })).toContainText('7/10')
  })

  test('blocks Enemy Turn while a PC attack request is pending', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-e2e/turn', [
      { type: 'combat_update', combat_state: combatState },
      { type: 'attack_request', attacker: 'Vanx', target: 'Goblin Warrior 1', bonus: 4, ac: 16, damage_expr: '1d6', attack_type: 'melee' },
      { type: 'done' },
    ])

    await boot(page)
    await sendCombatTurn(page)

    await expect(page.locator('.combat-phase-badge', { hasText: 'PC Attacks' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Enemy Turn' })).toBeDisabled()
  })

  test('streams close_combat narrative before clearing the tracker', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-e2e/turn', [
      { type: 'combat_update', combat_state: combatState },
      { type: 'done' },
    ])
    await routeSse(page, '**/api/sessions/sess-e2e/close_combat', [
      { type: 'token', content: 'The square falls quiet.' },
      { type: 'combat_update', combat_state: null },
      { type: 'done' },
    ])

    await boot(page)
    await sendCombatTurn(page)
    await page.getByRole('button', { name: 'End Combat' }).click()

    await expect(page.locator('.bubble-gm', { hasText: 'The square falls quiet.' })).toBeVisible()
    await expect(page.locator('.combat-panel')).not.toBeVisible()
  })
})
