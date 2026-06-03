import { useState, useEffect, useRef } from 'react'
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

type ActionType = 'standard' | 'move' | 'full' | 'swift' | 'free'

// Ordering used when building the hints array: primary first, move second, swift/free last.
const ACTION_BUTTON_ORDER: ActionType[] = ['standard', 'full', 'move', 'swift', 'free']

// Feature flag — set to true to re-enable action-type selection buttons.
const ENABLE_ACTION_TYPES = false

interface ActionButtonDef {
  type: ActionType
  label: string
  title: string
  /** Types that must be deselected when this button is selected. */
  exclusive?: ActionType[]
}

const ACTION_BUTTONS: ActionButtonDef[] = [
  { type: 'standard', label: 'Standard',   title: 'Standard Action (attack, cast, use ability)', exclusive: ['full'] },
  { type: 'move',     label: 'Move',        title: 'Move Action (movement, stand up, draw weapon)', exclusive: ['full'] },
  { type: 'full',     label: 'Full-Round',  title: 'Full-Round Action (full attack, charge, run)', exclusive: ['standard', 'move'] },
  { type: 'swift',    label: 'Swift',       title: 'Swift Action (one per turn; quickened spell, swift aid, etc.)' },
  { type: 'free',     label: 'Free',        title: 'Free Action (speak, drop item, etc.)' },
]

interface Props {
  onSend: (input: string, actionTypeHints: ActionType[]) => void
  onEnemyTurn?: () => void
  disabled: boolean
  activeSpeaker?: ActiveSpeaker | null
  combatWeapons?: string[]  // shown as a hint strip when it's a PC's combat turn
  inPcCombatTurn?: boolean  // show action-type buttons when true
  availableZones?: string[] // zone names to show as chips when Move is selected
}

export default function InputBar({ onSend, onEnemyTurn, disabled, activeSpeaker = null, combatWeapons, inPcCombatTurn = false, availableZones }: Props) {
  const [value, setValue] = useState('')
  const [selectedActions, setSelectedActions] = useState<Set<ActionType>>(new Set())
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isEnemy = activeSpeaker?.isEnemy ?? false

  // Reset all action selections when the turn changes to a new actor
  useEffect(() => {
    setSelectedActions(new Set())
  }, [activeSpeaker?.name])

  const toggleAction = (type: ActionType) => {
    setSelectedActions(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        // Remove mutually exclusive types before adding
        const excl = ACTION_BUTTONS.find(b => b.type === type)?.exclusive ?? []
        excl.forEach(e => next.delete(e as ActionType))
        next.add(type)
      }
      return next
    })
  }

  /** Build the ordered hints array from the current selection. */
  const buildHints = (): ActionType[] =>
    ACTION_BUTTON_ORDER.filter(t => selectedActions.has(t))

  const submit = () => {
    if (isEnemy) return  // enemy turn: Enter does nothing; use the Enemy Turn button
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed, buildHints())
    setValue('')
    setSelectedActions(new Set())
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
        {ENABLE_ACTION_TYPES && inPcCombatTurn && !isEnemy && (
          <div className="action-type-row">
            {ACTION_BUTTONS.map(({ type, label, title }) => (
              <button
                key={type}
                className={`btn btn-action-type${selectedActions.has(type) ? ' active' : ''}`}
                onClick={() => toggleAction(type)}
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
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className="input-area"
          rows={2}
          autoFocus
        />
        {ENABLE_ACTION_TYPES && inPcCombatTurn && !isEnemy && selectedActions.has('move') && availableZones && availableZones.length > 0 && (
          <div className="zone-chips">
            <span className="zone-chips-label">Zones:</span>
            {availableZones.map(zone => (
              <button
                key={zone}
                type="button"
                className="btn-zone-chip"
                disabled={disabled}
                onClick={() => {
                  setValue(prev => prev ? `${prev.trimEnd()} ${zone}` : zone)
                  textareaRef.current?.focus()
                }}
              >
                {zone}
              </button>
            ))}
          </div>
        )}
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
