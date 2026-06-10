import type { LocationZonesData, LocationAccessPointData } from '../api'

interface Props {
  zonesData: LocationZonesData
  actorId: string                          // "party" or slugified combatant name
  onActorChange: (id: string) => void
  onMove: (accessPointId: string) => void
  movePending: boolean
  collapsed: boolean
  onCollapse: (c: boolean) => void
}

const STATE_LABEL: Record<string, string> = {
  locked:  'Locked',
  blocked: 'Blocked',
}

export default function LocationZonesPanel({
  zonesData,
  actorId,
  onActorChange,
  onMove,
  movePending,
  collapsed,
  onCollapse,
}: Props) {
  const { current_location, current_zone_id, zones, access_points, occupants, available_moves } = zonesData

  // Build reachable zone ids from current zone (open APs only — available_moves already filtered)
  const reachableZoneIds = new Set(available_moves.map(m => m.to_zone_id))

  // Locked/blocked APs from the current zone (for LZ-009)
  const restrictedMoves: LocationAccessPointData[] = access_points.filter(ap => {
    if (ap.state === 'open' || ap.state === 'hidden') return false
    return ap.from === current_zone_id || (ap.bidirectional && ap.to === current_zone_id)
  })

  // Occupants grouped by zone id
  const occupantsByZone: Record<string, string[]> = {}
  for (const occ of occupants) {
    occupantsByZone[occ.zone_id] = [...(occupantsByZone[occ.zone_id] ?? []), occ.label]
  }

  const currentZone = zones.find(z => z.id === current_zone_id)
  const locationName = current_location?.name ?? current_location?.id ?? '—'

  return (
    <aside className={`location-zones-panel${collapsed ? ' location-zones-panel--collapsed' : ''}`}>
      <div className="lz-header">
        <span className="lz-title">📍 Zones</span>
        <span className="lz-location-name">{locationName}</span>
        <button
          className="lz-collapse-btn"
          onClick={() => onCollapse(!collapsed)}
          title={collapsed ? 'Expand zone panel' : 'Collapse zone panel'}
          aria-label={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '▶' : '◀'}
        </button>
      </div>

      {!collapsed && (
        <>
          {currentZone && (
            <div className="lz-current-zone">
              <div className="lz-current-zone-name">{currentZone.name}</div>
              {currentZone.description && (
                <div className="lz-current-zone-desc">{currentZone.description}</div>
              )}
            </div>
          )}

          <div className="lz-zone-list">
            {zones.filter(z => z.visible).map(z => {
              const isCurrent   = z.id === current_zone_id
              const isReachable = !isCurrent && reachableZoneIds.has(z.id)
              const occs        = occupantsByZone[z.id] ?? []
              return (
                <div
                  key={z.id}
                  className={[
                    'lz-zone-row',
                    isCurrent   ? 'lz-zone-current'   : '',
                    isReachable ? 'lz-zone-reachable'  : '',
                  ].filter(Boolean).join(' ')}
                >
                  <div className="lz-zone-row-main">
                    <span className="lz-zone-row-name">{z.name}</span>
                    {isReachable && <span className="lz-reachable-marker" title="Reachable from here">→</span>}
                    {z.tags.length > 0 && (
                      <span className="lz-zone-tags">
                        {z.tags.map(t => <span key={t} className="lz-tag">{t}</span>)}
                      </span>
                    )}
                  </div>
                  {occs.length > 0 && (
                    <div className="lz-zone-occupants">
                      {occs.map(label => {
                        const isActor = label.toLowerCase() === actorId.toLowerCase() ||
                          (actorId === 'party' && label.toLowerCase() === 'party')
                        return (
                          <span
                            key={label}
                            className={`lz-occupant${isActor ? ' lz-occupant-active' : ''}`}
                            onClick={() => onActorChange(label.toLowerCase())}
                            title={`Set ${label} as movement actor`}
                            style={{ cursor: 'pointer' }}
                          >
                            {label}
                          </span>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {(available_moves.length > 0 || restrictedMoves.length > 0) && (
            <div className="lz-moves">
              <div className="lz-moves-label">Move</div>
              {available_moves.map(m => {
                const destZone = zones.find(z => z.id === m.to_zone_id)
                const label    = destZone?.name ?? m.to_zone_id
                return (
                  <button
                    key={m.access_point_id}
                    className="btn btn-secondary btn-sm lz-move-btn"
                    onClick={() => onMove(m.access_point_id)}
                    disabled={movePending}
                    title={destZone?.description ?? label}
                  >
                    {label} →
                  </button>
                )
              })}
              {restrictedMoves.map(ap => {
                const stateLabel = STATE_LABEL[ap.state] ?? ap.state
                const hint = ap.requirements && ap.requirements !== '-'
                  ? `${stateLabel}: ${ap.requirements}`
                  : stateLabel
                const destId   = ap.from === current_zone_id ? ap.to : ap.from
                const destZone = zones.find(z => z.id === destId)
                const label    = destZone?.name ?? destId
                return (
                  <button
                    key={ap.id}
                    className="btn btn-secondary btn-sm lz-move-btn lz-move-btn--restricted"
                    disabled
                    title={hint}
                  >
                    {label} ({stateLabel.toLowerCase()})
                  </button>
                )
              })}
            </div>
          )}
        </>
      )}
    </aside>
  )
}
