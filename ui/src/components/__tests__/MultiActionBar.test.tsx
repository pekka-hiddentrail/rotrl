import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import InputBar from '../InputBar'
import type { ActiveSpeaker } from '../../types'

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

describe('multi-action feature flag', () => {
  it('does not render multi-action buttons during a PC combat turn while the feature is disabled', () => {
    renderBar()
    expect(screen.queryByRole('button', { name: /standard/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /move/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /full/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /swift/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /free/i })).not.toBeInTheDocument()
  })

  it('does not render multi-action buttons outside a PC combat turn', () => {
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
})
