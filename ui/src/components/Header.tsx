import type { SessionInfo } from '../types'

interface Props {
  session: SessionInfo | null
  streaming: boolean
  sessionNumber: number
  model: string
  devMode: boolean
  onSessionNumberChange: (n: number) => void
  onModelChange: (m: string) => void
  onDevModeChange: (v: boolean) => void
  onBoot: () => void
  onEnd: () => void
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
  session, streaming, sessionNumber, model, devMode,
  onSessionNumberChange, onModelChange, onDevModeChange, onBoot, onEnd,
}: Props) {
  const isBooted = session !== null

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
              />
            </label>
            <label className="control-label">
              Model
              <input
                type="text"
                value={model}
                onChange={e => onModelChange(e.target.value)}
                className="input-model"
              />
            </label>
            <label className="control-label dev-toggle" title="Dev mode uses a minimal prompt — fast but no rules">
              <input
                type="checkbox"
                checked={devMode}
                onChange={e => onDevModeChange(e.target.checked)}
              />
              Dev
            </label>
            <button onClick={onBoot} disabled={streaming} className="btn btn-primary">
              {streaming ? 'Booting…' : 'Boot Session'}
            </button>
          </>
        )}
        {isBooted && (
          <>
            <span className="session-badge">
              Session {session.sessionNumber} · {session.model}
            </span>
            <button onClick={onEnd} className="btn btn-danger">
              End Session
            </button>
          </>
        )}
      </div>
    </header>
  )
}
