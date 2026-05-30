const BASE = '/api'

export type SseEvent =
  | { type: 'token'; content: string }
  | { type: 'status'; message: string }
  | { type: 'done'; session_id?: string; recap_path?: string; boot_path?: string; saved_to?: string }
  | { type: 'error'; message: string }
  | { type: 'context'; npc: string | null; npc_trigger: string | null; skill: string | null; skill_trigger: string | null; location: string | null; location_npcs: string[]; scene_npcs: string[] }
  | { type: 'patch_last'; content: string }
  | { type: 'roll_request'; skill: string; dc: number; success: string; failure: string }
  | { type: 'rate_limits'; rpm_limit?: string; rpm_remaining?: string; rpm_reset?: string; tpm_limit?: string; tpm_remaining?: string; tpm_reset?: string }
  | { type: 'combat_update'; combat_state: import('./types').CombatState | null }
  | { type: 'attack_request'; attacker: string; target: string; bonus: number; ac: number; damage_expr: string; attack_type: string }
  | { type: 'attack_result'; attacker: string; target: string; roll: number; bonus: number; total: number; ac: number; hit: boolean; damage_rolls: number[]; damage_total: number; attack_type: string; is_pc: boolean }

export async function* bootSession(
  sessionNumber: number,
  model: string,
  devMode: boolean = false,
  provider: string = 'ollama',
): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_number: sessionNumber, model, dev_mode: devMode, provider }),
  })
  if (!res.ok) {
    const body = await res.text()
    let detail = body
    try { detail = (JSON.parse(body) as { detail?: string }).detail ?? body } catch { /* keep raw */ }
    throw new Error(`Boot failed (${res.status}): ${detail}`)
  }
  yield* parseSseStream(res)
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
): Promise<{ passed: boolean; skill: string; dc: number; rolled: number; outcome: string }> {
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
