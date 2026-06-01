import type { AttackPhase, CombatState } from '../types'
import HpBar from './HpBar'

interface Props {
  combatState: CombatState
  disabled?: boolean
  currentCombatantName?: string | null
  attackPhase?: AttackPhase
  enemyTurnStreaming?: boolean
  combatClosing?: boolean
  onRollInitiatives?: () => void
  onAdvanceTurn?: () => void
  onEnemyTurn?: () => void
  onEndCombat: () => void
}

const STATUS_LABEL: Record<string, string> = {
  unconscious: 'KO',
  fled:        'fled',
  dead:        'dead',
}

const CONDITION_TOOLTIPS: Record<string, string> = {
  prone:      'Prone: -4 melee attack; ranged attackers within 30 ft get -4; melee attackers get +4',
  grappled:   'Grappled: no movement; -4 Dex; can attempt to break free (Escape Artist or CMB)',
  pinned:     'Pinned: helpless; can only attempt to break free; +4 to attacks against you',
  blinded:    'Blinded: -2 AC; loses Dex bonus; -4 on most Str/Dex checks; 50% miss chance',
  deafened:   'Deafened: -4 initiative; 20% spell failure (verbal); cannot hear anything',
  shaken:     'Shaken: -2 attack rolls, saving throws, skill and ability checks',
  frightened: 'Frightened: -2 attack/saves/checks; must flee from source of fear if possible',
  panicked:   'Panicked: -2 attack/saves/checks; drops held items; flees at max speed',
  sickened:   'Sickened: -2 attack rolls, weapon damage, saving throws, skill and ability checks',
  nauseated:  'Nauseated: can only take a single move action per turn; no attacks or spells',
  dazed:      'Dazed: can take no actions; +2 AC (counts as standing still)',
  stunned:    'Stunned: drops everything; -2 AC; loses Dex bonus; attackers get +2',
  entangled:  'Entangled: -2 attack; -4 Dex; must make concentration check (DC 15) to cast',
  paralyzed:  'Paralyzed: Str and Dex drop to 0; helpless; subject to coup de grace',
  helpless:   'Helpless: Dex 0; subject to coup de grace; melee attackers get +4',
  fatigued:   'Fatigued: -2 Str and Dex; cannot charge or run; becomes exhausted on fatigue',
  exhausted:  'Exhausted: -6 Str and Dex; move at half speed; becomes fatigued after rest',
}

export default function CombatPanel({
  combatState,
  disabled,
  currentCombatantName,
  attackPhase,
  enemyTurnStreaming,
  combatClosing,
  onRollInitiatives,
  onAdvanceTurn,
  onEnemyTurn,
  onEndCombat,
}: Props) {
  const sorted = [...combatState.combatants].sort((a, b) => b.initiative - a.initiative)
  const effectiveCurrent = currentCombatantName ?? sorted.find(c => c.status === 'active')?.name ?? null
  const controlsDisabled = Boolean(disabled || enemyTurnStreaming || combatClosing)
  const enemyTurnDisabled = Boolean(controlsDisabled || attackPhase)
  const phase = enemyTurnStreaming ? 'Enemy Turn' : attackPhase ? 'PC Attacks' : null
  const showRound = combatState.round >= 1  // round < 1 = initiative not yet rolled (pending state)

  return (
    <aside className="combat-panel">
      <div className="combat-panel-header">
        <span className="combat-panel-title">⚔ Combat</span>
        <div className="combat-panel-badges">
          {phase && (
            <span className={`combat-phase-badge ${enemyTurnStreaming ? 'enemy' : 'pc'}`}>
              {phase}
            </span>
          )}
          {showRound && <span className="combat-round-badge">Round {combatState.round}</span>}
          {onRollInitiatives && (
            <button
              className="btn btn-secondary btn-xs combat-roll-init-btn"
              onClick={onRollInitiatives}
              disabled={Boolean(controlsDisabled || attackPhase)}
              title="Roll d20 + modifier for each combatant and re-sort initiative"
            >
              🎲 Roll Initiatives
            </button>
          )}
        </div>
      </div>

      <div className="combat-initiative-list">
        {sorted.map(c => {
          const isActive = c.status === 'active'
          const isCurrent = isActive && c.name === effectiveCurrent
          return (
            <div
              key={c.name}
              className={[
                'combatant-row',
                isCurrent        ? 'combatant-current'  : '',
                !isActive        ? 'combatant-inactive' : '',
                c.status === 'dead' ? 'combatant-dead'  : '',
              ].filter(Boolean).join(' ')}
            >
              <div className="combatant-name-row">
                <span className="combatant-name">{c.name}</span>
                <span className="combatant-meta">
                  <span className="combatant-init" title="Initiative">⚡ Init {c.initiative}</span>
                  <span className="combatant-ac" title="Armour Class">🛡 AC {c.ac}</span>
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
              {c.conditions && c.conditions.length > 0 && (
                <div className="combatant-conditions">
                  {c.conditions.map(cond => (
                    <span key={cond} className="condition-chip" title={CONDITION_TOOLTIPS[cond] ?? cond}>
                      {cond}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button
        className="btn btn-secondary btn-sm combat-end-btn"
        onClick={onAdvanceTurn}
        disabled={controlsDisabled}
        title="Advance the active-turn highlight to the next combatant"
      >
        Next Turn →
      </button>
      {onEnemyTurn && (
        <button
          className="btn btn-secondary btn-sm combat-end-btn combat-enemy-turn-btn"
          onClick={onEnemyTurn}
          disabled={enemyTurnDisabled}
          title="Run the current enemy actor through a focused backend-mediated turn"
        >
          {enemyTurnStreaming ? 'Enemy Acting...' : 'Enemy Turn'}
        </button>
      )}
      <button
        className="btn btn-secondary btn-sm combat-end-btn"
        onClick={onEndCombat}
        disabled={controlsDisabled}
        title="Narrate combat closure and clear the combat tracker"
      >
        {combatClosing ? 'Closing...' : 'End Combat'}
      </button>
    </aside>
  )
}
