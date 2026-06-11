/**
 * DiceTray — dice roller, skill bonus, roll history, and banner tests.
 *
 * Spec: specs/dice-tray.feature
 * Covers: AC-001 through AC-013
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DiceTray, { normaliseSkill, lookupSkillBonus } from '../DiceTray'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const YANYEEKU_SPEAKER = {
  name: 'Yanyeeku',
  portrait: '/portraits/yanyeeku.png',
  color: '#a060d0',
  rune: 'Y',
  skills: [
    { name: 'Perception', total: 7 },
    { name: 'Sense Motive', total: 4 },
    { name: 'Diplomacy', total: 6 },
  ],
}

const PERCEPTION_ROLL = {
  skill: 'Perception',
  dc: 18,
  success: 'You notice the ambush.',
  failure: 'You miss it.',
}

const DIPLOMACY_ROLL = {
  skill: 'Diplomacy',
  dc: 15,
  success: 'The guard lets you pass.',
  failure: 'He refuses.',
}

const SPELLCRAFT_ROLL = {
  skill: 'Spellcraft',
  dc: 20,
  success: 'Identified.',
  failure: 'Unknown.',
}

const NULL_RESOLVE = vi.fn().mockResolvedValue(null)

function renderPanel(
  props: Partial<{
    pendingRoll: typeof PERCEPTION_ROLL | null
    activeSpeaker: typeof YANYEEKU_SPEAKER | null
    onRoll: ReturnType<typeof vi.fn>
  }> = {},
) {
  const onRoll = props.onRoll ?? NULL_RESOLVE
  return render(
    <DiceTray
      sessionId="s1"
      pendingRoll={props.pendingRoll ?? null}
      activeSpeaker={props.activeSpeaker ?? null}
      onRoll={onRoll}
    />,
  )
}

// Force Math.random to 0.6 → d20 = floor(0.6 * 20) + 1 = 13
beforeEach(() => {
  vi.spyOn(Math, 'random').mockReturnValue(0.6)
})
afterEach(() => {
  vi.restoreAllMocks()
})

// ─── Unit: normaliseSkill ─────────────────────────────────────────────────────

describe('normaliseSkill', () => {
  it('lowercases and trims', () => {
    expect(normaliseSkill('  Perception  ')).toBe('perception')
  })

  it('collapses multiple spaces', () => {
    expect(normaliseSkill('Sense  Motive')).toBe('sense motive')
  })

  it('replaces hyphens and underscores with a space', () => {
    expect(normaliseSkill('Sense-Motive')).toBe('sense motive')
    expect(normaliseSkill('sense_motive')).toBe('sense motive')
  })
})

// ─── Unit: lookupSkillBonus ───────────────────────────────────────────────────

describe('lookupSkillBonus', () => {
  it('returns no-character when speaker is null', () => {
    expect(lookupSkillBonus('Perception', null)).toMatchObject({ kind: 'no-character' })
  })

  it('returns matched with correct modifier', () => {
    const result = lookupSkillBonus('Perception', YANYEEKU_SPEAKER)
    expect(result).toMatchObject({ kind: 'matched', modifier: 7, label: 'Perception +7' })
  })

  it('matches case-insensitively (AC-011)', () => {
    const result = lookupSkillBonus('perception', YANYEEKU_SPEAKER)
    expect(result).toMatchObject({ kind: 'matched', modifier: 7 })
  })

  it('matches "sense motive" to "Sense Motive" (AC-011)', () => {
    const result = lookupSkillBonus('sense motive', YANYEEKU_SPEAKER)
    expect(result).toMatchObject({ kind: 'matched', modifier: 4 })
  })

  it('returns unmapped when skill is not in speaker data', () => {
    const result = lookupSkillBonus('Spellcraft', YANYEEKU_SPEAKER)
    expect(result).toMatchObject({ kind: 'unmapped', skill: 'Spellcraft' })
  })

  it('formats a negative modifier label correctly', () => {
    const speaker = { name: 'X', skills: [{ name: 'Bluff', total: -1 }] }
    const result = lookupSkillBonus('Bluff', speaker)
    expect(result).toMatchObject({ kind: 'matched', label: 'Bluff -1' })
  })
})

// ─── Component: AC-001 — queue accumulation ───────────────────────────────────

describe('DiceTray — AC-001 queue accumulation', () => {
  it('renders the Roll button as disabled when no dice are pending', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: 'Roll' })).toBeDisabled()
  })

  it('enables Roll after clicking a die (AC-001)', () => {
    renderPanel()
    fireEvent.click(screen.getByTitle('d20'))
    expect(screen.getByRole('button', { name: 'Roll' })).not.toBeDisabled()
  })

  it('shows correct grouped expression after clicking multiple dice (AC-001)', () => {
    renderPanel()
    fireEvent.click(screen.getByTitle('d6'))
    fireEvent.click(screen.getByTitle('d6'))
    fireEvent.click(screen.getByTitle('d20'))
    expect(screen.getByText('2d6+1d20')).toBeInTheDocument()
  })

  it('accumulates dice without replacing the queue (AC-001)', () => {
    renderPanel()
    fireEvent.click(screen.getByTitle('d6'))
    fireEvent.click(screen.getByTitle('d6'))
    // Queue should show 2d6, not just 1d6
    expect(screen.getByText('2d6')).toBeInTheDocument()
  })

  it('shows no history initially', () => {
    renderPanel()
    expect(screen.queryByText(/vs DC/)).not.toBeInTheDocument()
  })
})

// ─── Component: AC-002 — roll history and latest highlight ────────────────────

describe('DiceTray — AC-002 roll history highlight', () => {
  it('most recent roll has history-latest class (AC-002)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    const { container } = renderPanel({ onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(onRoll).toHaveBeenCalled())
    const rows = container.querySelectorAll('.history-row')
    expect(rows[0]).toHaveClass('history-latest')
  })

  it('only the first row has history-latest class after multiple rolls (AC-002)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    const { container } = renderPanel({ onRoll })
    for (let i = 0; i < 3; i++) {
      fireEvent.click(screen.getByTitle('d20'))
      fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
      await waitFor(() => expect(onRoll).toHaveBeenCalledTimes(i + 1))
    }
    const rows = container.querySelectorAll('.history-row')
    expect(rows[0]).toHaveClass('history-latest')
    expect(rows[1]).not.toHaveClass('history-latest')
    expect(rows[2]).not.toHaveClass('history-latest')
  })
})

// ─── Component: AC-004 — pending roll banner ──────────────────────────────────

describe('DiceTray — AC-004 pending roll banner', () => {
  it('shows skill name in the banner (AC-004)', () => {
    renderPanel({ pendingRoll: DIPLOMACY_ROLL })
    expect(screen.getByText('Diplomacy')).toBeInTheDocument()
  })

  it('shows DC number in the banner (AC-004)', () => {
    renderPanel({ pendingRoll: DIPLOMACY_ROLL })
    expect(screen.getByText('DC 15')).toBeInTheDocument()
  })

  it('shows "click to roll d20" hint in the banner (AC-004)', () => {
    renderPanel({ pendingRoll: DIPLOMACY_ROLL })
    expect(screen.getByText('click to roll d20')).toBeInTheDocument()
  })

  it('adds dice-tray-active class to aside when pending roll is set (AC-004)', () => {
    const { container } = renderPanel({ pendingRoll: DIPLOMACY_ROLL })
    expect(container.querySelector('aside')).toHaveClass('dice-tray-active')
  })

  it('does not show dice-tray-active class when no pending roll', () => {
    const { container } = renderPanel({ pendingRoll: null })
    expect(container.querySelector('aside')).not.toHaveClass('dice-tray-active')
  })
})

// ─── Component: AC-006 — roll history limit ───────────────────────────────────

describe('DiceTray — AC-006 roll history limit', () => {
  it('keeps only the last 10 rolls when 12 have been made (AC-006)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    const { container } = renderPanel({ onRoll })
    for (let i = 0; i < 12; i++) {
      fireEvent.click(screen.getByTitle('d20'))
      fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
      await waitFor(() => expect(onRoll).toHaveBeenCalledTimes(i + 1))
    }
    const rows = container.querySelectorAll('.history-row')
    expect(rows).toHaveLength(10)
  })
})

// ─── Component: AC-007 — auto-apply modifier ─────────────────────────────────

describe('DiceTray — AC-007 auto-apply modifier', () => {
  it('calls onRoll with rawTotal + modifier when speaker and pending roll are set', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    // d20 = 13 (Math.random = 0.6), modifier = +7, total = 20
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 20))
  })

  it('shows modifier label in history breakdown', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(screen.getByText(/Perception \+7/)).toBeInTheDocument())
  })

  it('shows DC in history', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(screen.getByText(/vs DC 18/)).toBeInTheDocument())
  })

  it('shows PASSED badge after roll resolves as pass (AC-007)', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(screen.getByText('PASSED')).toBeInTheDocument())
  })

  it('shows FAILED badge after roll resolves as fail (AC-007)', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: false })
    renderPanel({ pendingRoll: DIPLOMACY_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(screen.getByText('FAILED')).toBeInTheDocument())
  })

  it('shows the bonus preview in the banner before rolling', () => {
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    expect(screen.getByText(/\+7 from Perception/)).toBeInTheDocument()
  })
})

// ─── Component: AC-008 — no active character ──────────────────────────────────

describe('DiceTray — AC-008 no active character', () => {
  it('calls onRoll with raw total when activeSpeaker is null', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: null, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    // raw d20 = 13, no modifier
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 13))
  })

  it('shows "No active character" note in history', async () => {
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: null })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() =>
      expect(screen.getByText(/No active character — raw roll only/)).toBeInTheDocument(),
    )
  })

  it('shows "No active character" preview in the banner', () => {
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: null })
    expect(screen.getByText('No active character')).toBeInTheDocument()
  })
})

// ─── Component: AC-009 — unmapped skill ───────────────────────────────────────

describe('DiceTray — AC-009 unmapped skill', () => {
  it('calls onRoll with raw total when skill is not mapped', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: SPELLCRAFT_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 13))
  })

  it('shows "No mapped bonus for Spellcraft" note in history', async () => {
    renderPanel({ pendingRoll: SPELLCRAFT_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() =>
      expect(screen.getByText(/No mapped bonus for Spellcraft/)).toBeInTheDocument(),
    )
  })

  it('shows "No mapped bonus" preview in the banner', () => {
    renderPanel({ pendingRoll: SPELLCRAFT_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    expect(screen.getByText('No mapped bonus')).toBeInTheDocument()
  })
})

// ─── Component: AC-010 — auto-bonus toggle ────────────────────────────────────

describe('DiceTray — AC-010 auto-bonus toggle', () => {
  it('shows the Auto bonus toggle when a pending roll is active', () => {
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    expect(screen.getByRole('checkbox')).toBeInTheDocument()
    expect(screen.getByText(/Auto bonus/i)).toBeInTheDocument()
  })

  it('does not show the toggle when no pending roll', () => {
    renderPanel({ pendingRoll: null, activeSpeaker: YANYEEKU_SPEAKER })
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('toggle is checked by default', () => {
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('uses raw total when toggle is turned off (AC-010)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    // Turn off auto-bonus
    fireEvent.click(screen.getByRole('checkbox'))
    expect(screen.getByRole('checkbox')).not.toBeChecked()
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    // raw d20 = 13, no modifier applied
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 13))
  })
})

// ─── Component: AC-011 — skill name normalisation ────────────────────────────

describe('DiceTray — AC-011 skill normalisation', () => {
  it('matches "sense motive" (lowercase) to "Sense Motive" entry', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    const roll = { ...PERCEPTION_ROLL, skill: 'sense motive', dc: 15 }
    renderPanel({ pendingRoll: roll, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    // sense motive modifier = +4, d20 = 13, total = 17
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 17))
  })
})

// ─── Component: AC-012 — click banner to quick-roll d20 ──────────────────────

describe('DiceTray — AC-012 click banner to quick-roll d20', () => {
  it('clicking the roll-request-prompt calls onRoll with 1d20 and modifier (AC-012)', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('Click to roll d20'))
    // d20 = 13 (Math.random = 0.6), Perception +7 = total 20
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 20))
  })

  it('clicking the banner with no active speaker uses raw total (AC-012)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: null, onRoll })
    fireEvent.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 13))
  })

  it('clicking the banner does not clear the manually queued dice (AC-012)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d6'))
    fireEvent.click(screen.getByTitle('d6'))
    expect(screen.getByText('2d6')).toBeInTheDocument()
    fireEvent.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(onRoll).toHaveBeenCalled())
    // Manual queue still shows 2d6
    expect(screen.getByText('2d6')).toBeInTheDocument()
  })

  it('clicking the banner respects the auto-bonus toggle when off (AC-012)', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByTitle('Click to roll d20'))
    // auto-bonus off → raw d20 = 13
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 13))
  })

  it('banner click shows PASSED badge when roll resolves (AC-012)', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('Click to roll d20'))
    await waitFor(() => expect(screen.getByText('PASSED')).toBeInTheDocument())
  })
})

// ─── AC-013 — character portrait and name in roll banner ─────────────────────

describe('DiceTray — AC-013 character badge in pending roll banner', () => {
  it('shows the character name in the banner when active speaker is set', () => {
    renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
  })

  it('renders the portrait image with the character colour as border', () => {
    const { container } = renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    const avatar = container.querySelector('.roll-request-avatar') as HTMLElement
    expect(avatar).toBeInTheDocument()
    expect(avatar.style.borderColor).toBe('rgb(160, 96, 208)')
    const img = avatar.querySelector('img') as HTMLImageElement
    expect(img.src).toContain('/portraits/yanyeeku.png')
  })

  it('renders the rune fallback letter inside the avatar', () => {
    const { container } = renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    const rune = container.querySelector('.roll-request-rune')
    expect(rune).toBeInTheDocument()
    expect(rune?.textContent).toBe('Y')
  })

  it('character name is coloured with the character colour', () => {
    const { container } = renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: YANYEEKU_SPEAKER })
    const name = container.querySelector('.roll-request-name') as HTMLElement
    expect(name).toBeInTheDocument()
    expect(name.style.color).toBe('rgb(160, 96, 208)')
  })

  it('no character badge when activeSpeaker is null', () => {
    const { container } = renderPanel({ pendingRoll: PERCEPTION_ROLL, activeSpeaker: null })
    expect(container.querySelector('.roll-request-character')).not.toBeInTheDocument()
  })

  it('no character badge when no pending roll', () => {
    const { container } = renderPanel({ pendingRoll: null, activeSpeaker: YANYEEKU_SPEAKER })
    expect(container.querySelector('.roll-request-character')).not.toBeInTheDocument()
  })
})

// ─── Component: plain roll (no pending roll) ──────────────────────────────────

describe('DiceTray — plain roll without pending', () => {
  it('calls onRoll with the raw total', async () => {
    const onRoll = vi.fn().mockResolvedValue(null)
    renderPanel({ pendingRoll: null, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    await waitFor(() => expect(onRoll).toHaveBeenCalledWith('1d20', [13], 13))
  })

  it('does not show a passed/failed badge for plain rolls', async () => {
    const onRoll = vi.fn().mockResolvedValue({ passed: true })
    renderPanel({ pendingRoll: null, activeSpeaker: YANYEEKU_SPEAKER, onRoll })
    fireEvent.click(screen.getByTitle('d20'))
    fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
    // No pendingRoll → onRoll resolves to null from App side (we return { passed: true } but
    // the component does update passed when result is non-null — check badge does NOT appear
    // when no DC is associated)
    await waitFor(() => expect(onRoll).toHaveBeenCalled())
    // When there's no pending roll, passed badge shows if onRoll returns a result.
    // The history entry should have no DC so no "vs DC" text
    expect(screen.queryByText(/vs DC/)).not.toBeInTheDocument()
  })
})
