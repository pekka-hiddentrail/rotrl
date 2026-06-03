export type Role = 'gm' | 'player' | 'intro' | 'ending' | 'combat-event'

export interface MessageSpeaker {
  name: string
  portrait: string
  color: string
  rune: string
}

export interface ActiveEffect {
  name: string
  bonus_type: string
  ac_bonus: number
  rounds_remaining: number
}

export interface Combatant {
  name: string
  hp_current: number
  hp_max: number
  ac: number
  effective_ac: number
  initiative: number
  status: 'active' | 'unconscious' | 'fled' | 'dead'
  conditions?: string[]
  active_effects?: ActiveEffect[]
}

export interface AttackResult {
  attacker: string
  target: string
  roll: number | null
  bonus: number
  total: number | null
  ac: number | null
  hit: boolean
  damage_rolls: number[]
  damage_total: number
  attack_type: string
  is_pc: boolean
  is_spell?: boolean
  spell_name?: string | null
}

export type AttackPhase =
  | null
  | { phase: 'to_hit'; attacker: string; target: string; bonus: number; ac: number; damage_expr: string; attack_type: string }
  | { phase: 'damage'; attacker: string; target: string; damage_expr: string; hit_total: number; attack_type: string }
  | { phase: 'spell_damage'; caster: string; target: string; damage_expr: string; spell_name: string }

export interface CombatState {
  round: number
  combatants: Combatant[]
  current_actor?: string | null  // name of whoever is acting this turn (AC-001)
}

export interface ActiveSpeaker {
  name: string
  rune: string
  color: string
  isEnemy?: boolean  // true when an NPC/enemy is the current initiative actor
}

export interface Message {
  role: Role
  content: string
  speaker?: MessageSpeaker | null
  attackResult?: AttackResult   // set when role === 'combat-event'
}

export interface SessionInfo {
  id: string
  sessionNumber: number
  model: string
}
