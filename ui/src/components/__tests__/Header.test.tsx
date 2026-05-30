/**
 * Header/session controls AC coverage.
 *
 * Covers session-controls.feature AC-001 through AC-008 plus
 * llm-providers.feature AC-001/AC-005.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import type { ComponentProps } from 'react'
import Header from '../Header'
import type { SessionInfo } from '../../types'

const session: SessionInfo = {
  id: 'sess-test',
  sessionNumber: 2,
  model: 'llama-3.3-70b-versatile',
}

const callbacks = {
  onSessionNumberChange: vi.fn(),
  onModelChange: vi.fn(),
  onDevModeChange: vi.fn(),
  onProviderChange: vi.fn(),
  onBoot: vi.fn(),
  onEnd: vi.fn(),
  onKillEnd: vi.fn(),
  onViewLog: vi.fn(),
  onOpenApiLogs: vi.fn(),
  onPurgeNpcs: vi.fn(),
}

function renderHeader(overrides: Partial<ComponentProps<typeof Header>> = {}) {
  return render(
    <Header
      session={null}
      streaming={false}
      ending={false}
      sessionNumber={1}
      model="llama-3.3-70b-versatile"
      devMode={false}
      provider="groq"
      rateLimits={null}
      {...callbacks}
      {...overrides}
    />,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Header - AC-001 pre-boot controls', () => {
  it('shows configuration controls and enabled Boot Session before boot', () => {
    renderHeader()

    expect(screen.getByRole('button', { name: /Groq/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ollama/ })).toBeInTheDocument()
    expect(screen.getByRole('spinbutton')).toHaveValue(1)
    expect(screen.getByRole('combobox')).toHaveValue('llama-3.3-70b-versatile')
    expect(screen.getByLabelText('Dev')).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Purge NPCs' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Boot Session' })).not.toBeDisabled()
  })
})

describe('Header - AC-002 / llm-providers AC-001 model switching', () => {
  it('requests provider switch and renders only the selected provider model options', () => {
    const { rerender } = renderHeader()

    fireEvent.click(screen.getByRole('button', { name: /Ollama/ }))
    expect(callbacks.onProviderChange).toHaveBeenCalledWith('ollama')

    rerender(
      <Header
        session={null}
        streaming={false}
        ending={false}
        sessionNumber={1}
        model="qwen3:4b"
        devMode={false}
        provider="ollama"
        rateLimits={null}
        {...callbacks}
      />,
    )

    const modelSelect = screen.getByRole('combobox')
    const optionTexts = within(modelSelect).getAllByRole('option').map(o => o.textContent)
    expect(modelSelect).toHaveValue('qwen3:4b')
    expect(optionTexts[0]).toBe('qwen3:4b')
    expect(optionTexts[1]).toContain('qwen2.5:1.5b')
    expect(optionTexts.some(text => text?.includes('llama'))).toBe(false)
  })
})

describe('Header - AC-003 boot disabled state', () => {
  it('disables boot while streaming and prevents duplicate boot clicks', () => {
    renderHeader({ streaming: true })

    const boot = screen.getByRole('button', { name: /Booting/ })
    expect(boot).toBeDisabled()
    fireEvent.click(boot)
    expect(callbacks.onBoot).not.toHaveBeenCalled()
  })
})

describe('Header - AC-004 post-boot controls', () => {
  it('shows the session badge and action buttons after boot', () => {
    renderHeader({ session })

    expect(screen.getByText(/Session 2/)).toBeInTheDocument()
    expect(screen.getByText(/llama-3.3-70b-versatile/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'View Log' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'API Logs' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'End Session' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Purge NPCs' })).not.toBeInTheDocument()
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
  })
})

describe('Header - AC-005 View Log', () => {
  it('calls the View Log handler without leaving the current UI', () => {
    renderHeader({ session })

    fireEvent.click(screen.getByRole('button', { name: 'View Log' }))
    expect(callbacks.onViewLog).toHaveBeenCalledOnce()
  })
})

describe('Header - AC-006 purge confirmation', () => {
  it('uses inline confirmation and calls purge only on Yes', () => {
    const confirmSpy = vi.spyOn(window, 'confirm')
    renderHeader()

    fireEvent.click(screen.getByRole('button', { name: 'Purge NPCs' }))
    expect(screen.getByText('Purge session NPCs?')).toBeInTheDocument()
    expect(confirmSpy).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    expect(callbacks.onPurgeNpcs).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Purge NPCs' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Purge NPCs' }))
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    expect(callbacks.onPurgeNpcs).toHaveBeenCalledOnce()
    expect(screen.getByRole('button', { name: 'Purge NPCs' })).toBeInTheDocument()
  })
})

describe('Header - AC-007 / llm-providers AC-005 rate-limit badge', () => {
  it('shows formatted TPM/RPM values and reset tooltip when rate limits arrive', () => {
    renderHeader({
      session,
      rateLimits: {
        tpm_remaining: '4500',
        tpm_limit: '6000',
        tpm_reset: '12s',
        rpm_remaining: '28',
        rpm_limit: '30',
        rpm_reset: '44s',
      },
    })

    const badge = screen.getByText(/4,500\/6,000 TPM/)
    expect(badge).toHaveTextContent(/28\/30 RPM/)
    expect(badge).toHaveAttribute('title', expect.stringContaining('resets in 12s'))
    expect(badge).toHaveAttribute('title', expect.stringContaining('resets in 44s'))
  })

  it('does not show a rate-limit badge before any event is received', () => {
    renderHeader({ session, rateLimits: null })
    expect(document.querySelector('.rate-limits-badge')).not.toBeInTheDocument()
  })
})

describe('Header - AC-008 Kill confirmation', () => {
  it('aborts ending only after inline Yes and keeps ending on No', () => {
    renderHeader({ session, ending: true })

    expect(screen.getByRole('button', { name: /Ending/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Kill' }))
    expect(screen.getByText('Discard and quit?')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    expect(callbacks.onKillEnd).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Kill' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Kill' }))
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    expect(callbacks.onKillEnd).toHaveBeenCalledOnce()
  })
})
