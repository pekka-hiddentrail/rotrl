import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InputBar from '../InputBar'

const noop = vi.fn()
const PC_SPEAKER = { name: 'Ani', rune: 'ᚢ', color: '#60a0d0', isEnemy: false }
const ENEMY_SPEAKER = { name: 'Goblin Warrior 1', rune: '', color: '#cc2222', isEnemy: true }

describe('InputBar action-economy feature flag', () => {
  it('keeps action buttons hidden during a PC combat turn while the feature flag is off', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)
    expect(screen.queryByRole('button', { name: 'Standard' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Move' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Full-Round' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Swift' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Free' })).not.toBeInTheDocument()
  })

  it('keeps action buttons hidden during enemy turns', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} inPcCombatTurn />)
    expect(screen.queryByRole('button', { name: 'Standard' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Move' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Full-Round' })).not.toBeInTheDocument()
  })

  it('still submits combat text with an empty action hint list', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} activeSpeaker={PC_SPEAKER} inPcCombatTurn />)

    await user.type(screen.getByRole('textbox'), 'I observe the enemy')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('I observe the enemy', [])
  })
})
