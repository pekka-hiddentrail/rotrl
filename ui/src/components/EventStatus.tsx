import { useState, useEffect, useCallback } from 'react'
import type { EventStatusData, WarmEventData } from '../api'
import { fetchEventStatus } from '../api'

const SCHEDULER_DEFAULT_TTL = 5

interface Props {
  onClose: () => void
  sessionId: string
}

function badge(label: string, color: string) {
  return (
    <span className={`es-badge es-badge--${color}`}>{label}</span>
  )
}

function eventStatus(
  eid: string,
  we: WarmEventData,
  activeId: string | null,
  completed: string[],
): React.ReactNode {
  if (eid === activeId)          return badge('ACTIVE', 'active')
  if (completed.includes(eid))   return badge('DONE', 'done')
  if (we.readiness >= we.threshold) return badge('ELIGIBLE', 'eligible')
  if (we.frozen)                 return badge('FROZEN', 'frozen')
  return badge('WARMING', 'warming')
}

function ReadinessBar({ we, isActive }: { we: WarmEventData; isActive: boolean }) {
  const pct = Math.min(100, we.readiness)
  const atThreshold = we.readiness >= we.threshold
  const colorClass = isActive ? 'active' : atThreshold ? 'eligible' : we.frozen ? 'frozen' : 'warming'
  const thresholdPos = Math.min(100, we.threshold)

  return (
    <div className="es-bar-wrap" title={`${we.readiness.toFixed(1)} / 100`}>
      <div className={`es-bar-fill es-bar-fill--${colorClass}`} style={{ width: `${pct}%` }} />
      <div className="es-bar-threshold" style={{ left: `${thresholdPos}%` }} title={`Threshold: ${we.threshold}`} />
      <span className="es-bar-label">{we.readiness.toFixed(1)}</span>
    </div>
  )
}

function TtlBar({ turnsRemaining }: { turnsRemaining: number }) {
  const pct = Math.max(0, Math.min(100, (turnsRemaining / SCHEDULER_DEFAULT_TTL) * 100))
  const colorClass = pct > 60 ? 'high' : pct > 30 ? 'mid' : 'low'
  return (
    <div className="es-bar-wrap es-ttl-bar" title={`${turnsRemaining} turns remaining`}>
      <div className={`es-bar-fill es-bar-fill--ttl-${colorClass}`} style={{ width: `${pct}%` }} />
      <span className="es-bar-label">{turnsRemaining} turn{turnsRemaining !== 1 ? 's' : ''}</span>
    </div>
  )
}

export default function EventStatus({ onClose, sessionId }: Props) {
  const [data, setData]       = useState<EventStatusData | null>(null)
  const [error, setError]     = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const refresh = useCallback(() => {
    fetchEventStatus(sessionId)
      .then(d => { setData(d); setError(null) })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [sessionId])

  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(refresh, 3000)
    return () => clearInterval(id)
  }, [autoRefresh, refresh])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  const warmEntries = data
    ? Object.entries(data.warm_events).filter(([eid]) => !data.completed_events.includes(eid))
    : []

  const activeWarm = data?.active_event_id
    ? data.warm_events[data.active_event_id]
    : null

  return (
    <div className="sheet-overlay es-overlay" onClick={handleBackdrop}>
      <div className="es-panel">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="es-header">
          <h2 className="es-title">Event Scheduler Status</h2>
          <div className="es-header-right">
            {data && (
              <>
                <span className={`es-badge es-badge--${data.scheduler_enabled ? 'active' : 'done'}`}>
                  Scheduler {data.scheduler_enabled ? 'ON' : 'OFF'}
                </span>
                <span className="es-turn-badge">Turn {data.turn_number}</span>
              </>
            )}
            <label className="es-auto-label" title="Auto-refresh every 3 s">
              <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
              Auto
            </label>
            <button className="es-refresh-btn" onClick={refresh} title="Refresh now">↺</button>
          </div>
          <button className="sheet-close" onClick={onClose} title="Close (Esc)">✕</button>
        </div>

        {/* ── Loading / error ─────────────────────────────────────────── */}
        {loading && <p className="es-loading">Loading…</p>}
        {error   && <p className="es-error">{error}</p>}

        {data && (
          <>
            {/* ── Active Event ──────────────────────────────────────── */}
            {data.active_event_id && activeWarm ? (
              <div className="es-active-card">
                <div className="es-active-header">
                  <span className="es-active-label">ACTIVE EVENT</span>
                  <span className="es-active-id">{data.active_event_id}</span>
                </div>
                <div className="es-active-body">
                  <div className="es-active-row">
                    <span className="es-active-key">TTL</span>
                    <TtlBar turnsRemaining={activeWarm.turns_remaining} />
                  </div>
                  <div className="es-active-row">
                    <span className="es-active-key">Readiness at trigger</span>
                    <span className="es-active-val">{activeWarm.readiness.toFixed(1)}</span>
                  </div>
                  <div className="es-active-row">
                    <span className="es-active-key">Zones</span>
                    <span className="es-active-val">{activeWarm.zones.join(', ') || '—'}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="es-no-active">No active event</div>
            )}

            {/* ── Warm Events Table ─────────────────────────────────── */}
            {warmEntries.length > 0 ? (
              <div className="es-section">
                <div className="es-section-title">Warming Events</div>
                <table className="es-table">
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>Readiness</th>
                      <th className="es-th-num">Threshold</th>
                      <th className="es-th-num">Gap</th>
                      <th>Status</th>
                      <th className="es-th-num">Failed</th>
                      <th>Zones</th>
                      <th>Gains</th>
                    </tr>
                  </thead>
                  <tbody>
                    {warmEntries.map(([eid, we]) => {
                      const gap = Math.max(0, we.threshold - we.readiness)
                      const isActive = eid === data.active_event_id
                      const gains = Object.entries(we.action_gain_map)
                        .map(([k, v]) => `${k}:+${v}`)
                        .join(' ')
                      return (
                        <tr key={eid} className={isActive ? 'es-row--active' : ''}>
                          <td className="es-td-id">{eid}</td>
                          <td className="es-td-bar">
                            <ReadinessBar we={we} isActive={isActive} />
                          </td>
                          <td className="es-td-num">{we.threshold}</td>
                          <td className="es-td-num">{gap > 0 ? gap.toFixed(1) : '—'}</td>
                          <td>{eventStatus(eid, we, data.active_event_id, data.completed_events)}</td>
                          <td className="es-td-num">{we.failed_rolls > 0 ? we.failed_rolls : '—'}</td>
                          <td className="es-td-zones">{we.zones.join(', ') || '—'}</td>
                          <td className="es-td-gains">
                            <span className="es-gain-base" title="Base gain per matched zone turn">
                              base: +{we.base_gain}
                            </span>
                            {gains && <span className="es-gain-actions">{gains}</span>}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="es-section">
                <div className="es-section-title">Warming Events</div>
                <div className="es-empty">No warm events loaded. Is the Scheduler checkbox enabled at boot?</div>
              </div>
            )}

            {/* ── Completed Events ──────────────────────────────────── */}
            {data.completed_events.length > 0 && (
              <div className="es-section">
                <div className="es-section-title">Completed</div>
                <div className="es-completed-list">
                  {data.completed_events.map(eid => (
                    <span key={eid} className="es-completed-item">{eid}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
