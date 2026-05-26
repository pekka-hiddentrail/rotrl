import { useState } from 'react'

interface RollRecord {
  id: number
  dice: number[]
  rolls: number[]
  total: number
}

interface Props {
  sessionId: string | null
  onRoll: (expr: string, rolls: number[], total: number) => void
}

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

function rollDie(sides: number): number {
  return Math.floor(Math.random() * sides) + 1
}

function groupDice(dice: number[]): string {
  // Preserve first-click order — no sorting
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

let nextId = 0

export default function DicePanel({ onRoll }: Props) {
  const [pending, setPending] = useState<number[]>([])
  const [history, setHistory] = useState<RollRecord[]>([])

  const addDie = (sides: number) => setPending(p => [...p, sides])
  const clearPending = () => setPending([])

  const doRoll = () => {
    if (pending.length === 0) return
    const rolls = pending.map(rollDie)
    const total = rolls.reduce((a, b) => a + b, 0)
    const expr = groupDice(pending)
    const record: RollRecord = { id: nextId++, dice: [...pending], rolls, total }
    setHistory(h => [record, ...h].slice(0, 10))
    setPending([])
    onRoll(expr, rolls, total)
  }

  return (
    <aside className="dice-panel">
      <div className="dice-panel-label">Dice</div>

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
                {r.rolls.length > 1 ? (
                  <div className="history-breakdown">
                    {r.rolls.map((v, j) => (
                      <span key={j}>
                        {j > 0 && <span className="hist-op">+</span>}
                        <span className="hist-num">{v}</span>
                      </span>
                    ))}
                    <span className="hist-eq"> = </span>
                    <span className="history-total">{r.total}</span>
                  </div>
                ) : (
                  <div className="history-breakdown">
                    <span className="history-total">{r.total}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  )
}
