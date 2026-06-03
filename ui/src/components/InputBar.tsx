import { useState, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import type { ActiveSpeaker } from '../types'

// ── Taunting placeholders for enemy turns ────────────────────────────────────
// Chosen deterministically by enemy name so the same enemy always shows the
// same phrase (no randomness = no flicker on re-render).
const ENEMY_TAUNTS = [
  'The enemy acts…',
  'Steel your nerve.',
  'Your foe advances.',
  'Make your move.',
  'Danger looms.',
]

function enemyTaunt(name: string): string {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return ENEMY_TAUNTS[h % ENEMY_TAUNTS.length]
}

// ── Skull icon (inline SVG — no asset dependency) ────────────────────────────
function SkullIcon() {
  return (
    <svg
      className="speaker-skull"
      aria-label="enemy"
      role="img"
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* skull dome */}
      <path d="M10 2a6 6 0 0 0-6 6c0 2.1 1.1 3.9 2.7 5H6v1.5A1.5 1.5 0 0 0 7.5 16h5a1.5 1.5 0 0 0 1.5-1.5V13h-.7A6 6 0 0 0 10 2z" />
      {/* eye sockets */}
      <circle cx="8" cy="9" r="1.2" fill="var(--hostile-bg, #1a0a0a)" />
      <circle cx="12" cy="9" r="1.2" fill="var(--hostile-bg, #1a0a0a)" />
      {/* teeth gaps */}
      <rect x="8.2" y="14.5" width="1" height="1.2" fill="var(--hostile-bg, #1a0a0a)" rx="0.2" />
      <rect x="10.8" y="14.5" width="1" height="1.2" fill="var(--hostile-bg, #1a0a0a)" rx="0.2" />
    </svg>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

type ActionType = 'standard' | 'move' | 'full'

const ACTION_BUTTONS: { type: ActionType; label: string; title: string }[] = [
  { type: 'standard', label: 'Standard',  title: 'Standard Action (attack, cast, use ability)' },
  { type: 'move',     label: 'Move',      title: 'Move Action (movement, stand up, draw weapon)' },
  { type: 'full',     label: 'Full-Round', title: 'Full-Round Action (full attack, charge, run)' },
]

interface Props {
  onSend: (input: string, actionTypeHint?: string) => void
  onEnemyTurn?: () => void
  disabled: boolean
  activeSpeaker?: ActiveSpeaker | null
  combatWeapons?: string[]  // shown as a hint strip when it's a PC's combat turn
  inPcCombatTurn?: boolean  // show action-type buttons when true
}

export default function InputBar({ onSend, onEnemyTurn, disabled, activeSpeaker = null, combatWeapons, inPcCombatTurn = false }: Props) {
  const [value, setValue] = useState('')
  const [actionType, setActionType] = useState<ActionType | null>(null)

  const isEnemy = activeSpeaker?.isEnemy ?? false

  // Reset selected action type when the turn changes to a new actor
  useEffect(() => {
    setActionType(null)
  }, [activeSpeaker?.name])

  const submit = () => {
    if (isEnemy) return  // enemy turn: Enter does nothing; use the Enemy Turn button
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    if (actionType) {
      onSend(trimmed, actionType)
    } else {
      onSend(trimmed)
    }
    setValue('')
    setActionType(null)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const placeholder = isEnemy
    ? enemyTaunt(activeSpeaker?.name ?? '')
    : 'What do you do?  (Enter to send · Shift+Enter for newline)'

  return (
    <div className={`input-bar${isEnemy ? ' hostile' : ''}`}>
      <div className="input-main">
        {inPcCombatTurn && !isEnemy && (
          <div className="action-type-row">
            {ACTION_BUTTONS.map(({ type, label, title }) => (
              <button
                key={type}
                className={`btn btn-action-type${actionType === type ? ' active' : ''}`}
                onClick={() => setActionType(prev => prev === type ? null : type)}
                disabled={disabled}
                title={title}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        )}
        {activeSpeaker && (
          <div
            className="speaker-badge"
            style={{ '--speaker-color': activeSpeaker.color } as React.CSSProperties}
          >
            {isEnemy ? (
              <SkullIcon />
            ) : (
              <span className="speaker-badge-rune" aria-hidden="true">{activeSpeaker.rune}</span>
            )}
            <span className="speaker-badge-label">
              {isEnemy
                ? <strong>{activeSpeaker.name}</strong>
                : <>Speaking as <strong>{activeSpeaker.name}</strong></>}
            </span>
          </div>
        )}
        <textarea
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className="input-area"
          rows={2}
          autoFocus
        />
      </div>
      {isEnemy && onEnemyTurn ? (
        <button
          onClick={onEnemyTurn}
          disabled={disabled}
          className="btn btn-send btn-enemy-turn"
        >
          {disabled ? '…' : 'Enemy Turn'}
        </button>
      ) : (
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="btn btn-send"
        >
          {disabled ? '…' : 'Send'}
        </button>
      )}
      {combatWeapons && combatWeapons.length > 0 && (
        <div className="combat-weapons-hint" title="Available weapons for intent extraction">
          ⚔ {combatWeapons.join(' · ')}
        </div>
      )}
    </div>
  )
}
