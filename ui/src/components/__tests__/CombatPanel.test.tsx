/**
 * CombatPanel and HpBar — combat tracker UI tests.
 *
 * Spec: specs/combat-tracker.feature
 * Covers: AC-007, AC-008, AC-009, AC-012, AC-014, AC-015
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CombatPanel from '../CombatPanel'
import HpBar from '../HpBar'
import type { CombatState } from '../../types'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const THREE_COMBATANTS: CombatState = {
  round: 2,
  combatants: [
    { name: 'Thaelion', hp_current: 12, hp_max: 22, ac: 16, initiative: 8,  status: 'active',      conditions: [] },
    { name: 'Shalelu',  hp_current: 18, hp_max: 24, ac: 17, initiative: 14, status: 'active',      conditions: [] },
    { name: 'Goblin 1', hp_current: 0,  hp_max: 5,  ac: 13, initiative: 6,  status: 'unconscious', conditions: [] },
  ],
}

// ─── AC-007 — initiative order ────────────────────────────────────────────────

describe('CombatPanel — AC-007 initiative order', () => {
  it('V0 — header keeps the combat icon label', () => {
    render(<CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} />)
    expect(screen.getByText('⚔ Combat')).toBeInTheDocument()
  })

  it('V1 — combatants are listed highest-initiative-first in the DOM', () => {
    render(<CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} />)
    const names = screen.getAllByText(/Shalelu|Thaelion|Goblin 1/).map(el => el.textContent)
    const shalelIdx  = names.findIndex(n => n === 'Shalelu')
    const thaelIdx   = names.findIndex(n => n === 'Thaelion')
    const goblinIdx  = names.findIndex(n => n === 'Goblin 1')
    // initiative: Shalelu 14 > Thaelion 8 > Goblin 1 6
    expect(shalelIdx).toBeLessThan(thaelIdx)
    expect(thaelIdx).toBeLessThan(goblinIdx)
  })

  it('V2 — the top active combatant gets the combatant-current class', () => {
    const { container } = render(
      <CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} />,
    )
    const rows = container.querySelectorAll('.combatant-row')
    // After sorting, Shalelu (init 14) is first and active
    expect(rows[0]).toHaveClass('combatant-current')
    expect(rows[0]).toHaveTextContent('Shalelu')
  })

  it('V3 — an inactive combatant gets combatant-inactive but not combatant-current', () => {
    const { container } = render(
      <CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} />,
    )
    const rows = Array.from(container.querySelectorAll('.combatant-row'))
    const goblinRow = rows.find(r => r.textContent?.includes('Goblin 1'))
    expect(goblinRow).toHaveClass('combatant-inactive')
    expect(goblinRow).not.toHaveClass('combatant-current')
  })

  it('V3.1 — combatant rows show initiative and AC icons', () => {
    render(<CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} />)
    expect(screen.getByText('⚡ Init 14')).toBeInTheDocument()
    expect(screen.getByText('🛡 AC 17')).toBeInTheDocument()
  })
})

// ─── AC-009 — HpBar colours ───────────────────────────────────────────────────

describe('HpBar — AC-009 colour thresholds', () => {
  function getFillColor(current: number, max: number): string {
    const { container } = render(<HpBar current={current} max={max} />)
    const fill = container.querySelector('.hp-bar-fill') as HTMLElement
    return fill.style.background
  }

  it('V4 — pct > 66 → green (#3a9a6a)', () => {
    expect(getFillColor(18, 24)).toBe('rgb(58, 154, 106)') // 75 %
  })

  it('V5 — pct 33–66 → amber (#c9a84c)', () => {
    expect(getFillColor(10, 20)).toBe('rgb(201, 168, 76)') // 50 %
  })

  it('V6 — pct < 33 and > 0 → red (#b04040)', () => {
    expect(getFillColor(3, 24)).toBe('rgb(176, 64, 64)')   // 12 %
  })

  it('V7 — pct = 0 → dark grey (#444)', () => {
    expect(getFillColor(0, 5)).toBe('rgb(68, 68, 68)')
  })
})

// ─── AC-008 — End Combat button ───────────────────────────────────────────────

describe('CombatPanel — AC-008 End Combat button', () => {
  it('V8 — clicking End Combat fires the onEndCombat callback', () => {
    const onEndCombat = vi.fn()
    render(<CombatPanel combatState={THREE_COMBATANTS} onEndCombat={onEndCombat} />)
    fireEvent.click(screen.getByRole('button', { name: 'End Combat' }))
    expect(onEndCombat).toHaveBeenCalledOnce()
  })

  it('V9 — disabled prop disables the button', () => {
    render(
      <CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} disabled />,
    )
    expect(screen.getByRole('button', { name: 'End Combat' })).toBeDisabled()
  })
})

// ─── AC-012 — conditions chips ────────────────────────────────────────────────

describe('CombatPanel — AC-012 conditions chips', () => {
  const stateWithConditions: CombatState = {
    round: 1,
    combatants: [
      {
        name: 'Shalelu',
        hp_current: 18, hp_max: 24,
        ac: 17, initiative: 14,
        status: 'active',
        conditions: ['prone', 'shaken'],
      },
    ],
  }

  const stateNoConditions: CombatState = {
    round: 1,
    combatants: [
      { name: 'Shalelu', hp_current: 18, hp_max: 24, ac: 17, initiative: 14, status: 'active', conditions: [] },
    ],
  }

  it('V10 — each condition renders as a chip with the correct label', () => {
    render(<CombatPanel combatState={stateWithConditions} onEndCombat={vi.fn()} />)
    expect(screen.getByText('prone')).toBeInTheDocument()
    expect(screen.getByText('shaken')).toBeInTheDocument()
    expect(document.querySelectorAll('.condition-chip')).toHaveLength(2)
  })

  it('V11 — each chip title contains the PF1e mechanical description', () => {
    render(<CombatPanel combatState={stateWithConditions} onEndCombat={vi.fn()} />)
    const proneChip  = screen.getByText('prone')
    const shakenChip = screen.getByText('shaken')
    expect(proneChip.title).toMatch(/melee attack/)
    expect(shakenChip.title).toMatch(/-2 attack rolls/)
  })

  it('V12 — a combatant with no conditions renders zero chips', () => {
    render(<CombatPanel combatState={stateNoConditions} onEndCombat={vi.fn()} />)
    expect(document.querySelectorAll('.condition-chip')).toHaveLength(0)
  })
})

// ─── AC-014 — active-turn highlight advances ──────────────────────────────────

describe('CombatPanel — AC-014 active-turn highlight advances', () => {
  it('V13 — currentCombatantName prop selects which row gets combatant-current', () => {
    // THREE_COMBATANTS: Shalelu (init 14 active), Thaelion (init 8 active), Goblin 1 (init 6 unconscious)
    const { container } = render(
      <CombatPanel
        combatState={THREE_COMBATANTS}
        onEndCombat={vi.fn()}
        currentCombatantName="Thaelion"
      />,
    )
    const rows = Array.from(container.querySelectorAll('.combatant-row'))
    const thaelionRow = rows.find(r => r.textContent?.includes('Thaelion'))
    const shalelRow   = rows.find(r => r.textContent?.includes('Shalelu'))
    expect(thaelionRow).toHaveClass('combatant-current')
    expect(shalelRow).not.toHaveClass('combatant-current')
  })

  it('V14 — "Next Turn →" button is rendered', () => {
    render(<CombatPanel combatState={THREE_COMBATANTS} onEndCombat={vi.fn()} onAdvanceTurn={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Next Turn →' })).toBeInTheDocument()
  })

  it('V15 — clicking "Next Turn →" fires the onAdvanceTurn callback', () => {
    const onAdvanceTurn = vi.fn()
    render(
      <CombatPanel
        combatState={THREE_COMBATANTS}
        onEndCombat={vi.fn()}
        onAdvanceTurn={onAdvanceTurn}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Next Turn →' }))
    expect(onAdvanceTurn).toHaveBeenCalledOnce()
  })

  it('V16 — when currentCombatantName is null, fallback highlights the first active combatant', () => {
    const { container } = render(
      <CombatPanel
        combatState={THREE_COMBATANTS}
        onEndCombat={vi.fn()}
        currentCombatantName={null}
      />,
    )
    const rows = Array.from(container.querySelectorAll('.combatant-row'))
    const shalelRow = rows.find(r => r.textContent?.includes('Shalelu'))
    // Shalelu has highest initiative among active combatants → gets the fallback highlight
    expect(shalelRow).toHaveClass('combatant-current')
  })
})

// ─── AC-015 — dead combatant styling ─────────────────────────────────────────

describe('CombatPanel — AC-015 dead combatant name styling', () => {
  const stateWithDead: CombatState = {
    round: 3,
    combatants: [
      { name: 'Shalelu',  hp_current: 18, hp_max: 24, ac: 17, initiative: 14, status: 'active', conditions: [] },
      { name: 'Goblin 1', hp_current: 0,  hp_max: 5,  ac: 13, initiative: 6,  status: 'dead',   conditions: [] },
    ],
  }

  it('V17 — a dead combatant row has the combatant-dead class', () => {
    const { container } = render(<CombatPanel combatState={stateWithDead} onEndCombat={vi.fn()} />)
    const rows = Array.from(container.querySelectorAll('.combatant-row'))
    const goblinRow = rows.find(r => r.textContent?.includes('Goblin 1'))
    expect(goblinRow).toHaveClass('combatant-dead')
  })

  it('V18 — a dead combatant row also has combatant-inactive', () => {
    const { container } = render(<CombatPanel combatState={stateWithDead} onEndCombat={vi.fn()} />)
    const rows = Array.from(container.querySelectorAll('.combatant-row'))
    const goblinRow = rows.find(r => r.textContent?.includes('Goblin 1'))
    expect(goblinRow).toHaveClass('combatant-inactive')
  })

  it('V19 — a dead combatant row does NOT get combatant-current', () => {
    const { container } = render(<CombatPanel combatState={stateWithDead} onEndCombat={vi.fn()} />)
    const rows = Array.from(container.querySelectorAll('.combatant-row'))
    const goblinRow = rows.find(r => r.textContent?.includes('Goblin 1'))
    expect(goblinRow).not.toHaveClass('combatant-current')
  })
})


// ─── ZC-005/006 — Zone badge display ─────────────────────────────────────────

describe('CombatPanel — zone badge (ZC-005/006)', () => {
  it('ZC-005 — renders zone badge when zone is set and not "default"', () => {
    const state: CombatState = {
      round: 1,
      combatants: [
        { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 8, status: 'active', zone: 'Cathedral Stairs' },
      ],
    }
    const { container } = render(<CombatPanel combatState={state} onEndCombat={vi.fn()} />)
    const badge = container.querySelector('.zone-badge')
    expect(badge).not.toBeNull()
    expect(badge?.textContent).toContain('Cathedral Stairs')
  })

  it('ZC-006 — omits zone badge when zone is "default"', () => {
    const state: CombatState = {
      round: 1,
      combatants: [
        { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 8, status: 'active', zone: 'default' },
      ],
    }
    const { container } = render(<CombatPanel combatState={state} onEndCombat={vi.fn()} />)
    expect(container.querySelector('.zone-badge')).toBeNull()
  })

  it('ZC-006b — omits zone badge when zone is absent', () => {
    const state: CombatState = {
      round: 1,
      combatants: [
        { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 8, status: 'active' },
      ],
    }
    const { container } = render(<CombatPanel combatState={state} onEndCombat={vi.fn()} />)
    expect(container.querySelector('.zone-badge')).toBeNull()
  })

  it('ZC-005b — badge is below the HP bar row', () => {
    const state: CombatState = {
      round: 1,
      combatants: [
        { name: 'Goblin Warrior 1', hp_current: 5, hp_max: 5, ac: 16, initiative: 8, status: 'active', zone: 'Well' },
      ],
    }
    const { container } = render(<CombatPanel combatState={state} onEndCombat={vi.fn()} />)
    const row = container.querySelector('.combatant-row')!
    const hpRow = row.querySelector('.combatant-hp-row')!
    const zoneRow = row.querySelector('.combatant-zone-row')!
    // Zone row must come after HP row in DOM order
    expect(hpRow.compareDocumentPosition(zoneRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})
