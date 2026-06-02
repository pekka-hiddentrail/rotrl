/**
 * CombatEventCard — action card rendered for role === 'combat-event'.
 *
 * Spec: specs/enemy-turn.feature  CB1.9-3
 * Covers: centered card appearance, HIT/MISS styling, graceful absence.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../MessageBubble'
import type { Message } from '../../types'

const hitCard: Message = {
  role: 'combat-event',
  content: '',
  attackResult: {
    attacker: 'Goblin Warchanter',
    target: 'Yanyeeku',
    roll: 15,
    bonus: 5,
    total: 20,
    ac: 12,
    hit: true,
    damage_rolls: [3],
    damage_total: 3,
    attack_type: 'ranged',
    is_pc: false,
  },
}

const missCard: Message = {
  ...hitCard,
  attackResult: {
    ...hitCard.attackResult!,
    roll: 5,
    total: 10,
    hit: false,
    damage_rolls: [],
    damage_total: 0,
  },
}

describe('CombatEventCard', () => {
  it('renders attacker and target', () => {
    render(<MessageBubble message={hitCard} isLast={false} streaming={false} />)
    expect(screen.getByText(/Goblin Warchanter.*Yanyeeku/)).toBeInTheDocument()
  })

  it('renders roll breakdown', () => {
    render(<MessageBubble message={hitCard} isLast={false} streaming={false} />)
    expect(screen.getByText(/15.*5.*20.*AC 12/)).toBeInTheDocument()
  })

  it('HIT shows damage total', () => {
    render(<MessageBubble message={hitCard} isLast={false} streaming={false} />)
    expect(screen.getByText(/HIT.*3 damage/i)).toBeInTheDocument()
  })

  it('MISS shows MISS label without damage', () => {
    render(<MessageBubble message={missCard} isLast={false} streaming={false} />)
    expect(screen.getByText(/^MISS$/i)).toBeInTheDocument()
  })

  it('HIT outcome has combat-event-hit class', () => {
    const { container } = render(<MessageBubble message={hitCard} isLast={false} streaming={false} />)
    expect(container.querySelector('.combat-event-hit')).not.toBeNull()
  })

  it('MISS outcome has combat-event-miss class', () => {
    const { container } = render(<MessageBubble message={missCard} isLast={false} streaming={false} />)
    expect(container.querySelector('.combat-event-miss')).not.toBeNull()
  })

  it('card is wrapped in combat-event-row for centering', () => {
    const { container } = render(<MessageBubble message={hitCard} isLast={false} streaming={false} />)
    expect(container.querySelector('.combat-event-row')).not.toBeNull()
  })

  it('no card rendered for gm role', () => {
    const msg: Message = { role: 'gm', content: 'normal text' }
    const { container } = render(<MessageBubble message={msg} isLast={false} streaming={false} />)
    expect(container.querySelector('.combat-event-card')).toBeNull()
  })
})
