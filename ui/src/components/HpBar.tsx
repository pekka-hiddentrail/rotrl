interface Props {
  current: number
  max: number
}

export default function HpBar({ current, max }: Props) {
  const pct = max > 0 ? Math.min(100, Math.round((current / max) * 100)) : 0
  const color =
    pct > 66 ? '#3a9a6a' :
    pct > 33 ? '#c9a84c' :
    pct >  0 ? '#b04040' :
               '#444'

  return (
    <div className="hp-bar-track">
      <div
        className="hp-bar-fill"
        style={{ width: `${pct}%`, background: color }}
      />
      <span className="hp-bar-label">{current}/{max}</span>
    </div>
  )
}
