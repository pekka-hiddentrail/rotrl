import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchCalmPhrase, type CalmPhrase } from '../api'

afterEach(() => vi.unstubAllGlobals())

function makePhrase(): CalmPhrase {
  return {
    phrase_id: 'p-1',
    mood: 'calm',
    key: 'C',
    scale: ['C', 'D', 'E', 'G', 'A'],
    bpm: 96,
    time_signature: '4/4',
    bars: 4,
    events: [
      { bar: 1, beat: 1, note: 'C5', midi: 72, duration: '4n', velocity: 88 },
    ],
    state: {
      motif_id: 'm-1',
      motif_degrees: [1, 3, 5],
      cadence_degree: 1,
      highest_degree: 5,
      novelty: 0.2,
    },
  }
}

describe('api.ts - fetchCalmPhrase', () => {
  it('posts snake_case request payload and returns phrase JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makePhrase()),
    })
    vi.stubGlobal('fetch', fetchMock)

    const phrase = await fetchCalmPhrase('sess-1', 42, null)

    expect(phrase.phrase_id).toBe('p-1')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/music/calm/next_phrase',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          session_id: 'sess-1',
          seed: 42,
          previous_state: null,
        }),
      }),
    )
  })

  it('throws a generation_failed specific message for 422', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: () => Promise.resolve(JSON.stringify({
        detail: 'could not generate phrase in retry budget',
        error_code: 'generation_failed',
      })),
    }))

    await expect(fetchCalmPhrase('sess-1', 7, null)).rejects.toThrow(/Music generation failed/i)
  })
})
