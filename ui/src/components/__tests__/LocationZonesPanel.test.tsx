/**
 * LocationZonesPanel — zone display and movement UI tests.
 * Spec: specs/location-zones.feature — LZ-007, LZ-008, LZ-009, LZ-010
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LocationZonesPanel from '../LocationZonesPanel'
import type { LocationZonesData } from '../../api'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const BASE_DATA: LocationZonesData = {
  current_location: { id: 'festival_square', name: 'Festival Square' },
  current_zone_id: 'center',
  zones: [
    { id: 'center',           name: 'Center',           description: 'Open clearing.', visible: true,  source: 'authored', tags: ['open'] },
    { id: 'alleyway',         name: 'Alleyway',         description: 'Side lane.',     visible: true,  source: 'authored', tags: ['shadowed'] },
    { id: 'cathedral_stairs', name: 'Cathedral Stairs', description: 'High ground.',  visible: true,  source: 'authored', tags: [] },
    { id: 'hidden_passage',   name: 'Hidden Passage',   description: 'Secret exit.',  visible: false, source: 'authored', tags: [] },
  ],
  access_points: [
    { id: 'center_alleyway', from: 'center', to: 'alleyway', label: 'Alley mouth', state: 'open',   bidirectional: true,  requirements: '-',              description: '' },
    { id: 'center_stairs',   from: 'center', to: 'cathedral_stairs', label: 'Stone steps', state: 'locked', bidirectional: true,  requirements: 'Key required', description: '' },
    { id: 'center_hidden',   from: 'center', to: 'hidden_passage',   label: 'Hidden door', state: 'hidden', bidirectional: false, requirements: '-',              description: '' },
  ],
  occupants: [
    { actor_id: 'party', label: 'Party', zone_id: 'center' },
    { actor_id: 'goblin_warrior_1', label: 'Goblin Warrior 1', zone_id: 'alleyway' },
  ],
  available_moves: [
    { access_point_id: 'center_alleyway', to_zone_id: 'alleyway', label: 'Alley mouth', state: 'open' },
  ],
}

function renderPanel(overrides: Partial<LocationZonesData> = {}, props = {}) {
  const data = { ...BASE_DATA, ...overrides }
  const onMove     = vi.fn()
  const onCollapse = vi.fn()
  render(
    <LocationZonesPanel
      zonesData={data}
      actorId="party"
      onMove={onMove}
      movePending={false}
      collapsed={false}
      onCollapse={onCollapse}
      {...props}
    />,
  )
  return { onMove, onCollapse }
}

// ── LZ-007 — current zone and movement controls ───────────────────────────────

describe('LocationZonesPanel — LZ-007 current zone display', () => {
  it('shows the location name in the header', () => {
    renderPanel()
    expect(screen.getByText('Festival Square')).toBeInTheDocument()
  })

  it('shows the current zone name prominently', () => {
    renderPanel()
    expect(screen.getAllByText('Center').length).toBeGreaterThan(0)
  })

  it('shows the current zone description', () => {
    renderPanel()
    expect(screen.getAllByText('Open clearing.').length).toBeGreaterThan(0)
  })

  it('renders an enabled move button for each open available move', () => {
    const { onMove } = renderPanel()
    const btn = screen.getByRole('button', { name: /Alleyway/i })
    expect(btn).not.toBeDisabled()
    fireEvent.click(btn)
    expect(onMove).toHaveBeenCalledWith('center_alleyway')
  })

  it('disables move buttons while movePending is true', () => {
    renderPanel({}, { movePending: true })
    const btn = screen.getByRole('button', { name: /Alleyway/i })
    expect(btn).toBeDisabled()
  })
})

// ── LZ-008 — zone list: reachable vs inspectable ─────────────────────────────

describe('LocationZonesPanel — LZ-008 zone list', () => {
  it('lists all visible zones', () => {
    renderPanel()
    expect(screen.getAllByText('Center').length).toBeGreaterThan(0)
    expect(screen.getByText('Alleyway')).toBeInTheDocument()
    expect(screen.getByText('Cathedral Stairs')).toBeInTheDocument()
  })

  it('does not render hidden zones', () => {
    renderPanel()
    expect(screen.queryByText('Hidden Passage')).not.toBeInTheDocument()
  })

  it('marks the current zone row with lz-zone-current class', () => {
    const { container } = render(
      <LocationZonesPanel
        zonesData={BASE_DATA}
        actorId="party"

        onMove={vi.fn()}
        movePending={false}
        collapsed={false}
        onCollapse={vi.fn()}
      />,
    )
    const rows = container.querySelectorAll('.lz-zone-row')
    const currentRow = Array.from(rows).find(r => r.textContent?.includes('Center') && r.classList.contains('lz-zone-current'))
    expect(currentRow).toBeTruthy()
  })

  it('marks reachable zones with lz-zone-reachable class', () => {
    const { container } = render(
      <LocationZonesPanel
        zonesData={BASE_DATA}
        actorId="party"

        onMove={vi.fn()}
        movePending={false}
        collapsed={false}
        onCollapse={vi.fn()}
      />,
    )
    const rows = container.querySelectorAll('.lz-zone-reachable')
    const names = Array.from(rows).map(r => r.textContent)
    expect(names.some(n => n?.includes('Alleyway'))).toBe(true)
  })

  it('non-reachable visible zones have neither current nor reachable class', () => {
    const { container } = render(
      <LocationZonesPanel
        zonesData={BASE_DATA}
        actorId="party"

        onMove={vi.fn()}
        movePending={false}
        collapsed={false}
        onCollapse={vi.fn()}
      />,
    )
    const rows = Array.from(container.querySelectorAll('.lz-zone-row'))
    const stairsRow = rows.find(r => r.textContent?.includes('Cathedral Stairs'))
    expect(stairsRow).toBeTruthy()
    expect(stairsRow!.classList.contains('lz-zone-current')).toBe(false)
    expect(stairsRow!.classList.contains('lz-zone-reachable')).toBe(false)
  })
})

// ── LZ-009 — access point states ─────────────────────────────────────────────

describe('LocationZonesPanel — LZ-009 access point states', () => {
  it('renders a disabled button for a locked access point', () => {
    const { container } = render(
      <LocationZonesPanel zonesData={BASE_DATA} actorId="party"
        onMove={vi.fn()} movePending={false} collapsed={false} onCollapse={vi.fn()} />,
    )
    const btn = container.querySelector('.lz-move-btn--restricted') as HTMLButtonElement
    expect(btn).toBeTruthy()
    expect(btn.disabled).toBe(true)
    expect(btn.textContent).toContain('Cathedral Stairs')
  })

  it('locked button title includes the requirement', () => {
    const { container } = render(
      <LocationZonesPanel zonesData={BASE_DATA} actorId="party"
        onMove={vi.fn()} movePending={false} collapsed={false} onCollapse={vi.fn()} />,
    )
    const btn = container.querySelector('.lz-move-btn--restricted') as HTMLButtonElement
    expect(btn.getAttribute('title')).toContain('Key required')
  })

  it('hidden access point is not rendered at all', () => {
    renderPanel()
    expect(screen.queryByText(/Hidden door/i)).not.toBeInTheDocument()
  })
})

// ── LZ-010 — character occupancy ─────────────────────────────────────────────

describe('LocationZonesPanel — LZ-010 occupancy', () => {
  it('shows Party in the Center zone row', () => {
    renderPanel()
    // "Party" occupant chip should appear inside the Center zone area
    const chips = screen.getAllByText('Party')
    expect(chips.length).toBeGreaterThan(0)
  })

  it('shows enemy occupant in their zone', () => {
    renderPanel()
    expect(screen.getByText('Goblin Warrior 1')).toBeInTheDocument()
  })

  it('occupant chips are not interactive (no pointer cursor or click handler)', () => {
    renderPanel()
    const chip = screen.getByText('Goblin Warrior 1')
    expect(chip.style.cursor).not.toBe('pointer')
    expect(chip.getAttribute('onClick')).toBeNull()
  })

  it('active actor chip has lz-occupant-active class', () => {
    const { container } = render(
      <LocationZonesPanel
        zonesData={BASE_DATA}
        actorId="party"

        onMove={vi.fn()}
        movePending={false}
        collapsed={false}
        onCollapse={vi.fn()}
      />,
    )
    const activeChips = container.querySelectorAll('.lz-occupant-active')
    const labels = Array.from(activeChips).map(c => c.textContent)
    expect(labels).toContain('Party')
  })
})

// ── Collapse behaviour ────────────────────────────────────────────────────────

describe('LocationZonesPanel — collapsed state', () => {
  it('hides zone list and moves when collapsed', () => {
    render(
      <LocationZonesPanel
        zonesData={BASE_DATA}
        actorId="party"

        onMove={vi.fn()}
        movePending={false}
        collapsed={true}
        onCollapse={vi.fn()}
      />,
    )
    expect(screen.queryByText('Open clearing.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Alleyway/i })).not.toBeInTheDocument()
  })

  it('collapse button toggles the panel', () => {
    const onCollapse = vi.fn()
    render(
      <LocationZonesPanel
        zonesData={BASE_DATA}
        actorId="party"

        onMove={vi.fn()}
        movePending={false}
        collapsed={false}
        onCollapse={onCollapse}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /Collapse/i }))
    expect(onCollapse).toHaveBeenCalledWith(true)
  })
})
