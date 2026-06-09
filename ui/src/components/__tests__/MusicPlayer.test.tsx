import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import MusicPlayer from '../MusicPlayer'
import type { CalmPhrase } from '../../api'

const stopMock = vi.fn()
const schedulePhraseMock = vi.fn(() => ({ start_delay_seconds: 0, duration_seconds: 0.2 }))
const startAudioContextMock = vi.fn().mockResolvedValue(undefined)
const fetchCalmPhraseMock = vi.fn<(...args: unknown[]) => Promise<CalmPhrase>>()

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

  it('keeps start disabled when Music Off is persisted', () => {
    window.localStorage.setItem('rotrl.music.off', 'true')
    render(<MusicPlayer sessionId="sess-1" />)

    expect(screen.getByRole('button', { name: 'Start Music' })).toBeDisabled()
    expect(screen.getByText('Off')).toBeInTheDocument()
  })

  it('starts playback and fetches one phrase on Start', async () => {
    render(<MusicPlayer sessionId="sess-1" />)

    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))

    await waitFor(() => expect(startAudioContextMock).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(1))
    expect(schedulePhraseMock).toHaveBeenCalledTimes(1)
  })

  it('stops playback and prevents follow-up fetches when Music Off is enabled', async () => {
    render(<MusicPlayer sessionId="sess-1" />)

    fireEvent.click(screen.getByRole('button', { name: 'Start Music' }))
    await waitFor(() => expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByLabelText('Music Off'))
    expect(stopMock).toHaveBeenCalled()

    await new Promise(resolve => setTimeout(resolve, 250))
    expect(fetchCalmPhraseMock).toHaveBeenCalledTimes(1)
  })
})
