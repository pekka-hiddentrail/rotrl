interface Character {
  id: string
  name: string
  race: string
  class: string
  level: number
  hpCurrent: number
  hpMax: number
  color: string
  initial: string
  rune: string
}

const CHARACTERS: Character[] = [
  {
    id: 'player_01',
    name: 'Yanyeeku',
    race: 'Kitsune',
    class: 'Sorcerer',
    level: 1,
    hpCurrent: 7,
    hpMax: 7,
    color: '#c47a35',
    initial: 'Y',
    rune: 'ᚲ',
  },
]

interface Props {
  activeCharacter: string | null
  onSelect: (id: string) => void
}

export default function CharacterSidebar({ activeCharacter, onSelect }: Props) {
  return (
    <aside className="char-sidebar">
      <div className="sidebar-label">Party</div>
      {CHARACTERS.map(c => {
        const hpPct = (c.hpCurrent / c.hpMax) * 100
        const isActive = activeCharacter === c.id
        return (
          <button
            key={c.id}
            className={`char-icon-btn${isActive ? ' active' : ''}`}
            onClick={() => onSelect(c.id)}
            title={`${c.name} — ${c.race} ${c.class} ${c.level}`}
          >
            <div
              className="char-avatar"
              style={{ borderColor: c.color, boxShadow: isActive ? `0 0 10px ${c.color}66` : undefined }}
            >
              <span className="char-rune" style={{ color: c.color }}>{c.rune}</span>
            </div>
            <div className="char-name-label">{c.name}</div>
            <div className="char-hp-bar-wrap">
              <div
                className="char-hp-bar"
                style={{
                  width: `${hpPct}%`,
                  background: hpPct > 50 ? '#3d7a58' : hpPct > 25 ? '#c9a84c' : '#b04040',
                }}
              />
            </div>
          </button>
        )
      })}
    </aside>
  )
}
