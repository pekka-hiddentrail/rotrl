/**
 * InputBar — action economy (action-type buttons) tests.
 *
 * Spec: specs/action-economy.feature
 * Covers: AC-001 through AC-006
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InputBar from '../InputBar'

const noop = vi.fn()

const PC_SPEAKER  = { name: 'Ani', rune: 'ᚢ', color: '#60a0d0', isEnemy: false }
const PC_SPEAKER2 = { name: 'Vanx', rune: 'ᚹ', color: '#a060d0', isEnemy: false }
const ENEMY_SPEAKER = { name: 'Goblin Warrior 1', rune: '', color: '#cc2222', isEnemy: true }

// ── AC-001 — Buttons only visible on a PC's combat turn ──────────────────────

describe('InputBar action-economy — AC-001: button visibility', () => {
  it('no action-type buttons when inPcCombatTurn is false (default)', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} />)
    expect(screen.queryByRole('button', { name: 'Standard' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Move' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Full-Round' })).toBeNull()
  })

  it('shows Standard, Move, Full-Round buttons when inPcCombatTurn is true and speaker is PC', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    expect(screen.getByRole('button', { name: 'Standard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Move' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Full-Round' })).toBeInTheDocument()
  })

  it('does NOT show buttons when inPcCombatTurn is true but speaker is enemy', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} inPcCombatTurn />)
    expect(screen.queryByRole('button', { name: 'Standard' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Move' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Full-Round' })).toBeNull()
  })

  it('does NOT show buttons when no activeSpeaker and inPcCombatTurn is false', () => {
    render(<InputBar onSend={noop} disabled={false} />)
    expect(screen.queryByRole('button', { name: 'Standard' })).toBeNull()
  })
})

// ── AC-002 — Selecting a button highlights it ─────────────────────────────────

describe('InputBar action-economy — AC-002: selection highlights button', () => {
  it('clicking Standard adds active class; Move and Full-Round are not active', () => {
    const { container } = render(
      <InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Standard' }))

    const standardBtn  = screen.getByRole('button', { name: 'Standard' })
    const moveBtn      = screen.getByRole('button', { name: 'Move' })
    const fullRoundBtn = screen.getByRole('button', { name: 'Full-Round' })

    expect(standardBtn.className).toContain('active')
    expect(moveBtn.className).not.toContain('active')
    expect(fullRoundBtn.className).not.toContain('active')
  })

  it('clicking Move highlights Move; others are not active', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    expect(screen.getByRole('button', { name: 'Move' }).className).toContain('active')
    expect(screen.getByRole('button', { name: 'Standard' }).className).not.toContain('active')
    expect(screen.getByRole('button', { name: 'Full-Round' }).className).not.toContain('active')
  })

  it('clicking a different button shifts the active class', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    fireEvent.click(screen.getByRole('button', { name: 'Standard' }))
    fireEvent.click(screen.getByRole('button', { name: 'Full-Round' }))

    expect(screen.getByRole('button', { name: 'Full-Round' }).className).toContain('active')
    expect(screen.getByRole('button', { name: 'Standard' }).className).not.toContain('active')
  })

  it('no button is active on initial render', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    for (const label of ['Standard', 'Move', 'Full-Round']) {
      expect(screen.getByRole('button', { name: label }).className).not.toContain('active')
    }
  })
})

// ── AC-003 — Toggle: clicking active button deselects ─────────────────────────

describe('InputBar action-economy — AC-003: toggle deselects active button', () => {
  it('clicking Standard twice leaves no button active', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    fireEvent.click(screen.getByRole('button', { name: 'Standard' }))
    fireEvent.click(screen.getByRole('button', { name: 'Standard' }))

    for (const label of ['Standard', 'Move', 'Full-Round']) {
      expect(screen.getByRole('button', { name: label }).className).not.toContain('active')
    }
  })

  it('clicking Move twice leaves no button active', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    expect(screen.getByRole('button', { name: 'Move' }).className).not.toContain('active')
  })
})

// ── AC-004 — Selection resets when the turn advances ─────────────────────────

describe('InputBar action-economy — AC-004: reset on speaker change', () => {
  it('selected action type is cleared when activeSpeaker name changes', () => {
    const { rerender } = render(
      <InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Full-Round' }))
    expect(screen.getByRole('button', { name: 'Full-Round' }).className).toContain('active')

    // Turn advances — different PC speaker
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER2} inPcCombatTurn />)

    for (const label of ['Standard', 'Move', 'Full-Round']) {
      expect(screen.getByRole('button', { name: label }).className).not.toContain('active')
    }
  })

  it('selection is cleared when the same PC gets the turn again (name change cycle)', () => {
    const { rerender } = render(
      <InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    // Enemy turn
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} inPcCombatTurn />)
    // Back to Ani
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    for (const label of ['Standard', 'Move', 'Full-Round']) {
      expect(screen.getByRole('button', { name: label }).className).not.toContain('active')
    }
  })
})

// ── AC-005 — Selection resets after submit ────────────────────────────────────

describe('InputBar action-economy — AC-005: reset after submit', () => {
  it('after sending, no action-type button remains active', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    fireEvent.click(screen.getByRole('button', { name: 'Standard' }))
    await user.type(screen.getByRole('textbox'), 'I attack the goblin')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    for (const label of ['Standard', 'Move', 'Full-Round']) {
      expect(screen.getByRole('button', { name: label }).className).not.toContain('active')
    }
  })
})

// ── AC-006 — action_type_hint sent in onSend call ─────────────────────────────

describe('InputBar action-economy — AC-006: action_type_hint forwarded to onSend', () => {
  it('calls onSend with ("text", "standard") when Standard is selected', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    fireEvent.click(screen.getByRole('button', { name: 'Standard' }))
    await user.type(screen.getByRole('textbox'), 'I swing at the goblin')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('I swing at the goblin', 'standard')
  })

  it('calls onSend with ("text", "move") when Move is selected', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    fireEvent.click(screen.getByRole('button', { name: 'Move' }))
    await user.type(screen.getByRole('textbox'), 'I run to cover')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('I run to cover', 'move')
  })

  it('calls onSend with ("text", "full") when Full-Round is selected', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    fireEvent.click(screen.getByRole('button', { name: 'Full-Round' }))
    await user.type(screen.getByRole('textbox'), 'Full attack!')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('Full attack!', 'full')
  })

  it('calls onSend with only the text (no hint) when no button is selected', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    await user.type(screen.getByRole('textbox'), 'I observe the enemy')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('I observe the enemy')
    expect(onSend).not.toHaveBeenCalledWith(expect.anything(), expect.anything())
  })

  it('also sends via Enter key with action_type_hint', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    fireEvent.click(screen.getByRole('button', { name: 'Move' }))
    await user.type(screen.getByRole('textbox'), 'I run{Enter}')

    expect(onSend).toHaveBeenCalledWith('I run', 'move')
  })
})
