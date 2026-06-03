/**
 * Spec: specs/roll-initiatives.feature  AC-008
 * Covers: App.tsx handles combat_update SSE with reordered combatants after
 *         auto-initiative roll — CombatPanel reflects server-rolled order.
 * The roll happens automatically on the backend; no player button is involved.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import type { CombatState } from '../types'

vi.mock('../api', () => ({
  advanceCombatTurn: vi.fn().mockResolvedValue({ current_actor: 'Goblin Warrior 1', is_pc: false }),
  bootSession: vi.fn(),
  sendTurn: vi.fn(),
  endSessionWithRecap: vi.fn(),
  logRoll: vi.fn().mockResolvedValue(undefined),
  resolveRoll: vi.fn().mockResolvedValue({ passed: true, outcome: 'ok' }),
  purgeSessionNpcs: vi.fn().mockResolvedValue({ purged: 0 }),
  closeCombat: vi.fn().mockReturnValue((async function* () {})()),
  runEnemyTurn: vi.fn().mockReturnValue((async function* () {})()),
  resolveAttackRoll: vi.fn(),
  resolveDamageRoll: vi.fn(),
  resumeCombat: vi.fn().mockReturnValue((async function* () {})()),
  setActiveCharacter: vi.fn().mockResolvedValue({}),
}))

vi.mock('../data/characters', () => ({
  useCharacters: vi.fn(),
  loadCharacterSheet: vi.fn(),
}))

import { bootSession, sendTurn } from '../api'
import { useCharacters } from '../data/characters'

const mockBoot = vi.mocked(bootSession)
const mockSend = vi.mocked(sendTurn)
const mockUseCharacters = vi.mocked(useCharacters)

// State the backend emits AFTER auto-rolling initiatives (server-sorted, server-rolled values)
const autoRolledCombatState: CombatState = {
  round: 1,
  current_actor: 'Goblin Warchanter',
  combatants: [
    { name: 'Goblin Warchanter', hp_current: 8,  hp_max: 8,  ac: 14, initiative: 18, status: 'active', conditions: [] },
    { name: 'Ani',               hp_current: 11, hp_max: 11, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',  hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
  ],
}

async function* makeGen<T>(...items: T[]): AsyncGenerator<T> {
  for (const item of items) yield item
}

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    text: () => Promise.resolve('# Intro'),
    json: () => Promise.resolve({}),
  }))
}

async function bootIntoAutoRolledCombat(user: ReturnType<typeof userEvent.setup>) {
  mockBoot.mockImplementation(() => makeGen({ type: 'done' as const, session_id: 'sess-ri' }))
  // Backend emits combat_update with the auto-rolled state (no button click needed)
  mockSend.mockImplementation(() => makeGen(
    { type: 'combat_update' as const, combat_state: autoRolledCombatState },
    { type: 'done' as const },
  ))
  const { container } = render(<App />)
  await user.click(screen.getByRole('button', { name: 'Boot Session' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument())
  await user.type(screen.getByPlaceholderText(/What do you do/i), 'Goblins attack!')
  await user.click(screen.getByRole('button', { name: 'Send' }))
  await waitFor(() => expect(screen.getByText('Round 1')).toBeInTheDocument())
  return { container }
}

describe('App — Auto-initiative roll via combat_update SSE (AC-008)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stubFetch()
    mockUseCharacters.mockReturnValue({
      characters: [],
      characterMap: {},
      loading: false,
      error: null,
    })
  })

  afterEach(() => vi.unstubAllGlobals())

  it('CombatPanel shows server-rolled initiative order from combat_update', async () => {
    const user = userEvent.setup()
    const { container } = await bootIntoAutoRolledCombat(user)

    const rows = container.querySelectorAll('.combatant-row')
    expect(rows.length).toBeGreaterThanOrEqual(3)
    // Goblin Warchanter rolled 18 → should be first row
    expect(rows[0].textContent).toContain('Goblin Warchanter')
    expect(rows[1].textContent).toContain('Ani')
    expect(rows[2].textContent).toContain('Goblin Warrior 1')
  })

  it('current actor is the highest-initiative combatant from auto-roll', async () => {
    const user = userEvent.setup()
    const { container } = await bootIntoAutoRolledCombat(user)

    const current = container.querySelector('.combatant-current')
    expect(current).not.toBeNull()
    expect(current!.textContent).toContain('Goblin Warchanter')
  })

  it('no Roll Initiatives button is visible', async () => {
    const user = userEvent.setup()
    await bootIntoAutoRolledCombat(user)
    expect(screen.queryByRole('button', { name: /Roll Initiatives/i })).toBeNull()
  })
})
