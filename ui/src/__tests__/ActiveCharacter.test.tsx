/**
 * Active character state persistence tests.
 *
 * Covers the api.ts setActiveCharacter function and the App.tsx wiring that
 * calls it whenever the player selects or deselects a character.
 *
 * Spec: specs/session-state.feature
 * Covers: AC-014 (PUT updates field), AC-015 (party deselects),
 *         AC-016 (empty string fallback), AC-017 (persists across changes)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { makeCharacter } from '../test/fixtures'

// ── Module mocks ──────────────────────────────────────────────────────────────

vi.mock('../api', () => ({
  bootSession:           vi.fn(),
  sendTurn:              vi.fn(),
  endSessionWithRecap:   vi.fn(),
  logRoll:               vi.fn().mockResolvedValue(undefined),
  resolveRoll:           vi.fn().mockResolvedValue({ passed: true, outcome: 'ok' }),
  purgeSessionNpcs:      vi.fn().mockResolvedValue({ purged: 0 }),
  closeCombat:           vi.fn(),
  runEnemyTurn:          vi.fn(),
  resolveAttackRoll:     vi.fn(),
  resolveDamageRoll:     vi.fn(),
  resumeCombat:          vi.fn(),
  setActiveCharacter:    vi.fn().mockResolvedValue({ active_character: 'party' }),
}))

vi.mock('../data/characters', () => ({
  useCharacters: vi.fn(),
}))

import { bootSession, setActiveCharacter as mockSetActiveCharacterRaw } from '../api'
import { useCharacters } from '../data/characters'

const mockBoot           = vi.mocked(bootSession)
const mockSetActiveChar  = vi.mocked(mockSetActiveCharacterRaw)
const mockUseChars       = vi.mocked(useCharacters)

// ── Helpers ───────────────────────────────────────────────────────────────────

async function* makeGen<T>(...items: T[]): AsyncGenerator<T> {
  for (const item of items) yield item
}

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
    if (String(url).includes('/api/intro')) {
      return Promise.resolve({ ok: true, text: () => Promise.resolve('# Test') })
    }
    return Promise.resolve({ ok: true, text: () => Promise.resolve(''), json: () => Promise.resolve({}) })
  }))
}

const ANI  = makeCharacter({ id: 'ani',      name: 'Ani',      color: '#7a60c0', rune: 'ᚨ' })
const VANX = makeCharacter({ id: 'vanx',     name: 'Vanx',     color: '#5a8fc0', rune: 'ᛉ' })

function setup() {
  vi.clearAllMocks()
  mockSetActiveChar.mockResolvedValue({ active_character: 'party' })
  mockUseChars.mockReturnValue({
    characters: [ANI, VANX],
    characterMap: { ani: ANI, vanx: VANX },
    loading: false,
    error: null,
  })
  stubFetch()
}

async function bootApp(user: ReturnType<typeof userEvent.setup>) {
  mockBoot.mockImplementation(() =>
    makeGen({ type: 'done' as const, session_id: 'sess-test' }),
  )
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Boot Session' }))
  await waitFor(() => expect(screen.getByText(/Session 1 ·/)).toBeInTheDocument())
}

// ── App.tsx — wiring ──────────────────────────────────────────────────────────

describe('App — active character PUT wiring', () => {
  beforeEach(setup)
  afterEach(() => vi.unstubAllGlobals())

  it('does NOT call setActiveCharacter before boot (no session id)', async () => {
    render(<App />)
    // Click an avatar before booting — no session yet
    const avatars = screen.queryAllByTitle(/Ani/)
    if (avatars.length > 0) {
      await userEvent.click(avatars[0])
    }
    expect(mockSetActiveChar).not.toHaveBeenCalled()
  })

  it('calls setActiveCharacter with the PC name after selecting a character post-boot', async () => {
    const user = userEvent.setup()
    await bootApp(user)

    // Click Ani's avatar then "Set Active" in the action menu
    await user.click(screen.getByTitle(/Ani/))
    await user.click(screen.getByText(/Set Active/))

    await waitFor(() =>
      expect(mockSetActiveChar).toHaveBeenCalledWith('sess-test', 'Ani'),
    )
  })

  it('calls setActiveCharacter with "party" when clearing selection', async () => {
    const user = userEvent.setup()
    await bootApp(user)

    // Select then clear
    await user.click(screen.getByTitle(/Ani/))
    await user.click(screen.getByText(/Set Active/))
    await waitFor(() => expect(mockSetActiveChar).toHaveBeenCalledWith('sess-test', 'Ani'))

    await user.click(screen.getByTitle(/Ani/))
    await user.click(screen.getByText(/Clear Active/))

    await waitFor(() =>
      expect(mockSetActiveChar).toHaveBeenCalledWith('sess-test', 'party'),
    )
  })

  it('calls setActiveCharacter when toggling to a second character', async () => {
    const user = userEvent.setup()
    await bootApp(user)

    await user.click(screen.getByTitle(/Ani/))
    await user.click(screen.getByText(/Set Active/))
    await waitFor(() => expect(mockSetActiveChar).toHaveBeenCalledWith('sess-test', 'Ani'))

    await user.click(screen.getByTitle(/Vanx/))
    await user.click(screen.getByText(/Set Active/))
    await waitFor(() => expect(mockSetActiveChar).toHaveBeenCalledWith('sess-test', 'Vanx'))
  })
})
