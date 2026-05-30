/**
 * Character sidebar data/display AC coverage.
 *
 * Covers character-system.feature AC-002/AC-003:
 * portrait/title, HP bar rendering, and HP color thresholds.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import CharacterSidebar from '../CharacterSidebar'
import { makeCharacter } from '../../test/fixtures'

function renderSidebar(current: number, max = 40) {
  return render(
    <CharacterSidebar
      characters={[makeCharacter({ hp: { current, max, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 } })]}
      loading={false}
      activeSpeakerId={null}
      onSetActive={vi.fn()}
      onOpenSheet={vi.fn()}
    />,
  )
}

describe('CharacterSidebar - AC-002 portrait, tooltip, and HP bar', () => {
  it('shows the portrait image, name label, hover title, and HP bar', () => {
    const { container } = renderSidebar(18, 30)

    expect(screen.getByRole('img', { name: 'Yanyeeku' })).toHaveAttribute('src', '/portraits/yanyeeku.png')
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
    expect(screen.getByTitle(/Yanyeeku/)).toHaveAttribute('title', expect.stringContaining('Kitsune Oracle Lv.1'))
    expect(container.querySelector('.char-hp-bar')).toHaveStyle({ width: '60%' })
  })
})

describe('CharacterSidebar - AC-003 HP color thresholds', () => {
  it('uses green above 50 percent HP', () => {
    const { container } = renderSidebar(32, 40)
    expect(container.querySelector('.char-hp-bar')).toHaveStyle({ background: '#3d7a58' })
  })

  it('uses gold from 25 through 50 percent HP', () => {
    const { container } = renderSidebar(16, 40)
    expect(container.querySelector('.char-hp-bar')).toHaveStyle({ background: '#c9a84c' })
  })

  it('uses red below 25 percent HP', () => {
    const { container } = renderSidebar(8, 40)
    expect(container.querySelector('.char-hp-bar')).toHaveStyle({ background: '#b04040' })
  })
})
