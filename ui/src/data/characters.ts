import { useEffect, useState } from 'react'

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

export type CharacterSummary = Pick<
  CharacterData,
  | 'id'
  | 'portrait'
  | 'color'
  | 'rune'
  | 'name'
  | 'player'
  | 'race'
  | 'subrace'
  | 'class'
  | 'archetype'
  | 'level'
  | 'hp'
>

export interface CharactersState {
  characters: CharacterSummary[]
  characterMap: Record<string, CharacterSummary>
  loading: boolean
  error: string | null
}

const summaryCache: {
  data: CharacterSummary[] | null
  promise: Promise<CharacterSummary[]> | null
} = { data: null, promise: null }

const sheetCache = new Map<string, CharacterData>()
const sheetPromises = new Map<string, Promise<CharacterData>>()

function loadCharacterSummaries(): Promise<CharacterSummary[]> {
  if (summaryCache.data) return Promise.resolve(summaryCache.data)
  if (!summaryCache.promise) {
    summaryCache.promise = fetch('/api/characters')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<CharacterSummary[]>
      })
      .then(data => {
        summaryCache.data = data
        return data
      })
      .finally(() => {
        summaryCache.promise = null
      })
  }
  return summaryCache.promise
}

export function loadCharacterSheet(id: string): Promise<CharacterData> {
  const cached = sheetCache.get(id)
  if (cached) return Promise.resolve(cached)
  const pending = sheetPromises.get(id)
  if (pending) return pending

  const promise = fetch(`/api/characters/${encodeURIComponent(id)}`)
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return r.json() as Promise<CharacterData>
    })
    .then(data => {
      sheetCache.set(id, data)
      return data
    })
    .finally(() => {
      sheetPromises.delete(id)
    })

  sheetPromises.set(id, promise)
  return promise
}

export function __resetCharacterCachesForTests() {
  summaryCache.data = null
  summaryCache.promise = null
  sheetCache.clear()
  sheetPromises.clear()
}

export function useCharacters(): CharactersState {
  const [characters, setCharacters] = useState<CharacterSummary[]>(() => summaryCache.data ?? [])
  const [loading, setLoading] = useState(() => summaryCache.data === null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    if (summaryCache.data) {
      setCharacters(summaryCache.data)
      setLoading(false)
      return
    }

    loadCharacterSummaries()
      .then(data => {
        if (cancelled) return
        setCharacters(data)
        setLoading(false)
      })
      .catch(e => {
        if (cancelled) return
        setError(String(e))
        setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  const characterMap = Object.fromEntries(characters.map(c => [c.id, c]))

  return { characters, characterMap, loading, error }
}
