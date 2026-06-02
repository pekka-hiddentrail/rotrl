import { useState, useCallback, useRef } from 'react'
import type { Message, SessionInfo, CombatState, AttackPhase, AttackResult, ActiveSpeaker } from './types'
import type { CharacterData } from './data/characters'
import Header from './components/Header'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import CharacterSidebar from './components/CharacterSidebar'
import CharacterSheet from './components/CharacterSheet'
import ApiLogPanel from './components/ApiLogPanel'
import TokenBenchmarks from './components/TokenBenchmarks'
import CoverageMatrix from './components/CoverageMatrix'
import DicePanel from './components/DicePanel'
import CombatPanel from './components/CombatPanel'
import IntentBar from './components/IntentBar'
import { useCharacters } from './data/characters'
import SplashHint from './components/SplashHint'
import { advanceCombatTurn, bootSession, sendTurn, endSessionWithRecap, logRoll, resolveRoll, purgeSessionNpcs, closeCombat, runEnemyTurn, resolveAttackRoll, resolveDamageRoll, resumeCombat, rollInitiatives, setActiveCharacter as setActiveCharacterApi } from './api'

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
  const [pendingRoll, setPendingRoll] = useState<{ skill: string; dc: number; success: string; failure: string; speaker?: string | null } | null>(null)
  const [diceKey, setDiceKey] = useState(0)
  const [rateLimits, setRateLimits] = useState<{ rpm_limit?: string; rpm_remaining?: string; rpm_reset?: string; tpm_limit?: string; tpm_remaining?: string; tpm_reset?: string } | null>(null)
  const [combatState, setCombatState] = useState<CombatState | null>(null)
  const [currentCombatantName, setCurrentCombatantName] = useState<string | null>(null)
  const [attackPhase, setAttackPhase] = useState<AttackPhase>(null)
  const [attackLog, setAttackLog] = useState<AttackResult[]>([])
  const [initiativePending, setInitiativePending] = useState(false)
  const [enemyTurnStreaming, setEnemyTurnStreaming] = useState(false)
  const [combatClosing, setCombatClosing] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [showApiLogs, setShowApiLogs] = useState(false)
  const [showBenchmarks, setShowBenchmarks] = useState(false)
  const [showCoverage,    setShowCoverage]    = useState(false)
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const endAbortRef = useRef<AbortController | null>(null)
  // Refs for reading current state inside async closures (stale closure guard)
  const attackPhaseRef = useRef<AttackPhase>(null)
  const attackLogRef = useRef<AttackResult[]>([])
  // Keep refs in sync with state
  const setAttackPhaseSync = (v: AttackPhase) => { attackPhaseRef.current = v; setAttackPhase(v) }
  const setAttackLogSync = (fn: (prev: AttackResult[]) => AttackResult[]) => {
    setAttackLog(prev => { const next = fn(prev); attackLogRef.current = next; return next })
  }
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
    setPendingRoll(null)
    setInitiativePending(false)
    setEnemyTurnStreaming(false)
    setCombatClosing(false)
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
      setMessages([])
      setError(String(e))
    } finally {
      setStreaming(false)
    }
  }

  const handleSend = async (input: string) => {
    if (!session) return
    // During combat, the current initiative actor is the speaker (if they're a PC).
    // Falls back to the manually selected activeCharacter outside combat.
    const combatPc = (combatState && currentCombatantName)
      ? Object.values(characterMap).find(c => c.name.toLowerCase() === currentCombatantName.toLowerCase()) ?? null
      : null
    const speaker = combatPc ?? (activeCharacter ? characterMap[activeCharacter] : null)
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
        if (event.type === 'combat_update') {
          const cs = event.combat_state
          setCombatState(cs)
          setCurrentCombatantName(cs?.current_actor ?? null)
          setInitiativePending(false)
        }
        if (event.type === 'initiative_pending') {
          // Combat is seeded but initiatives not yet rolled — prompt the player
          setInitiativePending(true)
        }
        if (event.type === 'attack_request') setAttackPhaseSync({ phase: 'to_hit', attacker: event.attacker, target: event.target, bonus: event.bonus, ac: event.ac, damage_expr: event.damage_expr, attack_type: event.attack_type })
        if (event.type === 'attack_result') setAttackLogSync(prev => [event, ...prev])
        if (event.type === 'error') throw new Error(event.message)
      }
      // Auto-resume if NPC attacks resolved but no PC attacks queued
      if (!attackPhaseRef.current && attackLogRef.current.length > 0 && session) {
        await doResumeCombat(session.id)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setStreaming(false)
    }
  }

  const doResumeCombat = async (sessionId: string) => {
    setStreaming(true)
    setAttackLogSync(() => [])
    // Seed a new GM bubble so the combat resolution narrative doesn't append
    // to the previous turn's response in the chat window.
    setMessages(prev => [...prev, { role: 'gm', content: '' }])
    try {
      for await (const event of resumeCombat(sessionId)) {
        if (event.type === 'token') appendToken(event.content)
        if (event.type === 'patch_last') {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last?.role === 'gm') return [...prev.slice(0, -1), { ...last, content: event.content }]
            return prev
          })
        }
        if (event.type === 'combat_update') {
          const cs = event.combat_state
          setCombatState(cs)
          setCurrentCombatantName(cs?.current_actor ?? null)
        }
        // If the LLM writes %%ATTACK%% blocks during the resume narration, the backend
        // queues PC attacks and emits attack_request events.  Without handling them here,
        // attackPhase stays null while the backend queue is non-empty — causing the next
        // enemy_turn call to return 409.
        if (event.type === 'attack_request') {
          setAttackPhaseSync({ phase: 'to_hit', attacker: event.attacker, target: event.target, bonus: event.bonus, ac: event.ac, damage_expr: event.damage_expr, attack_type: event.attack_type })
        }
        if (event.type === 'attack_result') setAttackLogSync(prev => [event, ...prev])
        if (event.type === 'error') throw new Error(event.message)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setStreaming(false)
    }
  }

  // AC-009: advance_turn is authoritative server-side; updates state.json and returns new actor.
  const handleAdvanceTurn = async () => {
    if (!session || !combatState) return
    try {
      const result = await advanceCombatTurn(session.id)
      setCurrentCombatantName(result.current_actor)
      if (result.round_incremented) {
        setCombatState(prev => prev ? { ...prev, round: result.round } : prev)
      }
    } catch {
      // Fallback: advance client-side if endpoint fails (e.g. offline)
      const sorted = [...combatState.combatants].sort((a, b) => b.initiative - a.initiative)
      const active = sorted.filter(c => c.status === 'active')
      if (active.length === 0) return
      const idx = active.findIndex(c => c.name === currentCombatantName)
      setCurrentCombatantName(active[(idx + 1) % active.length].name)
    }
  }

  const handleRollInitiatives = async () => {
    if (!session) return
    try {
      const result = await rollInitiatives(session.id)
      setCombatState(result.combat_state)
      setCurrentCombatantName(result.combat_state.current_actor ?? null)
      setInitiativePending(false)
    } catch (e) {
      setError(String(e))
    }
  }

  const handleAttackRoll = async (rolled: number) => {
    if (!session) return
    try {
      const phase = attackPhaseRef.current?.phase === 'to_hit' ? attackPhaseRef.current : null
      const result = await resolveAttackRoll(session.id, rolled)
      const resultEntry: AttackResult = {
        attacker: phase?.attacker ?? '?',
        target: phase?.target ?? '?',
        roll: result.roll, bonus: result.bonus, total: result.total, ac: result.ac,
        hit: result.hit, damage_rolls: [], damage_total: 0,
        attack_type: phase?.attack_type ?? 'melee', is_pc: true,
      }
      if (result.hit) {
        setAttackPhaseSync({ phase: 'damage', attacker: resultEntry.attacker, target: resultEntry.target, damage_expr: result.damage_expr!, hit_total: result.total, attack_type: resultEntry.attack_type })
      } else {
        setAttackLogSync(prev => [resultEntry, ...prev])
        if (result.next_attack) {
          setAttackPhaseSync({ phase: 'to_hit', ...result.next_attack })
        } else if (result.queue_remaining === 0) {
          setAttackPhaseSync(null)
          await doResumeCombat(session.id)
        }
      }
    } catch (e) {
      setError(String(e))
    }
  }

  const handleDamageRoll = async (rolls: number[], total: number) => {
    if (!session || !attackPhaseRef.current || attackPhaseRef.current.phase !== 'damage') return
    const { attacker, target, attack_type } = attackPhaseRef.current
    try {
      const result = await resolveDamageRoll(session.id, rolls, total)
      const resultEntry: AttackResult = {
        attacker, target, roll: 0, bonus: 0, total: 0, ac: 0,
        hit: true, damage_rolls: result.damage_rolls, damage_total: result.damage_total,
        attack_type, is_pc: true,
      }
      setAttackLogSync(prev => [resultEntry, ...prev])
      if (result.next_attack) {
        setAttackPhaseSync({ phase: 'to_hit', ...result.next_attack })
      } else if (result.queue_remaining === 0) {
        setAttackPhaseSync(null)
        await doResumeCombat(session.id)
      }
    } catch (e) {
      setError(String(e))
    }
  }

  const handleKillEnd = () => {
    endAbortRef.current?.abort()
    endAbortRef.current = null
    setEnding(false)
    setSession(null)
    setMessages([])
    setCombatState(null)
    setCurrentCombatantName(null)
    setPendingRoll(null)
    setAttackPhaseSync(null)
    setAttackLogSync(() => [])
    setEnemyTurnStreaming(false)
    setCombatClosing(false)
    setDiceKey(k => k + 1)
  }

  const handleEnemyTurn = async () => {
    if (!session || !combatState || attackPhaseRef.current) return
    setError(null)
    setEnemyTurnStreaming(true)
    setMessages(prev => [...prev, { role: 'gm', content: '' }])
    try {
      for await (const event of runEnemyTurn(session.id)) {
        if (event.type === 'token') appendToken(event.content)
        if (event.type === 'attack_result') setAttackLogSync(prev => [event, ...prev])
        if (event.type === 'combat_update') {
          const cs = event.combat_state
          setCombatState(cs)
          setCurrentCombatantName(cs?.current_actor ?? null)
        }
        if (event.type === 'error') throw new Error(event.message)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setEnemyTurnStreaming(false)
      // Enemy attacks are narrated and resolved entirely within the enemy turn stream.
      // Clearing the log here prevents stale entries from triggering a false
      // doResumeCombat call when the player sends their next turn.
      setAttackLogSync(() => [])
    }
  }

  const handleEndCombat = async () => {
    if (!session) { setCombatState(null); return }
    setError(null)
    setCombatClosing(true)
    setMessages(prev => [...prev, { role: 'gm', content: '' }])
    try {
      for await (const event of closeCombat(session.id)) {
        if (event.type === 'token') appendToken(event.content)
        if (event.type === 'combat_update') {
          const cs = event.combat_state
          setCombatState(cs)
          setCurrentCombatantName(cs?.current_actor ?? null)
          if (!cs) {
            setAttackPhaseSync(null)
            setAttackLogSync(() => [])
          }
        }
        if (event.type === 'error') throw new Error(event.message)
      }
    } catch {
      setCombatState(null)
      setCurrentCombatantName(null)
      setAttackPhaseSync(null)
      setAttackLogSync(() => [])
    } finally {
      setCombatClosing(false)
    }
  }

  const handleEndClick = () => {
    if (!session) return
    if (devMode) { setShowEndConfirm(true); return }
    void handleEnd()
  }

  const handleEnd = async () => {
    setShowEndConfirm(false)
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
      setCurrentCombatantName(null)
      setPendingRoll(null)
      setAttackPhaseSync(null)
      setAttackLogSync(() => [])
      setEnemyTurnStreaming(false)
      setCombatClosing(false)
      setDiceKey(k => k + 1)
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
    setActiveCharacter(prev => {
      const next = prev === id ? null : id
      if (session) {
        const name = next ? (characterMap[next]?.name ?? next) : 'party'
        setActiveCharacterApi(session.id, name).catch(() => {/* non-blocking */})
      }
      return next
    })
  }

  const handleOpenSheet = (id: string) => {
    setSheetCharId(id)
  }

  const isBooted = session !== null

  // AC-008 / AC-010: build activeSpeaker from current initiative actor when combat is active.
  // PC turn → normal character speaker data; enemy turn → isEnemy:true with red color.
  const inputActiveSpeaker: ActiveSpeaker | null = (() => {
    if (combatState && currentCombatantName) {
      const pcData = Object.values(characterMap).find(
        c => c.name.toLowerCase() === currentCombatantName.toLowerCase()
      )
      if (pcData) {
        return { name: pcData.name, rune: pcData.rune, color: pcData.color, isEnemy: false }
      }
      // Enemy / NPC — hostile variant
      return { name: currentCombatantName, rune: '', color: '#cc2222', isEnemy: true }
    }
    // Out of combat: use player-selected character
    return activeCharacter ? (characterMap[activeCharacter] ? { ...characterMap[activeCharacter], isEnemy: false } : null) : null
  })()

  const pendingRollSpeakerName = pendingRoll?.speaker?.toLowerCase()
  const pendingRollSpeaker = pendingRollSpeakerName
    ? characters.find(c => c.name.toLowerCase() === pendingRollSpeakerName) ?? null
    : null
  // During combat with a pending roll, fall back to the current PC combatant so the
  // dice banner shows the right portrait and the auto-bonus uses their skill modifier.
  const combatRollSpeaker = (pendingRoll && currentCombatantName)
    ? characters.find(c => c.name.toLowerCase() === currentCombatantName.toLowerCase()) ?? null
    : null
  const diceSpeaker = activeCharacter
    ? characterMap[activeCharacter]
    : pendingRollSpeaker ?? combatRollSpeaker

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
        onEnd={handleEndClick}
        onKillEnd={handleKillEnd}
        onViewLog={handleViewLog}
        onOpenApiLogs={() => setShowApiLogs(true)}
        onOpenBenchmarks={() => setShowBenchmarks(true)}
        onOpenCoverage={() => setShowCoverage(true)}
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

          {(messages.length > 0 || streaming || enemyTurnStreaming || combatClosing) && (
            <ChatWindow
              messages={messages}
              streaming={streaming || enemyTurnStreaming || combatClosing}
            />
          )}

          {isBooted && (
            <InputBar
              onSend={handleSend}
              disabled={streaming || ending || enemyTurnStreaming || combatClosing}
              activeSpeaker={inputActiveSpeaker}
            />
          )}
        </div>

        {combatState && (
          <CombatPanel
            combatState={combatState}
            disabled={streaming || ending}
            currentCombatantName={currentCombatantName}
            attackPhase={attackPhase}
            enemyTurnStreaming={enemyTurnStreaming}
            combatClosing={combatClosing}
            onAdvanceTurn={handleAdvanceTurn}
            onEnemyTurn={handleEnemyTurn}
            onEndCombat={handleEndCombat}
          />
        )}

        {isBooted && (
          <DicePanel
            key={diceKey}
            sessionId={session?.id ?? null}
            pendingRoll={pendingRoll}
            activeSpeaker={diceSpeaker}
            attackPhase={attackPhase}
            attackLog={attackLog}
            onAttackRoll={handleAttackRoll}
            onDamageRoll={handleDamageRoll}
            initiativePending={initiativePending}
            onRollInitiatives={handleRollInitiatives}
            onRoll={async (expr: string, rolls: number[], total: number) => {
              const speaker = diceSpeaker
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
              setMessages(prev => [...prev, {
                role: 'player',
                content: rollMsg,
                speaker: speaker
                  ? { name: speaker.name, portrait: speaker.portrait, color: speaker.color, rune: speaker.rune }
                  : null,
              }])
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
        )}
      </div>

      {sheetCharId && characterMap[sheetCharId] && (
        <CharacterSheet character={characterMap[sheetCharId]} onClose={() => setSheetCharId(null)} />
      )}

      {showApiLogs && (
        <ApiLogPanel onClose={() => setShowApiLogs(false)} />
      )}

      {showBenchmarks && (
        <TokenBenchmarks onClose={() => setShowBenchmarks(false)} />
      )}

      {showCoverage && (
        <CoverageMatrix onClose={() => setShowCoverage(false)} />
      )}

      <IntentBar intent={intent} lastInput={lastInput} streaming={streaming} />

      {toast && <div className="toast">{toast}</div>}

      {showEndConfirm && (
        <div className="end-confirm-overlay" onClick={() => setShowEndConfirm(false)}>
          <div className="end-confirm-panel" onClick={e => e.stopPropagation()}>
            <div className="end-confirm-title">End session?</div>
            <div className="end-confirm-body">Dev mode — choose how to close this session.</div>
            <div className="end-confirm-buttons">
              <button className="end-confirm-btn end-confirm-btn--primary" onClick={() => void handleEnd()}>
                Generate recap
                <span className="end-confirm-sub">LLM call — writes recap.md + boot.md</span>
              </button>
              <button className="end-confirm-btn end-confirm-btn--secondary" onClick={() => { setShowEndConfirm(false); handleKillEnd() }}>
                End without recap
                <span className="end-confirm-sub">No LLM call — session data discarded</span>
              </button>
              <button className="end-confirm-btn end-confirm-btn--cancel" onClick={() => setShowEndConfirm(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
