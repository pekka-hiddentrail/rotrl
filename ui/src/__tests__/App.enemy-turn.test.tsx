/**
 * Spec: specs/enemy-turn.feature
 * Covers: enemy-turn.feature AC-014
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
  runEnemyTurn: vi.fn(),
  resolveAttackRoll: vi.fn(),
  resolveDamageRoll: vi.fn(),
  resumeCombat: vi.fn().mockReturnValue((async function* () {})()),
  setActiveCharacter: vi.fn().mockResolvedValue({}),
}))

vi.mock('../data/characters', () => ({
  useCharacters: vi.fn(),
}))

import { bootSession, closeCombat, runEnemyTurn, sendTurn } from '../api'
import { useCharacters } from '../data/characters'

const mockBoot = vi.mocked(bootSession)
const mockSend = vi.mocked(sendTurn)
const mockRunEnemyTurn = vi.mocked(runEnemyTurn)
const mockCloseCombat = vi.mocked(closeCombat)
const mockUseCharacters = vi.mocked(useCharacters)

const combatState: CombatState = {
  round: 1,
  current_actor: 'Goblin Warrior 1',
  combatants: [
    { name: 'Vanx', hp_current: 10, hp_max: 10, ac: 18, initiative: 14, status: 'active' },
    { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 10, status: 'active' },
  ],
}

async function* makeGen<T>(...items: T[]): AsyncGenerator<T> {
  for (const item of items) yield item
}

function makeStalledGen<T>(...events: T[]) {
  let release = () => {}
  const latch = new Promise<void>(r => { release = r })
  async function* gen() {
    for (const e of events) yield e
    await latch
  }
  return { gen: gen(), release }
}

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    text: () => Promise.resolve('# Intro'),
    json: () => Promise.resolve({}),
  }))
}

async function bootIntoCombat(user: ReturnType<typeof userEvent.setup>) {
  mockBoot.mockImplementation(() => makeGen({ type: 'done' as const, session_id: 'sess-combat' }))
  mockSend.mockImplementation(() => makeGen({ type: 'combat_update' as const, combat_state: combatState }))
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Boot Session' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument())
  await user.type(screen.getByPlaceholderText(/What do you do/i), 'Do I spot any goblins?')
  await user.click(screen.getByRole('button', { name: 'Send' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Enemy Turn' })).toBeInTheDocument())
}

describe('App - enemy turn stream wiring', () => {
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

  it('calls POST /sessions/{id}/enemy_turn when Enemy Turn is clicked', async () => {
    const user = userEvent.setup()
    mockRunEnemyTurn.mockImplementation(() => makeGen({ type: 'done' as const }))
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: 'Enemy Turn' }))

    // Await state settlement before asserting the call was made
    await waitFor(() => expect(mockRunEnemyTurn).toHaveBeenCalledWith('sess-combat'), { timeout: 8000 })
  }, 15000)

  it('sets enemyTurnStreaming true during the enemy_turn SSE stream', async () => {
    const user = userEvent.setup()
    const stalled = makeStalledGen({ type: 'token' as const, content: 'The goblin snarls.' })
    mockRunEnemyTurn.mockImplementation(() => stalled.gen)
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: 'Enemy Turn' }))

    await waitFor(() => expect(screen.getByRole('button', { name: 'Enemy Acting...' })).toBeDisabled(), { timeout: 8000 })
    expect(screen.getByText('Enemy Turn', { selector: '.combat-phase-badge' })).toBeInTheDocument()
    stalled.release()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Enemy Turn' })).toBeEnabled(), { timeout: 8000 })
  }, 15000)

  it('appends token events and updates CombatPanel HP from combat_update events', async () => {
    const user = userEvent.setup()
    const damagedState: CombatState = {
      ...combatState,
      combatants: [
        { ...combatState.combatants[0], hp_current: 7 },
        combatState.combatants[1],
      ],
    }
    mockRunEnemyTurn.mockImplementation(() => makeGen(
      { type: 'token' as const, content: 'The goblin slashes Vanx.' },
      { type: 'attack_result' as const, attacker: 'Goblin Warrior 1', target: 'Vanx', roll: 15, bonus: 4, total: 19, ac: 18, hit: true, damage_rolls: [3], damage_total: 3, attack_type: 'melee', is_pc: false },
      { type: 'combat_update' as const, combat_state: damagedState },
      { type: 'done' as const },
    ))
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: 'Enemy Turn' }))

    await waitFor(() => expect(screen.getByText(/The goblin slashes Vanx/)).toBeInTheDocument())
    await waitFor(() => expect(screen.getByText('7/10')).toBeInTheDocument())
  })

  it('shows an error and clears streaming state on 409', async () => {
    const user = userEvent.setup()
    mockRunEnemyTurn.mockImplementation(() => { throw new Error('Enemy turn failed (409)') })
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: 'Enemy Turn' }))

    await waitFor(() => expect(screen.getByText(/Enemy turn failed \(409\)/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Enemy Turn' })).toBeEnabled()
  })

  it('calls POST /sessions/{id}/close_combat and streams closure before clearing combat', async () => {
    const user = userEvent.setup()
    mockCloseCombat.mockImplementation(() => makeGen(
      { type: 'token' as const, content: 'The square falls quiet.' },
      { type: 'combat_update' as const, combat_state: null },
      { type: 'done' as const },
    ))
    await bootIntoCombat(user)

    await user.click(screen.getByRole('button', { name: 'End Combat' }))

    expect(mockCloseCombat).toHaveBeenCalledWith('sess-combat')
    await waitFor(() => expect(screen.getByText(/The square falls quiet/)).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Enemy Turn' })).not.toBeInTheDocument()
  })
})
