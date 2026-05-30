import { useState } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface RollRecord {
  id: number
  dice: number[]
  rolls: number[]
  rawTotal: number
  modifier: number | null   // skill modifier applied (null = no pending roll or no match)
  total: number             // rawTotal + (modifier ?? 0)
  modifierLabel: string | null  // e.g. "Perception +7"
  dc: number | null
  passed: boolean | null    // null until resolve_roll responds
  bonusNote: string | null  // shown when modifier cannot be applied
}

interface PendingRoll {
  skill: string
  dc: number
  success: string
  failure: string
}

interface ActiveSpeaker {
  name: string
  skills: { name: string; total: number }[]
}

interface Props {
  sessionId: string | null
  pendingRoll: PendingRoll | null
  activeSpeaker: ActiveSpeaker | null
  onRoll: (expr: string, rolls: number[], total: number) => Promise<{ passed: boolean } | null>
}

// ─── Constants ────────────────────────────────────────────────────────────────

const DICE = [4, 6, 8, 10, 12, 20, 100] as const
type DieSides = typeof DICE[number]

// SVG polygon points (viewBox 0 0 44 44, center 22 22)
const DIE_SHAPES: Record<DieSides, string> = {
  4:   '22,3 40,39 4,39',                                          // triangle
  6:   '5,5 39,5 39,39 5,39',                                      // square
  8:   '22,3 36,8 41,22 36,36 22,41 8,36 3,22 8,8',               // octagon
  10:  '22,2 40,22 22,42 4,22',                                    // diamond
  12:  '22,3 40,16 33,37 11,37 4,16',                              // pentagon
  20:  '22,3 38,13 38,31 22,41 6,31 6,13',                        // hexagon
  100: '22,4 33,7 39,16 39,28 33,37 22,40 11,37 5,28 5,16 11,7',  // decagon
}

const DIE_LABELS: Record<DieSides, string> = {
  4: 'd4', 6: 'd6', 8: 'd8', 10: 'd10', 12: 'd12', 20: 'd20', 100: 'd100',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function rollDie(sides: number): number {
  return Math.floor(Math.random() * sides) + 1
}

function groupDice(dice: number[]): string {
  const order: number[] = []
  const counts = new Map<number, number>()
  for (const d of dice) {
    if (!counts.has(d)) order.push(d)
    counts.set(d, (counts.get(d) ?? 0) + 1)
  }
  return order
    .map(sides => `${counts.get(sides)}${DIE_LABELS[sides as DieSides]}`)
    .join('+')
}

/** Case- and whitespace-insensitive normalisation for skill name matching (AC-011). */
export function normaliseSkill(s: string): string {
  return s.trim().toLowerCase().replace(/[\s\-_]+/g, ' ')
}

type BonusResult =
  | { kind: 'matched'; modifier: number; label: string }
  | { kind: 'no-character' }
  | { kind: 'unmapped'; skill: string }

export function lookupSkillBonus(skill: string, speaker: ActiveSpeaker | null): BonusResult {
  if (!speaker) return { kind: 'no-character' }
  const norm = normaliseSkill(skill)
  const matched = speaker.skills.find(s => normaliseSkill(s.name) === norm)
  if (!matched) return { kind: 'unmapped', skill }
  const sign = matched.total >= 0 ? '+' : ''
  return { kind: 'matched', modifier: matched.total, label: `${skill} ${sign}${matched.total}` }
}

function signedStr(n: number): string {
  return n >= 0 ? `+${n}` : String(n)
}

// ─── Component ────────────────────────────────────────────────────────────────

let nextId = 0

export default function DicePanel({ pendingRoll, activeSpeaker, onRoll }: Props) {
  const [pending, setPending] = useState<number[]>([])
  const [history, setHistory] = useState<RollRecord[]>([])
  const [autoBonus, setAutoBonus] = useState(true)

  const addDie = (sides: number) => setPending(p => [...p, sides])
  const clearPending = () => setPending([])

  const executeRoll = async (dice: number[]) => {
    const rolls = dice.map(rollDie)
    const rawTotal = rolls.reduce((a, b) => a + b, 0)
    const expr = groupDice(dice)

    let modifier: number | null = null
    let modifierLabel: string | null = null
    let bonusNote: string | null = null

    if (pendingRoll && autoBonus) {
      const bonus = lookupSkillBonus(pendingRoll.skill, activeSpeaker)
      if (bonus.kind === 'matched') {
        modifier = bonus.modifier
        modifierLabel = bonus.label
      } else if (bonus.kind === 'no-character') {
        bonusNote = 'No active character — raw roll only'
      } else {
        bonusNote = `No mapped bonus for ${pendingRoll.skill}`
      }
    }

    const total = rawTotal + (modifier ?? 0)
    const recordId = nextId++
    const record: RollRecord = {
      id: recordId,
      dice,
      rolls,
      rawTotal,
      modifier,
      total,
      modifierLabel,
      dc: pendingRoll?.dc ?? null,
      passed: null,
      bonusNote,
    }

    setHistory(h => [record, ...h].slice(0, 10))

    const result = await onRoll(expr, rolls, total)
    if (result !== null) {
      setHistory(h => h.map(r => r.id === recordId ? { ...r, passed: result.passed } : r))
    }
  }

  const doRoll = async () => {
    if (pending.length === 0) return
    await executeRoll([...pending])
    setPending([])
  }

  const handleBannerClick = () => executeRoll([20])

  // Bonus preview shown in the roll-request banner (pure computation — no state needed)
  const bonusPreview = (pendingRoll && autoBonus)
    ? lookupSkillBonus(pendingRoll.skill, activeSpeaker)
    : null

  return (
    <aside className={`dice-panel${pendingRoll ? ' dice-panel-active' : ''}`}>
      {pendingRoll ? (
        <div className="roll-request-banner">
          <button
            className="roll-request-prompt"
            onClick={handleBannerClick}
            title="Click to roll d20"
          >
            <div className="roll-request-skill">{pendingRoll.skill}</div>
            <div className="roll-request-dc">DC {pendingRoll.dc}</div>
            <div className="roll-request-hint">click to roll d20</div>

            {bonusPreview?.kind === 'matched' && (
              <div className="roll-bonus-preview roll-bonus-matched">
                {signedStr(bonusPreview.modifier)} from {pendingRoll.skill}
              </div>
            )}
            {bonusPreview?.kind === 'no-character' && (
              <div className="roll-bonus-preview roll-bonus-note">No active character</div>
            )}
            {bonusPreview?.kind === 'unmapped' && (
              <div className="roll-bonus-preview roll-bonus-note">No mapped bonus</div>
            )}
          </button>

          <label className="roll-bonus-toggle">
            <input
              type="checkbox"
              checked={autoBonus}
              onChange={e => setAutoBonus(e.target.checked)}
            />
            Auto bonus
          </label>
        </div>
      ) : (
        <div className="dice-panel-label">Dice</div>
      )}

      <div className="dice-grid">
        {DICE.map(sides => (
          <button
            key={sides}
            className={`die-btn${sides === 100 ? ' die-btn-wide' : ''}`}
            onClick={() => addDie(sides)}
            title={DIE_LABELS[sides]}
          >
            <svg viewBox="0 0 44 44" className="die-svg">
              <polygon points={DIE_SHAPES[sides]} />
            </svg>
            <span className="die-label">{DIE_LABELS[sides]}</span>
          </button>
        ))}
      </div>

      <div className="dice-divider" />

      <div className="dice-queue-row">
        {pending.length === 0
          ? <span className="queue-empty">pick dice above</span>
          : <span className="queue-expr">{groupDice(pending)}</span>
        }
        {pending.length > 0 && (
          <button className="clear-btn" onClick={clearPending} title="Clear">×</button>
        )}
      </div>

      <button
        className="btn btn-roll"
        onClick={doRoll}
        disabled={pending.length === 0}
      >
        Roll
      </button>

      {history.length > 0 && (
        <>
          <div className="dice-divider" />
          <div className="dice-history">
            {history.map((r, i) => (
              <div key={r.id} className={`history-row${i === 0 ? ' history-latest' : ''}`}>
                <div className="history-expr">{groupDice(r.dice)}</div>

                {r.modifier !== null ? (
                  // Skill roll with modifier: show "13 + Perception +7 = 20"
                  <div className="history-breakdown">
                    <span className="hist-num">{r.rawTotal}</span>
                    <span className="hist-op"> + </span>
                    <span className="hist-skill-label">{r.modifierLabel}</span>
                    <span className="hist-eq"> = </span>
                    <span className="history-total">{r.total}</span>
                    {r.dc !== null && (
                      <span className="hist-dc"> vs DC {r.dc}</span>
                    )}
                  </div>
                ) : (
                  // Plain roll
                  <div className="history-breakdown">
                    {r.rolls.length > 1 ? (
                      <>
                        {r.rolls.map((v, j) => (
                          <span key={j}>
                            {j > 0 && <span className="hist-op">+</span>}
                            <span className="hist-num">{v}</span>
                          </span>
                        ))}
                        <span className="hist-eq"> = </span>
                        <span className="history-total">{r.total}</span>
                      </>
                    ) : (
                      <span className="history-total">{r.total}</span>
                    )}
                  </div>
                )}

                {r.passed !== null && (
                  <span className={`hist-outcome ${r.passed ? 'hist-passed' : 'hist-failed'}`}>
                    {r.passed ? 'PASSED' : 'FAILED'}
                  </span>
                )}

                {r.bonusNote && (
                  <div className="hist-bonus-note">{r.bonusNote}</div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  )
}

