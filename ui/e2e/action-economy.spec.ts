import { expect, test, type Page } from '@playwright/test'

const AniCharacter = {
  id: 'ani', name: 'Ani', portrait: '/portraits/ani.png', color: '#f0a060', rune: 'A',
  player: '', race: 'Human', subrace: '', class: 'Fighter', archetype: '', alignment: 'LN',
  deity: '', level: 1, appearance: '',
  hp:    { current: 11, max: 11, hitDie: 'd10', baseDieRoll: 10, conBonus: 1 },
  ac:    { total: 17, touch: 12, flatFooted: 14, components: [] },
  initiative: '+1', speed: '30 ft', bab: '+1', abilities: [], saves: [], skills: [], feats: [],
  weapons: [{ name: 'morningstar', atk: '+4', dmg: '1d8+2', type: 'melee', special: '' }],
  spells: { concentration: '+0', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

const PcCombatState = {
  round: 1,
  current_actor: 'Ani',
  combatants: [
    { name: 'Ani',             hp_current: 11, hp_max: 11, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
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
      body: sse([{ type: 'done', session_id: 'sess-ae' }]) }))
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function enterPcCombat(page: Page) {
  await page.route('**/api/sessions/sess-ae/turn', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'combat_update', combat_state: PcCombatState }, { type: 'done' }]) }))
  await page.getByRole('textbox').fill('goblins attack!')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-round-badge').first()).toBeVisible({ timeout: 10_000 })
}

test.describe('action-economy', () => {
  test('AE-E2E-001 — action buttons absent when no combat is active', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await expect(page.getByRole('button', { name: 'Standard' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Move' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Full-Round' })).toHaveCount(0)
  })

  test('AE-E2E-002 — action buttons stay hidden during a PC combat turn while the feature flag is off', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterPcCombat(page)
    await expect(page.getByRole('button', { name: 'Standard' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Move' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Full-Round' })).toHaveCount(0)
  })

  test('AE-E2E-003 — action buttons stay hidden during enemy turns', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await page.route('**/api/sessions/sess-ae/turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([{ type: 'combat_update', combat_state: EnemyCombatState }, { type: 'done' }]) }))
    await page.getByRole('textbox').fill('enemy turn')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.locator('.combat-round-badge').first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('button', { name: 'Standard' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Move' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Full-Round' })).toHaveCount(0)
  })

  test('AE-E2E-004 — pc_turn submits an empty action hint list while the picker is hidden', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterPcCombat(page)

    let capturedBody: Record<string, unknown> | null = null
    await page.route('**/api/sessions/sess-ae/pc_turn', async route => {
      capturedBody = JSON.parse(route.request().postData() ?? '{}')
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse([{ type: 'done' }]) })
    })

    await page.getByRole('textbox').fill('I strike at the goblin')
    await page.getByRole('button', { name: 'Send' }).click()

    await expect.poll(() => capturedBody, { timeout: 5_000 }).not.toBeNull()
    expect((capturedBody as Record<string, unknown>).action_type_hints).toEqual([])
  })
})
