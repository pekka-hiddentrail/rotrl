import { useState, useCallback, useRef } from 'react'
import type { Message, SessionInfo, CombatState } from './types'
import type { CharacterData } from './data/characters'
import Header from './components/Header'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import CharacterSidebar from './components/CharacterSidebar'
import CharacterSheet from './components/CharacterSheet'
import ApiLogPanel from './components/ApiLogPanel'
import DicePanel from './components/DicePanel'
import CombatPanel from './components/CombatPanel'
import IntentBar from './components/IntentBar'
import { useCharacters } from './data/characters'
import SplashHint from './components/SplashHint'
import { bootSession, sendTurn, endSessionWithRecap, logRoll, resolveRoll, purgeSessionNpcs, endCombat } from './api'

function SplashPortrait({ c }: { c: CharacterData }) {
  const [imgOk, setImgOk] = useState(true)
  return (
    <div className="splash-char">
      <div className="splash-char-avatar" style={{ borderColor: c.color }}>
        {imgOk
          ? <img src={c.portrait} alt={c.name} onError={() => setImgOk(false)} />
          : <span style={{ color: c.color }}>{c.rune}</span>
        }
      </div>
      <div className="splash-char-name" style={{ color: c.color }}>{c.name}</div>
      <div className="splash-char-info">{c.race} {c.class}</div>
    </div>
  )
}

export default function App() {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [sessionNumber, setSessionNumber] = useState(1)
  const [model, setModel] = useState('llama-3.3-70b-versatile')
  const [devMode, setDevMode] = useState(false)
  const [provider, setProvider] = useState<'ollama' | 'groq' | 'anthropic'>('groq')
  const [error, setError] = useState<string | null>(null)
  const [ending, setEnding] = useState(false)
  const [activeCharacter, setActiveCharacter] = useState<string | null>(null)
  const [sheetCharId, setSheetCharId] = useState<string | null>(null)
  const [lastInput, setLastInput] = useState('')
  const [intent, setIntent] = useState<{
    npc: string | null
    npc_trigger: string | null
    skill: string | null
    skill_trigger: string | null
    location: string | null
    location_npcs: string[]
    scene_npcs: string[]
  } | null>(null)
  const [pendingRoll, setPendingRoll] = useState<{ skill: string; dc: number; success: string; failure: string } | null>(null)
  const [diceKey, setDiceKey] = useState(0)
  const [rateLimits, setRateLimits] = useState<{ rpm_limit?: string; rpm_remaining?: string; rpm_reset?: string; tpm_limit?: string; tpm_remaining?: string; tpm_reset?: string } | null>(null)
  const [combatState, setCombatState] = useState<CombatState | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [showApiLogs, setShowApiLogs] = useState(false)
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
    const speaker = activeCharacter ? characterMap[activeCharacter] : null
    const sentInput = speaker ? `@${speaker.name}: "${input}"` : input
    setError(null)
    setLastInput(input)
    setIntent(null)
    setMessages(prev => [
      ...prev,
      {
        role: 'player',
        content: input,
        speaker: speaker
          ? { name: speaker.name, portrait: speaker.portrait, color: speaker.color, rune: speaker.rune }
          : null,
      },
    ])
    setStreaming(true)

    try {
      for await (const event of sendTurn(session.id, sentInput)) {
        if (event.type === 'token') appendToken(event.content)
        if (event.type === 'context') setIntent({ ...event, scene_npcs: event.scene_npcs ?? [] })
        if (event.type === 'patch_last') {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.role === 'gm') return [...prev.slice(0, -1), { ...last, content: event.content }]
            return prev
          })
        }
        if (event.type === 'roll_request') setPendingRoll(event)
        if (event.type === 'rate_limits') setRateLimits(event)
        if (event.type === 'combat_update') setCombatState(event.combat_state)
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
    setCombatState(null)
  }

  const handleEndCombat = async () => {
    if (!session) { setCombatState(null); return }
    try {
      await endCombat(session.id)
      setCombatState(null)
    } catch {
      setCombatState(null) // clear locally even if request fails
    }
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
          setSessionNumber(n => n + 1)
        }
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setEnding(false)
      setSession(null)
      setMessages([])
      setCombatState(null)
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

  const handleOpenSheet = (id: string) => {
    setSheetCharId(id)
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
          if (p === 'groq') setModel('llama-3.3-70b-versatile')
          else if (p === 'anthropic') setModel('claude-sonnet-4-6')
          else setModel('qwen3:4b')
        }}
        rateLimits={rateLimits}
        onBoot={handleBoot}
        onEnd={handleEnd}
        onKillEnd={handleKillEnd}
        onViewLog={handleViewLog}
        onOpenApiLogs={() => setShowApiLogs(true)}
        onPurgeNpcs={handlePurgeNpcs}
      />

      {error && <div className="error-bar">{error}</div>}
      {charsError && <div className="error-bar">Character data: {charsError}</div>}

      <div className={`main-content${combatState ? ' combat-active' : ''}`}>
        <CharacterSidebar
          characters={characters}
          loading={charsLoading}
          activeSpeakerId={activeCharacter}
          onSetActive={handleCharacterSelect}
          onOpenSheet={handleOpenSheet}
        />

        <div className="chat-area">
          {!isBooted && messages.length === 0 && !streaming && (
            <div className="splash">
              <div className="splash-runes" aria-hidden="true">ᚠ ᚢ ᚦ ᚨ ᚱ ᚲ ᚷ ᚹ ᚺ ᚾ ᛁ ᛃ ᛇ ᛈ ᛉ ᛊ</div>
              <div className="splash-title">Rise of the Runelords</div>
              {characters.length > 0 && (
                <div className="splash-party">
                  {characters.map(c => <SplashPortrait key={c.id} c={c} />)}
                </div>
              )}
              <div className="splash-sub">Configure your session above and click Boot Session</div>
              <SplashHint />
            </div>
          )}

          {(messages.length > 0 || streaming) && (
            <ChatWindow messages={messages} streaming={streaming} />
          )}

          {isBooted && (
            <InputBar
              onSend={handleSend}
              disabled={streaming || ending}
              activeSpeaker={activeCharacter ? characterMap[activeCharacter] : null}
            />
          )}
        </div>

        {combatState && (
          <CombatPanel
            combatState={combatState}
            disabled={streaming || ending}
            onEndCombat={handleEndCombat}
          />
        )}

        <DicePanel
          key={diceKey}
          sessionId={session?.id ?? null}
          pendingRoll={pendingRoll}
          activeSpeaker={activeCharacter ? characterMap[activeCharacter] : null}
          onRoll={async (expr: string, rolls: number[], total: number) => {
            const speaker = activeCharacter ? characterMap[activeCharacter] : null
            const speakerName = speaker?.name ?? null
            const rawTotal = rolls.reduce((a, b) => a + b, 0)
            const modifier = total - rawTotal
            let rollMsg: string
            if (modifier !== 0) {
              const sign = modifier > 0 ? `+${modifier}` : String(modifier)
              rollMsg = speakerName
                ? `${speakerName} rolled a ${rawTotal}. With bonus of ${sign} it is a total of ${total}.`
                : `Rolled ${rawTotal}. With bonus of ${sign} it is a total of ${total}.`
            } else {
              rollMsg = speakerName ? `${speakerName} rolled a ${rawTotal}.` : `Rolled ${rawTotal}.`
            }
            setMessages(prev => [...prev, { role: 'player', content: rollMsg }])
            if (!session) return null
            logRoll(session.id, expr, rolls, total)
            if (pendingRoll) {
              try {
                const result = await resolveRoll(session.id, total)
                setPendingRoll(null)
                setMessages(prev => [...prev, { role: 'gm', content: result.outcome }])
                return { passed: result.passed }
              } catch {
                setPendingRoll(null)
              }
            }
            return null
          }}
        />
      </div>

      {sheetCharId && characterMap[sheetCharId] && (
        <CharacterSheet character={characterMap[sheetCharId]} onClose={() => setSheetCharId(null)} />
      )}

      {showApiLogs && (
        <ApiLogPanel onClose={() => setShowApiLogs(false)} />
      )}

      <IntentBar intent={intent} lastInput={lastInput} streaming={streaming} />

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
