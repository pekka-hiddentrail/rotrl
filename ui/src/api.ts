import type { CombatState } from './types'

const BASE = '/api'

export interface NoteEvent {
  bar: number
  beat: number
  note: string
  midi: number
  duration: '8n' | '4n' | '2n' | '1n' | string
  velocity: number
}

export interface TrackEvents {
  track_id: string
  role: 'lead' | 'bass' | string
  events: NoteEvent[]
}

export interface PhraseState {
  motif_id: string
  motif_degrees: number[]
  cadence_degree: number
  highest_degree: number
  novelty: number
  bass_pattern_id: string
  bass_final_degree: number
}

export interface CalmPhrase {
  phrase_id: string
  mood: string
  key: string
  scale: string[]
  bpm: number
  time_signature: string
  bars: number
  tracks: TrackEvents[]
  state: PhraseState
}

export interface NextPhraseRequest {
  session_id?: string | null
  seed: number
  previous_state: PhraseState | null
}

export type SseEvent =
  | { type: 'token'; content: string }
  | { type: 'status'; message: string }
  | { type: 'done'; session_id?: string; recap_path?: string; boot_path?: string; saved_to?: string }
  | { type: 'error'; message: string }
  | { type: 'attention'; message: string }
  | { type: 'context'; npc: string | null; npc_trigger: string | null; skill: string | null; skill_trigger: string | null; location: string | null; location_npcs: string[]; scene_npcs: string[] }
  | { type: 'patch_last'; content: string }
  | { type: 'roll_request'; skill: string; dc: number; success: string; failure: string; speaker?: string | null }
  | { type: 'rate_limits'; rpm_limit?: string; rpm_remaining?: string; rpm_reset?: string; tpm_limit?: string; tpm_remaining?: string; tpm_reset?: string }
  | { type: 'combat_update'; combat_state: CombatState | null }
  | { type: 'initiative_pending'; combat_state: CombatState }
  | { type: 'attack_request'; attacker: string; target: string; bonus: number; ac: number; damage_expr: string; attack_type: string }
  | { type: 'damage_request'; caster: string; target: string; damage_expr: string; spell_name: string }
  | { type: 'heal_request';   caster: string; target: string; damage_expr: string; spell_name: string }
  | { type: 'attack_result'; attacker: string; target: string; roll: number; bonus: number; total: number; ac: number; hit: boolean; damage_rolls: number[]; damage_total: number; attack_type: string; is_pc: boolean }
  | { type: 'action_card';  attacker: string; target: string; roll: number | null; bonus: number; total: number | null; ac: number | null; hit: boolean; damage_rolls: number[]; damage_total: number; attack_type: string; action_type?: string; is_pc: boolean; is_spell?: boolean; spell_name?: string | null; is_heal?: boolean }

export async function* bootSession(
  sessionNumber: number,
  model: string,
  devMode: boolean = false,
  provider: string = 'ollama',
  eventScheduler: boolean = false,
): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_number: sessionNumber, model, dev_mode: devMode, provider, event_scheduler: eventScheduler }),
  })
  if (!res.ok) {
    const body = await res.text()
    let detail = body
    try { detail = (JSON.parse(body) as { detail?: string }).detail ?? body } catch { /* keep raw */ }
    throw new Error(`Boot failed (${res.status}): ${detail}`)
  }
  yield* parseSseStream(res)
}

export async function fetchCalmPhrase(
  sessionId: string | null,
  seed: number,
  previousState: PhraseState | null,
): Promise<CalmPhrase> {
  const req: NextPhraseRequest = {
    session_id: sessionId,
    seed,
    previous_state: previousState,
  }

  const res = await fetch(`${BASE}/music/calm/next_phrase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    const body = await res.text()
    let detail = body
    let errorCode: string | undefined
    try {
      const parsed = JSON.parse(body) as { detail?: string; error_code?: string }
      detail = parsed.detail ?? body
      errorCode = parsed.error_code
    } catch {
      // keep raw body text
    }
    if (res.status === 422 && errorCode === 'generation_failed') {
      throw new Error(`Music generation failed: ${detail}`)
    }
    throw new Error(`Calm phrase fetch failed (${res.status}): ${detail}`)
  }

  return res.json() as Promise<CalmPhrase>
}

export async function* sendTurn(
  sessionId: string,
  input: string,
): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`Turn failed (${res.status}): ${detail}`)
  }
  yield* parseSseStream(res)
}

export async function* endSessionWithRecap(sessionId: string, signal?: AbortSignal): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/end`, { method: 'POST', signal })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`End session failed (${res.status}): ${detail}`)
  }
  yield* parseSseStream(res, signal)
}

export async function endSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: 'DELETE' })
}

export async function resolveRoll(
  sessionId: string,
  rolled: number,
): Promise<{ passed: boolean; skill: string; dc: number; rolled: number; outcome: string; speaker?: string | null }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/resolve_roll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rolled }),
  })
  if (!res.ok) throw new Error(`Resolve roll failed (${res.status})`)
  return res.json()
}

export async function purgeSessionNpcs(): Promise<{ purged: number }> {
  const res = await fetch(`${BASE}/npcs/session`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Purge session NPCs failed (${res.status})`)
  return res.json()
}

export async function endCombat(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/combat`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`End combat failed (${res.status})`)
}

export async function rollInitiatives(sessionId: string): Promise<{ combat_state: CombatState }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/combat/roll_initiatives`, { method: 'POST' })
  if (!res.ok) throw new Error(`Roll initiatives failed (${res.status})`)
  return res.json()
}


export async function* pcTurn(sessionId: string, input: string, actionTypeHints?: string[], targetHint?: string): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/pc_turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input, action_type_hints: actionTypeHints ?? [], action_type_hint: null, target_hint: targetHint ?? null }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`PC turn failed (${res.status}): ${detail}`)
  }
  yield* parseSseStream(res)
}

export async function* runEnemyTurn(sessionId: string): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/enemy_turn`, { method: 'POST' })
  if (!res.ok) throw new Error(`Enemy turn failed (${res.status})`)
  yield* parseSseStream(res)
}

export async function* closeCombat(sessionId: string): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/close_combat`, { method: 'POST' })
  if (!res.ok) throw new Error(`Close combat failed (${res.status})`)
  yield* parseSseStream(res)
}

export async function advanceCombatTurn(
  sessionId: string,
): Promise<{
  current_actor: string | null
  is_pc: boolean
  position: number
  combatant_count: number
  round: number
  round_incremented: boolean
}> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/combat/advance_turn`, { method: 'POST' })
  if (!res.ok) throw new Error(`Advance turn failed (${res.status})`)
  return res.json()
}

export async function logRoll(
  sessionId: string,
  expr: string,
  rolls: number[],
  total: number,
): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}/roll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expr, rolls, total }),
  })
}

export interface BenchmarkRow {
  timestamp: string
  provider: string
  model: string
  session: string
  turn: string | number
  scenario?: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  system_chars: number
  log_file: string
}

export async function fetchBenchmarks(): Promise<BenchmarkRow[]> {
  const res = await fetch(`${BASE}/benchmarks`)
  if (!res.ok) throw new Error(`Benchmarks fetch failed (${res.status})`)
  const data: { rows: BenchmarkRow[] } = await res.json()
  return data.rows
}

export async function fetchCombatBenchmarks(): Promise<BenchmarkRow[]> {
  const res = await fetch(`${BASE}/benchmarks/combat`)
  if (!res.ok) throw new Error(`Combat benchmarks fetch failed (${res.status})`)
  const data: { rows: BenchmarkRow[] } = await res.json()
  return data.rows
}

export interface CoverageRow {
  feature_id:   string
  feature_file: string
  ac_id:        string
  title:        string
  pytest:       string[]
  vitest:       string[]
  playwright:   string[]
  exploratory:  string[]
  status:       'covered' | 'gap'
}

export interface CoverageData {
  generated: string | null
  summary:   { total: number; covered: number; gap: number }
  rows:      CoverageRow[]
  refresh_error?: string
}

export async function fetchCoverage(): Promise<CoverageData> {
  const res = await fetch(`${BASE}/coverage`)
  if (!res.ok) throw new Error(`Coverage fetch failed (${res.status})`)
  return res.json() as Promise<CoverageData>
}

export interface CodeCoverageFile {
  name:          string
  stmts:         number
  miss:          number
  covered:       number
  pct:           number
  delta:         number | null
  missing_lines: number[]
}

export interface CodeCoverageData {
  generated:       string | null
  files:           CodeCoverageFile[]
  has_prev:        boolean
  total_stmts:     number
  total_miss:      number
  total_pct:       number
  total_pct_delta: number | null
}

export async function fetchCodeCoverage(): Promise<CodeCoverageData> {
  const res = await fetch(`${BASE}/code-coverage`)
  if (!res.ok) throw new Error(`Code coverage fetch failed (${res.status})`)
  return res.json() as Promise<CodeCoverageData>
}

export async function resolveAttackRoll(
  sessionId: string,
  rolled: number,
): Promise<{ hit: boolean; ac: number; roll: number; bonus: number; total: number; damage_expr: string | null; queue_remaining: number; next_attack: { attacker: string; target: string; bonus: number; ac: number; damage_expr: string; attack_type: string } | null }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/resolve_attack_roll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rolled }),
  })
  if (!res.ok) throw new Error(`Resolve attack roll failed (${res.status})`)
  return res.json()
}

export async function resolveDamageRoll(
  sessionId: string,
  rolls: number[],
  total: number,
): Promise<{ damage_rolls: number[]; damage_total: number; queue_remaining: number; next_attack: { attacker: string; target: string; bonus: number; ac: number; damage_expr: string; attack_type: string } | null }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/resolve_damage_roll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rolls, total }),
  })
  if (!res.ok) throw new Error(`Resolve damage roll failed (${res.status})`)
  return res.json()
}

export async function* resumeCombat(sessionId: string): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/resume_combat`, { method: 'POST' })
  if (!res.ok) throw new Error(`Resume combat failed (${res.status})`)
  yield* parseSseStream(res)
}

export async function setActiveCharacter(
  sessionId: string,
  name: string,
): Promise<{ active_character: string }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/active_character`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(`Set active character failed (${res.status})`)
  return res.json()
}

export async function fetchApiLogList(): Promise<string[]> {
  const res = await fetch(`${BASE}/log/api`)
  if (!res.ok) throw new Error(`API log list failed (${res.status})`)
  const data: { files: { name: string; size_bytes: number }[] } = await res.json()
  return data.files.map(f => f.name)
}

export async function fetchApiLogEntry(filename: string): Promise<unknown> {
  const res = await fetch(`${BASE}/log/api/${encodeURIComponent(filename)}`)
  if (!res.ok) throw new Error(`API log fetch failed (${res.status})`)
  return res.json()
}

export interface WarmEventData {
  readiness: number
  threshold: number
  base_gain: number
  failed_rolls: number
  frozen: boolean
  last_zone_match_turn: number
  turns_remaining: number
  zones: string[]
  action_gain_map: Record<string, number>
}

export interface EventStatusData {
  scheduler_enabled: boolean
  turn_number: number
  active_event_id: string | null
  warm_events: Record<string, WarmEventData>
  completed_events: string[]
  cooldowns: Record<string, number>
}

export async function fetchEventStatus(sessionId: string): Promise<EventStatusData> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/event_status`)
  if (!res.ok) throw new Error(`Event status fetch failed (${res.status})`)
  return res.json() as Promise<EventStatusData>
}

async function* parseSseStream(response: Response, signal?: AbortSignal): AsyncGenerator<SseEvent> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  signal?.addEventListener('abort', () => reader.cancel())

  while (true) {
    const { done, value } = await reader.read()
    if (done || signal?.aborted) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      try {
        yield JSON.parse(raw) as SseEvent
      } catch {
        // skip malformed chunk
      }
    }
  }
}
