import { expect, test, type Page } from '@playwright/test'

// Spec: specs/pc-combat-turn.feature  AC-004, AC-005, AC-008, AC-009, AC-010
//
// Covers the PC combat turn flow end-to-end with mocked backend:
//   1. When it is a PC's turn, input routes to POST /pc_turn
//   2. attack_request SSE activates dice tray banner (no LLM call yet)
//   3. After dice resolved, action card appears before narrative
//   4. combat_update advances current actor

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PCombatState = {
  round: 2,
  current_actor: 'Ani',
  combatants: [
    { name: 'Ani',             hp_current: 11, hp_max: 11, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
  ],
}

const AdvancedState = {
  ...PCombatState,
  current_actor: 'Goblin Warrior 1',
}

const AniCharacter = {
  id: 'ani', name: 'Ani', portrait: '/portraits/ani.png', color: '#f0a060', rune: 'A',
  player: '', race: 'Human', subrace: '', class: 'Oracle', archetype: '', alignment: 'CG',
  deity: 'Desna', level: 1, appearance: '',
  hp: { current: 11, max: 11, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac: { total: 17, touch: 12, flatFooted: 14, components: [] },
  initiative: '+1', speed: '30 ft', bab: '+0', abilities: [], saves: [], skills: [], feats: [],
  weapons: [], spells: { concentration: '+0', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

function sse(events: unknown[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function setupRoutes(page: Page) {
  await page.route('**/api/characters', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([AniCharacter]) }))
  await page.route('**/api/intro?session=1', r => r.fulfill({ status: 200, contentType: 'text/plain', body: '# Session 1' }))
  await page.route('**/api/sessions', r => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse([{ type: 'done', session_id: 'sess-pc' }]) }))
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function enterCombat(page: Page) {
  await page.route('**/api/sessions/sess-pc/turn', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'combat_update', combat_state: PCombatState }, { type: 'done' }]) }))
  await page.getByRole('textbox').fill('goblins attack!')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-round-badge', { hasText: 'Round 2' })).toBeVisible({ timeout: 10_000 })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('PC combat turn flow', () => {

  test('CT-PC-001 — PC turn routes to /pc_turn and shows attack banner', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    // Now it's Ani's turn (PC) — next input should go to /pc_turn
    let pcTurnCalled = false
    await page.route('**/api/sessions/sess-pc/pc_turn', async route => {
      pcTurnCalled = true
      await route.fulfill({
        status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'attack_request', attacker: 'Ani', target: 'Goblin Warrior 1', bonus: 4, ac: 16, damage_expr: '1d8+2', attack_type: 'melee' },
          { type: 'done' },
        ]),
      })
    })

    await page.getByRole('textbox').fill('I swing my morningstar at the goblin!')
    await page.getByRole('button', { name: 'Send' }).click()

    // /pc_turn was called (not /turn)
    await expect.poll(() => pcTurnCalled, { timeout: 5_000 }).toBe(true)

    // Attack banner activates in dice tray
    await expect(page.locator('.roll-request-banner, .attack-banner').first()).toBeVisible({ timeout: 5_000 })
  })

  test('CT-PC-003 — combat_update from narration advances current actor', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    const advancedState = { ...PCombatState, current_actor: 'Goblin Warrior 1' }

    await page.route('**/api/sessions/sess-pc/pc_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'token', content: 'Ani swings wide.' },
          { type: 'combat_update', combat_state: advancedState },
          { type: 'done' },
        ]) }))

    await page.getByRole('textbox').fill('advance')
    await page.getByRole('button', { name: 'Send' }).click()

    await expect(page.locator('.combatant-current')).toContainText('Goblin Warrior 1', { timeout: 10_000 })
  })

})