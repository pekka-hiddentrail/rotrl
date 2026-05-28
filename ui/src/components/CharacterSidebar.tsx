import { useState, useRef, useEffect, useCallback } from 'react'
import type { CharacterData } from '../data/characters'

function Portrait({ src, rune, color, name, size }: {
  src: string; rune: string; color: string; name: string; size: number
}) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)
  const showImg = loaded && !error

  // Image may already be cached — onLoad won't fire in that case
  useEffect(() => {
    if (imgRef.current?.complete && imgRef.current.naturalWidth > 0) {
      setLoaded(true)
    }
  }, [])

  return (
    <div
      className="char-avatar"
      style={{ borderColor: color, width: size, height: size }}
    >
      {/* Fallback: fox silhouette SVG + rune */}
      <svg
        className="char-avatar-fallback"
        viewBox="0 0 72 72"
        style={{ opacity: showImg ? 0 : 1 }}
        aria-hidden="true"
      >
        {/* Radial glow */}
        <radialGradient id={`glow-${name}`} cx="50%" cy="55%" r="50%">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </radialGradient>
        <circle cx="36" cy="36" r="36" fill={`url(#glow-${name})`} />

        {/* Fox ears */}
        <polygon points="14,28 22,8 30,26" fill={color} opacity="0.85" />
        <polygon points="42,26 50,8 58,28" fill={color} opacity="0.85" />
        {/* Ear inner */}
        <polygon points="17,27 22,13 27,26" fill="#1a0f0f" opacity="0.6" />
        <polygon points="45,26 50,13 55,27" fill="#1a0f0f" opacity="0.6" />

        {/* Face circle */}
        <circle cx="36" cy="40" r="18" fill="#1e1010" stroke={color} strokeWidth="1.2" opacity="0.9" />

        {/* Rune glyph centred on face */}
        <text
          x="36" y="47"
          textAnchor="middle"
          fontFamily="serif"
          fontSize="18"
          fill={color}
          opacity="0.9"
        >{rune}</text>

        {/* Wisp left */}
        <path d="M10,44 Q6,38 10,32 Q14,26 11,20" stroke="#5bc8e8" strokeWidth="1.5" fill="none" opacity="0.5" strokeLinecap="round" />
        {/* Wisp right */}
        <path d="M62,44 Q66,38 62,32 Q58,26 61,20" stroke="#5bc8e8" strokeWidth="1.5" fill="none" opacity="0.5" strokeLinecap="round" />
      </svg>

      {/* Actual portrait */}
      <img
        ref={imgRef}
        src={src}
        alt={name}
        className="char-portrait-img"
        style={{ opacity: showImg ? 1 : 0 }}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
    </div>
  )
}

interface Props {
  characters: CharacterData[]
  loading: boolean
  activeSpeakerId: string | null
  onSetActive: (id: string) => void
  onOpenSheet: (id: string) => void
}

export default function CharacterSidebar({ characters, loading, activeSpeakerId, onSetActive, onOpenSheet }: Props) {
  const [menuId, setMenuId] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  // Close the action menu when the user clicks outside the character's wrap element
  const handleDocMouseDown = useCallback((e: MouseEvent) => {
    if (!menuId) return
    const wrap = document.querySelector(`[data-char-wrap="${menuId}"]`)
    if (wrap && !wrap.contains(e.target as Node)) {
      setMenuId(null)
    }
  }, [menuId])

  useEffect(() => {
    if (!menuId) return
    document.addEventListener('mousedown', handleDocMouseDown)
    return () => document.removeEventListener('mousedown', handleDocMouseDown)
  }, [menuId, handleDocMouseDown])

  return (
    <aside className="char-sidebar">
      <div className="sidebar-label">Party</div>
      {loading && <div className="sidebar-loading">…</div>}
      {characters.map(c => {
        const hpPct = (c.hp.current / c.hp.max) * 100
        const isActive = activeSpeakerId === c.id
        const isMenuOpen = menuId === c.id
        return (
          <div key={c.id} className="char-icon-wrap" data-char-wrap={c.id}>
            <button
              className={`char-icon-btn${isActive ? ' active' : ''}`}
              onClick={() => setMenuId(prev => prev === c.id ? null : c.id)}
              title={`${c.name} — ${c.race} ${c.class} Lv.${c.level}`}
            >
              <div
                className="char-halo-ring"
                style={isActive ? {
                  boxShadow: `0 0 0 3px ${c.color}, 0 0 10px ${c.color}88`,
                } : undefined}
              >
                <Portrait src={c.portrait} rune={c.rune} color={c.color} name={c.name} size={76} />
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
            {isMenuOpen && (
              <div className="char-action-menu" ref={menuRef}>
                <button
                  className="char-action-menu-item"
                  onClick={() => { onSetActive(c.id); setMenuId(null) }}
                >
                  {isActive ? '✕  Clear Active' : '◈  Set Active'}
                </button>
                <button
                  className="char-action-menu-item"
                  onClick={() => { onOpenSheet(c.id); setMenuId(null) }}
                >
                  ◳  Open Sheet
                </button>
              </div>
            )}
          </div>
        )
      })}
    </aside>
  )
}
