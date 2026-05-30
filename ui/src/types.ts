export type Role = 'gm' | 'player' | 'intro' | 'ending'

export interface Combatant {
  name: string
  hp_current: number
  hp_max: number
  ac: number
  initiative: number
  status: 'active' | 'unconscious' | 'fled' | 'dead'
}

export interface CombatState {
  round: number
  combatants: Combatant[]
}

export interface Message {
  role: Role
  content: string
}

export interface SessionInfo {
  id: string
  sessionNumber: number
  model: string
}
