/**
 * IntentBar AC coverage.
 *
 * Covers intent-bar.feature AC-001 through AC-005:
 * truncated input, NPC/skill/location tags, null tags, detecting state,
 * and the no-context-event diagnostic.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import IntentBar from '../IntentBar'

const baseIntent = {
  npc: 'Ameiko Kaijitsu',
  npc_trigger: 'ameiko',
  skill: 'Diplomacy',
  skill_trigger: 'convince',
  location: null,
  location_npcs: [],
  scene_npcs: [],
}

describe('IntentBar - AC-001 context tags and truncation', () => {
  it('truncates the displayed input to 52 characters without losing the title', () => {
    const longInput = 'I try to convince Ameiko to tell us about her brother Tsuto immediately'
    const { container } = render(
      <IntentBar intent={baseIntent} lastInput={longInput} streaming={false} />,
    )

    const input = container.querySelector('.intent-input')!
    expect(input).toHaveAttribute('title', longInput)
    expect(input.textContent).toContain(longInput.slice(0, 52))
    expect(input.textContent).not.toContain('immediately')
  })

  it('shows NPC and skill tags with their triggers', () => {
    render(<IntentBar intent={baseIntent} lastInput="convince Ameiko" streaming={false} />)

    expect(screen.getByText('npc')).toBeInTheDocument()
    expect(screen.getByText('Ameiko Kaijitsu')).toBeInTheDocument()
    expect(screen.getByText('"ameiko"')).toBeInTheDocument()
    expect(screen.getByText('skill')).toBeInTheDocument()
    expect(screen.getByText('Diplomacy')).toBeInTheDocument()
    expect(screen.getByText('"convince"')).toBeInTheDocument()
  })
})

describe('IntentBar - AC-002 location tag', () => {
  it('shows detected location with stationed NPCs', () => {
    render(
      <IntentBar
        intent={{
          ...baseIntent,
          npc: null,
          npc_trigger: null,
          skill: null,
          skill_trigger: null,
          location: 'garrison',
          location_npcs: ['Belor Hemlock'],
        }}
        lastInput="We go to the garrison"
        streaming={false}
      />,
    )

    expect(screen.getByText('loc')).toBeInTheDocument()
    expect(screen.getByText('garrison')).toBeInTheDocument()
    expect(screen.getByText('Belor Hemlock')).toBeInTheDocument()
  })
})

describe('IntentBar - AC-003 null fields', () => {
  it('shows no npc and no skill tags when context fields are null', () => {
    render(
      <IntentBar
        intent={{
          npc: null,
          npc_trigger: null,
          skill: null,
          skill_trigger: null,
          location: null,
          location_npcs: [],
          scene_npcs: [],
        }}
        lastInput="We wait"
        streaming={false}
      />,
    )

    expect(screen.getByText('no npc')).toBeInTheDocument()
    expect(screen.getByText('no skill')).toBeInTheDocument()
    expect(screen.queryByText('loc')).not.toBeInTheDocument()
  })
})

describe('IntentBar - AC-004 detecting state', () => {
  it('shows detecting while streaming and no context has arrived', () => {
    render(<IntentBar intent={null} lastInput="look around" streaming={true} />)

    expect(screen.getByText(/detecting/)).toBeInTheDocument()
    expect(screen.queryByText('no npc')).not.toBeInTheDocument()
    expect(screen.queryByText('no skill')).not.toBeInTheDocument()
  })
})

describe('IntentBar - AC-005 no-event diagnostic', () => {
  it('shows restart diagnostic when streaming ends without a context event', () => {
    render(<IntentBar intent={null} lastInput="look around" streaming={false} />)

    expect(screen.getByText(/restart backend/i)).toBeInTheDocument()
  })
})
