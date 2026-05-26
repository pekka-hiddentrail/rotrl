interface Props {
  onClose: () => void
}

const CHARACTER = {
  name: 'Yanyeeku',
  player: 'Player 01',
  race: 'Kitsune',
  class: 'Sorcerer',
  archetype: 'Nine Tailed Heir',
  alignment: 'Neutral Good',
  deity: 'Cayden Cailean',
  level: 1,
  hp: { current: 7, max: 7 },
  ac: 12,
  initiative: '+2',
  speed: '30 ft.',
  bab: '+0',
  appearance: 'In her vulpine form, a compact, sharp-eyed kitsune with dark orange and white fur and two proud fox tails. In human guise, she wears amber eyes beneath a bold orange mohawk, with dark skin and Tian Xia–shaped features.',
  abilities: [
    { name: 'STR', score: 9, mod: '−1' },
    { name: 'DEX', score: 15, mod: '+2' },
    { name: 'CON', score: 12, mod: '+1' },
    { name: 'INT', score: 12, mod: '+1' },
    { name: 'WIS', score: 10, mod: '+0' },
    { name: 'CHA', score: 20, mod: '+6' },
  ],
  saves: [
    { name: 'Fortitude', total: '+1' },
    { name: 'Reflex', total: '+2' },
    { name: 'Will', total: '+2' },
  ],
  skills: [
    { name: 'Acrobatics', total: 4 },
    { name: 'Appraise', total: 5 },
    { name: 'Bluff', total: 5 },
    { name: 'Diplomacy', total: 6 },
    { name: 'Disguise', total: 5 },
    { name: 'Intimidate', total: 5 },
    { name: 'Perception', total: 0 },
    { name: 'Spellcraft', total: 5 },
    { name: 'Use Magic Device', total: 9 },
  ],
  feats: ['Eschew Materials', 'Magical Tail (Disguise Self 2/day)'],
  spells: {
    concentration: '+7',
    innate: ['Disguise Self (2/day)', 'Dancing Lights (3/day)'],
    cantrips: ['Detect Magic', 'Disrupt Undead', 'Message', 'Read Magic'],
    level1: ['Magic Missile', 'Shield'],
    slots: '5/day',
  },
  weapons: [
    { name: 'Light Crossbow', atk: '+2', dmg: '1d8', crit: '19-20/×2' },
    { name: 'Quarterstaff', atk: '−1', dmg: '1d6−1', crit: '20/×2' },
    { name: 'Dagger', atk: '+2 (ranged)', dmg: '1d4−1', crit: '19-20/×2' },
    { name: 'Bite', atk: '−1', dmg: '1d4−1', crit: '20/×2' },
    { name: 'Laughing Touch (8/day)', atk: 'Touch −1', dmg: '—', crit: '—' },
  ],
  wealth: { gp: 11 },
}

export default function CharacterSheet({ onClose }: Props) {
  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div className="sheet-panel" onClick={e => e.stopPropagation()}>
        <button className="sheet-close" onClick={onClose}>✕</button>

        <div className="sheet-header">
          <div className="sheet-avatar">
            <span className="sheet-avatar-rune">ᚲ</span>
          </div>
          <div className="sheet-identity">
            <div className="sheet-name">{CHARACTER.name}</div>
            <div className="sheet-class">
              {CHARACTER.race} · {CHARACTER.class} ({CHARACTER.archetype}) · Level {CHARACTER.level}
            </div>
            <div className="sheet-meta">{CHARACTER.alignment} · {CHARACTER.deity}</div>
          </div>
        </div>

        <p className="sheet-appearance">{CHARACTER.appearance}</p>

        <div className="sheet-vitals">
          <div className="vital-box">
            <div className="vital-label">HP</div>
            <div className="vital-value">{CHARACTER.hp.current}/{CHARACTER.hp.max}</div>
          </div>
          <div className="vital-box">
            <div className="vital-label">AC</div>
            <div className="vital-value">{CHARACTER.ac}</div>
          </div>
          <div className="vital-box">
            <div className="vital-label">Init</div>
            <div className="vital-value">{CHARACTER.initiative}</div>
          </div>
          <div className="vital-box">
            <div className="vital-label">Speed</div>
            <div className="vital-value">{CHARACTER.speed}</div>
          </div>
          <div className="vital-box">
            <div className="vital-label">BAB</div>
            <div className="vital-value">{CHARACTER.bab}</div>
          </div>
          <div className="vital-box">
            <div className="vital-label">GP</div>
            <div className="vital-value">{CHARACTER.wealth.gp}</div>
          </div>
        </div>

        <div className="sheet-two-col">
          <div>
            <div className="sheet-section-title">Ability Scores</div>
            <div className="ability-grid">
              {CHARACTER.abilities.map(a => (
                <div key={a.name} className="ability-box">
                  <div className="ability-name">{a.name}</div>
                  <div className="ability-score">{a.score}</div>
                  <div className="ability-mod">{a.mod}</div>
                </div>
              ))}
            </div>

            <div className="sheet-section-title" style={{ marginTop: 16 }}>Saving Throws</div>
            {CHARACTER.saves.map(s => (
              <div key={s.name} className="stat-row">
                <span>{s.name}</span>
                <span className="stat-val">{s.total}</span>
              </div>
            ))}

            <div className="sheet-section-title" style={{ marginTop: 16 }}>Feats</div>
            {CHARACTER.feats.map(f => (
              <div key={f} className="feat-item">· {f}</div>
            ))}
          </div>

          <div>
            <div className="sheet-section-title">Skills</div>
            {CHARACTER.skills.map(s => (
              <div key={s.name} className="stat-row">
                <span>{s.name}</span>
                <span className="stat-val">{s.total >= 0 ? '+' : ''}{s.total}</span>
              </div>
            ))}

            <div className="sheet-section-title" style={{ marginTop: 16 }}>Weapons</div>
            {CHARACTER.weapons.map(w => (
              <div key={w.name} className="weapon-row">
                <div className="weapon-name">{w.name}</div>
                <div className="weapon-stats">{w.atk} · {w.dmg}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="sheet-section-title" style={{ marginTop: 16 }}>Spells (Conc. {CHARACTER.spells.concentration})</div>
        <div className="spell-section">
          <div className="spell-group-label">Innate</div>
          <div className="spell-list">{CHARACTER.spells.innate.join(' · ')}</div>
          <div className="spell-group-label">Cantrips</div>
          <div className="spell-list">{CHARACTER.spells.cantrips.join(' · ')}</div>
          <div className="spell-group-label">Level 1 ({CHARACTER.spells.slots})</div>
          <div className="spell-list">{CHARACTER.spells.level1.join(' · ')}</div>
        </div>
      </div>
    </div>
  )
}
