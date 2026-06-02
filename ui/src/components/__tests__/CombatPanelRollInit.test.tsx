/**
 * CombatPanel — initiative display tests.
 *
 * Spec: specs/roll-initiatives.feature  AC-008
 * Initiative is rolled automatically by the backend (no player button).
 * These tests verify the panel displays the server-rolled order correctly
 * and that the Roll Initiatives button is absent.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import CombatPanel from '../CombatPanel'
import type { CombatState } from '../../types'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const ROLLED_STATE: CombatState = {
  round: 1,
  current_actor: 'Goblin Warchanter',
  combatants: [
    { name: 'Goblin Warchanter', hp_current: 8, hp_max: 8,  ac: 14, initiative: 18, status: 'active', conditions: [] },
    { name: 'Ani',               hp_current: 11, hp_max: 11, ac: 17, initiative: 14, status: 'active', conditions: [] },
    { name: 'Goblin Warrior 1',  hp_current: 5,  hp_max: 5,  ac: 16, initiative: 9,  status: 'active', conditions: [] },
  ],
}

// ── No button ─────────────────────────────────────────────────────────────────

describe('CombatPanel — Roll Initiatives button removed (auto-roll)', () => {
  it('does not render a Roll Initiatives button', () => {
    render(<CombatPanel combatState={ROLLED_STATE} onEndCombat={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /Roll Initiatives/i })).toBeNull()
  })

  it('does not render a Roll Initiatives button even when combat is active', () => {
    render(
      <CombatPanel
        combatState={ROLLED_STATE}
        onEndCombat={vi.fn()}
        disabled={false}
      />,
    )
    expect(screen.queryByText(/Roll Initiatives/i)).toBeNull()
  })
})

// ── Initiative order display ──────────────────────────────────────────────────

describe('CombatPanel — server-rolled initiative order displayed', () => {
  it('shows combatants sorted descending by server-rolled initiative', () => {
    const { container } = render(<CombatPanel combatState={ROLLED_STATE} onEndCombat={vi.fn()} />)
    const rows = container.querySelectorAll('.combatant-row')
    expect(rows).toHaveLength(3)
    // First row = highest initiative
    expect(rows[0].textContent).toContain('Goblin Warchanter')
    expect(rows[1].textContent).toContain('Ani')
    expect(rows[2].textContent).toContain('Goblin Warrior 1')
  })

  it('shows the round badge when round >= 1', () => {
    render(<CombatPanel combatState={ROLLED_STATE} onEndCombat={vi.fn()} />)
    expect(screen.getByText('Round 1')).toBeInTheDocument()
  })

  it('highlights the current actor (highest after auto-roll)', () => {
    const { container } = render(
      <CombatPanel
        combatState={ROLLED_STATE}
        currentCombatantName="Goblin Warchanter"
        onEndCombat={vi.fn()}
      />,
    )
    const current = container.querySelector('.combatant-current')
    expect(current).not.toBeNull()
    expect(current!.textContent).toContain('Goblin Warchanter')
  })
})
