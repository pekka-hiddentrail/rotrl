const BASE = '/api'

export type SseEvent =
  | { type: 'token'; content: string }
  | { type: 'done'; session_id?: string }
  | { type: 'error'; message: string }

export async function* bootSession(
  sessionNumber: number,
  model: string,
  devMode: boolean = false,
): AsyncGenerator<SseEvent> {
  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_number: sessionNumber, model, dev_mode: devMode }),
  })
  if (!res.ok) {
    const detail = await res.text()
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

export async function endSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: 'DELETE' })
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

async function* parseSseStream(response: Response): AsyncGenerator<SseEvent> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
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
