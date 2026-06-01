/**
 * CombatPanel — Roll Initiatives button tests.
 *
 * Spec: specs/roll-initiatives.feature  AC-008
 * Covers: button presence, absence when no handler, disabled states, click callback.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CombatPanel from '../CombatPanel'
import type { CombatState } from '../../types'

// ── Fixture ───────────────────────────────────────────────────────────────────

const COMBAT: CombatState = {
  round: 2,
  current_actor: 'Goblin 1',
  combatants: [
    { name: 'Thaelion', hp_current: 18, hp_max: 22, ac: 16, initiative: 10, status: 'active',      conditions: [] },
    { name: 'Goblin 1', hp_current: 5,  hp_max: 5,  ac: 13, initiative: 14, status: 'active',      conditions: [] },
    { name: 'Goblin 2', hp_current: 0,  hp_max: 5,  ac: 13, initiative: 6,  status: 'unconscious', conditions: [] },
  ],
}

const INITIATIVE_PENDING: CombatState = {
  ...COMBAT,
  round: -1,
}

// ── AC-008 — button presence and interaction ──────────────────────────────────

describe('CombatPanel — Roll Initiatives button', () => {
  it('renders the button when onRollInitiatives prop is provided', () => {
    render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeInTheDocument()
  })

  it('does NOT render the button when onRollInitiatives is absent', () => {
    render(<CombatPanel combatState={COMBAT} onEndCombat={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /Roll Initiatives/i })).toBeNull()
  })

  it('calls onRollInitiatives when clicked', () => {
    const onRollInitiatives = vi.fn()
    render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={onRollInitiatives}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /Roll Initiatives/i }))
    expect(onRollInitiatives).toHaveBeenCalledOnce()
  })

  it('is disabled when disabled prop is true', () => {
    render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
        disabled
      />,
    )
    expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeDisabled()
  })

  it('is disabled when enemyTurnStreaming is true', () => {
    render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
        enemyTurnStreaming
      />,
    )
    expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeDisabled()
  })

  it('is disabled when combatClosing is true', () => {
    render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
        combatClosing
      />,
    )
    expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeDisabled()
  })

  it('is enabled when none of the disabled conditions apply', () => {
    render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
        disabled={false}
        enemyTurnStreaming={false}
        combatClosing={false}
      />,
    )
    expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeEnabled()
  })

  it('button is in the header area (beside Round badge)', () => {
    const { container } = render(
      <CombatPanel
        combatState={COMBAT}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
      />,
    )
    const header = container.querySelector('.combat-panel-header')
    expect(header).not.toBeNull()
    const btn = header!.querySelector('button')
    expect(btn).not.toBeNull()
    expect(btn!.textContent).toMatch(/Roll Initiatives/i)
  })

  it('hides the round badge while initiative is pending', () => {
    render(
      <CombatPanel
        combatState={INITIATIVE_PENDING}
        onEndCombat={vi.fn()}
        onRollInitiatives={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /Roll Initiatives/i })).toBeInTheDocument()
    expect(screen.queryByText(/Round/i)).not.toBeInTheDocument()
  })
})
