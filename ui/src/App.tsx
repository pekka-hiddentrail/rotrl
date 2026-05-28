import { useState, useCallback, useRef } from 'react'
import type { Message, SessionInfo } from './types'
import Header from './components/Header'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import CharacterSidebar from './components/CharacterSidebar'
import CharacterSheet from './components/CharacterSheet'
import DicePanel from './components/DicePanel'
import IntentBar from './components/IntentBar'
import { useCharacters } from './data/characters'
import { bootSession, sendTurn, endSessionWithRecap, logRoll, resolveRoll, purgeSessionNpcs } from './api'

export default function App() {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [sessionNumber, setSessionNumber] = useState(1)
  const [model, setModel] = useState('llama-3.3-70b-versatile')
  const [devMode, setDevMode] = useState(false)
  const [provider, setProvider] = useState<'ollama' | 'groq'>('groq')
  const [error, setError] = useState<string | null>(null)
  const [ending, setEnding] = useState(false)
  const [activeCharacter, setActiveCharacter] = useState<string | null>(null)
  const [lastInput, setLastInput] = useState('')
  const [rollInjection, setRollInjection] = useState<{ id: number; value: string } | null>(null)
  const [intent, setIntent] = useState<{ npc: string | null; npc_trigger: string | null; skill: string | null; skill_trigger: string | null } | null>(null)
  const [pendingRoll, setPendingRoll] = useState<{ skill: string; dc: number; success: string; failure: string } | null>(null)
  const [diceKey, setDiceKey] = useState(0)
  const [rateLimits, setRateLimits] = useState<{ rpm_limit?: string; rpm_remaining?: string; rpm_reset?: string; tpm_limit?: string; tpm_remaining?: string; tpm_reset?: string } | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const endAbortRef = useRef<AbortController | null>(null)
  const { characters, characterMap, loading: charsLoading, error: charsError } = useCharacters()

  const appendToken = useCallback((token: string) => {
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last?.role === 'gm') {
        return [...prev.slice(0, -1), { ...last, content: last.content + token }]
      }
      return [...prev, { role: 'gm', content: token }]
    })
  }, [])

  const handleBoot = async () => {
    setError(null)
    setMessages([])
    setSession(null)
    setStreaming(true)
    setDiceKey(k => k + 1)
    setRollInjection(null)   // clear any leftover roll value from the previous session

    // 1. Fetch and show the intro card immediately
    try {
      const res = await fetch(`/api/intro?session=${sessionNumber}`)
      if (res.ok) {
        const text = await res.text()
        setMessages([{ role: 'intro', content: text }])
      }
    } catch {
      // Non-fatal
    }

    // 2. Create the session (primes context, returns done instantly — no LLM call at boot)
    try {
      let sessionId: string | undefined
      for await (const event of bootSession(sessionNumber, model, devMode, provider)) {
        if (event.type === 'error') throw new Error(event.message)
        if (event.type === 'done') sessionId = event.session_id
      }
      if (sessionId) setSession({ id: sessionId, sessionNumber, model })
    } catch (e) {
      setError(String(e))
    } finally {
      setStreaming(false)
    }
  }

  const handleSend = async (input: string) => {
    if (!session) return
    setError(null)
    setLastInput(input)
    setIntent(null)
    setMessages(prev => [...prev, { role: 'player', content: input }])
    setStreaming(true)

    try {
      for await (const event of sendTurn(session.id, input)) {
        if (event.type === 'token') appendToken(event.content)
        if (event.type === 'context') setIntent(event)
        if (event.type === 'patch_last') {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.role === 'gm') return [...prev.slice(0, -1), { ...last, content: event.content }]
            return prev
          })
        }
        if (event.type === 'roll_request') setPendingRoll(event)
        if (event.type === 'rate_limits') setRateLimits(event)
        if (event.type === 'error') throw new Error(event.message)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setStreaming(false)
    }
  }

  const handleKillEnd = () => {
    endAbortRef.current?.abort()
    endAbortRef.current = null
    setEnding(false)
    setSession(null)
    setMessages([])
  }

  const handleEnd = async () => {
    if (!session) return
    const controller = new AbortController()
    endAbortRef.current = controller
    setEnding(true)
    setStreaming(false)
    // Add the ending status bubble
    setMessages(prev => [...prev, { role: 'ending', content: 'Wrapping up the session…' }])

    try {
      for await (const event of endSessionWithRecap(session.id, controller.signal)) {
        if (event.type === 'status') {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.role === 'ending') {
              return [...prev.slice(0, -1), { ...last, content: event.message }]
            }
            return prev
          })
        }
        if (event.type === 'error') throw new Error(event.message)
        if (event.type === 'done') {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.role === 'ending') {
              return [...prev.slice(0, -1), { ...last, content: 'Session saved. See you next time.' }]
            }
            return prev
          })
          // Brief pause so players see the final message before clearing
          await new Promise(r => setTimeout(r, 1800))
        }
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setEnding(false)
      setSession(null)
      setMessages([])
    }
  }

  const handleViewLog = () => {
    if (session) window.open(`/api/sessions/${session.id}/log`, '_blank')
  }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 5000)
  }

  const handlePurgeNpcs = async () => {
    try {
      const { purged } = await purgeSessionNpcs()
      showToast(`${purged} session NPC ${purged === 1 ? 'directory' : 'directories'} removed.`)
    } catch (e) {
      setError(String(e))
    }
  }

  const handleCharacterSelect = (id: string) => {
    setActiveCharacter(prev => (prev === id ? null : id))
  }

  const isBooted = session !== null

  return (
    <div className="app">
      <Header
        session={session}
        streaming={streaming}
        ending={ending}
        sessionNumber={sessionNumber}
        model={model}
        devMode={devMode}
        provider={provider}
        onSessionNumberChange={setSessionNumber}
        onModelChange={setModel}
        onDevModeChange={setDevMode}
        onProviderChange={(p) => {
          setProvider(p)
          setModel(p === 'groq' ? 'llama-3.3-70b-versatile' : 'qwen3:4b')
        }}
        rateLimits={rateLimits}
        onBoot={handleBoot}
        onEnd={handleEnd}
        onKillEnd={handleKillEnd}
        onViewLog={handleViewLog}
        onPurgeNpcs={handlePurgeNpcs}
      />

      {error && <div className="error-bar">{error}</div>}
      {charsError && <div className="error-bar">Character data: {charsError}</div>}

      <div className="main-content">
        <CharacterSidebar
          characters={characters}
          loading={charsLoading}
          activeCharacter={activeCharacter}
          onSelect={handleCharacterSelect}
        />

        <div className="chat-area">
          {!isBooted && messages.length === 0 && !streaming && (
            <div className="splash">
              <div className="splash-runes" aria-hidden="true">ᚠ ᚢ ᚦ ᚨ ᚱ ᚲ ᚷ ᚹ ᚺ ᚾ ᛁ ᛃ ᛇ ᛈ ᛉ ᛊ</div>
              <div className="splash-title">Rise of the Runelords</div>
              <div className="splash-sub">Configure your session above and click Boot Session</div>
              <div className="splash-hint">Using Groq — make sure <code>GROQ_API_KEY</code> is set in <code>.env</code></div>
            </div>
          )}

          {(messages.length > 0 || streaming) && (
            <ChatWindow messages={messages} streaming={streaming} />
          )}

          {isBooted && (
            <InputBar
              onSend={handleSend}
              disabled={streaming || ending}
              injectedValue={rollInjection?.value ?? null}
              injectionId={rollInjection?.id ?? 0}
            />
          )}
        </div>

        <DicePanel
          key={diceKey}
          sessionId={session?.id ?? null}
          pendingRoll={pendingRoll}
          onRoll={async (expr: string, rolls: number[], total: number) => {
            setRollInjection(prev => ({ id: (prev?.id ?? 0) + 1, value: String(total) }))
            if (!session) return
            logRoll(session.id, expr, rolls, total)
            if (pendingRoll) {
              try {
                const result = await resolveRoll(session.id, total)
                setPendingRoll(null)
                setMessages(prev => [...prev, { role: 'gm', content: result.outcome }])
              } catch {
                setPendingRoll(null)
              }
            }
          }}
        />
      </div>

      {activeCharacter && characterMap[activeCharacter] && (
        <CharacterSheet character={characterMap[activeCharacter]} onClose={() => setActiveCharacter(null)} />
      )}

      <IntentBar intent={intent} lastInput={lastInput} streaming={streaming} />

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
