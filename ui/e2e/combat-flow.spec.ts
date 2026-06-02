/**
 * CT-E2E-001 — Full combat round visual flow.
 *
 * Spec: specs/combat-tracker.feature
 * Covers: AC-006 (panel appears/disappears), AC-007 (initiative order),
 *         AC-008 (End Combat), AC-009 (HpBar colour change)
 *
 * Strategy: both the /turn and DELETE /combat endpoints are mocked so the
 * test never hits the real backend.  This keeps it deterministic and fast
 * while exercising the full React render path.
 */
import { expect, test, type Page, type Route } from '@playwright/test'

// ── Shared helpers (mirrors app-flows.spec.ts) ────────────────────────────────

const character = {
  id: 'yanyeeku', portrait: '/portraits/yanyeeku.png', color: '#a060d0', rune: 'Y',
  name: 'Yanyeeku', player: 'Player 1', race: 'Kitsune', subrace: '', class: 'Oracle',
  archetype: 'Flame Mystery', alignment: 'CG', deity: 'Desna', level: 1,
  appearance: 'A festival oracle.',
  hp:         { current: 9, max: 9, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac:         { total: 16, touch: 12, flatFooted: 14, components: [] },
  initiative: '+2', speed: '30 ft', bab: '+0',
  abilities:  [
    { name: 'STR', score: 10, mod: '+0' }, { name: 'DEX', score: 14, mod: '+2' },
    { name: 'CON', score: 12, mod: '+1' }, { name: 'INT', score: 11, mod: '+0' },
    { name: 'WIS', score: 13, mod: '+1' }, { name: 'CHA', score: 18, mod: '+4' },
  ],
  saves: [
    { name: 'Fortitude', ability: 'CON', total: '+1', base: '+0', abilityMod: '+1', magic: '+0', misc: '+0' },
    { name: 'Reflex',    ability: 'DEX', total: '+2', base: '+0', abilityMod: '+2', magic: '+0', misc: '+0' },
    { name: 'Will',      ability: 'WIS', total: '+3', base: '+2', abilityMod: '+1', magic: '+0', misc: '+0' },
  ],
  skills: [], feats: [], weapons: [],
  spells: { concentration: '+5', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

function sse(...events: object[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function fulfillSse(route: Route, ...events: object[]) {
  await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse(...events) })
}

async function installBaseRoutes(page: Page) {
  await page.route('**/api/characters', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([character]) }),
  )
  await page.route('**/api/intro?session=1', route =>
    route.fulfill({ status: 200, contentType: 'text/plain', body: '# Test Session Intro' }),
  )
  await page.route('**/api/sessions', route =>
    fulfillSse(route, { type: 'done', session_id: 'sess-e2e' }),
  )
  await page.route('**/api/npcs/session', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ purged: 0 }) }),
  )
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.getByText(/Session 1/)).toBeVisible()
}

// ── Combat-state fixture ───────────────────────────────────────────────────────

const ROUND_1_STATE = {
  round: 1,
  combatants: [
    { name: 'Shalelu',  hp_current: 24, hp_max: 24, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin 1', hp_current:  5, hp_max:  5, ac: 13, initiative: 12, status: 'active', conditions: [] },
    { name: 'Thaelion', hp_current: 22, hp_max: 22, ac: 16, initiative:  8, status: 'active', conditions: [] },
  ],
}

// Same round, Goblin 1 knocked out — drives HP-bar colour change check
const ROUND_2_STATE = {
  round: 2,
  combatants: [
    { name: 'Shalelu',  hp_current:  8, hp_max: 24, ac: 17, initiative: 14, status: 'active',      conditions: [] },
    { name: 'Goblin 1', hp_current:  0, hp_max:  5, ac: 13, initiative: 12, status: 'unconscious', conditions: [] },
    { name: 'Thaelion', hp_current: 22, hp_max: 22, ac: 16, initiative:  8, status: 'active',      conditions: [] },
  ],
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.beforeEach(async ({ page }) => {
  await installBaseRoutes(page)
})

// Covers: AC-006, AC-007
test('CT-E2E-001a — combat_update renders CombatPanel in initiative order', async ({ page }) => {
  await page.route('**/api/sessions/sess-e2e/turn', route =>
    fulfillSse(
      route,
      { type: 'token', content: 'Goblins charge!' },
      { type: 'combat_update', combat_state: ROUND_1_STATE },
    ),
  )
  await boot(page)

  await page.getByRole('textbox').fill('attack the goblin')
  await page.getByRole('button', { name: 'Send' }).click()

  // Panel is visible with round badge
  await expect(page.locator('.combat-panel')).toBeVisible()
  await expect(page.getByText('Round 1')).toBeVisible()

  // AC-007: Shalelu (init 14) appears before Goblin 1 (12) before Thaelion (8)
  const names = page.locator('.combatant-name')
  await expect(names.nth(0)).toHaveText('Shalelu')
  await expect(names.nth(1)).toHaveText('Goblin 1')
  await expect(names.nth(2)).toHaveText('Thaelion')

  // Top active combatant gets combatant-current styling
  await expect(page.locator('.combatant-current').first()).toContainText('Shalelu')

  // AC-006: .main-content has combat-active class
  await expect(page.locator('.main-content')).toHaveClass(/combat-active/)
})

// Covers: AC-009
test('CT-E2E-001b — HP bar colour shifts on combat_update with reduced HP', async ({ page }) => {
  // First turn: establish combat at full HP
  await page.route('**/api/sessions/sess-e2e/turn', route =>
    fulfillSse(
      route,
      { type: 'combat_update', combat_state: ROUND_1_STATE },
    ),
  ).then(() => undefined)

  // Second turn route set immediately so Playwright routes by call order
  let callCount = 0
  await page.route('**/api/sessions/sess-e2e/turn', async route => {
    callCount++
    if (callCount === 1) {
      await fulfillSse(route, { type: 'combat_update', combat_state: ROUND_1_STATE })
    } else {
      await fulfillSse(route, { type: 'combat_update', combat_state: ROUND_2_STATE })
    }
  })

  await boot(page)

  // Turn 1: establish combat
  await page.getByRole('textbox').fill('fight')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByText('Round 1')).toBeVisible()

  // Shalelu at 100 % HP → green bar
  const shaleluBar = page.locator('.combatant-row').filter({ hasText: 'Shalelu' }).locator('.hp-bar-fill')
  await expect(shaleluBar).toHaveCSS('background-color', 'rgb(58, 154, 106)')  // #3a9a6a

  // Turn 2: Shalelu drops to 8/24 = 33 % → red bar; Goblin 1 → KO status badge
  await page.getByRole('textbox').fill('round 2')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-round-badge', { hasText: 'Round 2' })).toBeVisible()

  await expect(shaleluBar).toHaveCSS('background-color', 'rgb(176, 64, 64)')   // #b04040

  const goblinRow = page.locator('.combatant-row').filter({ hasText: 'Goblin 1' })
  await expect(goblinRow).toHaveClass(/combatant-inactive/)
  await expect(goblinRow.locator('.status-badge')).toBeVisible()
})

// Covers: AC-008, AC-006
test('CT-E2E-001c — End Combat clears panel via close_combat stream', async ({ page }) => {
  // The UI uses POST /close_combat (SSE stream) not DELETE /combat directly.
  await page.route('**/api/sessions/sess-e2e/turn', route =>
    fulfillSse(route, { type: 'combat_update', combat_state: ROUND_1_STATE }),
  )

  let closeCombatCalled = false
  await page.route('**/api/sessions/sess-e2e/close_combat', async route => {
    closeCombatCalled = true
    await fulfillSse(
      route,
      { type: 'token', content: 'The goblins flee.' },
      { type: 'combat_update', combat_state: null },
      { type: 'done' },
    )
  })

  await boot(page)

  await page.getByRole('textbox').fill('fight')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-panel')).toBeVisible()

  await page.getByRole('button', { name: 'End Combat' }).click()

  // Panel disappears after combat_update: null
  await expect(page.locator('.combat-panel')).not.toBeVisible({ timeout: 5_000 })

  // Layout reverts — no combat-active class
  await expect(page.locator('.main-content')).not.toHaveClass(/combat-active/)

  // close_combat endpoint was called
  expect(closeCombatCalled).toBe(true)
})
