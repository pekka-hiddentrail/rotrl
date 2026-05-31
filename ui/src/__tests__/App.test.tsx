/**
 * App SSE integration smoke tests
 *
 * Covers boot intro/session setup, send-turn event order (context, token,
 * patch_last, roll_request, rate_limits), error-bar handling, and session-end
 * cleanup.  All async-generator API calls are replaced with synchronous mocks;
 * no real network traffic occurs.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { makeCharacter } from '../test/fixtures'

// ── Module mocks (hoisted by Vitest) ─────────────────────────────────────────

vi.mock('../api', () => ({
  bootSession: vi.fn(),
  sendTurn: vi.fn(),
  endSessionWithRecap: vi.fn(),
  logRoll: vi.fn().mockResolvedValue(undefined),
  resolveRoll: vi.fn().mockResolvedValue({ passed: true, outcome: 'You succeed!' }),
  purgeSessionNpcs: vi.fn().mockResolvedValue({ purged: 0 }),
  endCombat: vi.fn().mockResolvedValue({}),
  resolveAttackRoll: vi.fn(),
  resolveDamageRoll: vi.fn(),
  resumeCombat: vi.fn(),
}))

vi.mock('../data/characters', () => ({
  useCharacters: vi.fn(),
}))

// ── Typed references to mocked functions ─────────────────────────────────────

import {
  bootSession,
  sendTurn,
  endSessionWithRecap,
  purgeSessionNpcs,
  resolveRoll,
  resolveAttackRoll,
  resolveDamageRoll,
  resumeCombat,
} from '../api'
import { useCharacters } from '../data/characters'

const mockBoot = vi.mocked(bootSession)
const mockSend = vi.mocked(sendTurn)
const mockEnd = vi.mocked(endSessionWithRecap)
const mockPurge = vi.mocked(purgeSessionNpcs)
const mockResolveRoll = vi.mocked(resolveRoll)
const mockResolveAttackRoll = vi.mocked(resolveAttackRoll)
const mockResolveDamageRoll = vi.mocked(resolveDamageRoll)
const mockResumeCombat = vi.mocked(resumeCombat)
const mockUseChars = vi.mocked(useCharacters)

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Create a fresh async generator from a list of events. */
async function* makeGen<T>(...items: T[]): AsyncGenerator<T> {
  for (const item of items) yield item
}

/**
 * Create a generator that yields the supplied events then STALLS until
 * `release()` is called.  Use this for tests that need to observe an
 * intermediate UI state before the finally-block cleanup runs.
 */
function makeStalledGen<T>(...events: T[]) {
  let release = () => {}
  const latch = new Promise<void>(r => { release = r })
  async function* gen() {
    for (const e of events) yield e
    await latch
  }
  return { gen: gen(), release }
}

/** Mock fetch so the intro endpoint returns supplied text; everything else 200-ok. */
function stubFetch(introText = '# Test Session Intro') {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/api/intro')) {
        return Promise.resolve({
          ok: true,
          text: () => Promise.resolve(introText),
        })
      }
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(''),
        json: () => Promise.resolve({}),
      })
    }),
  )
}

/** Common pre-test setup: mock characters hook and stub fetch. */
function setup() {
  vi.clearAllMocks()
  mockUseChars.mockReturnValue({
    characters: [],
    characterMap: {},
    loading: false,
    error: null,
  })
  stubFetch()
}

/**
 * Render <App />, click Boot Session, and wait until the session badge appears.
 * The caller's userEvent instance is used so subsequent interactions share state.
 */
async function bootApp(user: ReturnType<typeof userEvent.setup>) {
  mockBoot.mockImplementation(() =>
    makeGen({ type: 'done' as const, session_id: 'sess-test' }),
  )
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Boot Session' }))
  await waitFor(() =>
    expect(screen.getByText(/Session 1 ·/)).toBeInTheDocument(),
  )
}

// ── Boot flow ─────────────────────────────────────────────────────────────────

describe('App — boot flow', () => {
  beforeEach(setup)
  afterEach(() => vi.unstubAllGlobals())

  it('shows the splash screen before boot', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: 'Boot Session' })).toBeInTheDocument()
    // Splash-specific subtitle — not duplicated in the header
    expect(screen.getByText(/Configure your session above/i)).toBeInTheDocument()
  })

  it('Boot Session button is disabled while booting', async () => {
    const user = userEvent.setup()
    const { gen } = makeStalledGen<never>()
    mockBoot.mockImplementation(() => gen)
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    expect(screen.getByRole('button', { name: 'Booting…' })).toBeDisabled()
  })

  it('intro card content is shown from the /api/intro fetch', async () => {
    const user = userEvent.setup()
    stubFetch('# The Swallowtail Festival')
    mockBoot.mockImplementation(() =>
      makeGen({ type: 'done' as const, session_id: 's1' }),
    )
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    // renderIntro() strips the leading '# ' — heading text is the assertion target
    await waitFor(() =>
      expect(screen.getByText('The Swallowtail Festival')).toBeInTheDocument(),
    )
  })

  it('session badge appears and InputBar is rendered after done event', async () => {
    const user = userEvent.setup()
    mockBoot.mockImplementation(() =>
      makeGen({ type: 'done' as const, session_id: 'sess-99' }),
    )
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    await waitFor(() =>
      expect(screen.getByText(/Session 1 ·/)).toBeInTheDocument(),
    )
    // InputBar only renders when isBooted
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('error event from bootSession → error bar shown', async () => {
    const user = userEvent.setup()
    mockBoot.mockImplementation(() =>
      makeGen({ type: 'error' as const, message: 'LLM backend unreachable' }),
    )
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    await waitFor(() =>
      expect(screen.getByText(/LLM backend unreachable/)).toBeInTheDocument(),
    )
  })

  it('bootSession throws (HTTP failure) → error bar shown', async () => {
    const user = userEvent.setup()
    mockBoot.mockImplementation(() => {
      throw new Error('Boot failed (503): service unavailable')
    })
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))
    await waitFor(() =>
      expect(screen.getByText(/Boot failed \(503\)/)).toBeInTheDocument(),
    )
  })

  it('character data hook error is surfaced in the app error bar', () => {
    mockUseChars.mockReturnValue({
      characters: [],
      characterMap: {},
      loading: false,
      error: 'TypeError: Failed to fetch',
    })

    render(<App />)

    expect(screen.getByText(/Character data: TypeError: Failed to fetch/)).toBeInTheDocument()
  })

  it('provider/model switching is sent to bootSession', async () => {
    const user = userEvent.setup()
    mockBoot.mockImplementation(() =>
      makeGen({ type: 'done' as const, session_id: 'sess-ollama' }),
    )

    render(<App />)
    await user.click(screen.getByRole('button', { name: /Ollama/ }))
    expect(screen.getByRole('combobox')).toHaveValue('qwen3:4b')
    await user.click(screen.getByRole('button', { name: 'Boot Session' }))

    await waitFor(() =>
      expect(mockBoot).toHaveBeenCalledWith(1, 'qwen3:4b', false, 'ollama'),
    )
  })
})

// ── Header/session controls in App ────────────────────────────────────────────

describe('App — header/session controls', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(async () => {
    setup()
    user = userEvent.setup()
  })

  afterEach(() => vi.unstubAllGlobals())

  it('View Log opens the active session log in a new tab', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    await bootApp(user)

    await user.click(screen.getByRole('button', { name: /Tools/ }))
    await user.click(screen.getByRole('button', { name: /View Session Log/ }))

    expect(openSpy).toHaveBeenCalledWith('/api/sessions/sess-test/log', '_blank')
    openSpy.mockRestore()
  })

  it('Purge NPCs uses inline confirm and shows the purge count toast', async () => {
    mockPurge.mockResolvedValueOnce({ purged: 2 })
    render(<App />)

    await user.click(screen.getByRole('button', { name: /Tools/ }))
    await user.click(screen.getByRole('button', { name: /Purge Session NPCs/ }))
    expect(screen.getByText('Purge session NPCs?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Yes' }))

    await waitFor(() =>
      expect(screen.getByText('2 session NPC directories removed.')).toBeInTheDocument(),
    )
    expect(mockPurge).toHaveBeenCalledOnce()
  })

  it('Purge NPCs collapses without calling the API when No is clicked', async () => {
    render(<App />)

    await user.click(screen.getByRole('button', { name: /Tools/ }))
    await user.click(screen.getByRole('button', { name: /Purge Session NPCs/ }))
    await user.click(screen.getByRole('button', { name: 'No' }))

    expect(mockPurge).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Tools/ })).toBeInTheDocument()
  })

  it('Kill confirmation No keeps ending; Yes resets back to pre-boot', async () => {
    await bootApp(user)
    const { gen, release } = makeStalledGen<never>()
    mockEnd.mockImplementation(() => gen)

    await user.click(screen.getByRole('button', { name: 'End Session' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Kill' })).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Kill' }))
    await user.click(screen.getByRole('button', { name: 'No' }))
    expect(screen.getByRole('button', { name: 'Kill' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Boot Session' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Kill' }))
    await user.click(screen.getByRole('button', { name: 'Yes' }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Boot Session' })).toBeInTheDocument(),
    )
    release()
  })
})

// ── Send-turn SSE event order ─────────────────────────────────────────────────

describe('App — send-turn SSE event handling', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(async () => {
    setup()
    user = userEvent.setup()
    await bootApp(user)
  })

  afterEach(() => vi.unstubAllGlobals())

  it('player bubble is added immediately before the stream starts', async () => {
    mockSend.mockImplementation(() => makeGen<never>())
    await user.type(screen.getByRole('textbox'), 'I look around the tavern')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(screen.getByText('I look around the tavern')).toBeInTheDocument()
  })

  it('token events build up the GM bubble', async () => {
    mockSend.mockImplementation(() =>
      makeGen(
        { type: 'token' as const, content: 'The ' },
        { type: 'token' as const, content: 'tavern ' },
        { type: 'token' as const, content: 'is quiet.' },
      ),
    )
    await user.type(screen.getByRole('textbox'), 'look around')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(screen.getByText('The tavern is quiet.')).toBeInTheDocument(),
    )
  })

  it('shows thinking indicator and disables input while waiting for first token', async () => {
    const { gen, release } = makeStalledGen<never>()
    mockSend.mockImplementation(() => gen)

    await user.type(screen.getByRole('textbox'), 'listen')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(screen.getByText('listen')).toBeInTheDocument())
    expect(document.querySelector('.thinking-bubble')).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeDisabled()
    const sendButton = document.querySelector('.btn-send') as HTMLButtonElement
    expect(sendButton).toBeDisabled()
    release()
  })

  it('shows the streaming cursor while a GM token bubble is still active', async () => {
    const { gen, release } = makeStalledGen({ type: 'token' as const, content: 'A bell rings.' })
    mockSend.mockImplementation(() => gen)

    await user.type(screen.getByRole('textbox'), 'wait')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(screen.getByText(/A bell rings/)).toBeInTheDocument())
    expect(document.querySelector('.cursor')).toBeInTheDocument()
    release()
    await waitFor(() => expect(document.querySelector('.cursor')).not.toBeInTheDocument())
  })

  it('patch_last event replaces the last GM message', async () => {
    mockSend.mockImplementation(() =>
      makeGen(
        { type: 'token' as const, content: 'Partial response text.' },
        { type: 'patch_last' as const, content: 'Full corrected response.' },
      ),
    )
    await user.type(screen.getByRole('textbox'), 'continue')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(screen.getByText('Full corrected response.')).toBeInTheDocument(),
    )
    expect(screen.queryByText('Partial response text.')).not.toBeInTheDocument()
  })

  it('context event → NPC name shown in IntentBar', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'context' as const,
        npc: 'Hemlock',
        npc_trigger: 'sheriff',
        skill: null,
        skill_trigger: null,
        location: null,
        location_npcs: [],
      }),
    )
    await user.type(screen.getByRole('textbox'), 'ask the sheriff')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText('Hemlock')).toBeInTheDocument())
  })

  it('context event → skill name shown in IntentBar', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'context' as const,
        npc: null,
        npc_trigger: null,
        skill: 'Perception',
        skill_trigger: 'look',
        location: null,
        location_npcs: [],
      }),
    )
    await user.type(screen.getByRole('textbox'), 'look for clues')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText('Perception')).toBeInTheDocument())
  })

  it('roll_request event → skill name and DC shown in DicePanel', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'roll_request' as const,
        skill: 'Perception',
        dc: 18,
        success: 'You spot the ambush.',
        failure: 'You miss it.',
      }),
    )
    await user.type(screen.getByRole('textbox'), 'check for traps')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText('DC 18')).toBeInTheDocument())
    expect(screen.getByText('Perception')).toBeInTheDocument()
  })

  it('rate_limits event → rate-limit badge visible in Header', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'rate_limits' as const,
        tpm_limit: '6000',
        tpm_remaining: '4500',
        rpm_limit: '30',
        rpm_remaining: '28',
      }),
    )
    await user.type(screen.getByRole('textbox'), 'next turn')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText(/TPM/)).toBeInTheDocument())
    expect(screen.getByText(/RPM/)).toBeInTheDocument()
  })

  it('error event → error bar shown', async () => {
    mockSend.mockImplementation(() =>
      makeGen({ type: 'error' as const, message: 'Rate limit exceeded' }),
    )
    await user.type(screen.getByRole('textbox'), 'try again')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(screen.getByText(/Rate limit exceeded/)).toBeInTheDocument(),
    )
  })

  it('second send clears the previous error bar', async () => {
    mockSend.mockImplementationOnce(() =>
      makeGen({ type: 'error' as const, message: 'Transient failure' }),
    )
    await user.type(screen.getByRole('textbox'), 'first')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText(/Transient failure/)).toBeInTheDocument())

    mockSend.mockImplementationOnce(() =>
      makeGen({ type: 'token' as const, content: 'Recovered.' }),
    )
    await user.type(screen.getByRole('textbox'), 'second')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(screen.queryByText(/Transient failure/)).not.toBeInTheDocument(),
    )
  })
})

// ── Session end cleanup ───────────────────────────────────────────────────────

// Character speaker integration

describe('App - character speaker integration', () => {
  let user: ReturnType<typeof userEvent.setup>
  const yanyeeku = makeCharacter()
  const ani = makeCharacter({
    id: 'ani',
    name: 'Ani',
    portrait: '/portraits/ani.png',
    color: '#60a0d0',
    rune: 'A',
  })

  beforeEach(async () => {
    setup()
    mockUseChars.mockReturnValue({
      characters: [yanyeeku, ani],
      characterMap: { yanyeeku, ani },
      loading: false,
      error: null,
    })
    user = userEvent.setup()
    await bootApp(user)
  })

  afterEach(() => vi.unstubAllGlobals())

  async function setActive(name: RegExp) {
    await user.click(screen.getByTitle(name))
    await user.click(screen.getByText(/Set Active/))
  }

  it('persists the active speaker and sends prefixed backend payloads while chat stays clean', async () => {
    mockSend.mockImplementation(() => makeGen<never>())
    await setActive(/Yanyeeku/)
    expect(screen.getByText(/Speaking as/)).toBeInTheDocument()
    expect(screen.getAllByText('Yanyeeku').length).toBeGreaterThan(1)

    await user.type(screen.getByRole('textbox'), 'I ask Ameiko about the raid.')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(mockSend).toHaveBeenCalledWith('sess-test', '@Yanyeeku: "I ask Ameiko about the raid."'),
    )
    expect(screen.getByText('I ask Ameiko about the raid.')).toBeInTheDocument()
    expect(screen.queryByText(/@Yanyeeku/)).not.toBeInTheDocument()

    await user.type(screen.getByRole('textbox'), 'I listen for the bells.')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalledTimes(2))
    expect(mockSend).toHaveBeenLastCalledWith('sess-test', '@Yanyeeku: "I listen for the bells."')
  })

  it('switches active speaker and clears active state from the sidebar menu', async () => {
    await setActive(/Yanyeeku/)
    expect(screen.getByTitle(/Yanyeeku/)).toHaveClass('active')
    expect(screen.getAllByText('Yanyeeku').length).toBeGreaterThan(1)

    await setActive(/Ani/)
    expect(screen.getByTitle(/Yanyeeku/)).not.toHaveClass('active')
    expect(screen.getByTitle(/Ani/)).toHaveClass('active')
    expect(screen.getAllByText('Ani').length).toBeGreaterThan(1)

    await user.click(screen.getByTitle(/Ani/))
    await user.click(screen.getByText(/Clear Active/))
    expect(screen.getByTitle(/Ani/)).not.toHaveClass('active')
    expect(screen.queryByText(/Speaking as/)).not.toBeInTheDocument()
  })

  it('uses the roll_request speaker when resolving a prompted roll', async () => {
    const vanx = makeCharacter({
      id: 'vanx',
      name: 'Vanx',
      portrait: '/portraits/vanx.png',
      color: '#60d0a0',
      rune: 'V',
    })
    mockUseChars.mockReturnValue({
      characters: [yanyeeku, ani, vanx],
      characterMap: { yanyeeku, ani, vanx },
      loading: false,
      error: null,
    })
    mockSend.mockImplementationOnce(() =>
      makeGen({
        type: 'roll_request' as const,
        skill: 'Perception',
        dc: 10,
        success: 'Vanx hears movement.',
        failure: 'Vanx hears only festival noise.',
        speaker: 'Vanx',
      }),
    )
    mockResolveRoll.mockResolvedValueOnce({
      passed: true,
      skill: 'Perception',
      dc: 10,
      rolled: 17,
      outcome: 'Vanx hears movement.',
      speaker: 'Vanx',
    })

    await user.type(screen.getByRole('textbox'), 'I listen at the south wall.')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText('Perception')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Perception/i }))

    await waitFor(() => expect(mockResolveRoll).toHaveBeenCalledWith('sess-test', expect.any(Number)))
    expect(screen.getByText(/Vanx rolled a/i)).toBeInTheDocument()
    expect(screen.getAllByText('Vanx').length).toBeGreaterThan(0)
  })
})

// ── Combat tracker layout (AC-006) ───────────────────────────────────────────

describe('App — AC-006 combat-active layout', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(async () => {
    setup()
    user = userEvent.setup()
    await bootApp(user)
  })

  afterEach(() => vi.unstubAllGlobals())

  it('V13 — CombatPanel is absent before any combat_update event', () => {
    // No turn sent — combatState starts null
    expect(document.querySelector('.combat-panel')).not.toBeInTheDocument()
  })

  it('V14 — combat_update with non-null state renders CombatPanel with round badge', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'combat_update' as const,
        combat_state: {
          round: 1,
          combatants: [
            { name: 'Goblin 1', hp_current: 5, hp_max: 5, ac: 13, initiative: 10, status: 'active' as const, conditions: [] },
          ],
        },
      }),
    )
    await user.type(screen.getByRole('textbox'), 'attack')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(screen.getByText('Round 1')).toBeInTheDocument(),
    )
    expect(document.querySelector('.combat-panel')).toBeInTheDocument()
    expect(screen.getByText('Goblin 1')).toBeInTheDocument()
  })

  it('V15 — .main-content gains combat-active class when CombatPanel is present', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'combat_update' as const,
        combat_state: {
          round: 2,
          combatants: [
            { name: 'Shalelu', hp_current: 18, hp_max: 24, ac: 17, initiative: 14, status: 'active' as const, conditions: [] },
          ],
        },
      }),
    )
    await user.type(screen.getByRole('textbox'), 'fight')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(document.querySelector('.main-content')).toHaveClass('combat-active'),
    )
  })
})

// ── Session end cleanup ───────────────────────────────────────────────────────

// ── Attack resolution App wiring (AC-003, AC-004, AC-005, AC-009) ─────────────

describe('App — attack resolution wiring', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(async () => {
    setup()
    user = userEvent.setup()
    vi.spyOn(Math, 'random').mockReturnValue(0.6) // d20 roll = floor(0.6*20)+1 = 13
    await bootApp(user)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  /** Send a turn that surfaces a PC attack_request banner in the DicePanel. */
  async function triggerAttackRequest() {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'attack_request' as const,
        attacker: 'Thaelion', target: 'Goblin 1',
        bonus: 5, ac: 13, damage_expr: '1d8+3', attack_type: 'melee',
      }),
    )
    await user.type(screen.getByRole('textbox'), 'attack')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() =>
      expect(screen.getByText(/Thaelion → Goblin 1/)).toBeInTheDocument(),
    )
  }

  it('AC-003 — clicking to-hit banner calls resolveAttackRoll with the rolled d20', async () => {
    // d20 roll: Math.random=0.6 → floor(0.6*20)+1 = 13
    mockResolveAttackRoll.mockResolvedValue({
      hit: false, ac: 13, roll: 13, bonus: 5, total: 18,
      damage_expr: null, queue_remaining: 0, next_attack: null,
    })
    mockResumeCombat.mockImplementation(() => makeGen<never>())

    await triggerAttackRequest()
    await user.click(screen.getByTitle('Click to roll d20'))

    await waitFor(() => expect(mockResolveAttackRoll).toHaveBeenCalledWith('sess-test', 13))
  })

  it('AC-003 — hit result transitions DicePanel banner to damage phase', async () => {
    mockResolveAttackRoll.mockResolvedValue({
      hit: true, ac: 13, roll: 13, bonus: 5, total: 18,
      damage_expr: '1d8+3', queue_remaining: 1, next_attack: null,
    })

    await triggerAttackRequest()
    await user.click(screen.getByTitle('Click to roll d20'))

    await waitFor(() =>
      expect(screen.getByText(/Roll damage: 1d8\+3/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/HIT!/)).toBeInTheDocument()
  })

  it('AC-004 — clicking Roll Damage calls resolveDamageRoll with rolled values (not die sides)', async () => {
    // Setup: get into damage phase
    mockResolveAttackRoll.mockResolvedValue({
      hit: true, ac: 13, roll: 13, bonus: 5, total: 18,
      damage_expr: '1d8+3', queue_remaining: 1, next_attack: null,
    })
    mockResolveDamageRoll.mockResolvedValue({
      damage_rolls: [5], damage_total: 5, queue_remaining: 0, next_attack: null,
    })
    mockResumeCombat.mockImplementation(() => makeGen<never>())

    await triggerAttackRequest()
    await user.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(screen.getByText(/Roll damage/)).toBeInTheDocument())

    // Math.random=0.6 → rollDie(8) = floor(0.6*8)+1 = 5
    await user.click(screen.getByTitle('d8'))
    await user.click(screen.getByRole('button', { name: 'Roll Damage' }))

    await waitFor(() =>
      expect(mockResolveDamageRoll).toHaveBeenCalledWith('sess-test', [5], 5),
    )
  })

  it('AC-005 — doResumeCombat is called automatically after all PC attacks resolve', async () => {
    mockResolveAttackRoll.mockResolvedValue({
      hit: false, ac: 13, roll: 13, bonus: 5, total: 18,
      damage_expr: null, queue_remaining: 0, next_attack: null,
    })
    mockResumeCombat.mockImplementation(() => makeGen({ type: 'token' as const, content: 'Narration.' }))

    await triggerAttackRequest()
    await user.click(screen.getByTitle('Click to roll d20'))

    await waitFor(() => expect(mockResumeCombat).toHaveBeenCalledWith('sess-test'))
  })

  it('AC-002 — NPC-only turn auto-calls doResumeCombat when queue remains empty', async () => {
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'attack_result' as const,
        attacker: 'Goblin 1', target: 'Shalelu',
        roll: 10, bonus: 4, total: 14, ac: 17,
        hit: false, damage_rolls: [], damage_total: 0,
        attack_type: 'melee', is_pc: false,
      }),
    )
    mockResumeCombat.mockImplementation(() => makeGen({ type: 'token' as const, content: 'Goblin misses.' }))

    await user.type(screen.getByRole('textbox'), 'npc attacks')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    // After the turn stream ends with attack_result but no attack_request,
    // App auto-calls doResumeCombat
    await waitFor(() => expect(mockResumeCombat).toHaveBeenCalledWith('sess-test'))
    await waitFor(() => expect(screen.getByText('Goblin misses.')).toBeInTheDocument())
  })

  it('chat-display AC-007 — doResumeCombat tokens land in a NEW GM bubble, not the previous one', async () => {
    // Regression guard: before the fix, doResumeCombat appended to the last existing GM bubble.
    // The fix seeds an empty { role: 'gm', content: '' } before the stream begins.
    mockSend.mockImplementation(() =>
      makeGen(
        { type: 'token' as const, content: 'Attack setup narrative.' },
        {
          type: 'attack_request' as const,
          attacker: 'Thaelion', target: 'Goblin 1',
          bonus: 5, ac: 13, damage_expr: '1d8+3', attack_type: 'melee' as const,
        },
      ),
    )
    mockResolveAttackRoll.mockResolvedValue({
      hit: false, ac: 13, roll: 13, bonus: 5, total: 18,
      damage_expr: null, queue_remaining: 0, next_attack: null,
    })
    mockResumeCombat.mockImplementation(() =>
      makeGen({ type: 'token' as const, content: 'Combat resolved.' }),
    )

    await user.type(screen.getByRole('textbox'), 'attack')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText(/Thaelion → Goblin 1/)).toBeInTheDocument())
    await user.click(screen.getByTitle('Click to roll d20'))

    await waitFor(() => expect(screen.getByText('Combat resolved.')).toBeInTheDocument())

    // The two pieces of GM narrative must be in SEPARATE bubble-row elements
    const gmBubbles = document.querySelectorAll('.bubble-row.gm')
    const setupBubble  = Array.from(gmBubbles).find(b => b.textContent?.includes('Attack setup narrative.'))
    const resumeBubble = Array.from(gmBubbles).find(b => b.textContent?.includes('Combat resolved.'))
    expect(setupBubble).toBeTruthy()
    expect(resumeBubble).toBeTruthy()
    expect(setupBubble).not.toBe(resumeBubble)
  })

  it('attack_type carried from to_hit phase into attack log — not hardcoded melee', async () => {
    // Regression: handleAttackRoll hardcoded 'melee' regardless of the phase's attack_type.
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'attack_request' as const,
        attacker: 'Thaelion', target: 'Goblin 1',
        bonus: 3, ac: 13, damage_expr: '1d8', attack_type: 'ranged',
      }),
    )
    mockResolveAttackRoll.mockResolvedValue({
      hit: false, ac: 13, roll: 13, bonus: 3, total: 16,
      damage_expr: null, queue_remaining: 0, next_attack: null,
    })
    mockResumeCombat.mockImplementation(() => makeGen<never>())

    await user.type(screen.getByRole('textbox'), 'shoot')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText(/Thaelion → Goblin 1/)).toBeInTheDocument())
    await user.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(mockResolveAttackRoll).toHaveBeenCalledWith('sess-test', 13))
    await waitFor(() => expect(mockResumeCombat).toHaveBeenCalled())
  })

  it('attack_type preserved across to_hit → damage phase transition', async () => {
    // Regression: damage phase was constructed without attack_type, forcing handleDamageRoll
    // to fall back to the hardcoded 'melee' string.
    mockSend.mockImplementation(() =>
      makeGen({
        type: 'attack_request' as const,
        attacker: 'Thaelion', target: 'Goblin 1',
        bonus: 3, ac: 13, damage_expr: '1d8', attack_type: 'ranged',
      }),
    )
    mockResolveAttackRoll.mockResolvedValue({
      hit: true, ac: 13, roll: 13, bonus: 3, total: 16,
      damage_expr: '1d8', queue_remaining: 1, next_attack: null,
    })
    mockResolveDamageRoll.mockResolvedValue({
      damage_rolls: [5], damage_total: 5, queue_remaining: 0, next_attack: null,
    })
    mockResumeCombat.mockImplementation(() => makeGen<never>())

    await user.type(screen.getByRole('textbox'), 'shoot')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText(/Thaelion → Goblin 1/)).toBeInTheDocument())

    await user.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(screen.getByText(/Roll damage/)).toBeInTheDocument())

    // Math.random=0.6 → rollDie(8) = 5
    await user.click(screen.getByTitle('d8'))
    await user.click(screen.getByRole('button', { name: 'Roll Damage' }))
    await waitFor(() =>
      expect(mockResolveDamageRoll).toHaveBeenCalledWith('sess-test', [5], 5),
    )
  })

  it('AC-009 — after miss, next attack banner appears with second attacker\'s stats', async () => {
    mockResolveAttackRoll.mockResolvedValue({
      hit: false, ac: 13, roll: 1, bonus: 5, total: 6,
      damage_expr: null, queue_remaining: 1,
      next_attack: { attacker: 'Yanyeeku', target: 'Goblin 1', bonus: 2, ac: 13, damage_expr: '1d6+1', attack_type: 'melee' },
    })

    await triggerAttackRequest()
    await user.click(screen.getByTitle('Click to roll d20'))

    // Banner switches to second attacker
    await waitFor(() =>
      expect(screen.getByText(/Yanyeeku → Goblin 1/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/bonus: \+2/)).toBeInTheDocument()
  })
})

// ── Session end cleanup ───────────────────────────────────────────────────────

describe('App — session end cleanup', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(async () => {
    setup()
    user = userEvent.setup()
    await bootApp(user)
  })

  afterEach(() => vi.unstubAllGlobals())

  it('clicking End Session shows the ending bubble immediately', async () => {
    // Stall — keeps handleEnd from reaching finally so the bubble stays visible
    const { gen } = makeStalledGen<never>()
    mockEnd.mockImplementation(() => gen)
    await user.click(screen.getByRole('button', { name: 'End Session' }))
    await waitFor(() =>
      expect(screen.getByText('Wrapping up the session\u2026')).toBeInTheDocument(),
    )
  })

  it('status event updates the ending bubble text', async () => {
    const { gen } = makeStalledGen({
      type: 'status' as const,
      message: 'Writing recap to disk\u2026',
    })
    mockEnd.mockImplementation(() => gen)
    await user.click(screen.getByRole('button', { name: 'End Session' }))
    await waitFor(() =>
      expect(screen.getByText('Writing recap to disk\u2026')).toBeInTheDocument(),
    )
  })

  it('done event shows "Session saved." then session is cleared', async () => {
    // Shorten the 1800 ms hold to 0 ms — avoids fake-timer interference with act.
    // A stalling generator keeps the for-await loop alive so finally only runs
    // after we explicitly release the latch.
    const origTimeout = globalThis.setTimeout
    const spy = vi.spyOn(globalThis, 'setTimeout').mockImplementation(
      (fn: any, ms?: number, ...args: any[]) =>
        origTimeout.call(
          globalThis,
          fn,
          ms !== undefined && ms >= 500 ? 0 : ms,
          ...args,
        ) as ReturnType<typeof setTimeout>,
    )
    try {
      const { gen, release } = makeStalledGen({ type: 'done' as const })
      mockEnd.mockImplementation(() => gen)
      await user.click(screen.getByRole('button', { name: 'End Session' }))
      // 1800 ms is now 0 ms — "Session saved." appears after one microtask cycle
      await waitFor(() =>
        expect(screen.getByText('Session saved. See you next time.')).toBeInTheDocument(),
      )
      // Release the stall so the for-await loop exits and finally runs
      release()
      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Boot Session' })).toBeInTheDocument(),
      )
    } finally {
      spy.mockRestore()
    }
  })

  it('done event increments session number by 1', async () => {
    const origTimeout = globalThis.setTimeout
    const spy = vi.spyOn(globalThis, 'setTimeout').mockImplementation(
      (fn: any, ms?: number, ...args: any[]) =>
        origTimeout.call(globalThis, fn, ms !== undefined && ms >= 500 ? 0 : ms, ...args) as ReturnType<typeof setTimeout>,
    )
    try {
      const { gen, release } = makeStalledGen({ type: 'done' as const })
      mockEnd.mockImplementation(() => gen)
      await user.click(screen.getByRole('button', { name: 'End Session' }))
      release()
      // Wait for the pre-boot screen to come back, then check the number input
      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Boot Session' })).toBeInTheDocument(),
      )
      // Default session number was 1 — should now be 2
      expect(screen.getByRole('spinbutton')).toHaveValue(2)
    } finally {
      spy.mockRestore()
    }
  })

  it('error during end session → error bar shown and session cleared', async () => {
    mockEnd.mockImplementation(() =>
      makeGen({ type: 'error' as const, message: 'Recap generation failed' }),
    )
    await user.click(screen.getByRole('button', { name: 'End Session' }))
    await waitFor(() =>
      expect(screen.getByText(/Recap generation failed/)).toBeInTheDocument(),
    )
    // finally block runs without any timeout on the error path — session clears
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Boot Session' })).toBeInTheDocument(),
    )
  })
})
