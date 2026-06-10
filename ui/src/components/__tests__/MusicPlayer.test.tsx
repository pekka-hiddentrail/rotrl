import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import MusicPlayer from '../MusicPlayer'
import type { CalmPhrase } from '../../api'

const stopMock = vi.fn()
const schedulePhraseMock = vi.fn(() => ({ start_delay_seconds: 0, duration_seconds: 0.2 }))
const startAudioContextMock = vi.fn().mockResolvedValue(undefined)
const fetchCalmPhraseMock = vi.fn<(...args: unknown[]) => Promise<CalmPhrase>>()

vi.mock('tone', () => ({
  getDestination: () => ({ volume: { value: 0 } }),
}))

vi.mock('../../music/player', () => ({
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

function makePhrase(): CalmPhrase {
  return {
    phrase_id: 'p-1',
    mood: 'calm',
    key: 'C',
    scale: ['C', 'D', 'E', 'G', 'A'],
    bpm: 100,
    time_signature: '4/4',
    bars: 4,
    events: [{ bar: 1, beat: 1, note: 'C5', midi: 72, duration: '4n', velocity: 88 }],
    state: {
      motif_id: 'm-1',
      motif_degrees: [1, 3, 5],
      cadence_degree: 1,
      highest_degree: 5,
      novelty: 0.3,
    },
  }
}

describe('MusicPlayer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    fetchCalmPhraseMock.mockResolvedValue(makePhrase())
  })

  it('starts playback and fetches one phrase on Start', async () => {
    render(<MusicPlayer sessionId="sess-1" />)

    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(startAudioContextMock).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(1))
    expect(schedulePhraseMock).toHaveBeenCalledTimes(1)
  })

  it('shows Stopped status and no Off badge', () => {
    render(<MusicPlayer sessionId="sess-1" />)
    expect(screen.getByText('Stopped')).toBeInTheDocument()
    expect(screen.queryByText('Off')).not.toBeInTheDocument()
  })

  it('stop button halts playback and prevents follow-up fetches', async () => {
    render(<MusicPlayer sessionId="sess-1" />)

    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: 'Stop Music' }))
    expect(stopMock).toHaveBeenCalled()

    await new Promise(resolve => setTimeout(resolve, 250))
    expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(1)
  })

  it('volume slider persists to localStorage and updates displayed value', () => {
    render(<MusicPlayer sessionId="sess-1" />)
    const slider = screen.getByLabelText('Music volume') as HTMLInputElement

    fireEvent.change(slider, { target: { value: '50' } })

    expect(slider.value).toBe('50')
    expect(window.localStorage.getItem('rotrl.music.volume')).toBe('50')
  })

  it('restores volume from localStorage on mount', () => {
    window.localStorage.setItem('rotrl.music.volume', '30')
    render(<MusicPlayer sessionId="sess-1" />)

    const slider = screen.getByLabelText('Music volume') as HTMLInputElement
    expect(slider.value).toBe('30')
  })
})
