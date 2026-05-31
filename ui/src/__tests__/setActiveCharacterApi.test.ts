/**
 * Unit tests for the api.ts setActiveCharacter function.
 * Uses the real implementation (no module mock) and stubs global fetch.
 *
 * Spec: specs/session-state.feature
 * Covers: AC-014 (PUT sends name), AC-015 (party), AC-016 (error path)
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { setActiveCharacter } from '../api'

afterEach(() => vi.unstubAllGlobals())

describe('api.ts — setActiveCharacter', () => {
  it('calls PUT /api/sessions/{id}/active_character with the character name', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ active_character: 'Ani' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await setActiveCharacter('sess-1', 'Ani')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/sessions/sess-1/active_character',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ name: 'Ani' }),
      }),
    )
  })

  it('sends "party" to deselect', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ active_character: 'party' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await setActiveCharacter('sess-1', 'party')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/sessions/sess-1/active_character',
      expect.objectContaining({ body: JSON.stringify({ name: 'party' }) }),
    )
  })

  it('returns the active_character from the response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ active_character: 'Yanyeeku' }),
    }))

    const result = await setActiveCharacter('sess-1', 'Yanyeeku')
    expect(result.active_character).toBe('Yanyeeku')
  })

  it('throws when the server returns non-200', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    await expect(setActiveCharacter('sess-1', 'Ani')).rejects.toThrow('404')
  })

  it('includes Content-Type application/json header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ active_character: 'Ani' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await setActiveCharacter('sess-2', 'Ani')

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })
})
