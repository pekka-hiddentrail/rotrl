/**
 * Spec: specs/enemy-turn.feature
 * Covers: enemy-turn.feature AC-013
 * Covers: combat-tracker.feature AC-016, AC-017, AC-018
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CombatPanel from '../CombatPanel'
import type { CombatState } from '../../types'

const combatState: CombatState = {
  round: 1,
  current_actor: 'Goblin Warrior 1',
  combatants: [
    { name: 'Vanx', hp_current: 10, hp_max: 10, ac: 18, initiative: 14, status: 'active' },
    { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 10, status: 'active' },
  ],
}

function renderPanel(overrides: Partial<Parameters<typeof CombatPanel>[0]> = {}) {
  const props = {
    combatState,
    currentCombatantName: 'Goblin Warrior 1',
    onAdvanceTurn: vi.fn(),
    onEnemyTurn: vi.fn(),
    onEndCombat: vi.fn(),
    ...overrides,
  }
  render(<CombatPanel {...props} />)
  return props
}

describe('CombatPanel - enemy turn controls', () => {
  it('renders an enabled Enemy Turn button when onEnemyTurn is provided', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: 'Enemy Turn' })).toBeEnabled()
  })

  it('clicking Enemy Turn calls onEnemyTurn once', () => {
    const props = renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Enemy Turn' }))
    expect(props.onEnemyTurn).toHaveBeenCalledTimes(1)
  })

  it('disables Enemy Turn when the panel disabled prop is true', () => {
    renderPanel({ disabled: true })
    expect(screen.getByRole('button', { name: 'Enemy Turn' })).toBeDisabled()
  })

  it('disables Enemy Turn while a PC attack phase is pending', () => {
    renderPanel({
      attackPhase: {
        phase: 'to_hit',
        attacker: 'Vanx',
        target: 'Goblin Warrior 1',
        bonus: 4,
        ac: 16,
        damage_expr: '1d6',
        attack_type: 'melee',
      },
    })
    expect(screen.getByRole('button', { name: 'Enemy Turn' })).toBeDisabled()
  })

  it('shows no phase badge when no attack or enemy stream is active', () => {
    renderPanel()
    expect(screen.queryByText('PC Attacks')).not.toBeInTheDocument()
    expect(screen.queryByText('Enemy Turn', { selector: '.combat-phase-badge' })).not.toBeInTheDocument()
  })

  it('shows a red Enemy Turn phase badge while enemyTurnStreaming is true', () => {
    renderPanel({ enemyTurnStreaming: true })
    const badge = screen.getByText('Enemy Turn', { selector: '.combat-phase-badge' })
    expect(badge).toHaveClass('enemy')
    expect(screen.getByRole('button', { name: 'Enemy Acting...' })).toBeDisabled()
  })

  it('shows an amber PC Attacks phase badge while attackPhase is non-null', () => {
    renderPanel({
      attackPhase: {
        phase: 'damage',
        attacker: 'Vanx',
        target: 'Goblin Warrior 1',
        damage_expr: '1d6',
        hit_total: 20,
        attack_type: 'melee',
      },
    })
    const badge = screen.getByText('PC Attacks')
    expect(badge).toHaveClass('pc')
  })

  it('gives Enemy Turn badge precedence when both states are true', () => {
    renderPanel({
      enemyTurnStreaming: true,
      attackPhase: {
        phase: 'damage',
        attacker: 'Vanx',
        target: 'Goblin Warrior 1',
        damage_expr: '1d6',
        hit_total: 20,
        attack_type: 'melee',
      },
    })
    expect(screen.getByText('Enemy Turn', { selector: '.combat-phase-badge' })).toHaveClass('enemy')
    expect(screen.queryByText('PC Attacks')).not.toBeInTheDocument()
  })

  it('shows a disabled Closing... button while close_combat is streaming', () => {
    renderPanel({ combatClosing: true })
    expect(screen.getByRole('button', { name: 'Closing...' })).toBeDisabled()
  })
})
