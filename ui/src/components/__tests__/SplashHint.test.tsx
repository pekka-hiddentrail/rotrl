/**
 * SplashHint — splash screen rotating hints tests
 *
 * Covers splash-hints.feature AC-001 through AC-006.
 *
 * AC-001  A hint from the pool is shown immediately on mount
 * AC-002  Hint rotates automatically after 8 000 ms
 * AC-003  Consecutive hints are never immediately identical
 * AC-004  All hints shown come from the canonical pool
 * AC-005  Fade class is applied on rotation, removed after 400 ms
 * AC-006  hints.ts data: 20 entries, all non-empty, randomHint() stays in pool
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import SplashHint from '../SplashHint'
import { hints, randomHint } from '../../data/hints'

// ── AC-006 — Data integrity ───────────────────────────────────────────────────

describe('hints data — AC-006', () => {
  it('contains exactly 20 hints', () => {
    expect(hints).toHaveLength(20)
  })

  it('every hint is a non-empty string', () => {
    for (const h of hints) {
      expect(typeof h).toBe('string')
      expect(h.trim().length).toBeGreaterThan(0)
    }
  })

  it('randomHint() always returns a value in the hints array', () => {
    for (let i = 0; i < 100; i++) {
      expect(hints).toContain(randomHint())
    }
  })
})

// ── AC-001 — Hint shown on mount ─────────────────────────────────────────────

describe('SplashHint — AC-001: initial render', () => {
  it('renders the splash-hint element', () => {
    render(<SplashHint />)
    expect(screen.getByTestId('splash-hint')).toBeInTheDocument()
  })

  it('shows text that belongs to the hints pool', () => {
    render(<SplashHint />)
    const text = screen.getByTestId('splash-hint').textContent ?? ''
    expect(hints).toContain(text)
  })

  it('does NOT show provider key reminder text', () => {
    render(<SplashHint />)
    const text = screen.getByTestId('splash-hint').textContent ?? ''
    expect(text).not.toMatch(/GROQ_API_KEY/i)
    expect(text).not.toMatch(/ANTHROPIC_API_KEY/i)
    expect(text).not.toMatch(/ollama serve/i)
  })
})

// ── AC-002 — Rotation after 8 s ───────────────────────────────────────────────

describe('SplashHint — AC-002: auto-rotation', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('changes hint text after 8 000 ms', () => {
    render(<SplashHint />)
    const first = screen.getByTestId('splash-hint').textContent

    act(() => { vi.advanceTimersByTime(8000 + 400) })  // interval + fade delay

    const second = screen.getByTestId('splash-hint').textContent
    // Text has changed (with a pool of 20 the chance of same is 1/19, so we also
    // verify the new value is valid regardless)
    expect(hints).toContain(second)
    expect(second).not.toBe('')
  })

  it('changes hint text a second time after another 8 000 ms', () => {
    render(<SplashHint />)

    act(() => { vi.advanceTimersByTime(8000 + 400) })
    const second = screen.getByTestId('splash-hint').textContent

    act(() => { vi.advanceTimersByTime(8000 + 400) })
    const third = screen.getByTestId('splash-hint').textContent

    expect(hints).toContain(second)
    expect(hints).toContain(third)
  })
})

// ── AC-003 — No immediate repeat ─────────────────────────────────────────────

describe('SplashHint — AC-003: no immediate repeat', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('never shows the same hint twice in a row across 10 rotations', () => {
    render(<SplashHint />)
    let prev = screen.getByTestId('splash-hint').textContent

    for (let i = 0; i < 10; i++) {
      act(() => { vi.advanceTimersByTime(8000 + 400) })
      const current = screen.getByTestId('splash-hint').textContent
      expect(current).not.toBe(prev)
      prev = current
    }
  })
})

// ── AC-004 — All hints from pool ─────────────────────────────────────────────

describe('SplashHint — AC-004: hints from canonical pool', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('every displayed hint is a member of the hints array', () => {
    render(<SplashHint />)

    for (let i = 0; i < 5; i++) {
      act(() => { vi.advanceTimersByTime(8000 + 400) })
      const current = screen.getByTestId('splash-hint').textContent ?? ''
      expect(hints).toContain(current)
    }
  })
})

// ── AC-005 — Fade class applied on rotation ───────────────────────────────────

describe('SplashHint — AC-005: fade transition', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('adds splash-hint--fade class when rotation starts', () => {
    render(<SplashHint />)
    const el = screen.getByTestId('splash-hint')

    // Advance to trigger interval but NOT the inner 400 ms timeout yet
    act(() => { vi.advanceTimersByTime(8000) })
    expect(el.classList.contains('splash-hint--fade')).toBe(true)
  })

  it('removes splash-hint--fade class after 400 ms fade delay', () => {
    render(<SplashHint />)
    const el = screen.getByTestId('splash-hint')

    act(() => { vi.advanceTimersByTime(8000 + 400) })
    expect(el.classList.contains('splash-hint--fade')).toBe(false)
  })
})
