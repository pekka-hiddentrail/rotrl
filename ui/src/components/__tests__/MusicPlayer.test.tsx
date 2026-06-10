import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import MusicPlayer from '../MusicPlayer'
import type { CalmPhrase } from '../../api'

// ── Mocks ────────────────────────────────────────────────────────────────────

const stopMock = vi.fn()

// Calls onBarChange(1) synchronously so the first bar chip becomes active
// immediately after schedulePhrase is called, enabling AC-014 assertions.
const schedulePhraseMock = vi.fn(
  (_phrase: CalmPhrase, _delay?: number, onBarChange?: (bar: number) => void) => {
    onBarChange?.(1)
    return { start_delay_seconds: 0.05, duration_seconds: 2.0 }
  },
)

const startAudioContextMock = vi.fn().mockResolvedValue(undefined)
const fetchCalmPhraseMock = vi.fn<(...args: unknown[]) => Promise<CalmPhrase>>()

vi.mock('tone', () => ({
  getDestination: () => ({ volume: { value: 0 } }),
}))

vi.mock('../../music/music_player', () => ({
  createCalmPhrasePlayer: () => ({
    schedulePhrase: schedulePhraseMock,
    stop: stopMock,
  }),
}))

vi.mock('../../music/synth', () => ({
  startAudioContext: (...args: unknown[]) => startAudioContextMock(...args),
}))

vi.mock('../../api', async () => {
  const actual = await vi.importActual<typeof import('../../api')>('../../api')
  return {
    ...actual,
    fetchCalmPhrase: (...args: unknown[]) => fetchCalmPhraseMock(...args),
  }
})

// ── Helpers ──────────────────────────────────────────────────────────────────

function makePhrase(overrides: Partial<CalmPhrase> = {}): CalmPhrase {
  return {
    phrase_id: 'p-1',
    mood: 'calm',
    key: 'C',
    scale: ['C', 'D', 'E', 'G', 'A'],
    bpm: 100,
    time_signature: '4/4',
    bars: 4,
    tracks: [
      { track_id: 'lead', role: 'lead', events: [{ bar: 1, beat: 1, note: 'C5', midi: 72, duration: '4n', velocity: 0.69 }] },
      { track_id: 'bass', role: 'bass', events: [{ bar: 1, beat: 1, note: 'C3', midi: 48, duration: '4n', velocity: 0.45 }] },
    ],
    state: {
      motif_id: 'm-1',
      motif_degrees: [1, 3, 5],
      cadence_degree: 1,
      highest_degree: 5,
      novelty: 0.3,
      bass_pattern_id: 'bp-1',
      bass_final_degree: 0,
    },
    ...overrides,
  }
}

// 4-bar phrase with one lead event per bar — used for intent-row tests.
function makePhrase4Bars(): CalmPhrase {
  return makePhrase({
    bars: 4,
    tracks: [
      {
        track_id: 'lead', role: 'lead', events: [
          { bar: 1, beat: 1, note: 'C5', midi: 72, duration: '4n', velocity: 0.69 },
          { bar: 2, beat: 1, note: 'E5', midi: 76, duration: '4n', velocity: 0.63 },
          { bar: 3, beat: 1, note: 'D5', midi: 74, duration: '4n', velocity: 0.67 },
          { bar: 4, beat: 1, note: 'G4', midi: 67, duration: '4n', velocity: 0.61 },
        ],
      },
      {
        track_id: 'bass', role: 'bass', events: [
          { bar: 1, beat: 1, note: 'C3', midi: 48, duration: '4n', velocity: 0.45 },
        ],
      },
    ],
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MusicPlayer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    fetchCalmPhraseMock.mockResolvedValue(makePhrase())
  })

  // AC-001, AC-002 ─────────────────────────────────────────────────────────────

  it('shows Stopped status on mount, no fetch or audio before user gesture (AC-001)', () => {
    render(<MusicPlayer sessionId="sess-1" />)
    expect(screen.getByText('Stopped')).toBeInTheDocument()
    expect(fetchCalmPhraseMock).not.toHaveBeenCalled()
    expect(startAudioContextMock).not.toHaveBeenCalled()
  })

  it('resumes AudioContext and schedules phrase 1 on Start (AC-002)', async () => {
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(startAudioContextMock).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(schedulePhraseMock).toHaveBeenCalledTimes(1))
    expect(screen.getByText('Playing')).toBeInTheDocument()
  })

  // AC-003 ─────────────────────────────────────────────────────────────────────

  it('Stop Music triggers a 0.5s fade stop and transitions to Stopped (AC-003, AC-013)', async () => {
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))
    await waitFor(() => expect(schedulePhraseMock).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: 'Stop Music' }))

    expect(stopMock).toHaveBeenCalledWith(0.5)
    expect(screen.getByText('Stopped')).toBeInTheDocument()
  })

  it('no further fetches occur after Stop (AC-003)', async () => {
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))
    // Phrase 1 + 2 prefetches (both queue slots) = 3 calls
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(3))

    fireEvent.click(screen.getByRole('button', { name: 'Stop Music' }))
    const countAtStop = fetchCalmPhraseMock.mock.calls.length

    await new Promise(resolve => setTimeout(resolve, 200))
    expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(countAtStop)
  })

  // AC-005 / AC-011 ─────────────────────────────────────────────────────────────

  it('both prefetch queue slots fill immediately after phrase 1 schedules (AC-005, AC-011)', async () => {
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    // Phrase-1 fetch + 2 prefetches = 3 total; second prefetch auto-fires after first completes
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(3))
    // Only phrase 1 is scheduled so far (phrases 2 & 3 wait in the queue)
    expect(schedulePhraseMock).toHaveBeenCalledTimes(1)
  })

  it('phrase-1 fetch uses previous_state=null; prefetch uses phrase-1 state (AC-009, AC-011)', async () => {
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(3))
    // First call: previous_state = null
    expect(fetchCalmPhraseMock.mock.calls[0][2]).toBeNull()
    // Second call (prefetch 1): previous_state = phrase-1's state
    expect(fetchCalmPhraseMock.mock.calls[1][2]).toEqual(makePhrase().state)
  })

  // AC-012 ─────────────────────────────────────────────────────────────────────

  it('prefetch failure triggers automatic retry — queue refills without error UI (AC-012)', async () => {
    // Phrase 1 succeeds; prefetch 1 fails; retry and second slot succeed via default mock
    fetchCalmPhraseMock
      .mockResolvedValueOnce(makePhrase())
      .mockRejectedValueOnce(new Error('network'))

    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    // 4 calls: phrase 1 + failed prefetch + retry + second slot
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(4))
    expect(schedulePhraseMock).toHaveBeenCalledTimes(1)
    // Prefetch failure is silent — error is only shown at swap time if queue is still empty
    expect(screen.queryByText(/timed out/i)).not.toBeInTheDocument()
  })

  // AC-013 — hard stop on error ─────────────────────────────────────────────────

  it('fetch error in handleStart triggers hard stop — no fade (AC-013)', async () => {
    fetchCalmPhraseMock.mockRejectedValueOnce(new Error('network'))
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(stopMock).toHaveBeenCalledWith(0))
    expect(screen.queryByText('Playing')).not.toBeInTheDocument()
  })

  // AC-010 ─────────────────────────────────────────────────────────────────────

  it('volume slider persists to localStorage and displays updated value (AC-010)', () => {
    render(<MusicPlayer sessionId="sess-1" />)
    const slider = screen.getByLabelText('Music volume') as HTMLInputElement

    fireEvent.change(slider, { target: { value: '50' } })

    expect(slider.value).toBe('50')
    expect(window.localStorage.getItem('rotrl.music.volume')).toBe('50')
  })

  it('volume is restored from localStorage on mount (AC-010)', () => {
    window.localStorage.setItem('rotrl.music.volume', '30')
    render(<MusicPlayer sessionId="sess-1" />)
    const slider = screen.getByLabelText('Music volume') as HTMLInputElement
    expect(slider.value).toBe('30')
  })

  // AC-014 ─────────────────────────────────────────────────────────────────────

  it('Intent row shows all bar chips after phrase is scheduled (AC-014)', async () => {
    fetchCalmPhraseMock.mockResolvedValue(makePhrase4Bars())
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(schedulePhraseMock).toHaveBeenCalledTimes(1))

    expect(screen.getByText('Intent:')).toBeInTheDocument()
    expect(screen.getByText('B1')).toBeInTheDocument()
    expect(screen.getByText('B2')).toBeInTheDocument()
    expect(screen.getByText('B3')).toBeInTheDocument()
    expect(screen.getByText('B4')).toBeInTheDocument()
  })

  it('active bar chip is highlighted when onBarChange fires (AC-014)', async () => {
    fetchCalmPhraseMock.mockResolvedValue(makePhrase4Bars())
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(schedulePhraseMock).toHaveBeenCalledTimes(1))

    // schedulePhraseMock calls onBarChange(1), so B1 chip should be active
    const b1 = screen.getByText('B1')
    expect(b1.closest('.music-intent-bar')).toHaveClass('music-intent-bar-active')

    // B2–B4 should not be active
    expect(screen.getByText('B2').closest('.music-intent-bar')).not.toHaveClass('music-intent-bar-active')
    expect(screen.getByText('B3').closest('.music-intent-bar')).not.toHaveClass('music-intent-bar-active')
    expect(screen.getByText('B4').closest('.music-intent-bar')).not.toHaveClass('music-intent-bar-active')
  })

  it('Stop Music clears the active bar indicator (AC-014)', async () => {
    fetchCalmPhraseMock.mockResolvedValue(makePhrase4Bars())
    render(<MusicPlayer sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))
    await waitFor(() => expect(schedulePhraseMock).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: 'Stop Music' }))

    expect(document.querySelector('.music-intent-bar-active')).toBeNull()
  })
})
