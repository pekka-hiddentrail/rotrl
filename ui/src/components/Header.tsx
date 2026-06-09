import { useState, useEffect, useRef } from 'react'
import type { SessionInfo } from '../types'

const MODELS: Record<string, { value: string; label: string }[]> = {
  ollama: [
    { value: 'qwen3:4b',     label: 'qwen3:4b' },
    { value: 'qwen2.5:1.5b', label: 'qwen2.5:1.5b — fast' },
  ],
  groq: [
    { value: 'llama-3.3-70b-versatile', label: 'llama-3.3-70b — best quality' },
    { value: 'llama-3.1-8b-instant',    label: 'llama-3.1-8b — fastest' },
  ],
  anthropic: [
    { value: 'claude-sonnet-4-6',        label: 'claude-sonnet-4-6 — default' },
    { value: 'claude-opus-4-7',          label: 'claude-opus-4-7 — quality' },
    { value: 'claude-haiku-4-5-20251001', label: 'claude-haiku-4-5 — fast' },
  ],
}

interface RateLimits {
  rpm_limit?: string
  rpm_remaining?: string
  rpm_reset?: string
  tpm_limit?: string
  tpm_remaining?: string
  tpm_reset?: string
}

interface Props {
  session: SessionInfo | null
  streaming: boolean
  ending: boolean
  sessionNumber: number
  model: string
  devMode: boolean
  eventScheduler: boolean
  provider: 'ollama' | 'groq' | 'anthropic'
  rateLimits: RateLimits | null
  onSessionNumberChange: (n: number) => void
  onModelChange: (m: string) => void
  onDevModeChange: (v: boolean) => void
  onEventSchedulerChange: (v: boolean) => void
  onProviderChange: (p: 'ollama' | 'groq' | 'anthropic') => void
  onBoot: () => void
  onEnd: () => void
  onKillEnd: () => void
  onViewLog: () => void
  onOpenApiLogs: () => void
  onOpenBenchmarks: () => void
  onOpenCoverage: () => void
  onPurgeNpcs: () => void
}

const RUNE_CHARS = 'ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ'

const BG_RUNES = Array.from({ length: 32 }, (_, i) => ({
  char: RUNE_CHARS[i % RUNE_CHARS.length],
  left: `${(i * 3.2) % 100}%`,
  top: `${(i * 7 + 10) % 80}%`,
  delay: `${(i * 0.4) % 8}s`,
  size: `${14 + (i % 5) * 4}px`,
  opacity: 0.07 + (i % 4) * 0.03,
}))

export default function Header({
  session, streaming, ending, sessionNumber, model, devMode, eventScheduler, provider, rateLimits,
  onSessionNumberChange, onModelChange, onDevModeChange, onEventSchedulerChange, onProviderChange,
  onBoot, onEnd, onKillEnd, onViewLog, onOpenApiLogs, onOpenBenchmarks, onOpenCoverage, onPurgeNpcs,
}: Props) {
  const [confirmingPurge, setConfirmingPurge] = useState(false)
  const [confirmingKill,  setConfirmingKill]  = useState(false)
  const [toolsOpen,       setToolsOpen]       = useState(false)
  const toolsRef = useRef<HTMLDivElement>(null)

  useEffect(() => { if (!ending) setConfirmingKill(false) }, [ending])

  // Close tools dropdown on outside click
  useEffect(() => {
    if (!toolsOpen) return
    const handler = (e: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) {
        setToolsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [toolsOpen])

  // Close tools dropdown on Escape
  useEffect(() => {
    if (!toolsOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setToolsOpen(false) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toolsOpen])

  const isBooted = session !== null
  const locked   = streaming || ending

  function openTool(fn: () => void) {
    setToolsOpen(false)
    fn()
  }

  function triggerPurge() {
    setToolsOpen(false)
    setConfirmingPurge(true)
  }

  return (
    <header className="header">
      <div className="header-rune-bg" aria-hidden="true">
        {BG_RUNES.map((r, i) => (
          <span
            key={i}
            className="bg-rune"
            style={{ left: r.left, top: r.top, animationDelay: r.delay, fontSize: r.size, opacity: r.opacity }}
          >
            {r.char}
          </span>
        ))}
      </div>

      <div className="header-logo-area">
        <div className="header-rune-row" aria-hidden="true">
          {Array.from('ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊ').map((r, i) => (
            <span key={i} className="rune-accent">{r}</span>
          ))}
        </div>
        <div className="logo-title">Rise of the Runelords</div>
        <div className="logo-subtitle">✦ Agentic Game Master ✦</div>
      </div>

      <div className="header-controls">

        {/* ── Pre-boot controls ─────────────────────────────────────────── */}
        {!isBooted && (
          <>
            <div className="provider-toggle" title="LLM backend">
              {(['ollama', 'groq', 'anthropic'] as const).map(p => (
                <button
                  key={p}
                  className={`provider-btn${provider === p ? ' active' : ''}`}
                  onClick={() => onProviderChange(p)}
                  disabled={locked}
                >
                  {p === 'groq' ? '⚡ Groq' : p === 'anthropic' ? '🤖 Claude' : '🖥 Ollama'}
                </button>
              ))}
            </div>
            <label className="control-label">
              Session
              <input
                type="number" min={1} value={sessionNumber}
                onChange={e => onSessionNumberChange(Number(e.target.value))}
                className="input-num" disabled={locked}
              />
            </label>
            <label className="control-label">
              Model
              <select value={model} onChange={e => onModelChange(e.target.value)} className="input-model" disabled={locked}>
                {MODELS[provider].map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </label>
            <label className="control-label dev-toggle" title="Dev mode: shows raw %%section%% markers in the stream. With Ollama also caps tokens for speed.">
              <input type="checkbox" checked={devMode} onChange={e => onDevModeChange(e.target.checked)} disabled={locked} />
              Dev
            </label>
            <label className="control-label dev-toggle" title="Event scheduler: enables the temperature-based event scheduler (E1 MVP). The %%EVENT%% LLM path stays active alongside it.">
              <input type="checkbox" checked={eventScheduler} onChange={e => onEventSchedulerChange(e.target.checked)} disabled={locked} />
              Scheduler
            </label>
            <button onClick={onBoot} disabled={locked} className="btn btn-primary">
              {streaming ? 'Booting…' : 'Boot Session'}
            </button>
          </>
        )}

        {/* ── Post-boot controls ────────────────────────────────────────── */}
        {isBooted && (
          <>
            <span className="session-badge">
              Session {session.sessionNumber} · {session.model}
            </span>
            {rateLimits && (
              <span
                className="rate-limits-badge"
                title={[
                  rateLimits.tpm_remaining && rateLimits.tpm_limit
                    ? `TPM: ${rateLimits.tpm_remaining}/${rateLimits.tpm_limit} remaining${rateLimits.tpm_reset ? ` · resets in ${rateLimits.tpm_reset}` : ''}`
                    : null,
                  rateLimits.rpm_remaining && rateLimits.rpm_limit
                    ? `RPM: ${rateLimits.rpm_remaining}/${rateLimits.rpm_limit} remaining${rateLimits.rpm_reset ? ` · resets in ${rateLimits.rpm_reset}` : ''}`
                    : null,
                ].filter(Boolean).join('\n') || 'Groq rate limits'}
              >
                {rateLimits.tpm_remaining && rateLimits.tpm_limit
                  ? `⚡ ${Number(rateLimits.tpm_remaining).toLocaleString()}/${Number(rateLimits.tpm_limit).toLocaleString()} TPM`
                  : null}
                {rateLimits.tpm_remaining && rateLimits.tpm_limit && rateLimits.rpm_remaining && rateLimits.rpm_limit
                  ? ' · ' : null}
                {rateLimits.rpm_remaining && rateLimits.rpm_limit
                  ? `${rateLimits.rpm_remaining}/${rateLimits.rpm_limit} RPM`
                  : null}
              </span>
            )}
            {ending ? (
              <>
                <button disabled className="btn btn-danger">Ending…</button>
                {confirmingKill ? (
                  <span className="inline-confirm">
                    <span className="inline-confirm-label">Discard and quit?</span>
                    <button className="btn btn-danger btn-sm" onClick={() => { setConfirmingKill(false); onKillEnd() }}>Yes</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setConfirmingKill(false)}>No</button>
                  </span>
                ) : (
                  <button className="btn btn-secondary" onClick={() => setConfirmingKill(true)} title="Force-quit the ending process and discard recap">
                    Kill
                  </button>
                )}
              </>
            ) : (
              <button onClick={onEnd} className="btn btn-danger">End Session</button>
            )}
          </>
        )}

        {/* ── Tools dropdown — always visible ──────────────────────────── */}
        {confirmingPurge ? (
          <span className="inline-confirm">
            <span className="inline-confirm-label">Purge session NPCs?</span>
            <button className="btn btn-danger btn-sm" onClick={() => { setConfirmingPurge(false); onPurgeNpcs() }}>Yes</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setConfirmingPurge(false)}>No</button>
          </span>
        ) : (
          <div className="tools-dropdown" ref={toolsRef}>
            <button
              className={`btn btn-secondary tools-toggle${toolsOpen ? ' active' : ''}`}
              onClick={() => setToolsOpen(v => !v)}
              title="Dev & utility tools"
            >
              Tools ▾
            </button>
            {toolsOpen && (
              <div className="tools-menu">
                {isBooted && (
                  <>
                    <button className="tools-item" onClick={() => openTool(onViewLog)} disabled={ending}>
                      📄 View Session Log
                    </button>
                    <button className="tools-item" onClick={() => openTool(onOpenApiLogs)} disabled={ending}>
                      🔌 API Logs
                    </button>
                    <div className="tools-separator" />
                  </>
                )}
                <button className="tools-item" onClick={() => openTool(onOpenBenchmarks)}>
                  📈 Token Benchmarks
                </button>
                <button className="tools-item" onClick={() => openTool(onOpenCoverage)}>
                  ✅ Coverage Matrix
                </button>
                <div className="tools-separator" />
                <button className="tools-item tools-item--danger" onClick={triggerPurge}>
                  🗑 Purge Session NPCs
                </button>
              </div>
            )}
          </div>
        )}

      </div>
    </header>
  )
}
