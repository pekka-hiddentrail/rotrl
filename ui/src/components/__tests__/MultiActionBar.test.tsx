/**
 * Multi-action economy bar — frontend component tests.
 *
 * Spec: specs/action-economy.feature
 * Covers: AC-010, AC-011, AC-012, AC-013 (UI side)
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import InputBar from '../InputBar'
import type { ActiveSpeaker } from '../../types'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PC_SPEAKER: ActiveSpeaker = {
  name: 'Bonnie',
  color: '#8b5cf6',
  rune: '✦',
  isEnemy: false,
}

function renderBar(onSend = vi.fn()) {
  return render(
    <InputBar
      onSend={onSend}
      disabled={false}
      activeSpeaker={PC_SPEAKER}
      inPcCombatTurn
    />
  )
}

// ── AC-010 — Standard + Move can be active simultaneously ─────────────────────

describe('multi-action — AC-010: Standard + Move multi-select', () => {
  it('shows Standard, Move, Full-Round, Swift, Free buttons when inPcCombatTurn', () => {
    renderBar()
    expect(screen.getByRole('button', { name: /standard/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /move/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /full/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /swift/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /free/i })).toBeInTheDocument()
  })

  it('Standard and Move can both be active at the same time', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    expect(screen.getByRole('button', { name: /standard/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /move/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /full/i })).not.toHaveClass('active')
  })

  it('deselecting Standard leaves Move still active', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    // toggle Standard off
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    expect(screen.getByRole('button', { name: /standard/i })).not.toHaveClass('active')
    expect(screen.getByRole('button', { name: /move/i })).toHaveClass('active')
  })
})

// ── AC-011 — Full-Round exclusive of Standard and Move ────────────────────────

describe('multi-action — AC-011: Full-Round exclusivity', () => {
  it('selecting Full-Round deactivates Standard and Move', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    fireEvent.click(screen.getByRole('button', { name: /full/i }))
    expect(screen.getByRole('button', { name: /full/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /standard/i })).not.toHaveClass('active')
    expect(screen.getByRole('button', { name: /move/i })).not.toHaveClass('active')
  })

  it('selecting Standard while Full-Round is active deactivates Full-Round', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /full/i }))
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    expect(screen.getByRole('button', { name: /standard/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /full/i })).not.toHaveClass('active')
  })

  it('selecting Move while Full-Round is active deactivates Full-Round', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /full/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    expect(screen.getByRole('button', { name: /move/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /full/i })).not.toHaveClass('active')
  })
})

// ── AC-012 — Swift and Free are non-exclusive modifiers ───────────────────────

describe('multi-action — AC-012: Swift and Free non-exclusive', () => {
  it('Swift can be added alongside Full-Round', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /full/i }))
    fireEvent.click(screen.getByRole('button', { name: /swift/i }))
    expect(screen.getByRole('button', { name: /full/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /swift/i })).toHaveClass('active')
  })

  it('Free can be added to Standard+Move', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    fireEvent.click(screen.getByRole('button', { name: /free/i }))
    expect(screen.getByRole('button', { name: /standard/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /move/i })).toHaveClass('active')
    expect(screen.getByRole('button', { name: /free/i })).toHaveClass('active')
  })

  it('Swift does NOT deactivate Full-Round', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /full/i }))
    fireEvent.click(screen.getByRole('button', { name: /swift/i }))
    expect(screen.getByRole('button', { name: /full/i })).toHaveClass('active')
  })

  it('Free does NOT deactivate Standard', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /free/i }))
    expect(screen.getByRole('button', { name: /standard/i })).toHaveClass('active')
  })
})

// ── AC-013 (UI) — action_type_hints sent as ordered array ────────────────────

describe('multi-action — AC-013: onSend receives ordered hints array', () => {
  it('sends ["standard", "move"] when both are selected', () => {
    const onSend = vi.fn()
    renderBar(onSend)
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    const textarea = screen.getByPlaceholderText(/what do you do/i)
    fireEvent.change(textarea, { target: { value: 'I attack and move' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('I attack and move', ['standard', 'move'])
  })

  it('sends ["full", "swift"] when both are selected', () => {
    const onSend = vi.fn()
    renderBar(onSend)
    fireEvent.click(screen.getByRole('button', { name: /full/i }))
    fireEvent.click(screen.getByRole('button', { name: /swift/i }))
    const textarea = screen.getByPlaceholderText(/what do you do/i)
    fireEvent.change(textarea, { target: { value: 'I full attack' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('I full attack', ['full', 'swift'])
  })

  it('sends [] when no buttons are selected', () => {
    const onSend = vi.fn()
    renderBar(onSend)
    const textarea = screen.getByPlaceholderText(/what do you do/i)
    fireEvent.change(textarea, { target: { value: 'I do something' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('I do something', [])
  })

  it('sends ["standard", "move", "free"] in correct priority order', () => {
    const onSend = vi.fn()
    renderBar(onSend)
    // Click in arbitrary order: free, move, standard
    fireEvent.click(screen.getByRole('button', { name: /free/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    const textarea = screen.getByPlaceholderText(/what do you do/i)
    fireEvent.change(textarea, { target: { value: 'I do it' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    // Order must be: standard first, then move, then free
    expect(onSend).toHaveBeenCalledWith('I do it', ['standard', 'move', 'free'])
  })

  it('clears all action selections after submit', () => {
    renderBar()
    fireEvent.click(screen.getByRole('button', { name: /standard/i }))
    fireEvent.click(screen.getByRole('button', { name: /move/i }))
    const textarea = screen.getByPlaceholderText(/what do you do/i)
    fireEvent.change(textarea, { target: { value: 'go' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(screen.getByRole('button', { name: /standard/i })).not.toHaveClass('active')
    expect(screen.getByRole('button', { name: /move/i })).not.toHaveClass('active')
  })
})

// ── Existing AC-001 regression: buttons hidden outside PC combat turn ──────────

describe('multi-action — regression: action row hidden outside PC combat turn', () => {
  it('does not render action buttons when inPcCombatTurn is false', () => {
    render(
      <InputBar
        onSend={vi.fn()}
        disabled={false}
        activeSpeaker={PC_SPEAKER}
        inPcCombatTurn={false}
      />
    )
    expect(screen.queryByRole('button', { name: /standard/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /swift/i })).not.toBeInTheDocument()
  })

  it('does not render action buttons when no combat', () => {
    render(
      <InputBar
        onSend={vi.fn()}
        disabled={false}
        activeSpeaker={PC_SPEAKER}
      />
    )
    expect(screen.queryByRole('button', { name: /standard/i })).not.toBeInTheDocument()
  })
})
