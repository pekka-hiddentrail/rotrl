import type { SessionInfo } from '../types'

const MODELS = [
  { value: 'qwen2.5:1.5b', label: 'qwen2.5:1.5b — fast' },
  { value: 'qwen3:4b',     label: 'qwen3:4b' },
]

interface Props {
  session: SessionInfo | null
  streaming: boolean
  ending: boolean
  sessionNumber: number
  model: string
  devMode: boolean
  onSessionNumberChange: (n: number) => void
  onModelChange: (m: string) => void
  onDevModeChange: (v: boolean) => void
  onBoot: () => void
  onEnd: () => void
  onViewLog: () => void
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
  session, streaming, ending, sessionNumber, model, devMode,
  onSessionNumberChange, onModelChange, onDevModeChange, onBoot, onEnd, onViewLog,
}: Props) {
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
                {MODELS.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </label>
            <label className="control-label dev-toggle" title="Dev mode uses a minimal prompt — fast but no rules">
              <input
                type="checkbox"
                checked={devMode}
                onChange={e => onDevModeChange(e.target.checked)}
                disabled={locked}
              />
              Dev
            </label>
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
            <button onClick={onViewLog} disabled={ending} className="btn btn-secondary">
              View Log
            </button>
            <button onClick={onEnd} disabled={ending} className="btn btn-danger">
              {ending ? 'Ending…' : 'End Session'}
            </button>
          </>
        )}
      </div>
    </header>
  )
}
