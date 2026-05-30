import { useState, useEffect } from 'react'
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
  provider: 'ollama' | 'groq' | 'anthropic'
  rateLimits: RateLimits | null
  onSessionNumberChange: (n: number) => void
  onModelChange: (m: string) => void
  onDevModeChange: (v: boolean) => void
  onProviderChange: (p: 'ollama' | 'groq' | 'anthropic') => void
  onBoot: () => void
  onEnd: () => void
  onKillEnd: () => void
  onViewLog: () => void
  onOpenApiLogs: () => void
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
  session, streaming, ending, sessionNumber, model, devMode, provider, rateLimits,
  onSessionNumberChange, onModelChange, onDevModeChange, onProviderChange, onBoot, onEnd, onKillEnd, onViewLog, onOpenApiLogs, onPurgeNpcs,
}: Props) {
  const [confirmingPurge, setConfirmingPurge] = useState(false)
  const [confirmingKill, setConfirmingKill] = useState(false)
  useEffect(() => { if (!ending) setConfirmingKill(false) }, [ending])
  const isBooted = session !== null
  const locked = streaming || ending

  return (
    <header className="header">
      <div className="header-rune-bg" aria-hidden="true">
        {BG_RUNES.map((r, i) => (
          <span
            key={i}
            className="bg-rune"
            style={{
              left: r.left,
              top: r.top,
              animationDelay: r.delay,
              fontSize: r.size,
              opacity: r.opacity,
            }}
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
                type="number"
                min={1}
                value={sessionNumber}
                onChange={e => onSessionNumberChange(Number(e.target.value))}
                className="input-num"
                disabled={locked}
              />
            </label>
            <label className="control-label">
              Model
              <select
                value={model}
                onChange={e => onModelChange(e.target.value)}
                className="input-model"
                disabled={locked}
              >
                {MODELS[provider].map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </label>
            <label className="control-label dev-toggle" title="Dev mode: shows raw %%section%% markers in the stream. With Ollama also caps tokens for speed.">
              <input
                type="checkbox"
                checked={devMode}
                onChange={e => onDevModeChange(e.target.checked)}
                disabled={locked}
              />
              Dev
            </label>
            {confirmingPurge ? (
              <span className="inline-confirm">
                <span className="inline-confirm-label">Purge session NPCs?</span>
                <button className="btn btn-danger btn-sm" onClick={() => { setConfirmingPurge(false); onPurgeNpcs() }}>Yes</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setConfirmingPurge(false)}>No</button>
              </span>
            ) : (
              <button onClick={() => setConfirmingPurge(true)} className="btn btn-secondary" title="Delete all auto-created session NPCs">
                Purge NPCs
              </button>
            )}
            <button onClick={onBoot} disabled={locked} className="btn btn-primary">
              {streaming ? 'Booting…' : 'Boot Session'}
            </button>
          </>
        )}
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
                  ? ' · '
                  : null}
                {rateLimits.rpm_remaining && rateLimits.rpm_limit
                  ? `${rateLimits.rpm_remaining}/${rateLimits.rpm_limit} RPM`
                  : null}
              </span>
            )}
            <button onClick={onViewLog} disabled={ending} className="btn btn-secondary">
              View Log
            </button>
            <button onClick={onOpenApiLogs} disabled={ending} className="btn btn-secondary">
              API Logs
            </button>
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
      </div>
    </header>
  )
}
