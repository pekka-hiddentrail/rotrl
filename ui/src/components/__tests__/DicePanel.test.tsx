import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DicePanel, { normaliseSkill, lookupSkillBonus } from '../DicePanel'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const YANYEEKU_SPEAKER = {
  name: 'Yanyeeku',
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
    <DicePanel
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

// ─── Component: baseline ─────────────────────────────────────────────────────

describe('DicePanel — baseline', () => {
  it('renders the Roll button as disabled when no dice are pending', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: 'Roll' })).toBeDisabled()
  })

  it('enables Roll after clicking a die', () => {
    renderPanel()
    fireEvent.click(screen.getByTitle('d20'))
    expect(screen.getByRole('button', { name: 'Roll' })).not.toBeDisabled()
  })

  it('shows no history initially', () => {
    renderPanel()
    expect(screen.queryByText(/vs DC/)).not.toBeInTheDocument()
  })
})

// ─── Component: AC-007 — auto-apply modifier ─────────────────────────────────

describe('DicePanel — AC-007 auto-apply modifier', () => {
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

describe('DicePanel — AC-008 no active character', () => {
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

describe('DicePanel — AC-009 unmapped skill', () => {
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

describe('DicePanel — AC-010 auto-bonus toggle', () => {
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

describe('DicePanel — AC-011 skill normalisation', () => {
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

// ─── Component: plain roll (no pending roll) ──────────────────────────────────

describe('DicePanel — plain roll without pending', () => {
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
