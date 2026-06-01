/**
 * Spec: specs/roll-initiatives.feature  AC-009
 * Covers: App.tsx handleRollInitiatives — click → rollInitiatives API call →
 *         setCombatState + setCurrentCombatantName updated; error path shows error bar.
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
  rollInitiatives: vi.fn(),
  runEnemyTurn: vi.fn().mockReturnValue((async function* () {})()),
  resolveAttackRoll: vi.fn(),
  resolveDamageRoll: vi.fn(),
  resumeCombat: vi.fn().mockReturnValue((async function* () {})()),
  setActiveCharacter: vi.fn().mockResolvedValue({}),
}))

vi.mock('../data/characters', () => ({
  useCharacters: vi.fn(),
}))

import { bootSession, rollInitiatives, sendTurn } from '../api'
import { useCharacters } from '../data/characters'

const mockBoot = vi.mocked(bootSession)
const mockSend = vi.mocked(sendTurn)
const mockRollInitiatives = vi.mocked(rollInitiatives)
const mockUseCharacters = vi.mocked(useCharacters)

const initialCombatState: CombatState = {
  round: 1,
  current_actor: 'Goblin Warrior 1',
  combatants: [
    { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 13, initiative: 14, status: 'active', conditions: [] },
    { name: 'Thaelion', hp_current: 18, hp_max: 22, ac: 16, initiative: 8, status: 'active', conditions: [] },
  ],
}

const rerolledCombatState: CombatState = {
  round: 1,
  current_actor: 'Thaelion',
  combatants: [
    { name: 'Thaelion', hp_current: 18, hp_max: 22, ac: 16, initiative: 19, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 13, initiative: 6, status: 'active', conditions: [] },
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

async function bootIntoCombat(user: ReturnType<typeof userEvent.setup>) {
  mockBoot.mockImplementation(() => makeGen({ type: 'done' as const, session_id: 'sess-ri' }))
  mockSend.mockImplementation(() => makeGen({ type: 'combat_update' as const, combat_state: initialCombatState }))
  const { container } = render(<App />)
  await user.click(screen.getByRole('button', { name: 'Boot Session' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument())
  await user.type(screen.getByPlaceholderText(/What do you do/i), 'Goblins attack!')
  await user.click(screen.getByRole('button', { name: 'Send' }))
  await waitFor(() => expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeInTheDocument())
  return { container }
}

describe('App — Roll Initiatives wiring (AC-009)', () => {
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

  it('calls rollInitiatives with the session id when button is clicked', async () => {
    const user = userEvent.setup()
    mockRollInitiatives.mockResolvedValue({ combat_state: rerolledCombatState })
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: /Roll Initiatives/i }))

    await waitFor(() => expect(mockRollInitiatives).toHaveBeenCalledWith('sess-ri'))
  })

  it('updates CombatPanel with the new current_actor after rolling', async () => {
    const user = userEvent.setup()
    mockRollInitiatives.mockResolvedValue({ combat_state: rerolledCombatState })
    const { container } = await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: /Roll Initiatives/i }))

    // Thaelion should now be the highlighted current actor (initiative 19 after reroll)
    await waitFor(() => {
      const currentRow = container.querySelector('.combatant-current')
      expect(currentRow).not.toBeNull()
      expect(currentRow!.textContent).toContain('Thaelion')
    })
  })

  it('shows an error message when rollInitiatives fails', async () => {
    const user = userEvent.setup()
    mockRollInitiatives.mockRejectedValue(new Error('Roll initiatives failed (503)'))
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: /Roll Initiatives/i }))

    await waitFor(() =>
      expect(screen.getByText(/Roll initiatives failed/i)).toBeInTheDocument(),
    )
  })

  it('does not change combatState when rollInitiatives fails', async () => {
    const user = userEvent.setup()
    mockRollInitiatives.mockRejectedValue(new Error('503'))
    const { container } = await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: /Roll Initiatives/i }))

    await waitFor(() => expect(mockRollInitiatives).toHaveBeenCalled())
    // Original current_actor still shown — Goblin Warrior 1 should still be current
    const currentRow = container.querySelector('.combatant-current')
    expect(currentRow).not.toBeNull()
    expect(currentRow!.textContent).toContain('Goblin Warrior 1')
  })
})
