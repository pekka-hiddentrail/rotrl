import { useState, useCallback } from 'react'
import type { Message, SessionInfo } from './types'
import Header from './components/Header'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import CharacterSidebar from './components/CharacterSidebar'
import CharacterSheet from './components/CharacterSheet'
import DicePanel from './components/DicePanel'
import { bootSession, sendTurn, endSession } from './api'

export default function App() {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [sessionNumber, setSessionNumber] = useState(1)
  const [model, setModel] = useState('qwen3:4b')
  const [devMode, setDevMode] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeCharacter, setActiveCharacter] = useState<string | null>(null)

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

    try {
      let sessionId: string | undefined
      for await (const event of bootSession(sessionNumber, model, devMode)) {
        if (event.type === 'token') appendToken(event.content)
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
    setMessages(prev => [...prev, { role: 'player', content: input }])
    setStreaming(true)

    try {
      for await (const event of sendTurn(session.id, input)) {
        if (event.type === 'token') appendToken(event.content)
        if (event.type === 'error') throw new Error(event.message)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setStreaming(false)
    }
  }

  const handleEnd = async () => {
    if (session) await endSession(session.id)
    setSession(null)
    setMessages([])
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
        sessionNumber={sessionNumber}
        model={model}
        devMode={devMode}
        onSessionNumberChange={setSessionNumber}
        onModelChange={setModel}
        onDevModeChange={setDevMode}
        onBoot={handleBoot}
        onEnd={handleEnd}
      />

      {error && <div className="error-bar">{error}</div>}

      <div className="main-content">
        <CharacterSidebar
          activeCharacter={activeCharacter}
          onSelect={handleCharacterSelect}
        />

        <div className="chat-area">
          {!isBooted && messages.length === 0 && !streaming && (
            <div className="splash">
              <div className="splash-runes" aria-hidden="true">ᚠ ᚢ ᚦ ᚨ ᚱ ᚲ ᚷ ᚹ ᚺ ᚾ ᛁ ᛃ ᛇ ᛈ ᛉ ᛊ</div>
              <div className="splash-title">Rise of the Runelords</div>
              <div className="splash-sub">Configure your session above and click Boot Session</div>
              <div className="splash-hint">Make sure Ollama is running: <code>ollama serve</code></div>
            </div>
          )}

          {(messages.length > 0 || streaming) && (
            <ChatWindow messages={messages} streaming={streaming} />
          )}

          {isBooted && <InputBar onSend={handleSend} disabled={streaming} />}
        </div>

        <DicePanel />
      </div>

      {activeCharacter && (
        <CharacterSheet onClose={() => setActiveCharacter(null)} />
      )}
    </div>
  )
}
