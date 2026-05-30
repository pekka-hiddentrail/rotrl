export type Role = 'gm' | 'player' | 'intro' | 'ending'

export interface MessageSpeaker {
  name: string
  portrait: string
  color: string
  rune: string
}

export interface Combatant {
  name: string
  hp_current: number
  hp_max: number
  ac: number
  initiative: number
  status: 'active' | 'unconscious' | 'fled' | 'dead'
  conditions?: string[]
}

export interface AttackResult {
  attacker: string
  target: string
  roll: number
  bonus: number
  total: number
  ac: number
  hit: boolean
  damage_rolls: number[]
  damage_total: number
  attack_type: string
  is_pc: boolean
}

export type AttackPhase =
  | null
  | { phase: 'to_hit'; attacker: string; target: string; bonus: number; ac: number; damage_expr: string; attack_type: string }
  | { phase: 'damage'; attacker: string; target: string; damage_expr: string; hit_total: number }

export interface CombatState {
  round: number
  combatants: Combatant[]
}

export interface Message {
  role: Role
  content: string
  speaker?: MessageSpeaker | null
}

export interface SessionInfo {
  id: string
  sessionNumber: number
  model: string
}
