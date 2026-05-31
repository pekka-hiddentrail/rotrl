/**
 * DicePanel — attack-resolution UI tests.
 *
 * Spec: specs/attack-resolution.feature
 * Covers: AC-002, AC-003, AC-004, AC-008
 *
 * Separate from DicePanel.test.tsx so build_coverage.py can attribute
 * these ACs to attack-resolution.feature without ambiguity.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DicePanel from '../DicePanel'
import type { AttackPhase, AttackResult } from '../../types'

// ─── Fixtures ────────────────────────────────────────────────────────────────

const TO_HIT_PHASE: AttackPhase = {
  phase: 'to_hit',
  attacker: 'Thaelion',
  target: 'Goblin 1',
  bonus: 5,
  ac: 13,
  damage_expr: '1d8+3',
  attack_type: 'melee',
}

const DAMAGE_PHASE: AttackPhase = {
  phase: 'damage',
  attacker: 'Thaelion',
  target: 'Goblin 1',
  damage_expr: '1d8+3',
  hit_total: 20,
}

const HIT_RESULT: AttackResult = {
  attacker: 'Thaelion', target: 'Goblin 1',
  roll: 15, bonus: 5, total: 20, ac: 13,
  hit: true, damage_rolls: [6], damage_total: 6,
  attack_type: 'melee', is_pc: true,
}

const MISS_RESULT: AttackResult = {
  attacker: 'Goblin 1', target: 'Shalelu',
  roll: 3, bonus: 4, total: 7, ac: 17,
  hit: false, damage_rolls: [], damage_total: 0,
  attack_type: 'melee', is_pc: false,
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function renderPanel(props: {
  attackPhase?: AttackPhase
  attackLog?: AttackResult[]
  onAttackRoll?: ReturnType<typeof vi.fn>
  onDamageRoll?: ReturnType<typeof vi.fn>
  onRoll?: ReturnType<typeof vi.fn>
} = {}) {
  return render(
    <DicePanel
      sessionId="s1"
      pendingRoll={null}
      activeSpeaker={null}
      onRoll={props.onRoll ?? vi.fn().mockResolvedValue(null)}
      attackPhase={props.attackPhase ?? null}
      attackLog={props.attackLog ?? []}
      onAttackRoll={props.onAttackRoll}
      onDamageRoll={props.onDamageRoll}
    />,
  )
}

// Math.random fixed to 0.6 → floor(0.6 * 20) + 1 = 13
beforeEach(() => { vi.spyOn(Math, 'random').mockReturnValue(0.6) })
afterEach(() => { vi.restoreAllMocks() })

// ─── AC-003 — to-hit banner ───────────────────────────────────────────────────

describe('DicePanel — AC-003 to-hit banner', () => {
  it('renders attacker and target', () => {
    renderPanel({ attackPhase: TO_HIT_PHASE })
    expect(screen.getByText(/Thaelion → Goblin 1/)).toBeInTheDocument()
  })

  it('renders AC and bonus', () => {
    renderPanel({ attackPhase: TO_HIT_PHASE })
    expect(screen.getByText(/vs AC 13/)).toBeInTheDocument()
    expect(screen.getByText(/bonus: \+5/)).toBeInTheDocument()
  })

  it('applies dice-panel-active class to aside', () => {
    const { container } = renderPanel({ attackPhase: TO_HIT_PHASE })
    expect(container.querySelector('aside')).toHaveClass('dice-panel-active')
  })

  it('clicking the banner calls onAttackRoll with the rolled d20 value', async () => {
    const onAttackRoll = vi.fn().mockResolvedValue(undefined)
    renderPanel({ attackPhase: TO_HIT_PHASE, onAttackRoll })
    fireEvent.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(onAttackRoll).toHaveBeenCalledWith(13))
  })
})

// ─── AC-004 — damage banner ───────────────────────────────────────────────────

describe('DicePanel — AC-004 damage banner', () => {
  it('renders HIT and attacker → target', () => {
    renderPanel({ attackPhase: DAMAGE_PHASE })
    expect(screen.getByText(/HIT!.*Thaelion/)).toBeInTheDocument()
    expect(screen.getByText(/Thaelion.*Goblin 1/)).toBeInTheDocument()
  })

  it('renders the damage expression', () => {
    renderPanel({ attackPhase: DAMAGE_PHASE })
    expect(screen.getByText(/Roll damage: 1d8\+3/)).toBeInTheDocument()
  })

  it('Roll Damage button is disabled when the dice queue is empty', () => {
    renderPanel({ attackPhase: DAMAGE_PHASE })
    expect(screen.getByRole('button', { name: 'Roll Damage' })).toBeDisabled()
  })

  it('Roll Damage button is enabled after queuing dice', () => {
    renderPanel({ attackPhase: DAMAGE_PHASE })
    fireEvent.click(screen.getByTitle('d8'))
    expect(screen.getByRole('button', { name: 'Roll Damage' })).not.toBeDisabled()
  })

  it('V8 — Roll Damage calls onDamageRoll with actual rolled values, not die sizes', async () => {
    // Math.random = 0.6 → rollDie(8) = floor(0.6 * 8) + 1 = 5
    const onDamageRoll = vi.fn().mockResolvedValue(undefined)
    renderPanel({ attackPhase: DAMAGE_PHASE, onDamageRoll })
    fireEvent.click(screen.getByTitle('d8'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll Damage' }))
    await waitFor(() => expect(onDamageRoll).toHaveBeenCalledWith([5], 5))
  })
})

// ─── AC-003 — null phase ──────────────────────────────────────────────────────

describe('DicePanel — AC-003 null attack phase', () => {
  it('no attack banner rendered when attackPhase is null', () => {
    const { container } = renderPanel({ attackPhase: null })
    expect(container.querySelector('.attack-banner')).not.toBeInTheDocument()
  })

  it('no dice-panel-active class when attackPhase and pendingRoll are both null', () => {
    const { container } = renderPanel({ attackPhase: null })
    expect(container.querySelector('aside')).not.toHaveClass('dice-panel-active')
  })
})

// ─── AC-002, AC-008 — attack log ─────────────────────────────────────────────

describe('DicePanel — AC-002 AC-008 attack log', () => {
  it('hit entry shows HIT badge and damage total', () => {
    renderPanel({ attackLog: [HIT_RESULT] })
    expect(screen.getByText('HIT')).toBeInTheDocument()
    expect(screen.getByText(/6 dmg/)).toBeInTheDocument()
  })

  it('hit entry shows attacker → target and PC label', () => {
    renderPanel({ attackLog: [HIT_RESULT] })
    expect(screen.getByText(/Thaelion → Goblin 1/)).toBeInTheDocument()
    expect(screen.getByText(/PC/)).toBeInTheDocument()
  })

  it('miss entry shows MISS badge and no damage', () => {
    renderPanel({ attackLog: [MISS_RESULT] })
    expect(screen.getByText('MISS')).toBeInTheDocument()
    expect(screen.queryByText(/dmg/)).not.toBeInTheDocument()
  })

  it('miss entry shows NPC label', () => {
    renderPanel({ attackLog: [MISS_RESULT] })
    expect(screen.getByText(/NPC/)).toBeInTheDocument()
  })

  it('attack log rows appear before skill-roll history rows in DOM', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    const { container } = renderPanel({ attackLog: [HIT_RESULT], onRoll })
    // Generate one skill-roll entry
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(onRoll).toHaveBeenCalled())

    const allRows     = Array.from(container.querySelectorAll('.history-row'))
    const firstAttack = allRows.findIndex(r => r.classList.contains('attack-history-row'))
    const firstSkill  = allRows.findIndex(r => !r.classList.contains('attack-history-row'))

    expect(firstAttack).toBeGreaterThanOrEqual(0)
    expect(firstSkill).toBeGreaterThanOrEqual(0)
    expect(firstAttack).toBeLessThan(firstSkill)
  })
})
