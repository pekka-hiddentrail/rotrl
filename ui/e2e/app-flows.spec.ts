import { expect, test, type Page, type Route } from '@playwright/test'

const character = {
  id: 'yanyeeku',
  portrait: '/portraits/yanyeeku.png',
  color: '#a060d0',
  rune: 'Y',
  name: 'Yanyeeku',
  player: 'Player 1',
  race: 'Kitsune',
  subrace: '',
  class: 'Oracle',
  archetype: 'Flame Mystery',
  alignment: 'CG',
  deity: 'Desna',
  level: 1,
  appearance: 'A festival oracle.',
  hp: { current: 9, max: 9, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac: { total: 16, touch: 12, flatFooted: 14, components: [{ source: 'Armor', value: 4 }] },
  initiative: '+2',
  speed: '30 ft',
  bab: '+0',
  abilities: [
    { name: 'STR', score: 10, mod: '+0' },
    { name: 'DEX', score: 14, mod: '+2' },
    { name: 'CON', score: 12, mod: '+1' },
    { name: 'INT', score: 11, mod: '+0' },
    { name: 'WIS', score: 13, mod: '+1' },
    { name: 'CHA', score: 18, mod: '+4' },
  ],
  saves: [
    { name: 'Fortitude', ability: 'CON', total: '+1', base: '+0', abilityMod: '+1', magic: '+0', misc: '+0' },
    { name: 'Reflex', ability: 'DEX', total: '+2', base: '+0', abilityMod: '+2', magic: '+0', misc: '+0' },
    { name: 'Will', ability: 'WIS', total: '+3', base: '+2', abilityMod: '+1', magic: '+0', misc: '+0' },
  ],
  skills: [{ name: 'Perception', ability: 'WIS', total: 7, ranks: 1, abilityMod: 1, misc: 5 }],
  feats: [{ name: 'Selective Channeling', desc: 'Exclude targets.' }],
  weapons: [{
    display: 'Morningstar +0 (1d8)',
    name: 'Morningstar',
    type: 'Melee',
    atk: '+0',
    dmg: '1d8',
    crit: 'x2',
    range: '-',
    dmgType: 'B/P',
    special: '',
    ammo: '',
  }],
  spells: {
    concentration: '+5',
    list: [{
      name: 'Detect Magic',
      level: '0',
      perDay: 'at will',
      castTime: '1 standard action',
      duration: 'concentration',
      range: '60 ft',
      components: 'V, S',
      school: 'divination',
      target: 'cone',
      cl: 1,
      sr: 'no',
      save: 'none',
      effect: 'Detects magic.',
    }],
  },
  inventory: {
    worn: ['Explorer outfit'],
    weapons: ['Morningstar'],
    carried: ['Holy symbol'],
    wealth: { pp: 0, gp: 10, sp: 0, cp: 0 },
  },
}

function sse(...events: object[]) {
  return events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('')
}

async function fulfillSse(route: Route, ...events: object[]) {
  await route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: sse(...events),
  })
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
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ purged: 2 }) }),
  )
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.getByText(/Session 1/)).toBeVisible()
}

test.beforeEach(async ({ page }) => {
  await installBaseRoutes(page)
})

// Covers: session-boot.feature AC-001
test('boot shows the session badge', async ({ page }) => {
  await boot(page)

  await expect(page.getByText(/llama-3.3-70b-versatile/)).toBeVisible()
})

// Covers: chat-display.feature AC-001, AC-002
test('send turn displays a streamed GM message', async ({ page }) => {
  await page.route('**/api/sessions/sess-e2e/turn', route =>
    fulfillSse(
      route,
      { type: 'token', content: 'The square ' },
      { type: 'token', content: 'wakes.' },
    ),
  )
  await boot(page)

  await page.getByRole('textbox').fill('look around')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('The square wakes.')).toBeVisible()
})

// Covers: dice-panel.feature AC-001, AC-002, AC-003
test('roll_request event activates the dice panel', async ({ page }) => {
  await page.route('**/api/sessions/sess-e2e/turn', route =>
    fulfillSse(route, {
      type: 'roll_request',
      skill: 'Perception',
      dc: 18,
      success: 'You spot it.',
      failure: 'You miss it.',
    }),
  )
  await boot(page)

  await page.getByRole('textbox').fill('check for trouble')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.locator('.dice-panel-active')).toBeVisible()
  await expect(page.getByText('Perception')).toBeVisible()
  await expect(page.getByText('DC 18')).toBeVisible()
})

// Covers: session-end-recap.feature AC-001
test('end session clears chat and returns to pre-boot', async ({ page }) => {
  await page.route('**/api/sessions/sess-e2e/end', route =>
    fulfillSse(
      route,
      { type: 'status', message: 'Writing recap to disk...' },
      { type: 'done' },
    ),
  )
  await boot(page)

  await page.getByRole('button', { name: 'End Session' }).click()

  await expect(page.getByRole('button', { name: 'Boot Session' })).toBeVisible({ timeout: 6_000 })
  await expect(page.getByText(/Session 1/)).not.toBeVisible()
})

// Covers: session-controls.feature AC-002
test('Kill button confirms and resets stuck ending flow', async ({ page }) => {
  let releaseEnd: (() => void) | null = null
  await page.route('**/api/sessions/sess-e2e/end', async route => {
    await new Promise<void>(resolve => { releaseEnd = resolve })
    await route.abort().catch(() => undefined)
  })
  await boot(page)

  await page.getByRole('button', { name: 'End Session' }).click()
  await expect(page.getByRole('button', { name: 'Kill' })).toBeVisible()
  await page.getByRole('button', { name: 'Kill' }).click()
  await expect(page.getByText('Discard and quit?')).toBeVisible()
  await page.getByRole('button', { name: 'No' }).click()
  await expect(page.getByRole('button', { name: 'Kill' })).toBeVisible()

  await page.getByRole('button', { name: 'Kill' }).click()
  await page.getByRole('button', { name: 'Yes' }).click()

  await expect(page.getByRole('button', { name: 'Boot Session' })).toBeVisible()
  releaseEnd?.()
})

// Covers: npc-system.feature AC-001
test('Purge NPCs confirms inline and shows a toast', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('button', { name: /Tools/ }).click()
  await page.getByRole('button', { name: /Purge Session NPCs/ }).click()
  await expect(page.getByText('Purge session NPCs?')).toBeVisible()
  await page.getByRole('button', { name: 'Yes' }).click()

  await expect(page.getByText('2 session NPC directories removed.')).toBeVisible()
})

// Covers: character-system.feature AC-001, AC-002
test('character sidebar opens the character sheet modal', async ({ page }) => {
  await page.goto('/')

  await page.getByTitle(/Yanyeeku/).click()
  await page.getByText(/Open Sheet/).click()

  await expect(page.locator('.sheet-panel')).toBeVisible()
  await expect(page.getByText('Ability Scores')).toBeVisible()
  await expect(page.getByText('Morningstar +0 (1d8)')).toBeVisible()
})
