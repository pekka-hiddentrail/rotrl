/**
 * InputBar — hostile / enemy-turn state tests.
 *
 * Spec: specs/combat-active-character.feature AC-010 through AC-013
 * Covers: skull icon, hostile class, taunting placeholder, determinism,
 * enemy name label, and revert-to-normal when combat ends.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import InputBar from '../InputBar'

const noop = vi.fn()

// ── helpers ───────────────────────────────────────────────────────────────────

const PC_SPEAKER = { name: 'Yanyeeku', rune: 'ᚠ', color: '#a060d0', isEnemy: false }
const ENEMY_SPEAKER = { name: 'Goblin 1', rune: '', color: '#cc2222', isEnemy: true }
const ENEMY_SPEAKER_2 = { name: 'Goblin Warchanter', rune: '', color: '#cc2222', isEnemy: true }

// ── AC-010 — ActiveSpeaker isEnemy flag ──────────────────────────────────────

describe('InputBar — PC speaker (isEnemy false)', () => {
  it('no hostile class on container when PC is speaking', () => {
    const { container } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} />)
    expect(container.querySelector('.hostile')).toBeNull()
  })

  it('shows character rune, not skull', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} />)
    expect(screen.getByText('ᚠ')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /skull/i })).toBeNull()
  })

  it('shows normal placeholder', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} />)
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'placeholder',
      expect.stringContaining('What do you do?'),
    )
  })
})

// ── AC-011 — hostile styling for enemy turns ──────────────────────────────────

describe('InputBar — enemy speaker (isEnemy true)', () => {
  it('applies hostile class to container', () => {
    const { container } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    expect(container.querySelector('.hostile')).not.toBeNull()
  })

  it('shows skull icon (not character rune)', () => {
    const { container } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    // Skull should be present as an SVG or element with role/aria-label
    const skull = container.querySelector('.speaker-skull') ?? container.querySelector('[aria-label="enemy"]')
    expect(skull).not.toBeNull()
  })

  it('shows the enemy name as label', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    expect(screen.getByText('Goblin 1')).toBeInTheDocument()
  })

  it('does NOT show the PC rune string', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    // rune is empty for enemies; the rune span should not show visible text
    expect(screen.queryByText('ᚠ')).not.toBeInTheDocument()
  })

  it('placeholder is a taunting phrase (not the default)', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    const textarea = screen.getByRole('textbox')
    const placeholder = textarea.getAttribute('placeholder') ?? ''
    expect(placeholder).not.toContain('What do you do?')
    expect(placeholder.length).toBeGreaterThan(5)
  })

  it('still renders a send button', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })
})

// ── AC-012 — deterministic placeholder by enemy name ─────────────────────────

describe('InputBar — taunting placeholder determinism', () => {
  it('same enemy name always gets the same placeholder', () => {
    const { unmount } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    const placeholder1 = screen.getByRole('textbox').getAttribute('placeholder')
    unmount()
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    const placeholder2 = screen.getByRole('textbox').getAttribute('placeholder')
    expect(placeholder1).toBe(placeholder2)
  })

  it('different enemy names may get different placeholders (pool covers multiple)', () => {
    const { unmount } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />)
    const p1 = screen.getByRole('textbox').getAttribute('placeholder')
    unmount()
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER_2} />)
    const p2 = screen.getByRole('textbox').getAttribute('placeholder')
    // They may or may not differ depending on pool size — just assert both are non-empty
    expect(p1).toBeTruthy()
    expect(p2).toBeTruthy()
  })
})

// ── AC-013 — revert to normal when combat ends ────────────────────────────────

describe('InputBar — revert to normal after combat', () => {
  it('removes hostile class when activeSpeaker becomes null', () => {
    const { container, rerender } = render(
      <InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />,
    )
    expect(container.querySelector('.hostile')).not.toBeNull()
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={null} />)
    expect(container.querySelector('.hostile')).toBeNull()
  })

  it('restores normal placeholder when activeSpeaker becomes null', () => {
    const { rerender } = render(
      <InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />,
    )
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={null} />)
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'placeholder',
      expect.stringContaining('What do you do?'),
    )
  })

  it('switches from enemy to PC speaker cleanly', () => {
    const { container, rerender } = render(
      <InputBar onSend={noop} disabled={false} activeSpeaker={ENEMY_SPEAKER} />,
    )
    expect(container.querySelector('.hostile')).not.toBeNull()
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={PC_SPEAKER} />)
    expect(container.querySelector('.hostile')).toBeNull()
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
  })
})
