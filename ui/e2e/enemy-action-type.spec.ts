import { expect, test, type Page } from '@playwright/test'

/**
 * E2E — enemy-action-type.feature
 *
 * Covers:
 *   AC-006 — action_type included in the action_card SSE event
 *   AC-007 — action_type visible in the rendered action card in the UI
 *
 * Strategy: backend calls are mocked. The action_card SSE event from the
 * /enemy_turn stream is injected directly to verify the UI renders it.
 */

// ── Fixtures ──────────────────────────────────────────────────────────────────

const VanxCharacter = {
  id: 'vanx', name: 'Vanx', portrait: '/portraits/vanx.png', color: '#60a0f0', rune: 'V',
  player: '', race: 'Human', subrace: '', class: 'Rogue', archetype: '', alignment: 'CN',
  deity: '', level: 1, appearance: '',
  hp:    { current: 10, max: 10, hitDie: 'd8', baseDieRoll: 8, conBonus: 2 },
  ac:    { total: 15, touch: 12, flatFooted: 13, components: [] },
  initiative: '+3', speed: '30 ft', bab: '+0', abilities: [], saves: [], skills: [], feats: [],
  weapons: [{ name: 'shortsword', atk: '+3', dmg: '1d6+1', type: 'melee', special: '' }],
  spells: { concentration: '+0', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

const EnemyCombatState = {
  round: 1,
  current_actor: 'Goblin Warrior 1',
  combatants: [
    { name: 'Vanx',            hp_current: 10, hp_max: 10, ac: 15, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
  ],
}

const AdvancedState = { ...EnemyCombatState, current_actor: 'Vanx' }

function sse(events: unknown[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function setupRoutes(page: Page) {
  await page.route('**/api/characters', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([VanxCharacter]) }))
  await page.route('**/api/intro?session=1', r =>
    r.fulfill({ status: 200, contentType: 'text/plain', body: '# Session 1' }))
  await page.route('**/api/sessions', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'done', session_id: 'sess-eat' }]) }))
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function enterEnemyCombat(page: Page) {
  await page.route('**/api/sessions/sess-eat/turn', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'combat_update', combat_state: EnemyCombatState }, { type: 'done' }]) }))
  await page.getByRole('textbox').fill('a goblin attacks!')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-round-badge').first()).toBeVisible({ timeout: 10_000 })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('enemy-action-type', () => {

  test('EAT-E2E-001 — action_type "standard" from action_card renders in UI (AC-006)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterEnemyCombat(page)

    await page.route('**/api/sessions/sess-eat/enemy_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'token',   content: 'The goblin slashes at Vanx.' },
          { type: 'action_card', attacker: 'Goblin Warrior 1', target: 'Vanx',
            action_type: 'standard', roll: 12, bonus: 3, total: 15, ac: 15, hit: true,
            damage_rolls: [4], damage_total: 4, attack_type: 'melee', is_pc: false },
          { type: 'combat_update', combat_state: AdvancedState },
          { type: 'done' },
        ]) }))

    await page.getByRole('button', { name: 'Enemy Turn' }).first().click()

    const card = page.locator('.combat-event-card').first()
    await expect(card).toBeVisible({ timeout: 8_000 })
    await expect(card).toContainText('standard')
    await expect(card).toContainText('Goblin Warrior 1')
  })

  test('EAT-E2E-002 — action_type "full" attack renders action card (AC-006)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterEnemyCombat(page)

    await page.route('**/api/sessions/sess-eat/enemy_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'token',   content: 'The goblin unleashes a full assault.' },
          { type: 'action_card', attacker: 'Goblin Warrior 1', target: 'Vanx',
            action_type: 'full', roll: 15, bonus: 3, total: 18, ac: 15, hit: true,
            damage_rolls: [6], damage_total: 6, attack_type: 'melee', is_pc: false },
          { type: 'combat_update', combat_state: AdvancedState },
          { type: 'done' },
        ]) }))

    await page.getByRole('button', { name: 'Enemy Turn' }).first().click()

    await expect(page.locator('.combat-event-card').first()).toContainText('full')
  })

  test('EAT-E2E-003 — delay action produces no attack result, only combat_update (AC-007)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterEnemyCombat(page)

    await page.route('**/api/sessions/sess-eat/enemy_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'token',   content: 'The goblin waits.' },
          { type: 'combat_update', combat_state: AdvancedState },
          { type: 'done' },
        ]) }))

    await page.getByRole('button', { name: 'Enemy Turn' }).first().click()

    await expect(page.locator('.bubble-row.gm .bubble-gm').first())
      .toContainText('goblin', { timeout: 8_000 })

    await expect(page.locator('.combat-event-card')).toHaveCount(0)
  })

})
