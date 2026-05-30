import type { CombatState } from '../types'
import HpBar from './HpBar'

interface Props {
  combatState: CombatState
  disabled?: boolean
  onEndCombat: () => void
}

const STATUS_LABEL: Record<string, string> = {
  unconscious: 'KO',
  fled:        'fled',
  dead:        'dead',
}

export default function CombatPanel({ combatState, disabled, onEndCombat }: Props) {
  const sorted = [...combatState.combatants].sort((a, b) => b.initiative - a.initiative)

  return (
    <aside className="combat-panel">
      <div className="combat-panel-header">
        <span className="combat-panel-title">⚔ Combat</span>
        <span className="combat-round-badge">Round {combatState.round}</span>
      </div>

      <div className="combat-initiative-list">
        {sorted.map((c, i) => {
          const isActive = c.status === 'active'
          const isCurrent = i === 0 && isActive
          return (
            <div
              key={c.name}
              className={[
                'combatant-row',
                isCurrent ? 'combatant-current' : '',
                !isActive  ? 'combatant-inactive' : '',
              ].filter(Boolean).join(' ')}
            >
              <div className="combatant-name-row">
                <span className="combatant-name">{c.name}</span>
                <span className="combatant-meta">
                  <span className="combatant-init" title="Initiative">⚡{c.initiative}</span>
                  <span className="combatant-ac"  title="Armour Class">🛡{c.ac}</span>
                </span>
              </div>
              <div className="combatant-hp-row">
                <HpBar current={c.hp_current} max={c.hp_max} />
                {!isActive && (
                  <span className={`status-badge status-${c.status}`}>
                    {STATUS_LABEL[c.status] ?? c.status}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <button
        className="btn btn-secondary btn-sm combat-end-btn"
        onClick={onEndCombat}
        disabled={disabled}
        title="Clear the combat tracker (no mechanical effect)"
      >
        End Combat
      </button>
    </aside>
  )
}
