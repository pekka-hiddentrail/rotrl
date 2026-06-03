/**
 * Character data hook AC coverage.
 *
 * Covers character-system.feature AC-001: /api/characters load success and
 * failure state used by App's "Character data: <reason>" error bar.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { __resetCharacterCachesForTests, loadCharacterSheet, useCharacters } from '../characters'
import { makeCharacter } from '../../test/fixtures'

function Probe() {
  const { characters, loading, error, characterMap } = useCharacters()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="error">{error ?? ''}</span>
      <span data-testid="count">{characters.length}</span>
      <span data-testid="mapped">{characterMap.yanyeeku?.name ?? ''}</span>
    </div>
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  __resetCharacterCachesForTests()
})

describe('useCharacters - AC-001 loading', () => {
  it('fetches /api/characters and exposes characters plus characterMap', async () => {
    const summary = {
      id: 'yanyeeku',
      portrait: '/p.png',
      color: '#fff',
      rune: 'Y',
      name: 'Yanyeeku',
      player: 'P',
      race: 'Aasimar',
      subrace: '',
      class: 'Bard',
      archetype: '',
      level: 1,
      hp: { current: 8, max: 10, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
    }
    const fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([summary]),
    })
    vi.stubGlobal('fetch', fetch)

    render(<Probe />)

    expect(screen.getByTestId('loading')).toHaveTextContent('true')
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(fetch).toHaveBeenCalledWith('/api/characters')
    expect(fetch).not.toHaveBeenCalledWith('/api/characters/yanyeeku')
    expect(screen.getByTestId('count')).toHaveTextContent('1')
    expect(screen.getByTestId('mapped')).toHaveTextContent('Yanyeeku')
    expect(screen.getByTestId('error')).toHaveTextContent('')
  })

  it('fetches a full character sheet only when requested and reuses the cache', async () => {
    const full = makeCharacter()
    const fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(full),
    })
    vi.stubGlobal('fetch', fetch)

    const first = await loadCharacterSheet('yanyeeku')
    const second = await loadCharacterSheet('yanyeeku')

    expect(first).toEqual(full)
    expect(second).toEqual(full)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledWith('/api/characters/yanyeeku')
  })

  it('sets an error when /api/characters returns a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    }))

    render(<Probe />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('error')).toHaveTextContent('Error: HTTP 500')
    expect(screen.getByTestId('count')).toHaveTextContent('0')
  })

  it('sets an error when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    render(<Probe />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('error')).toHaveTextContent('TypeError: Failed to fetch')
  })
})
