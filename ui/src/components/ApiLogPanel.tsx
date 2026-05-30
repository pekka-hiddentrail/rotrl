import { useState, useEffect, useCallback } from 'react'
import { fetchApiLogList, fetchApiLogEntry } from '../api'

// Filename format: YYYYMMDD_HHMMSS_mmm_{provider}_s{NNN}_t{TTT}_{session[:8]}.json
function parseLogFilename(filename: string) {
  const m = filename.match(/^(\d{8})_(\d{6})_\d+_(\w+)_s(\d+)_t(\d+)_/)
  if (!m) return null
  const d = m[1]
  const t = m[2]
  return {
    ts: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)} ${t.slice(0, 2)}:${t.slice(2, 4)}:${t.slice(4, 6)}`,
    provider: m[3],
    session: parseInt(m[4], 10),
    turn: parseInt(m[5], 10),
  }
}

interface LogEntry {
  status?: string
  section_format_ok?: boolean | null
  first_token_ms?: number | null
  duration_ms?: number | null
  usage?: { total_tokens?: number } | null
  [key: string]: unknown
}

interface Props {
  onClose: () => void
}

function StatusBadge({ val }: { val: string | undefined }) {
  if (val === 'ok')    return <span className="api-log-badge api-log-badge--ok">{val}</span>
  if (val === 'error') return <span className="api-log-badge api-log-badge--err">{val}</span>
  return <span className="api-log-badge api-log-badge--nil">{val ?? '—'}</span>
}

function FormatBadge({ val }: { val: boolean | null | undefined }) {
  if (val === true)  return <span className="api-log-badge api-log-badge--ok">✓ structured</span>
  if (val === false) return <span className="api-log-badge api-log-badge--err">✗ flat</span>
  return <span className="api-log-badge api-log-badge--nil">—</span>
}

export default function ApiLogPanel({ onClose }: Props) {
  const [files, setFiles]               = useState<string[]>([])
  const [listLoading, setListLoading]   = useState(true)
  const [listError, setListError]       = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [entry, setEntry]               = useState<LogEntry | null>(null)
  const [entryLoading, setEntryLoading] = useState(false)
  const [entryError, setEntryError]     = useState<string | null>(null)

  useEffect(() => {
    fetchApiLogList()
      .then(setFiles)
      .catch(e => setListError(String(e)))
      .finally(() => setListLoading(false))
  }, [])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleSelect = useCallback(async (filename: string) => {
    setSelectedFile(filename)
    setEntry(null)
    setEntryError(null)
    setEntryLoading(true)
    try {
      setEntry(await fetchApiLogEntry(filename) as LogEntry)
    } catch (e) {
      setEntryError(String(e))
    } finally {
      setEntryLoading(false)
    }
  }, [])

  const handleBack = () => {
    setSelectedFile(null)
    setEntry(null)
    setEntryError(null)
  }

  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div className="sheet-overlay api-log-overlay" onClick={handleBackdrop}>
      <div className="api-log-panel">
        <button className="sheet-close" onClick={onClose} title="Close (Esc)">✕</button>

        {!selectedFile ? (
          // ── LIST VIEW ──────────────────────────────────────────────────
          <>
            <h2 className="api-log-title">API Logs</h2>
            {listLoading && <p className="api-log-empty">Loading…</p>}
            {listError   && <p className="api-log-empty api-log-empty--err">{listError}</p>}
            {!listLoading && !listError && files.length === 0 && (
              <p className="api-log-empty">No API logs yet</p>
            )}
            {!listLoading && !listError && files.length > 0 && (
              <ul className="api-log-list">
                {files.map(f => {
                  const meta = parseLogFilename(f)
                  return (
                    <li key={f} className="api-log-row" onClick={() => handleSelect(f)}>
                      <span className="api-log-ts">{meta?.ts ?? f}</span>
                      <span className="api-log-meta">
                        {meta
                          ? `${meta.provider} · S${String(meta.session).padStart(3, '0')} · T${String(meta.turn).padStart(3, '0')}`
                          : f}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}
          </>
        ) : (
          // ── DETAIL VIEW ────────────────────────────────────────────────
          <>
            <button className="api-log-back" onClick={handleBack}>← Back</button>
            <h2 className="api-log-title api-log-title--detail">{selectedFile}</h2>

            {entryLoading && <p className="api-log-empty">Loading…</p>}
            {entryError   && (
              <p className="api-log-empty api-log-empty--err">{entryError}</p>
            )}

            {entry && (
              <>
                <div className="api-log-summary">
                  <div className="api-log-metric">
                    <span className="api-log-metric-label">status</span>
                    <StatusBadge val={entry.status} />
                  </div>
                  <div className="api-log-metric">
                    <span className="api-log-metric-label">format</span>
                    <FormatBadge val={entry.section_format_ok} />
                  </div>
                  <div className="api-log-metric">
                    <span className="api-log-metric-label">first token</span>
                    <span className="api-log-metric-value">
                      {entry.first_token_ms != null ? `${entry.first_token_ms} ms` : '—'}
                    </span>
                  </div>
                  <div className="api-log-metric">
                    <span className="api-log-metric-label">duration</span>
                    <span className="api-log-metric-value">
                      {entry.duration_ms != null ? `${entry.duration_ms} ms` : '—'}
                    </span>
                  </div>
                  <div className="api-log-metric">
                    <span className="api-log-metric-label">total tokens</span>
                    <span className="api-log-metric-value">
                      {entry.usage?.total_tokens != null
                        ? entry.usage.total_tokens.toLocaleString()
                        : '—'}
                    </span>
                  </div>
                </div>

                <pre className="api-log-json">{JSON.stringify(entry, null, 2)}</pre>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
