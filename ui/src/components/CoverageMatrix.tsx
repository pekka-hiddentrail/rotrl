/**
 * CoverageMatrix — two-tab coverage panel.
 *
 * Tab 1 "Feature ACs": maps each spec AC to the test file(s) that cover it.
 *   Data: GET /api/coverage (outputs/coverage.json — built by scripts/build_coverage.py)
 *
 * Tab 2 "Code Lines": per-file pytest-cov line coverage with inline bar chart.
 *   Data: GET /api/code-coverage (outputs/code_coverage.json — built by pytest --cov --cov-report=json)
 *
 * Spec: specs/coverage-matrix.feature
 */
import { useState, useEffect } from 'react'
import type { CoverageData, CodeCoverageData } from '../api'
import { fetchCoverage, fetchCodeCoverage } from '../api'

// ── Helpers ───────────────────────────────────────────────────────────────────

function TestPill({ name, suite }: { name: string; suite: 'pytest' | 'vitest' | 'playwright' | 'exploratory' }) {
  const label = name
    .replace(/\.spec\.tsx?$/, '')
    .replace(/\.test\.tsx?$/, '')
    .replace(/\.py$/, '')
    .replace(/\.md$/, '')
    .replace(/^test_/, '')
    .replace(/^explore_/, '')
  return (
    <span className={`cm-pill cm-pill--${suite}`} title={name}>
      {label.length > 24 ? `${label.slice(0, 22)}…` : label}
    </span>
  )
}

function coverageTier(covered: number, total: number): 'full' | 'high' | 'mid' | 'low' | 'empty' {
  if (total === 0) return 'empty'
  const pct = covered / total
  if (pct >= 1.0) return 'full'
  if (pct >= 0.7) return 'high'
  if (pct >= 0.4) return 'mid'
  return 'low'
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  onClose: () => void
}

export default function CoverageMatrix({ onClose }: Props) {
  const [tab, setTab] = useState<'features' | 'code'>('features')

  // Feature AC state
  const [data,          setData]          = useState<CoverageData | null>(null)
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState<string | null>(null)
  const [gapsOnly,         setGapsOnly]         = useState(false)
  const [expandedFeatures, setExpandedFeatures] = useState<Set<string>>(new Set())

  // Code coverage state — loaded lazily on first tab activation
  const [ccData,    setCcData]    = useState<CodeCoverageData | null>(null)
  const [ccLoading, setCcLoading] = useState(false)
  const [ccError,   setCcError]   = useState<string | null>(null)

  useEffect(() => {
    fetchCoverage()
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (tab !== 'code' || ccData !== null || ccLoading) return
    setCcLoading(true)
    fetchCodeCoverage()
      .then(setCcData)
      .catch(e => setCcError(String(e)))
      .finally(() => setCcLoading(false))
  }, [tab, ccData, ccLoading])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  const toggleFeature = (fid: string) => {
    setExpandedFeatures(prev => {
      const next = new Set(prev)
      if (next.has(fid)) next.delete(fid); else next.add(fid)
      return next
    })
  }

  const featureGroups = data
    ? [...new Set(data.rows.map(r => r.feature_id))].sort().map(fid => {
        const allRows = data.rows.filter(r => r.feature_id === fid)
        const covered = allRows.filter(r => r.status === 'covered').length
        return {
          fid,
          allRows,
          covered,
          total: allRows.length,
          visibleRows: gapsOnly ? allRows.filter(r => r.status === 'gap') : allRows,
        }
      }).filter(g => !gapsOnly || g.covered < g.total)
    : []

  const generatedLabel = data?.generated
    ? data.generated.replace('T', ' ').replace('+00:00', ' UTC').slice(0, 22) + ' UTC'
    : null

  const ccGeneratedLabel = ccData?.generated
    ? ccData.generated.replace('T', ' ').slice(0, 19)
    : null

  return (
    <div className="sheet-overlay cm-overlay" onClick={handleBackdrop}>
      <div className="cm-panel">
        <button className="sheet-close" onClick={onClose} title="Close (Esc)">✕</button>

        <h2 className="cm-title">Coverage</h2>

        {/* ── Tab bar ─────────────────────────────────────────────────────── */}
        <div className="cm-tabs">
          <button
            className={`cm-tab${tab === 'features' ? ' cm-tab--active' : ''}`}
            onClick={() => setTab('features')}
          >
            Feature ACs
          </button>
          <button
            className={`cm-tab${tab === 'code' ? ' cm-tab--active' : ''}`}
            onClick={() => setTab('code')}
          >
            Code Lines
          </button>
        </div>

        {/* ── Feature ACs tab ─────────────────────────────────────────────── */}
        {tab === 'features' && (
          <>
            <p className="cm-subtitle">
              Run <code>python scripts/build_coverage.py</code> to refresh.
              {generatedLabel && <span className="cm-generated"> · Built {generatedLabel}</span>}
            </p>

            {loading && <p className="api-log-empty">Loading…</p>}
            {error   && <p className="api-log-empty api-log-empty--err">{error}</p>}

            {!loading && !error && data && (
              <>
                <div className="cm-summary">
                  <span className="cm-stat cm-stat--covered">{data.summary.covered} covered</span>
                  <span className="cm-stat-sep">/</span>
                  <span className="cm-stat">{data.summary.total} total ACs</span>
                  <span className="cm-stat cm-stat--gap">{data.summary.gap} gaps</span>
                </div>

                <div className="cm-filters">
                  <button
                    className={`cm-filter-btn${!gapsOnly ? ' active' : ''}`}
                    onClick={() => setGapsOnly(false)}
                  >
                    All
                  </button>
                  <button
                    className={`cm-filter-btn${gapsOnly ? ' active' : ''}`}
                    onClick={() => setGapsOnly(true)}
                  >
                    Gaps only
                  </button>
                  <button
                    className="cm-filter-btn"
                    onClick={() => setExpandedFeatures(new Set(featureGroups.map(g => g.fid)))}
                  >
                    Expand all
                  </button>
                  <button
                    className="cm-filter-btn"
                    onClick={() => setExpandedFeatures(new Set())}
                  >
                    Collapse all
                  </button>
                  <span className="cm-count">
                    {featureGroups.length} features
                    {' · '}
                    {featureGroups.reduce((s, g) => s + g.visibleRows.length, 0)} ACs
                  </span>
                </div>

                {data.summary.total === 0 ? (
                  <p className="api-log-empty">
                    No data — run <code>python scripts/build_coverage.py</code> first.
                  </p>
                ) : (
                  <div className="cm-table-wrap">
                    <table className="cm-table">
                      <thead>
                        <tr>
                          <th>AC</th>
                          <th>Title</th>
                          <th>pytest</th>
                          <th>Vitest</th>
                          <th>Playwright</th>
                          <th>Expl.</th>
                          <th title="Coverage status">●</th>
                        </tr>
                      </thead>
                      {featureGroups.map(g => {
                        const isOpen = expandedFeatures.has(g.fid)
                        const tier = coverageTier(g.covered, g.total)
                        return (
                          <tbody key={g.fid}>
                            <tr className="cm-feature-row" onClick={() => toggleFeature(g.fid)}>
                              <td colSpan={7} className="cm-feature-header-cell">
                                <div className="cm-feature-header-inner">
                                  <span className="cm-chevron">{isOpen ? '▾' : '▸'}</span>
                                  <span className="cm-feature-label">{g.fid}</span>
                                  <span className={`cm-badge cm-badge--${tier}`}>{g.covered}/{g.total}</span>
                                </div>
                              </td>
                            </tr>
                            {isOpen && g.visibleRows.map((r, i) => (
                              <tr key={i} className={`cm-row cm-row--${r.status}`}>
                                <td className="cm-ac-cell"><code>{r.ac_id}</code></td>
                                <td className="cm-title-cell">{r.title}</td>
                                <td className="cm-tests-cell">
                                  {r.pytest.map(n => <TestPill key={n} name={n} suite="pytest" />)}
                                </td>
                                <td className="cm-tests-cell">
                                  {r.vitest.map(n => <TestPill key={n} name={n} suite="vitest" />)}
                                </td>
                                <td className="cm-tests-cell">
                                  {r.playwright.map(n => <TestPill key={n} name={n} suite="playwright" />)}
                                </td>
                                <td className="cm-tests-cell">
                                  {r.exploratory.map(n => <TestPill key={n} name={n} suite="exploratory" />)}
                                </td>
                                <td className="cm-status-cell">
                                  <span className={`cm-dot cm-dot--${r.status}`} title={r.status} />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        )
                      })}
                    </table>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* ── Code Lines tab ──────────────────────────────────────────────── */}
        {tab === 'code' && (
          <>
            <p className="cm-subtitle">
              Run <code>pytest --cov --cov-report=json</code> to refresh.
              {ccGeneratedLabel && <span className="cm-generated"> · Built {ccGeneratedLabel}</span>}
            </p>

            {ccLoading && <p className="api-log-empty">Loading…</p>}
            {ccError   && <p className="api-log-empty api-log-empty--err">{ccError}</p>}

            {!ccLoading && !ccError && ccData && (
              ccData.files.length === 0 ? (
                <p className="api-log-empty">
                  No data — run <code>pytest --cov --cov-report=json</code> first.
                </p>
              ) : (
                <>
                  <div className="cm-summary">
                    <span className={`cm-stat ${ccData.total_pct >= 80 ? 'cm-stat--covered' : 'cm-stat--gap'}`}>
                      {ccData.total_pct}% total
                    </span>
                    <span className="cm-stat-sep">·</span>
                    <span className="cm-stat">
                      {ccData.total_stmts - ccData.total_miss} / {ccData.total_stmts} lines
                    </span>
                    <span className="cm-stat cm-stat--gap">{ccData.total_miss} uncovered</span>
                  </div>

                  <div className="cm-table-wrap">
                    <table className="cm-table cc-table">
                      <thead>
                        <tr>
                          <th>File</th>
                          <th className="cc-num-col">Stmts</th>
                          <th className="cc-num-col">Miss</th>
                          <th className="cc-num-col">%</th>
                          <th className="cc-bar-col"></th>
                          <th>Missing lines</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ccData.files.map((f, i) => {
                          const tier = f.pct >= 90 ? 'high' : f.pct >= 70 ? 'mid' : 'low'
                          const shown = f.missing_lines.slice(0, 15)
                          const extra = f.missing_lines.length - shown.length
                          const barColor = f.pct >= 90 ? '#4a9068' : f.pct >= 70 ? '#c9a84c' : '#c06060'
                          const dirPart = f.name.replace(/[^/]+$/, '').replace(/\/$/, '')
                          const filePart = f.name.split('/').pop()!
                          return (
                            <tr key={i} className={`cm-row cc-row--${tier}`}>
                              <td className="cc-file-cell" title={f.name}>
                                {filePart}
                                {dirPart && <span className="cc-file-dir"> {dirPart}</span>}
                              </td>
                              <td className="cc-num-col">{f.stmts}</td>
                              <td className="cc-num-col cc-miss">{f.miss || '—'}</td>
                              <td className={`cc-num-col cc-pct cc-pct--${tier}`}>{f.pct}%</td>
                              <td className="cc-bar-col">
                                <div className="cc-bar-wrap" title={`${f.pct}% covered`}>
                                  <div
                                    className="cc-bar-fill"
                                    style={{ width: `${f.pct}%`, background: barColor }}
                                  />
                                </div>
                              </td>
                              <td className="cc-lines-cell">
                                {shown.join(', ')}
                                {extra > 0 && <span className="cc-lines-more"> +{extra} more</span>}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              )
            )}
          </>
        )}
      </div>
    </div>
  )
}
