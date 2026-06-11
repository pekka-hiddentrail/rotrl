/**
 * Character speaker activation, dice-tray roll banner, and active_character
 * state persistence tests.
 *
 * Spec: specs/character-system.feature, specs/dice-tray.feature,
 *       specs/session-state.feature
 * Covers: character-system AC-004 (active speaker), AC-005 (speaker badge),
 *         AC-006 (clear active); dice-tray AC-007 (auto-bonus), AC-012
 *         (banner click), AC-013 (portrait in banner);
 *         session-state AC-014 (PUT sets name), AC-015 (party on deselect)
 *
 * All network calls are mocked — no real backend required.
 */
import { expect, test, type Page, type Route } from '@playwright/test'

// ── Character fixtures (matches ui/public/data/player_*.json) ─────────────────

const YANYEEKU = {
  id: 'player_01', name: 'Yanyeeku', color: '#c47a35', rune: 'ᚲ',
  portrait: '/portraits/yanyeeku.png', player: 'Player 1',
  race: 'Kitsune', subrace: '', class: 'Oracle', archetype: 'Flame Mystery',
  alignment: 'CG', deity: 'Desna', level: 1, appearance: 'A festival oracle.',
  hp: { current: 9, max: 9, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac: { total: 16, touch: 12, flatFooted: 14, components: [] },
  initiative: '+2', speed: '30 ft', bab: '+0',
  abilities: [], saves: [], feats: [], weapons: [], inventory: { worn: [], weapons: [], carried: [], wealth: { pp:0, gp:0, sp:0, cp:0 } },
  skills: [{ name: 'Perception', ability: 'WIS', total: 7, ranks: 1, abilityMod: 4, misc: 2 }],
  spells: { concentration: '+5', list: [] },
}

const VANX = {
  id: 'player_02', name: 'Vanx', color: '#5a8fc0', rune: 'ᛉ',
  portrait: '/portraits/vanx.png', player: 'Player 2',
  race: 'Human', subrace: '', class: 'Fighter', archetype: '',
  alignment: 'LN', deity: '', level: 1, appearance: 'A stern fighter.',
  hp: { current: 7, max: 7, hitDie: 'd6', baseDieRoll: 6, conBonus: 1 },
  ac: { total: 12, touch: 10, flatFooted: 12, components: [] },
  initiative: '+1', speed: '30 ft', bab: '+1',
  abilities: [], saves: [], feats: [], weapons: [], inventory: { worn: [], weapons: [], carried: [], wealth: { pp:0, gp:0, sp:0, cp:0 } },
  skills: [{ name: 'Perception', ability: 'WIS', total: 0, ranks: 0, abilityMod: 0, misc: 0 }],
  spells: { concentration: '+0', list: [] },
}

const ANI = {
  id: 'player_03', name: 'Ani', color: '#7a60c0', rune: 'ᚨ',
  portrait: '/portraits/ani.png', player: 'Player 3',
  race: 'Half-Elf', subrace: '', class: 'Cleric', archetype: '',
  alignment: 'NG', deity: 'Sarenrae', level: 1, appearance: 'A healer devoted to the Dawnflower.',
  hp: { current: 11, max: 11, hitDie: 'd8', baseDieRoll: 8, conBonus: 3 },
  ac: { total: 17, touch: 11, flatFooted: 16, components: [] },
  initiative: '+2', speed: '30 ft', bab: '+0',
  abilities: [], saves: [], feats: [], weapons: [], inventory: { worn: [], weapons: [], carried: [], wealth: { pp:0, gp:0, sp:0, cp:0 } },
  skills: [{ name: 'Perception', ability: 'WIS', total: 8, ranks: 1, abilityMod: 4, misc: 3 }],
  spells: { concentration: '+5', list: [] },
}

const ALL_CHARACTERS = [YANYEEKU, VANX, ANI]

// ── Helpers ───────────────────────────────────────────────────────────────────

function sse(...events: object[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function fulfillSse(route: Route, ...events: object[]) {
  await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse(...events) })
}

async function installBaseRoutes(page: Page) {
  await page.route('**/api/characters', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ALL_CHARACTERS) }),
  )
  await page.route('**/api/intro?session=1', route =>
    route.fulfill({ status: 200, contentType: 'text/plain', body: '# The Swallowtail Festival' }),
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

async function setActiveCharacter(page: Page, name: string) {
  await page.getByTitle(new RegExp(name)).click()
  await page.getByText(/Set Active/).click()
}

async function clearActiveCharacter(page: Page, name: string) {
  await page.getByTitle(new RegExp(name)).click()
  await page.getByText(/Clear Active/).click()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.beforeEach(async ({ page }) => {
  await installBaseRoutes(page)
})

// Covers: character-system.feature AC-004, AC-005, AC-006
test('CS-E2E-001 — each character can be activated and shows the Speaking as badge', async ({ page }) => {
  await boot(page)

  for (const character of [YANYEEKU, VANX, ANI]) {
    // Activate this character
    await setActiveCharacter(page, character.name)

    // Speaking as badge appears with the correct name
    await expect(page.getByText(new RegExp(`Speaking as`))).toBeVisible()
    await expect(page.locator('.speaker-badge-label').getByText(character.name)).toBeVisible()

    // The avatar in the sidebar has the active halo style
    await expect(page.getByTitle(new RegExp(character.name))).toHaveClass(/active/)

    // Clear and verify the badge disappears
    await clearActiveCharacter(page, character.name)
    await expect(page.getByText(/Speaking as/)).not.toBeVisible()
    await expect(page.getByTitle(new RegExp(character.name))).not.toHaveClass(/active/)
  }
})

// Covers: dice-tray.feature AC-007, AC-012, AC-013
test('CS-E2E-002 — Ani active: portrait in roll banner, Perception roll with auto-bonus', async ({ page }) => {
  // Mock turn returning a Perception roll request
  await page.route('**/api/sessions/sess-e2e/turn', route =>
    fulfillSse(route,
      { type: 'token', content: 'Something moves in the shadows.' },
      { type: 'roll_request', skill: 'Perception', dc: 15, success: 'You spot the ambush!', failure: 'You miss it.' },
    ),
  )

  // Mock the roll log and resolve endpoints
  await page.route('**/api/sessions/sess-e2e/roll', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  await page.route('**/api/sessions/sess-e2e/resolve_roll', route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ passed: true, outcome: 'You spot the ambush!' }) }),
  )

  await boot(page)

  // Activate Ani
  await setActiveCharacter(page, 'Ani')
  await expect(page.getByText(/Speaking as/)).toBeVisible()

  // Send a turn to trigger the roll request
  await page.getByRole('textbox').fill('I look around carefully')
  await page.getByRole('button', { name: 'Send' }).click()

  // Dice Tray activates with amber border
  await expect(page.locator('.dice-tray-active')).toBeVisible()

  // AC-013 — Ani's portrait and name appear in the banner
  await expect(page.locator('.roll-request-character')).toBeVisible()
  await expect(page.locator('.roll-request-name')).toHaveText('Ani')
  await expect(page.locator('.roll-request-avatar')).toBeVisible()

  // Skill name and DC visible
  await expect(page.locator('.roll-request-skill')).toHaveText('Perception')
  await expect(page.locator('.roll-request-dc')).toHaveText('DC 15')

  // AC-013 — name is styled in Ani's colour
  await expect(page.locator('.roll-request-name')).toHaveCSS('color', 'rgb(122, 96, 192)')

  // AC-012 — click the banner to quick-roll d20
  await page.locator('.roll-request-prompt').click()

  // After rolling, the panel returns to idle (no pending roll banner)
  await expect(page.locator('.roll-request-prompt')).not.toBeVisible()

  // AC-007 — roll history shows Perception modifier in the breakdown
  await expect(page.locator('.hist-skill-label')).toContainText('Perception')
  await expect(page.locator('.hist-skill-label')).toContainText('+8')

  // Result: PASSED badge in history
  await expect(page.locator('.hist-passed')).toBeVisible()
  await expect(page.locator('.hist-passed')).toHaveText('PASSED')

  // Chat shows the player bubble with Ani's roll
  await expect(page.getByText(/Ani rolled/)).toBeVisible()
})

// Covers: session-state.feature AC-014
test('CS-E2E-003 — selecting a character fires PUT /active_character with the PC name', async ({ page }) => {
  const putCalls: { name: string }[] = []

  await page.route('**/api/sessions/sess-e2e/active_character', async route => {
    const body = JSON.parse(route.request().postData() ?? '{}')
    putCalls.push(body)
    await route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ active_character: body.name }) })
  })

  await boot(page)
  await setActiveCharacter(page, 'Ani')

  await expect(async () => {
    expect(putCalls.some(c => c.name === 'Ani')).toBe(true)
  }).toPass()
})

// Covers: session-state.feature AC-015
test('CS-E2E-004 — clearing a character fires PUT /active_character with "party"', async ({ page }) => {
  const putCalls: { name: string }[] = []

  await page.route('**/api/sessions/sess-e2e/active_character', async route => {
    const body = JSON.parse(route.request().postData() ?? '{}')
    putCalls.push(body)
    await route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ active_character: body.name }) })
  })

  await boot(page)
  await setActiveCharacter(page, 'Ani')
  await clearActiveCharacter(page, 'Ani')

  await expect(async () => {
    expect(putCalls.some(c => c.name === 'party')).toBe(true)
  }).toPass()
})
