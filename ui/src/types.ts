export type Role = 'gm' | 'player' | 'intro'

export interface Message {
  role: Role
  content: string
}

export interface SessionInfo {
  id: string
  sessionNumber: number
  model: string
}
