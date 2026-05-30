import { useState, useEffect } from 'react'
import type { BenchmarkRow } from '../api'
import { fetchBenchmarks } from '../api'

const SERIES = [
  { key: 'prompt_tokens'     as const, label: 'prompt',     color: '#4a9068' },
  { key: 'completion_tokens' as const, label: 'completion', color: '#c9a84c' },
  { key: 'total_tokens'      as const, label: 'total',      color: '#c06060' },
]

const TURN_LABELS: Record<number, string> = {
  1: 'Turn 1 — Swallowtail Festival',
  2: 'Turn 2 — Convince Hemlock',
  3: 'Turn 3 — Rusty Dragon',
}

interface ChartProps {
  rows: BenchmarkRow[]
  title: string
}

function LineChart({ rows, title }: ChartProps) {
  if (rows.length === 0) {
    return (
      <div className="bm-chart">
        <div className="bm-chart-title">{title}</div>
        <div className="bm-chart-no-data">No data yet</div>
      </div>
    )
  }

  const W = 360, H = 200
  const PAD = { top: 12, right: 12, bottom: 28, left: 52 }
  const iW = W - PAD.left - PAD.right
  const iH = H - PAD.top - PAD.bottom

  const allVals = SERIES.flatMap(s => rows.map(r => Number(r[s.key]) || 0))
  const maxVal = Math.max(...allVals, 1)

  const xOf = (i: number) =>
    rows.length === 1 ? iW / 2 : (i / (rows.length - 1)) * iW
  const yOf = (v: number) => iH - (v / maxVal) * iH

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(t => ({
    y: iH - t * iH,
    label: Math.round(t * maxVal).toLocaleString(),
  }))

  return (
    <div className="bm-chart">
      <div className="bm-chart-title">{title}</div>
      <svg viewBox={`0 0 ${W} ${H}`} className="bm-chart-svg">
        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {yTicks.map((t, i) => (
            <g key={i}>
              <line x1={0} y1={t.y} x2={iW} y2={t.y} stroke="#2a2010" strokeWidth={1} />
              <text x={-4} y={t.y + 4} textAnchor="end" fontSize={9} fill="#7a6a50">
                {t.label}
              </text>
            </g>
          ))}

          {SERIES.map(s => {
            const pts = rows
              .map((r, i) => `${xOf(i)},${yOf(Number(r[s.key]) || 0)}`)
              .join(' ')
            return (
              <polyline
                key={s.key}
                points={pts}
                fill="none"
                stroke={s.color}
                strokeWidth={1.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            )
          })}

          {SERIES.map(s =>
            rows.map((r, i) => (
              <circle
                key={`${s.key}-${i}`}
                cx={xOf(i)}
                cy={yOf(Number(r[s.key]) || 0)}
                r={2.5}
                fill={s.color}
              />
            ))
          )}

          {rows.map((_, i) => (
            <text
              key={i}
              x={xOf(i)}
              y={iH + 16}
              textAnchor="middle"
              fontSize={9}
              fill="#7a6a50"
            >
              {i + 1}
            </text>
          ))}
        </g>
      </svg>

      <div className="bm-chart-legend">
        {SERIES.map(s => (
          <span key={s.key} className="bm-legend-item">
            <span className="bm-legend-dot" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  )
}

interface Props {
  onClose: () => void
}

export default function TokenBenchmarks({ onClose }: Props) {
  const [rows, setRows] = useState<BenchmarkRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchBenchmarks()
      .then(data => setRows([...data].reverse()))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  // Chronological order for charts (oldest first)
  const byTurn = (turn: number) =>
    [...rows].reverse().filter(r => Number(r.turn) === turn)

  return (
    <div className="sheet-overlay bm-overlay" onClick={handleBackdrop}>
      <div className="bm-panel">
        <button className="sheet-close" onClick={onClose} title="Close (Esc)">✕</button>
        <h2 className="bm-title">Token Benchmarks</h2>
        <p className="bm-subtitle">
          Run <code>pytest tests/test_token_benchmark.py</code> to add data points.
        </p>

        {loading && <p className="api-log-empty">Loading…</p>}
        {error && <p className="api-log-empty api-log-empty--err">{error}</p>}

        {!loading && !error && rows.length === 0 && (
          <p className="api-log-empty">No benchmark data yet.</p>
        )}

        {!loading && !error && rows.length > 0 && (
          <>
            <div className="bm-table-wrap">
              <table className="bm-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Provider / Model</th>
                    <th>Session</th>
                    <th>Turn</th>
                    <th>Prompt</th>
                    <th>Completion</th>
                    <th>Total</th>
                    <th>Sys chars</th>
                    <th>Log</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className={`bm-row bm-row--t${r.turn}`}>
                      <td className="bm-ts">{r.timestamp.replace('T', ' ')}</td>
                      <td className="bm-model">{r.provider} / {r.model}</td>
                      <td><code className="bm-session">{r.session}</code></td>
                      <td className="bm-turn-cell">{r.turn}</td>
                      <td className="bm-num">{Number(r.prompt_tokens).toLocaleString()}</td>
                      <td className="bm-num">{Number(r.completion_tokens).toLocaleString()}</td>
                      <td className="bm-num bm-total">{Number(r.total_tokens).toLocaleString()}</td>
                      <td className="bm-num">{Number(r.system_chars).toLocaleString()}</td>
                      <td>
                        {r.log_file
                          ? (
                            <a
                              href={`/api/log/api/${encodeURIComponent(r.log_file)}`}
                              target="_blank"
                              rel="noreferrer"
                              className="bm-log-link"
                            >
                              view
                            </a>
                          )
                          : <span className="bm-log-link bm-log-none">—</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bm-charts">
              {([1, 2, 3] as const).map(t => (
                <LineChart key={t} rows={byTurn(t)} title={TURN_LABELS[t]} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
