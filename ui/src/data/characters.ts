import { useState, useEffect } from 'react'

export interface CharacterData {
  id: string
  portrait: string
  color: string
  rune: string
  name: string
  player: string
  race: string
  subrace: string
  class: string
  archetype: string
  alignment: string
  deity: string
  level: number
  appearance: string
  hp: { current: number; max: number; hitDie: string; baseDieRoll: number; conBonus: number }
  ac: { total: number; touch: number; flatFooted: number; components: { source: string; value: number }[] }
  initiative: string
  speed: string
  bab: string
  abilities: { name: string; score: number; mod: string }[]
  saves: { name: string; ability: string; total: string; base: string; abilityMod: string; magic: string; misc: string }[]
  skills: { name: string; ability: string; total: number; ranks: number; abilityMod: number; misc: number }[]
  feats: { name: string; desc: string }[]
  weapons: { display: string; name: string; type: string; atk: string; dmg: string; crit: string; range: string; dmgType: string; special: string; ammo: string }[]
  spells: {
    concentration: string
    list: { name: string; level: string; perDay: string; castTime: string; duration: string; range: string; components: string; school: string; target: string; cl: number; sr: string; save: string; effect: string }[]
  }
  inventory: {
    worn: string[]
    weapons: string[]
    carried: string[]
    wealth: { pp: number; gp: number; sp: number; cp: number }
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export interface CharactersState {
  characters: CharacterData[]
  characterMap: Record<string, CharacterData>
  loading: boolean
  error: string | null
}

export function useCharacters(): CharactersState {
  const [characters, setCharacters] = useState<CharacterData[]>([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/characters')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<CharacterData[]>
      })
      .then(data => {
        setCharacters(data)
        setLoading(false)
      })
      .catch(e => {
        setError(String(e))
        setLoading(false)
      })
  }, [])

  const characterMap = Object.fromEntries(characters.map(c => [c.id, c]))

  return { characters, characterMap, loading, error }
}
