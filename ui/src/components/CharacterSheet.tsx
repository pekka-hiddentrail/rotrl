import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import type { CharacterData } from '../data/characters'

// ─── Tooltip ─────────────────────────────────────────────────────────────────

function Tooltip({ children, tip }: { children: React.ReactNode; tip: React.ReactNode }) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const ref = useRef<HTMLSpanElement>(null)

  const show = () => {
    timer.current = setTimeout(() => {
      if (!ref.current) return
      const r = ref.current.getBoundingClientRect()
      const x = Math.min(r.right + 10, window.innerWidth - 278)
      const y = Math.max(8, Math.min(r.top, window.innerHeight - 40))
      setPos({ x, y })
    }, 900)
  }

  const hide = () => {
    if (timer.current) clearTimeout(timer.current)
    setPos(null)
  }

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  return (
    <>
      <span ref={ref} onMouseEnter={show} onMouseLeave={hide} className="has-tip">
        {children}
      </span>
      {pos && createPortal(
        <div className="tooltip-box" style={{ left: pos.x, top: pos.y }}>
          {tip}
        </div>,
        document.body
      )}
    </>
  )
}

// ─── Tip helpers ─────────────────────────────────────────────────────────────

function TipRow({ label, val }: { label: string; val: React.ReactNode }) {
  return (
    <div className="tip-row">
      <span className="tip-label">{label}</span>
      <span className="tip-val">{val}</span>
    </div>
  )
}

function TipTitle({ text }: { text: string }) {
  return <div className="tip-title">{text}</div>
}

// ─── Data loaded from characters.ts ──────────────────────────────────────────

// ─── SheetPortrait ────────────────────────────────────────────────────────────

function SheetPortrait({ char }: { char: CharacterData }) {
  const [loaded, setLoaded] = useState(false)
  const [error,  setError]  = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)
  const showImg = loaded && !error
  const col = char.color

  useEffect(() => {
    setLoaded(false)
    setError(false)
  }, [char.portrait])

  useEffect(() => {
    if (imgRef.current?.complete && imgRef.current.naturalWidth > 0) {
      setLoaded(true)
    }
  }, [char.portrait])

  return (
    <div className="sheet-avatar" style={{ borderColor: col }}>
      <svg className="sheet-avatar-fallback" viewBox="0 0 152 152" style={{ opacity: showImg ? 0 : 1 }} aria-hidden="true">
        <radialGradient id={`sheet-glow-${char.id}`} cx="50%" cy="55%" r="50%">
          <stop offset="0%" stopColor={col} stopOpacity="0.3" />
          <stop offset="100%" stopColor={col} stopOpacity="0" />
        </radialGradient>
        <circle cx="76" cy="76" r="76" fill={`url(#sheet-glow-${char.id})`} />
        <polygon points="29,58 47,17 64,55" fill={col} opacity="0.85" />
        <polygon points="88,55 105,17 123,58" fill={col} opacity="0.85" />
        <polygon points="36,57 47,28 57,54" fill="#1a0f0f" opacity="0.6" />
        <polygon points="95,54 105,28 116,57" fill="#1a0f0f" opacity="0.6" />
        <circle cx="76" cy="86" r="41" fill="#1e1010" stroke={col} strokeWidth="2" opacity="0.92" />
        <text x="76" y="101" textAnchor="middle" fontFamily="serif" fontSize="40" fill={col} opacity="0.9">{char.rune}</text>
        <path d="M17,93 Q8,78 17,62 Q26,46 20,30" stroke="#5bc8e8" strokeWidth="2.5" fill="none" opacity="0.5" strokeLinecap="round" />
        <path d="M135,93 Q144,78 135,62 Q126,46 132,30" stroke="#5bc8e8" strokeWidth="2.5" fill="none" opacity="0.5" strokeLinecap="round" />
      </svg>
      <img ref={imgRef} src={char.portrait} alt={char.name} className="sheet-portrait-img"
        style={{ opacity: showImg ? 1 : 0 }}
        onLoad={() => setLoaded(true)} onError={() => setError(true)} />
    </div>
  )
}

// ─── CharacterSheet ───────────────────────────────────────────────────────────

interface Props { character: CharacterData; onClose: () => void }

export default function CharacterSheet({ character: C, onClose }: Props) {

  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div className="sheet-panel" onClick={e => e.stopPropagation()}>
        <button className="sheet-close" onClick={onClose}>✕</button>

        {/* Header */}
        <div className="sheet-header">
          <SheetPortrait char={C} />
          <div className="sheet-identity">
            <div className="sheet-name">{C.name}</div>
            <div className="sheet-class">{C.race} · {C.class} ({C.archetype}) · Level {C.level}</div>
            <div className="sheet-meta">{C.alignment} · {C.deity}</div>
          </div>
        </div>

        <p className="sheet-appearance">{C.appearance}</p>

        {/* Vitals — 5 boxes (GP moved to inventory) */}
        <div className="sheet-vitals">
          <Tooltip tip={
            <>
              <TipTitle text="Hit Points" />
              <TipRow label="Hit Die"       val={`${C.level}${C.hp.hitDie}`} />
              <TipRow label="Base (die)"    val={C.hp.baseDieRoll} />
              <TipRow label="CON bonus"     val={`+${C.hp.conBonus}`} />
              <TipRow label="Total"         val={`${C.hp.max} / ${C.hp.max}`} />
            </>
          }>
            <div className="vital-box">
              <div className="vital-label">HP</div>
              <div className="vital-value">{C.hp.current}/{C.hp.max}</div>
            </div>
          </Tooltip>

          <Tooltip tip={
            <>
              <TipTitle text="Armor Class" />
              {C.ac.components.map(x => (
                <TipRow key={x.source} label={x.source} val={x.value >= 0 ? `+${x.value}` : x.value} />
              ))}
              <TipRow label="Total"        val={C.ac.total} />
              <TipRow label="Touch"        val={C.ac.touch} />
              <TipRow label="Flat-Footed"  val={C.ac.flatFooted} />
            </>
          }>
            <div className="vital-box">
              <div className="vital-label">AC</div>
              <div className="vital-value">{C.ac.total}</div>
            </div>
          </Tooltip>

          <div className="vital-box"><div className="vital-label">Init</div><div className="vital-value">{C.initiative}</div></div>
          <div className="vital-box"><div className="vital-label">Speed</div><div className="vital-value">{C.speed}</div></div>
          <div className="vital-box"><div className="vital-label">BAB</div><div className="vital-value">{C.bab}</div></div>
        </div>

        {/* Two columns */}
        <div className="sheet-two-col">
          {/* Left */}
          <div>
            <div className="sheet-section-title">Ability Scores</div>
            <div className="ability-grid">
              {C.abilities.map(a => (
                <div key={a.name} className="ability-box">
                  <div className="ability-name">{a.name}</div>
                  <div className="ability-score">{a.score}</div>
                  <div className="ability-mod">{a.mod}</div>
                </div>
              ))}
            </div>

            <div className="sheet-section-title" style={{ marginTop: 14 }}>Saving Throws</div>
            {C.saves.map(s => (
              <Tooltip key={s.name} tip={
                <>
                  <TipTitle text={s.name} />
                  <TipRow label="Total"        val={s.total} />
                  <TipRow label="Base"         val={s.base} />
                  <TipRow label={`Ability (${s.ability})`} val={s.abilityMod} />
                  <TipRow label="Magic"        val={s.magic} />
                  <TipRow label="Misc"         val={s.misc} />
                </>
              }>
                <div className="stat-row">
                  <span>{s.name}</span>
                  <span className="stat-val">{s.total}</span>
                </div>
              </Tooltip>
            ))}

            <div className="sheet-section-title" style={{ marginTop: 14 }}>Feats</div>
            {C.feats.map(f => (
              <Tooltip key={f.name} tip={
                <>
                  <TipTitle text={f.name} />
                  <div className="tip-desc">{f.desc}</div>
                </>
              }>
                <div className="feat-item">· {f.name}</div>
              </Tooltip>
            ))}
          </div>

          {/* Right */}
          <div>
            <div className="sheet-section-title">Skills</div>
            {C.skills.map(s => (
              <Tooltip key={s.name} tip={
                <>
                  <TipTitle text={s.name} />
                  <TipRow label="Ability"      val={s.ability} />
                  <TipRow label="Total"        val={s.total >= 0 ? `+${s.total}` : s.total} />
                  <TipRow label="Ranks"        val={s.ranks} />
                  <TipRow label="Ability Mod"  val={s.abilityMod >= 0 ? `+${s.abilityMod}` : s.abilityMod} />
                  <TipRow label="Misc Mod"     val={s.misc >= 0 ? `+${s.misc}` : s.misc} />
                </>
              }>
                <div className="stat-row">
                  <span>{s.name}</span>
                  <span className="stat-val">{s.total >= 0 ? '+' : ''}{s.total}</span>
                </div>
              </Tooltip>
            ))}

            <div className="sheet-section-title" style={{ marginTop: 14 }}>Weapons</div>
            {C.weapons.map(w => (
              <Tooltip key={w.name} tip={
                <>
                  <TipTitle text={w.name} />
                  <TipRow label="Type"    val={w.type} />
                  <TipRow label="Attack"  val={w.atk} />
                  <TipRow label="Damage"  val={w.dmg} />
                  <TipRow label="Crit"    val={w.crit} />
                  <TipRow label="Range"   val={w.range} />
                  <TipRow label="Dmg Type" val={w.dmgType} />
                  {w.ammo   && <TipRow label="Ammo"    val={w.ammo} />}
                  {w.special && <div className="tip-desc" style={{ marginTop: 6 }}>{w.special}</div>}
                </>
              }>
                <div className="weapon-row">
                  <div className="weapon-display">{w.display}</div>
                </div>
              </Tooltip>
            ))}
          </div>
        </div>

        {/* Spells */}
        <div className="sheet-section-title" style={{ marginTop: 14 }}>
          Spells · Conc. {C.spells.concentration}
        </div>
        <div className="spell-section">
          {Array.from(new Set(C.spells.list.map(s => s.level))).map(lvl => {
            const group = C.spells.list.filter(s => s.level === lvl)
            if (!group.length) return null
            return (
              <div key={lvl}>
                <div className="spell-group-label">{lvl}</div>
                <div className="spell-list">
                  {group.map((s, i) => (
                    <span key={s.name}>
                      {i > 0 && <span style={{ color: '#4a3030' }}> · </span>}
                      <Tooltip tip={
                        <>
                          <TipTitle text={s.name} />
                          <TipRow label="Uses"       val={s.perDay} />
                          <TipRow label="Cast Time"  val={s.castTime} />
                          <TipRow label="Duration"   val={s.duration} />
                          <TipRow label="Range"      val={s.range} />
                          <TipRow label="School"     val={s.school} />
                          <TipRow label="Components" val={s.components} />
                          <TipRow label="Target"     val={s.target} />
                          <TipRow label="SR"         val={s.sr} />
                          <TipRow label="Save"       val={s.save} />
                          <div className="tip-desc" style={{ marginTop: 6 }}>{s.effect}</div>
                        </>
                      }>
                        <span>{s.name}</span>
                      </Tooltip>
                    </span>
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {/* Inventory */}
        <div className="sheet-section-title" style={{ marginTop: 14 }}>Inventory</div>
        <div className="inventory-section">
          {/* Wealth */}
          <div className="wealth-row">
            {(['pp', 'gp', 'sp', 'cp'] as const).map(coin => (
              <div key={coin} className="coin-box">
                <div className="coin-label">{coin.toUpperCase()}</div>
                <div className="coin-value">{C.inventory.wealth[coin]}</div>
              </div>
            ))}
          </div>

          {/* Equipment lists */}
          <div className="inv-two-col">
            <div>
              <div className="inv-group-label">Weapons</div>
              {C.inventory.weapons.map(w => (
                <div key={w} className="inv-item">· {w}</div>
              ))}
              {C.inventory.worn.length > 0 && (
                <>
                  <div className="inv-group-label" style={{ marginTop: 8 }}>Equipped</div>
                  {C.inventory.worn.map(w => <div key={w} className="inv-item">· {w}</div>)}
                </>
              )}
            </div>
            <div>
              <div className="inv-group-label">Carried</div>
              {C.inventory.carried.map(w => (
                <div key={w} className="inv-item">· {w}</div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
