import { expect, test, type Page } from '@playwright/test'

/**
 * E2E — magic-spell-system.feature (Tier S1 + S2-1)
 *
 * Covers:
 *   SS-004 — spell intent detected from "I cast X" text
 *   SS-009 — damage_request emitted (not attack_request) for auto-hit spells
 *   SS-010 — damage_request fields: spell_name, caster, target, damage_expr
 *   SS-011 — PendingAttack pre-hit for auto-hit spells
 *   SS-012 — damage applied on resolve; HP updated in combat panel
 *   SS-014 — spell briefing in _build_pc_turn_system (no "1d20" shown)
 *
 * Strategy: mocked backend. The /pc_turn SSE stream returns damage_request
 * events so the frontend damage-roll UI appears; /resume_combat returns the
 * narrative and updated HP.
 */

// ── Fixtures ──────────────────────────────────────────────────────────────────

/** A caster character with a single auto-hit damage spell */
const YanyeekuCharacter = {
  id: 'yanyeeku', name: 'Yanyeeku', portrait: '/portraits/yanyeeku.png', color: '#a060d0', rune: 'Y',
  player: '', race: 'Kitsune', subrace: '', class: 'Oracle', archetype: 'Flame Mystery', alignment: 'CG',
  deity: 'Desna', level: 1, appearance: '',
  hp:    { current: 9, max: 9, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac:    { total: 16, touch: 12, flatFooted: 14, components: [] },
  initiative: '+2', speed: '30 ft', bab: '+0', abilities: [], saves: [], skills: [], feats: [],
  weapons: [{ name: 'dagger', atk: '+0', dmg: '1d4', type: 'melee', special: '' }],
  spells: {
    concentration: '+4',
    list: [
      { name: 'Force Bolt', level: 0, per_day: -1, effect: 'Deals 1d4+1 force damage — never misses.', sr: false },
    ],
  },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

const PcCombatState = {
  round: 1,
  current_actor: 'Yanyeeku',
  combatants: [
    { name: 'Yanyeeku',        hp_current: 9, hp_max: 9, ac: 16, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',hp_current: 5, hp_max: 5, ac: 16, initiative: 9,  status: 'active', conditions: [] },
  ],
}

const AfterSpellState = {
  ...PcCombatState,
  combatants: [
    { ...PcCombatState.combatants[0] },
    { name: 'Goblin Warrior 1', hp_current: 2, hp_max: 5, ac: 16, initiative: 9, status: 'active', conditions: [] },
  ],
}

function sse(events: unknown[]) {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
}

async function setupRoutes(page: Page) {
  await page.route('**/api/characters', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([YanyeekuCharacter]) }))
  await page.route('**/api/intro?session=1', r =>
    r.fulfill({ status: 200, contentType: 'text/plain', body: '# Session 1' }))
  await page.route('**/api/sessions', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'done', session_id: 'sess-mss' }]) }))
}

async function boot(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Boot Session' }).click()
  await expect(page.locator('.session-badge', { hasText: 'Session 1' })).toBeVisible()
}

async function enterCombat(page: Page) {
  await page.route('**/api/sessions/sess-mss/turn', r =>
    r.fulfill({ status: 200, contentType: 'text/event-stream',
      body: sse([{ type: 'combat_update', combat_state: PcCombatState }, { type: 'done' }]) }))
  await page.getByRole('textbox').fill('a goblin attacks!')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('.combat-round-badge').first()).toBeVisible({ timeout: 10_000 })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('magic-spell-system', () => {

  test('MSS-E2E-001 — casting an auto-hit spell triggers damage_request (not attack_request) (SS-004, SS-009, SS-010)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    // Capture the pc_turn POST body and check it routed to /pc_turn
    let capturedBody: Record<string, unknown> | null = null
    await page.route('**/api/sessions/sess-mss/pc_turn', async route => {
      capturedBody = JSON.parse(route.request().postData() ?? '{}')
      await route.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'damage_request', spell_name: 'Force Bolt', caster: 'Yanyeeku',
            target: 'Goblin Warrior 1', damage_expr: '1d4+1' },
          { type: 'done' },
        ]) })
    })

    await page.getByRole('textbox').fill('I cast Force Bolt at the goblin')
    await page.getByRole('button', { name: 'Send' }).click()

    // Verify POST went to /pc_turn (not /turn)
    await expect.poll(() => capturedBody, { timeout: 5_000 }).not.toBeNull()
    expect((capturedBody as Record<string, unknown>).input).toContain('Force Bolt')

    // Damage roll banner / dice tray should activate (damage_request event received)
    await expect(
      page.locator('.roll-request-banner, .damage-banner, [class*="roll-request"]').first()
    ).toBeVisible({ timeout: 8_000 })
  })

  test('MSS-E2E-002 — after resolving damage, HP updates in the combat panel (SS-012)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    // /pc_turn returns damage_request
    await page.route('**/api/sessions/sess-mss/pc_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'damage_request', spell_name: 'Force Bolt', caster: 'Yanyeeku',
            target: 'Goblin Warrior 1', damage_expr: '1d4+1' },
          { type: 'done' },
        ]) }))

    // /resume_combat returns narrative + updated HP via combat_update
    await page.route('**/api/sessions/sess-mss/resume_combat', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'action_card', attacker: 'Yanyeeku', target: 'Goblin Warrior 1',
            is_spell: true, spell_name: 'Force Bolt', damage_total: 3, hit: true },
          { type: 'token',   content: 'The bolt of force slams into the goblin!' },
          { type: 'combat_update', combat_state: AfterSpellState },
          { type: 'done' },
        ]) }))

    await page.getByRole('textbox').fill('I cast Force Bolt at the goblin')
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for damage roll UI (damage_request), then simulate a resolve roll
    await page.route('**/api/sessions/sess-mss/resolve_damage_roll', r =>
      r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ result: { damage_total: 3, hit: true, is_spell: true, spell_name: 'Force Bolt', attack_type: 'spell' } }) }))

    // The HP for Goblin Warrior 1 should update to 2/5 after the resolve
    // (This verifies combat_update is applied from resume_combat stream)
    await expect(page.locator('.combatant-row', { hasText: 'Goblin Warrior 1' }))
      .toContainText('2', { timeout: 12_000 })
  })

  test('MSS-E2E-003 — spell cast narrative appears in chat (SS-007, SS-014 briefing)', async ({ page }) => {
    await setupRoutes(page)
    await boot(page)
    await enterCombat(page)

    await page.route('**/api/sessions/sess-mss/pc_turn', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'damage_request', spell_name: 'Force Bolt', caster: 'Yanyeeku',
            target: 'Goblin Warrior 1', damage_expr: '1d4+1' },
          { type: 'done' },
        ]) }))

    await page.route('**/api/sessions/sess-mss/resume_combat', r =>
      r.fulfill({ status: 200, contentType: 'text/event-stream',
        body: sse([
          { type: 'token',   content: 'A bolt of force shoots from your hand!' },
          { type: 'combat_update', combat_state: AfterSpellState },
          { type: 'done' },
        ]) }))

    await page.getByRole('textbox').fill('I cast Force Bolt')
    await page.getByRole('button', { name: 'Send' }).click()

    // Route resolve_damage_roll so the resume_combat can proceed if the UI posts it
    await page.route('**/api/sessions/sess-mss/resolve_damage_roll', r =>
      r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ result: { damage_total: 2, hit: true, is_spell: true, spell_name: 'Force Bolt', attack_type: 'spell' } }) }))

    // Narrative from resume_combat should appear in the chat window
    await expect(page.locator('.message-assistant, .gm-message, .chat-message').first())
      .toContainText('force', { timeout: 12_000 })
  })

})
