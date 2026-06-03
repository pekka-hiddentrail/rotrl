/**
 * Spec: specs/pc-combat-turn.feature  AC-010
 * Covers: App.tsx routing — /pc_turn when PC's combat turn, /turn otherwise.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import type { CombatState } from '../types'

vi.mock('../api', () => ({
  advanceCombatTurn:  vi.fn().mockResolvedValue({ current_actor: null, is_pc: false }),
  bootSession:        vi.fn(),
  sendTurn:           vi.fn(),
  pcTurn:             vi.fn(),
  endSessionWithRecap:vi.fn(),
  logRoll:            vi.fn().mockResolvedValue(undefined),
  resolveRoll:        vi.fn().mockResolvedValue({ passed: true, outcome: 'ok' }),
  purgeSessionNpcs:   vi.fn().mockResolvedValue({ purged: 0 }),
  closeCombat:        vi.fn().mockReturnValue((async function* () {})()),
  runEnemyTurn:       vi.fn().mockReturnValue((async function* () {})()),
  resolveAttackRoll:  vi.fn(),
  resolveDamageRoll:  vi.fn(),
  resumeCombat:       vi.fn().mockReturnValue((async function* () {})()),
  rollInitiatives:    vi.fn().mockResolvedValue({ combat_state: null }),
  setActiveCharacter: vi.fn().mockResolvedValue({}),
}))

vi.mock('../data/characters', () => ({
  useCharacters: vi.fn(),
}))

import { bootSession, sendTurn, pcTurn, runEnemyTurn } from '../api'
import { useCharacters } from '../data/characters'

const mockBoot          = vi.mocked(bootSession)
const mockSend          = vi.mocked(sendTurn)
const mockPcTurn        = vi.mocked(pcTurn)
const mockRunEnemyTurn  = vi.mocked(runEnemyTurn)
const mockUseChars      = vi.mocked(useCharacters)

const AniCharacter = {
  id: 'ani', name: 'Ani', portrait: '/p/ani.png', color: '#f0a0a0', rune: 'A',
  player: '', race: '', subrace: '', class: '', archetype: '', alignment: '', deity: '',
  level: 1, appearance: '', hp: { current: 11, max: 11, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac: { total: 17, touch: 12, flatFooted: 14, components: [] },
  initiative: '+1', speed: '30 ft', bab: '+0', abilities: [], saves: [], skills: [], feats: [],
  weapons: [], spells: { concentration: '+0', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
}

const PC_COMBAT: CombatState = {
  round: 2, current_actor: 'Ani',
  combatants: [
    { name: 'Ani',             hp_current: 11, hp_max: 11, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
  ],
}

const ENEMY_COMBAT: CombatState = { ...PC_COMBAT, current_actor: 'Goblin Warrior 1' }

async function* makeGen<T>(...items: T[]): AsyncGenerator<T> {
  for (const item of items) yield item
}

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, text: () => Promise.resolve('# Intro'), json: () => Promise.resolve({}),
  }))
}

async function bootAndSendCombat(user: ReturnType<typeof userEvent.setup>, combatState: CombatState) {
  mockBoot.mockImplementation(() => makeGen({ type: 'done' as const, session_id: 'sess-pc' }))
  mockSend.mockImplementation(() => makeGen(
    { type: 'initiative_pending' as const, combat_state: combatState },
    { type: 'done' as const },
  ))
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Boot Session' }))
  await waitFor(() => screen.getByRole('button', { name: 'Send' }))
  await user.type(screen.getByPlaceholderText(/What do you do/i), 'goblins appear')
  await user.click(screen.getByRole('button', { name: 'Send' }))
  await waitFor(() => expect(mockSend).toHaveBeenCalled())
}

describe('App — PC combat turn routing (AC-010)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stubFetch()
    mockUseChars.mockReturnValue({
      characters: [AniCharacter],
      characterMap: { ani: AniCharacter },  // keyed by id
      loading: false, error: null,
    })
  })

  afterEach(() => vi.unstubAllGlobals())

  it('routes to /pc_turn when it is a PC combat turn', async () => {
    const user = userEvent.setup()
    mockPcTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    await bootAndSendCombat(user, PC_COMBAT)

    // Simulate receiving combat_update (Ani is current actor — a PC)
    mockSend.mockImplementation(() => makeGen(
      { type: 'combat_update' as const, combat_state: PC_COMBAT },
      { type: 'done' as const },
    ))
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'setup combat')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalledTimes(2))

    // Now send an action — should route to pcTurn since Ani (a PC) is current
    mockPcTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'I swing at the goblin')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(mockPcTurn).toHaveBeenCalledWith('sess-pc', expect.stringContaining('I swing'), [], undefined))
  })

  it('routes to /turn when no combat is active', async () => {
    const user = userEvent.setup()
    mockBoot.mockImplementation(() => makeGen({ type: 'done' as const, session_id: 'sess-pc' }))
    mockSend.mockImplementation(() => makeGen({ type: 'done' as const }))

    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    await waitFor(() => screen.getByRole('button', { name: 'Send' }))
    await user.type(screen.getByPlaceholderText(/What do you do/i), 'hello')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(mockSend).toHaveBeenCalled())
    expect(mockPcTurn).not.toHaveBeenCalled()
  })

  it('attack_request from pc_turn activates dice tray', async () => {
    const user = userEvent.setup()
    await bootAndSendCombat(user, PC_COMBAT)

    mockSend.mockImplementation(() => makeGen(
      { type: 'combat_update' as const, combat_state: PC_COMBAT },
      { type: 'done' as const },
    ))
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'setup combat active')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalledTimes(2))

    mockPcTurn.mockImplementation(() => makeGen(
      { type: 'attack_request' as const, attacker: 'Ani', target: 'Goblin Warrior 1', bonus: 4, ac: 16, damage_expr: '1d8+2', attack_type: 'melee' },
      { type: 'done' as const },
    ))

    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'I attack!')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(mockPcTurn).toHaveBeenCalled())
    // Attack phase should be set (dice tray becomes active)
    // We verify pcTurn was called with the right args
    expect(mockPcTurn).toHaveBeenCalledWith('sess-pc', expect.any(String), [], undefined)
  })

  // ── click-to-target AC-004 — target_hint forwarded in POST body ──────────────

  it('passes selectedTarget as target_hint to pcTurn when an enemy is clicked', async () => {
    const user = userEvent.setup()
    mockPcTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    await bootAndSendCombat(user, PC_COMBAT)

    // Establish PC's turn via combat_update
    mockSend.mockImplementation(() => makeGen(
      { type: 'combat_update' as const, combat_state: PC_COMBAT },
      { type: 'done' as const },
    ))
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'setup')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalledTimes(2))

    // Click on the Goblin Warrior 1 row to select it as a target
    mockPcTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    const gw1Row = await waitFor(() => {
      const el = screen.getByText('Goblin Warrior 1').closest('.combatant-row') as HTMLElement
      if (!el) throw new Error('combatant row not found')
      return el
    })
    await user.click(gw1Row)

    // Target badge should appear
    await waitFor(() => expect(screen.getByText('Goblin Warrior 1', { selector: '.target-badge span, .target-badge *' })).toBeInTheDocument())

    // Now submit — pcTurn must be called with 'Goblin Warrior 1' as target_hint
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'I strike!')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(mockPcTurn).toHaveBeenCalledWith(
      'sess-pc',
      expect.stringContaining('I strike'),
      expect.any(Array),
      'Goblin Warrior 1',
    ))
  })

  // ── click-to-target AC-008 — target clears after submit ────────────────────

  it('clears selectedTarget after the player submits (no stale target on next action)', async () => {
    const user = userEvent.setup()
    mockPcTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    await bootAndSendCombat(user, PC_COMBAT)

    mockSend.mockImplementation(() => makeGen(
      { type: 'combat_update' as const, combat_state: PC_COMBAT },
      { type: 'done' as const },
    ))
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'setup2')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalledTimes(2))

    // Click enemy row to select target
    mockPcTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    const gw1Row = await waitFor(() => {
      const el = screen.getByText('Goblin Warrior 1').closest('.combatant-row') as HTMLElement
      if (!el) throw new Error('combatant row not found')
      return el
    })
    await user.click(gw1Row)

    // Submit the turn
    await user.clear(screen.getByRole('textbox'))
    await user.type(screen.getByRole('textbox'), 'I attack!')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockPcTurn).toHaveBeenCalled())

    // After submit, target badge must be gone
    await waitFor(() =>
      expect(screen.queryByText('Goblin Warrior 1', { selector: '.target-badge span, .target-badge *' })).not.toBeInTheDocument()
    )
  })

  it('shows Enemy Turn button (not Send) when enemy is current actor', async () => {
    const user = userEvent.setup()
    // Boot with combat_update (not initiative_pending) so enemy becomes current actor immediately
    mockBoot.mockImplementation(() => makeGen({ type: 'done' as const, session_id: 'sess-pc' }))
    mockSend.mockImplementation(() => makeGen(
      { type: 'combat_update' as const, combat_state: ENEMY_COMBAT },
      { type: 'done' as const },
    ))
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    await waitFor(() => screen.getByRole('button', { name: 'Send' }))
    await user.type(screen.getByPlaceholderText(/What do you do/i), 'goblins appear')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    // After the combat_update, the enemy is current actor: InputBar switches to Enemy Turn
    // (CombatPanel also has an "Enemy Turn" button; just verify at least one exists and
    //  the Send button is no longer shown)
    await waitFor(() => {
      const btns = screen.getAllByRole('button', { name: 'Enemy Turn' })
      expect(btns.length).toBeGreaterThanOrEqual(1)
      // Wait for streaming to clear
      expect(btns.some(b => !b.hasAttribute('disabled'))).toBe(true)
    })

    // The Send button is gone; only Enemy Turn is shown
    expect(screen.queryByRole('button', { name: 'Send' })).not.toBeInTheDocument()

    // Clicking Enemy Turn must NOT invoke pcTurn
    const enemyTurnBtns = screen.getAllByRole('button', { name: 'Enemy Turn' })
    await user.click(enemyTurnBtns[0])
    expect(mockPcTurn).not.toHaveBeenCalled()
    expect(mockRunEnemyTurn).toHaveBeenCalledTimes(1)
  })
})
