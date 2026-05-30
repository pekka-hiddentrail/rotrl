/**
 * MessageBubble — player speaker identity tests
 *
 * Covers player-bubble-speaker.feature AC-001 through AC-006.
 *
 * AC-001  No active speaker → "Player" circle label, clean content
 * AC-002  Active speaker → portrait + name label, clean content
 * AC-003  Speaker snapshot is baked into the message (tested via prop immutability)
 * AC-004  GM bubble is unchanged (plain "GM" text label, no portrait)
 * AC-005  Portrait image error → rune fallback still shows name
 * AC-006  GM bubble is unaffected
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MessageBubble from '../MessageBubble'
import type { Message } from '../../types'

// ── Helpers ──────────────────────────────────────────────────────────────────

const gmMsg: Message = { role: 'gm', content: 'The tavern is quiet.' }

const playerNoSpeaker: Message = {
  role: 'player',
  content: 'I look around the room.',
}

const playerWithSpeaker: Message = {
  role: 'player',
  content: 'I cast fireball.',
  speaker: {
    name: 'Yanyeeku',
    portrait: '/portraits/yanyeeku.png',
    color: '#a060d0',
    rune: 'ᚠ',
  },
}

const playerSeoni: Message = {
  role: 'player',
  content: 'I sneak forward.',
  speaker: {
    name: 'Seoni',
    portrait: '/portraits/seoni.png',
    color: '#d04060',
    rune: 'ᛊ',
  },
}

// ── AC-001 — No active speaker → "Player" circle label ───────────────────────

describe('MessageBubble — AC-001: no active speaker', () => {
  it('shows a "player" label element when speaker is absent', () => {
    render(<MessageBubble message={playerNoSpeaker} isLast={false} streaming={false} />)
    // The party/player label should contain the text "player"
    expect(screen.getByText(/^player$/i)).toBeInTheDocument()
  })

  it('does NOT show the text "You" as the label', () => {
    render(<MessageBubble message={playerNoSpeaker} isLast={false} streaming={false} />)
    expect(screen.queryByText(/^you$/i)).not.toBeInTheDocument()
  })

  it('renders the clean message content without any prefix', () => {
    render(<MessageBubble message={playerNoSpeaker} isLast={false} streaming={false} />)
    expect(screen.getByText('I look around the room.')).toBeInTheDocument()
  })

  it('does not render any character name', () => {
    render(<MessageBubble message={playerNoSpeaker} isLast={false} streaming={false} />)
    expect(screen.queryByText('Yanyeeku')).not.toBeInTheDocument()
    expect(screen.queryByText('Seoni')).not.toBeInTheDocument()
  })
})

// ── AC-002 — Active speaker → portrait + name ─────────────────────────────────

describe('MessageBubble — AC-002: active speaker', () => {
  it('shows the character name', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
  })

  it('renders the portrait img with the character portrait src', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    const img = screen.getByRole('img', { name: 'Yanyeeku' })
    expect(img).toHaveAttribute('src', '/portraits/yanyeeku.png')
  })

  it('renders clean message content — no "@Name:" prefix visible', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    expect(screen.getByText('I cast fireball.')).toBeInTheDocument()
    expect(screen.queryByText(/@Yanyeeku/)).not.toBeInTheDocument()
  })

  it('does NOT show the "player" circle label when a speaker is present', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    expect(screen.queryByText(/^player$/i)).not.toBeInTheDocument()
  })

  it('applies the character color as the portrait border color via inline style', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    // The portrait wrapper should carry the character's color via a CSS custom property or inline style
    const portrait = screen.getByTestId('bubble-speaker-portrait')
    const style = portrait.getAttribute('style') ?? ''
    expect(style).toMatch(/#a060d0|--speaker-color/)
  })

  it('shows different characters for different messages', () => {
    const { rerender } = render(
      <MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />,
    )
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
    rerender(<MessageBubble message={playerSeoni} isLast={false} streaming={false} />)
    expect(screen.getByText('Seoni')).toBeInTheDocument()
    expect(screen.queryByText('Yanyeeku')).not.toBeInTheDocument()
  })
})

// ── AC-003 — Snapshot immutability (structural) ───────────────────────────────

describe('MessageBubble — AC-003: speaker snapshot', () => {
  it('renders the name baked into the message regardless of any external state', () => {
    // The message object carries the snapshot; there is no external context.
    // This test confirms the component is purely data-driven.
    const msg: Message = {
      role: 'player',
      content: 'Forward!',
      speaker: { name: 'Vanx', portrait: '/p/vanx.png', color: '#60d0a0', rune: 'ᚢ' },
    }
    render(<MessageBubble message={msg} isLast={false} streaming={false} />)
    expect(screen.getByText('Vanx')).toBeInTheDocument()
  })
})

// ── AC-004 — Backend payload separation (App-level, tested in App.test.tsx) ──
// Placeholder — see App.test.tsx for the full sendTurn call assertion.

// ── AC-005 — Portrait image error → rune fallback ────────────────────────────

describe('MessageBubble — AC-005: portrait fallback', () => {
  it('shows the rune glyph when the portrait image errors', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    const img = screen.getByRole('img', { name: 'Yanyeeku' })
    fireEvent.error(img)
    expect(screen.getByText('ᚠ')).toBeInTheDocument()
  })

  it('still shows the character name after portrait error', () => {
    render(<MessageBubble message={playerWithSpeaker} isLast={false} streaming={false} />)
    fireEvent.error(screen.getByRole('img', { name: 'Yanyeeku' }))
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
  })
})

// ── AC-006 — GM bubble is unaffected ─────────────────────────────────────────

describe('MessageBubble — AC-006: GM bubble unchanged', () => {
  it('shows the plain "GM" text label on a GM message', () => {
    render(<MessageBubble message={gmMsg} isLast={false} streaming={false} />)
    expect(screen.getByText('GM')).toBeInTheDocument()
  })

  it('does not show a "player" circle or portrait on a GM message', () => {
    render(<MessageBubble message={gmMsg} isLast={false} streaming={false} />)
    expect(screen.queryByText(/^player$/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('renders GM message content unchanged', () => {
    render(<MessageBubble message={gmMsg} isLast={false} streaming={false} />)
    expect(screen.getByText('The tavern is quiet.')).toBeInTheDocument()
  })
})
