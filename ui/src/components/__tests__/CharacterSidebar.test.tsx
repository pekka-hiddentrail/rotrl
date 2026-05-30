import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CharacterSidebar from '../CharacterSidebar'
import type { CharacterData } from '../../data/characters'

// Minimal character fixture
const makeChar = (overrides: Partial<CharacterData> = {}): CharacterData => ({
  id: 'yanyeeku',
  portrait: '/data/yanyeeku.png',
  color: '#a060d0',
  rune: 'ᚠ',
  name: 'Yanyeeku',
  player: 'Player 1',
  race: 'Kitsune',
  class: 'Oracle',
  archetype: '',
  alignment: 'CG',
  deity: 'Desna',
  level: 1,
  appearance: '',
  hp: { current: 9, max: 9, hitDie: 'd8', baseDieRoll: 8, conBonus: 1 },
  ac: { total: 15, touch: 12, flatFooted: 13, components: [] },
  initiative: '+2',
  speed: '30 ft',
  bab: '+0',
  abilities: [],
  saves: [],
  skills: [],
  feats: [],
  weapons: [],
  spells: { concentration: '', list: [] },
  inventory: { worn: [], weapons: [], carried: [], wealth: { pp: 0, gp: 0, sp: 0, cp: 0 } },
  ...overrides,
})

const ANI = makeChar({ id: 'ani', name: 'Ani', color: '#60a0d0', rune: 'ᚢ' })
const YANYEEKU = makeChar()

const defaultProps = {
  characters: [YANYEEKU, ANI],
  loading: false,
  activeSpeakerId: null,
  onSetActive: vi.fn(),
  onOpenSheet: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('CharacterSidebar — action menu', () => {
  it('renders character names', () => {
    render(<CharacterSidebar {...defaultProps} />)
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
    expect(screen.getByText('Ani')).toBeInTheDocument()
  })

  it('shows no action menu initially', () => {
    render(<CharacterSidebar {...defaultProps} />)
    expect(screen.queryByText(/Set Active/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Open Sheet/i)).not.toBeInTheDocument()
  })

  it('opens action menu when avatar button is clicked', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    expect(screen.getByText(/Set Active/i)).toBeInTheDocument()
    expect(screen.getByText(/Open Sheet/i)).toBeInTheDocument()
  })

  it('closes menu when same avatar is clicked again (toggle)', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    expect(screen.getByText(/Set Active/i)).toBeInTheDocument()
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    expect(screen.queryByText(/Set Active/i)).not.toBeInTheDocument()
  })

  it('switches menu when a different avatar is clicked', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    expect(screen.getByText(/Set Active/i)).toBeInTheDocument()
    fireEvent.click(screen.getByTitle(/Ani/))
    // Menu should now show for Ani — still one menu visible
    expect(screen.getAllByText(/Set Active/i)).toHaveLength(1)
  })

  it('calls onSetActive with character id when Set Active is clicked', () => {
    const onSetActive = vi.fn()
    render(<CharacterSidebar {...defaultProps} onSetActive={onSetActive} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    fireEvent.click(screen.getByText(/Set Active/i))
    expect(onSetActive).toHaveBeenCalledOnce()
    expect(onSetActive).toHaveBeenCalledWith('yanyeeku')
  })

  it('calls onOpenSheet with character id when Open Sheet is clicked', () => {
    const onOpenSheet = vi.fn()
    render(<CharacterSidebar {...defaultProps} onOpenSheet={onOpenSheet} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    fireEvent.click(screen.getByText(/Open Sheet/i))
    expect(onOpenSheet).toHaveBeenCalledOnce()
    expect(onOpenSheet).toHaveBeenCalledWith('yanyeeku')
  })

  it('closes menu after Set Active is clicked', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    fireEvent.click(screen.getByText(/Set Active/i))
    expect(screen.queryByText(/Set Active/i)).not.toBeInTheDocument()
  })

  it('closes menu after Open Sheet is clicked', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    fireEvent.click(screen.getByText(/Open Sheet/i))
    expect(screen.queryByText(/Open Sheet/i)).not.toBeInTheDocument()
  })
})

describe('CharacterSidebar — action menu placement (AC-012)', () => {
  it('action menu has data-placement="right"', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    const menu = document.querySelector('.char-action-menu')
    expect(menu).toHaveAttribute('data-placement', 'right')
  })

  it('action menu is portaled to document.body (not clipped by sidebar overflow)', () => {
    render(<CharacterSidebar {...defaultProps} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    const menu = document.querySelector('.char-action-menu')!
    // Menu must be a direct child of document.body so sidebar overflow does not clip it
    expect(menu.parentElement).toBe(document.body)
  })
})

describe('CharacterSidebar — active speaker halo', () => {
  it('adds .active class to the active character button', () => {
    render(<CharacterSidebar {...defaultProps} activeSpeakerId="yanyeeku" />)
    const btn = screen.getByTitle(/Yanyeeku/)
    expect(btn).toHaveClass('active')
  })

  it('does not add .active class to inactive character buttons', () => {
    render(<CharacterSidebar {...defaultProps} activeSpeakerId="yanyeeku" />)
    const aniBtn = screen.getByTitle(/Ani/)
    expect(aniBtn).not.toHaveClass('active')
  })

  it('shows "Clear Active" label in menu when character is already active', () => {
    render(<CharacterSidebar {...defaultProps} activeSpeakerId="yanyeeku" />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    expect(screen.getByText(/Clear Active/i)).toBeInTheDocument()
    expect(screen.queryByText(/◈.*Set Active/)).not.toBeInTheDocument()
  })

  it('shows "Set Active" label in menu when character is not active', () => {
    render(<CharacterSidebar {...defaultProps} activeSpeakerId={null} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    expect(screen.getByText(/Set Active/i)).toBeInTheDocument()
  })

  it('calls onSetActive to toggle off when Clear Active is clicked', () => {
    const onSetActive = vi.fn()
    render(<CharacterSidebar {...defaultProps} activeSpeakerId="yanyeeku" onSetActive={onSetActive} />)
    fireEvent.click(screen.getByTitle(/Yanyeeku/))
    fireEvent.click(screen.getByText(/Clear Active/i))
    expect(onSetActive).toHaveBeenCalledWith('yanyeeku')
  })
})

describe('CharacterSidebar — loading state', () => {
  it('shows loading indicator when loading is true', () => {
    render(<CharacterSidebar {...defaultProps} loading={true} characters={[]} />)
    expect(screen.getByText('…')).toBeInTheDocument()
  })

  it('shows no characters when loading', () => {
    render(<CharacterSidebar {...defaultProps} loading={true} characters={[]} />)
    expect(screen.queryByText('Yanyeeku')).not.toBeInTheDocument()
  })
})
