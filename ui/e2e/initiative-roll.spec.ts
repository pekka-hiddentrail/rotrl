import { expect, test, type Page } from '@playwright/test'

// Spec: specs/roll-initiatives.feature  AC-007, AC-008, AC-009
//
// Covers the user-triggered initiative-roll flow:
//
//   1. A combat event fires on the same turn as %%COMBAT%% round 1
//   2. Backend emits "initiative_pending" SSE (not "combat_update")
//      → CombatPanel stays hidden; DicePanel stays in right column
//   3. DicePanel shows "⚔ Combat begins — roll for initiative" banner
//      with a "Roll for all combatants" button
//   4. User clicks the button → POST /roll_initiatives returns a rolled combat_state
//   5. CombatPanel appears (left ← DicePanel, right ← CombatPanel)
//   6. Combatants are sorted descending by rolled initiative

// ── Fixtures ─────────────────────────────────────────────────────────────────

/** Seeded-but-unrolled state: backend seeded combatants, no initiatives yet. */
const pendingCombatState = {
  round: 1,
  current_actor: null,
  combatants: [
    { name: 'Goblin Warchanter', hp_current: 8,  hp_max: 8,  ac: 14, initiative: 0, status: 'active',  conditions: [] },
    { name: 'Goblin Warrior 1',  hp_current: 5,  hp_max: 5,  ac: 16, initiative: 0, status: 'active',  conditions: [] },
    { name: 'Ani',               hp_current: 11, hp_max: 11, ac: 17, initiative: 0, status: 'active',  conditions: [] },
    { name: 'Yanyeeku',          hp_current: 7,  hp_max: 7,  ac: 12, initiative: 0, status: 'active',  conditions: [] },
  ],
}

/** Rolled state returned by POST /roll_initiatives.
 *  Warchanter rolled 18, Yanyeeku 15, Warrior 9, Ani 6. */
const rolledCombatState = {
  round: 1,
  current_actor: 'Goblin Warchanter',
  combatants: [
    { name: 'Goblin Warchanter', hp_current: 8,  hp_max: 8,  ac: 14, initiative: 18, status: 'active', conditions: [] },
    { name: 'Yanyeeku',          hp_current: 7,  hp_max: 7,  ac: 12, initiative: 15, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',  hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
    { name: 'Ani',               hp_current: 11, hp_max: 11, ac: 17, initiative: 6,  status: 'active', conditions: [] },
  ],
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function sse(events: unknown[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function routeJson(page: Page, url: string, body: unknown) {
  await page.route(url, route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(body),
  }))
}

async function routeSse(page: Page, url: string, events: unknown[]) {
  await page.route(url, route => route.fulfill({
    status: 200, contentType: 'text/event-stream', body: sse(events),
  }))
}

async function setupCommonRoutes(page: Page) {
  await routeJson(page, '**/api/characters', [])
  await page.route('**/api/intro?session=1', route => route.fulfill({
    status: 200, contentType: 'text/plain', body: '# Session 1',
  }))
  await routeSse(page, '**/api/sessions', [{ type: 'done', session_id: 'sess-init' }])
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function sendInitiativeTurn(page: Page) {
  await page.getByRole('textbox').fill('The goblins charge!')
  await page.getByRole('button', { name: 'Send' }).click()
  // Wait for the initiative banner — confirms initiative_pending event was received
  await expect(page.locator('.initiative-banner')).toBeVisible({ timeout: 15_000 })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('Initiative roll flow', () => {

  test('shows initiative banner before CombatPanel when combat event fires', async ({ page }) => {
    await setupCommonRoutes(page)
    // Turn returns initiative_pending (not combat_update) — CombatPanel must stay hidden
    await routeSse(page, '**/api/sessions/sess-init/turn', [
      { type: 'initiative_pending', combat_state: pendingCombatState },
      { type: 'done' },
    ])

    await boot(page)
    await sendInitiativeTurn(page)

    // DicePanel (right column) shows the combat-start banner
    await expect(page.locator('.initiative-banner')).toBeVisible()
    await expect(page.locator('.initiative-banner-label')).toContainText('Combat begins')
    await expect(page.getByRole('button', { name: /Roll for all combatants/i })).toBeVisible()

    // CombatPanel must NOT yet be visible — it only appears after rolling
    await expect(page.locator('.combat-panel')).not.toBeVisible()
  })

  test('DicePanel stays in right column until initiatives are rolled', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-init/turn', [
      { type: 'initiative_pending', combat_state: pendingCombatState },
      { type: 'done' },
    ])

    await boot(page)
    await sendInitiativeTurn(page)

    // No combat-active class yet → DicePanel is still in right column position
    const mainContent = page.locator('.main-content')
    await expect(mainContent).not.toHaveClass(/combat-active/)
  })

  test('clicking Roll for all combatants shows CombatPanel with rolled order', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-init/turn', [
      { type: 'initiative_pending', combat_state: pendingCombatState },
      { type: 'done' },
    ])
    // POST /roll_initiatives returns the server-rolled combat state
    await routeJson(page, '**/api/sessions/sess-init/combat/roll_initiatives', {
      combat_state: rolledCombatState,
    })

    await boot(page)
    await sendInitiativeTurn(page)
    await page.getByRole('button', { name: /Roll for all combatants/i }).click()

    // CombatPanel must now be visible with rolled initiatives
    await expect(page.locator('.combat-panel')).toBeVisible({ timeout: 5_000 })

    // First row = highest initiative = Goblin Warchanter (rolled 18)
    const rows = page.locator('.combatant-row')
    await expect(rows.first()).toContainText('Goblin Warchanter')

    // Round badge appears
    await expect(page.locator('.combat-round-badge')).toContainText('Round 1')
  })

  test('initiative banner disappears after rolling', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-init/turn', [
      { type: 'initiative_pending', combat_state: pendingCombatState },
      { type: 'done' },
    ])
    await routeJson(page, '**/api/sessions/sess-init/combat/roll_initiatives', {
      combat_state: rolledCombatState,
    })

    await boot(page)
    await sendInitiativeTurn(page)
    await page.getByRole('button', { name: /Roll for all combatants/i }).click()

    await expect(page.locator('.combat-panel')).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('.initiative-banner')).not.toBeVisible()
  })

  test('CombatPanel shows PC HP seeded from profiles (not 0/0)', async ({ page }) => {
    await setupCommonRoutes(page)
    await routeSse(page, '**/api/sessions/sess-init/turn', [
      { type: 'initiative_pending', combat_state: pendingCombatState },
      { type: 'done' },
    ])
    await routeJson(page, '**/api/sessions/sess-init/combat/roll_initiatives', {
      combat_state: rolledCombatState,
    })

    await boot(page)
    await sendInitiativeTurn(page)
    await page.getByRole('button', { name: /Roll for all combatants/i }).click()

    await expect(page.locator('.combat-panel')).toBeVisible({ timeout: 5_000 })

    // Ani's HP should be 11/11, not 0/0 (seeded from pc_profiles)
    await expect(page.locator('.combatant-row', { hasText: 'Ani' })).toContainText('11/11')
  })

})
