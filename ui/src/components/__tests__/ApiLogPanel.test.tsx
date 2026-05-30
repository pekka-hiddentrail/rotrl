import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ApiLogPanel from '../ApiLogPanel'
import * as api from '../../api'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FILE_A = '20260530_143022_123_groq_s001_t003_abcd1234.json'
const FILE_B = '20260530_144500_456_ollama_s002_t001_efgh5678.json'

const ENTRY_OK: Record<string, unknown> = {
  status: 'ok',
  section_format_ok: true,
  first_token_ms: 312,
  duration_ms: 2100,
  usage: { total_tokens: 1850 },
  provider: 'groq',
}

const ENTRY_ERR: Record<string, unknown> = {
  status: 'error',
  section_format_ok: null,
  first_token_ms: null,
  duration_ms: null,
  usage: null,
  provider: 'groq',
}

function setup(files: string[] = [FILE_A, FILE_B], onClose = vi.fn()) {
  vi.spyOn(api, 'fetchApiLogList').mockResolvedValue(files)
  return { onClose, ...render(<ApiLogPanel onClose={onClose} />) }
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ── AC-009 — List view ────────────────────────────────────────────────────────

describe('AC-009 — API log list view', () => {
  it('shows "No API logs yet" when list is empty', async () => {
    setup([])
    await screen.findByText('No API logs yet')
  })

  it('renders a row for each file', async () => {
    setup([FILE_A, FILE_B])
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(2)
    })
  })

  it('parses timestamp from filename and displays it', async () => {
    setup([FILE_A])
    await screen.findByText('2026-05-30 14:30:22')
  })

  it('displays provider, session, and turn parsed from filename', async () => {
    setup([FILE_A])
    await screen.findByText(/groq · S001 · T003/)
  })

  it('shows "API Logs" heading', async () => {
    setup([FILE_A])
    await screen.findByText('API Logs')
  })

  it('shows error message when list fetch fails', async () => {
    vi.spyOn(api, 'fetchApiLogList').mockRejectedValue(new Error('Network error'))
    render(<ApiLogPanel onClose={vi.fn()} />)
    await screen.findByText(/Network error/)
  })

  it('closes when backdrop is clicked', async () => {
    const onClose = vi.fn()
    setup([FILE_A], onClose)
    await screen.findByText('API Logs')
    // The overlay div is the backdrop
    const overlay = document.querySelector('.api-log-overlay') as HTMLElement
    fireEvent.click(overlay)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes when Escape key is pressed', async () => {
    const onClose = vi.fn()
    setup([FILE_A], onClose)
    await screen.findByText('API Logs')
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes when the ✕ button is clicked', async () => {
    const onClose = vi.fn()
    setup([FILE_A], onClose)
    await screen.findByText('API Logs')
    fireEvent.click(screen.getByTitle('Close (Esc)'))
    expect(onClose).toHaveBeenCalledOnce()
  })
})

// ── AC-010 — Detail view ──────────────────────────────────────────────────────

describe('AC-010 — API log detail view', () => {
  it('switches to detail view on row click', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('← Back')
    expect(screen.queryByText('API Logs')).not.toBeInTheDocument()
  })

  it('displays "ok" status badge', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('ok')
  })

  it('displays "✓ structured" badge when section_format_ok is true', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('✓ structured')
  })

  it('displays "✗ flat" badge when section_format_ok is false', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue({ ...ENTRY_OK, section_format_ok: false })
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('✗ flat')
  })

  it('displays "—" badge when section_format_ok is null', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_ERR)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('error') // status
    // format cell renders "—" (there will be multiple "—" for nulls)
    const dashes = await screen.findAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })

  it('shows first_token_ms in ms', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('312 ms')
  })

  it('shows duration_ms in ms', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('2100 ms')
  })

  it('shows total_tokens formatted with locale', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('1,850')
  })

  it('shows "—" for null first_token_ms (error turn)', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_ERR)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('error')
    const dashes = await screen.findAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(3) // first_token, duration, tokens all null
  })

  it('shows raw JSON in a code block', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    // Wait for summary bar to confirm detail view is rendered
    await screen.findByText('312 ms')
    const pre = document.querySelector('.api-log-json')
    expect(pre).toBeTruthy()
    expect(pre!.textContent).toContain('"status"')
    expect(pre!.textContent).toContain('"ok"')
  })

  it('returns to list view when ← Back is clicked', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockResolvedValue(ENTRY_OK)
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText('← Back')
    fireEvent.click(screen.getByText('← Back'))
    await screen.findByText('API Logs')
    expect(screen.queryByText('← Back')).not.toBeInTheDocument()
  })

  it('shows an error message when entry fetch fails', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockRejectedValue(new Error('Fetch failed'))
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText(/Fetch failed/)
    expect(screen.getByText('← Back')).toBeInTheDocument()
  })

  it('still shows ← Back after a fetch error', async () => {
    vi.spyOn(api, 'fetchApiLogEntry').mockRejectedValue(new Error('500'))
    setup([FILE_A])
    fireEvent.click(await screen.findByText('2026-05-30 14:30:22'))
    await screen.findByText(/500/)
    expect(screen.getByText('← Back')).toBeInTheDocument()
  })
})
