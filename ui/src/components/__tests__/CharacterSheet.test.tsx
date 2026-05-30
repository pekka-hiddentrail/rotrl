/**
 * Character sheet AC coverage.
 *
 * Covers character-system.feature AC-004 through AC-006:
 * modal close behavior, sheet sections, stat/save tooltips, tooltip positioning,
 * spell grouping, and per-spell tooltips.
 */
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CharacterSheet from '../CharacterSheet'
import { makeCharacter } from '../../test/fixtures'

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('CharacterSheet - AC-004 modal content and close behavior', () => {
  it('shows the expected identity, vitals, and sheet sections', () => {
    render(<CharacterSheet character={makeCharacter()} onClose={vi.fn()} />)

    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
    expect(screen.getByText(/Kitsune/)).toBeInTheDocument()
    expect(screen.getByText('HP')).toBeInTheDocument()
    expect(screen.getByText('AC')).toBeInTheDocument()
    expect(screen.getByText('Ability Scores')).toBeInTheDocument()
    expect(screen.getByText('Saving Throws')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getAllByText('Weapons').length).toBeGreaterThan(1)
    expect(screen.getByText(/Spells/)).toBeInTheDocument()
    expect(screen.getByText('Inventory')).toBeInTheDocument()
  })

  it('closes when the backdrop is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(<CharacterSheet character={makeCharacter()} onClose={onClose} />)

    fireEvent.click(container.querySelector('.sheet-overlay')!)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('does not close when the sheet panel itself is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(<CharacterSheet character={makeCharacter()} onClose={onClose} />)

    fireEvent.click(container.querySelector('.sheet-panel')!)
    expect(onClose).not.toHaveBeenCalled()
  })

  it('closes when the close button is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(<CharacterSheet character={makeCharacter()} onClose={onClose} />)

    fireEvent.click(container.querySelector('.sheet-close')!)
    expect(onClose).toHaveBeenCalledOnce()
  })
})

describe('CharacterSheet - AC-005 stat tooltips', () => {
  it('shows AC component breakdown after the tooltip delay', () => {
    vi.useFakeTimers()
    render(<CharacterSheet character={makeCharacter()} onClose={vi.fn()} />)

    fireEvent.mouseEnter(screen.getByText('AC').closest('.has-tip')!)
    act(() => vi.advanceTimersByTime(900))

    expect(screen.getByText('Armor Class')).toBeInTheDocument()
    expect(screen.getByText('Armor')).toBeInTheDocument()
    expect(screen.getAllByText('+4').length).toBeGreaterThan(0)
    expect(screen.getByText('Flat-Footed')).toBeInTheDocument()
  })

  it('positions the tooltip away from the right viewport edge', () => {
    vi.useFakeTimers()
    const { container } = render(<CharacterSheet character={makeCharacter()} onClose={vi.fn()} />)
    const target = screen.getByText('AC').closest('.has-tip') as HTMLElement
    vi.spyOn(target, 'getBoundingClientRect').mockReturnValue({
      x: 970,
      y: 10,
      left: 970,
      top: 10,
      right: 990,
      bottom: 30,
      width: 20,
      height: 20,
      toJSON: () => ({}),
    } as DOMRect)
    vi.stubGlobal('innerWidth', 1000)
    vi.stubGlobal('innerHeight', 800)

    fireEvent.mouseEnter(target)
    act(() => vi.advanceTimersByTime(900))

    expect(container.ownerDocument.body.querySelector('.tooltip-box')).toHaveStyle({ left: '722px' })
    vi.unstubAllGlobals()
  })

  it('shows saving throw breakdowns', () => {
    vi.useFakeTimers()
    render(<CharacterSheet character={makeCharacter()} onClose={vi.fn()} />)

    fireEvent.mouseEnter(screen.getByText('Fortitude').closest('.has-tip')!)
    act(() => vi.advanceTimersByTime(900))

    expect(screen.getAllByText('Fortitude').length).toBeGreaterThan(1)
    expect(screen.getByText('Base')).toBeInTheDocument()
    expect(screen.getByText('Ability (CON)')).toBeInTheDocument()
    expect(screen.getByText('Magic')).toBeInTheDocument()
    expect(screen.getByText('Misc')).toBeInTheDocument()
  })
})

describe('CharacterSheet - AC-006 spell grouping and tooltips', () => {
  it('groups spells by level', () => {
    const { container } = render(<CharacterSheet character={makeCharacter()} onClose={vi.fn()} />)
    const levels = Array.from(container.querySelectorAll('.spell-group-label')).map(el => el.textContent)

    expect(levels).toEqual(['0', '1', '2'])
    expect(screen.getByText('Detect Magic')).toBeInTheDocument()
    expect(screen.getByText('Burning Hands')).toBeInTheDocument()
    expect(screen.getByText('Flaming Sphere')).toBeInTheDocument()
  })

  it('shows per-spell casting details in the tooltip', () => {
    vi.useFakeTimers()
    render(<CharacterSheet character={makeCharacter()} onClose={vi.fn()} />)

    fireEvent.mouseEnter(screen.getByText('Burning Hands').closest('.has-tip')!)
    act(() => vi.advanceTimersByTime(900))

    expect(screen.getByText('Cast Time')).toBeInTheDocument()
    expect(screen.getByText('Duration')).toBeInTheDocument()
    expect(screen.getByText('Range')).toBeInTheDocument()
    expect(screen.getByText('Components')).toBeInTheDocument()
    expect(screen.getByText('School')).toBeInTheDocument()
    expect(screen.getByText('Reflex half')).toBeInTheDocument()
    expect(screen.getByText(/cone of flame/i)).toBeInTheDocument()
  })
})
