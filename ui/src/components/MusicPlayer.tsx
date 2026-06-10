import * as Tone from 'tone'
import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchCalmPhrase, type CalmPhrase, type PhraseState } from '../api'
import { createCalmPhrasePlayer } from '../music/player'
import { startAudioContext } from '../music/synth'

const LOOKAHEAD_CAP_MS = 1500
const VOLUME_STORAGE_KEY = 'rotrl.music.volume'
const DEFAULT_VOLUME = 70
const VOLUME_BOOST_DB = 15

function linearToDb(linear: number): number {
  if (linear === 0) return -Infinity
  return 20 * Math.log10(linear / 100) + VOLUME_BOOST_DB
}

interface MusicPlayerProps {
  sessionId: string | null
  devMode?: boolean
}

function formatPhraseCompact(phrase: CalmPhrase): string {
  const barMap = new Map<number, string[]>()
  for (const event of phrase.events) {
    const events = barMap.get(event.bar) ?? []
    events.push(`${event.note}-${event.duration}`)
    barMap.set(event.bar, events)
  }

  return Array.from(barMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([bar, events]) => `B${bar}: ${events.join(' ')}`)
    .join(' | ')
}

export default function MusicPlayer({ sessionId, devMode = false }: MusicPlayerProps) {
  const [status, setStatus] = useState<'stopped' | 'playing' | 'error'>('stopped')
  const [volume, setVolume] = useState(DEFAULT_VOLUME)
  const [error, setError] = useState<string | null>(null)
  const [lastPhrase, setLastPhrase] = useState<CalmPhrase | null>(null)

  const playerRef = useRef(createCalmPhrasePlayer())
  const previousStateRef = useRef<PhraseState | null>(null)
  const seedRef = useRef(1)
  const nextPhraseStartAtMsRef = useRef<number | null>(null)
  const playingRef = useRef(false)
  const requestInFlightRef = useRef(false)
  const fetchTimerRef = useRef<number | null>(null)

  const compactPhrase = useMemo(() => {
    if (!lastPhrase) return ''
    return formatPhraseCompact(lastPhrase)
  }, [lastPhrase])

  useEffect(() => {
    const stored = window.localStorage.getItem(VOLUME_STORAGE_KEY)
    const initial = stored !== null ? Number(stored) : DEFAULT_VOLUME
    setVolume(initial)
    Tone.getDestination().volume.value = linearToDb(initial)
  }, [])

  const clearFetchTimer = () => {
    if (fetchTimerRef.current !== null) {
      window.clearTimeout(fetchTimerRef.current)
      fetchTimerRef.current = null
    }
  }

  const hardStop = () => {
    clearFetchTimer()
    playingRef.current = false
    requestInFlightRef.current = false
    nextPhraseStartAtMsRef.current = null
    playerRef.current.stop()
    setStatus('stopped')
  }

  const queueNextPhrase = async () => {
    if (!playingRef.current || requestInFlightRef.current) return

    requestInFlightRef.current = true
    try {
      const phrase = await fetchCalmPhrase(sessionId, seedRef.current, previousStateRef.current)
      seedRef.current += 1

      // Capture nowMs AFTER the fetch so startDelayMs reflects actual remaining time.
      const nowMs = performance.now()
      if (nextPhraseStartAtMsRef.current === null || nextPhraseStartAtMsRef.current < nowMs) {
        // First phrase, or we've drifted behind real time — reset the clock.
        nextPhraseStartAtMsRef.current = nowMs + 100
      }

      const startDelayMs = nextPhraseStartAtMsRef.current - nowMs
      const scheduled = playerRef.current.schedulePhrase(phrase, startDelayMs / 1000)
      const durationMs = scheduled.duration_seconds * 1000
      const lookaheadMs = Math.min(LOOKAHEAD_CAP_MS, durationMs / 2)

      previousStateRef.current = phrase.state
      nextPhraseStartAtMsRef.current += durationMs
      setLastPhrase(phrase)
      setStatus('playing')
      setError(null)

      clearFetchTimer()
      fetchTimerRef.current = window.setTimeout(() => {
        void queueNextPhrase()
      }, Math.max(0, startDelayMs + durationMs - lookaheadMs))
    } catch (e) {
      setStatus('error')
      setError(String(e))
      hardStop()
    } finally {
      requestInFlightRef.current = false
    }
  }

  const handleStart = async () => {
    if (playingRef.current) return
    try {
      await startAudioContext()
      playingRef.current = true
      setError(null)
      setStatus('playing')
      void queueNextPhrase()
    } catch (e) {
      setStatus('error')
      setError(String(e))
    }
  }

  const handleStop = () => {
    hardStop()
  }

  const handleVolume = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(e.target.value)
    setVolume(next)
    Tone.getDestination().volume.value = linearToDb(next)
    window.localStorage.setItem(VOLUME_STORAGE_KEY, String(next))
  }

  const handleDebugGenerate = async () => {
    try {
      const phrase = await fetchCalmPhrase(sessionId, seedRef.current, previousStateRef.current)
      seedRef.current += 1
      previousStateRef.current = phrase.state
      setLastPhrase(phrase)
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => {
    return () => {
      hardStop()
    }
  }, [])

  return (
    <div className="music-player" aria-label="Music Player">
      <div className="music-player-top">
        <div className="music-player-title">Calm Music</div>
        <div className={`music-player-status music-player-status-${status}`}>
          {status === 'playing' ? 'Playing' : 'Stopped'}
        </div>
      </div>

      <div className="music-player-controls">
        <button className="btn btn-secondary" onClick={handleStart} disabled={status === 'playing'}>
          Start Music
        </button>
        <button className="btn btn-secondary" onClick={handleStop} disabled={status !== 'playing'}>
          Stop Music
        </button>
        <label className="music-volume">
          <span>Vol</span>
          <input
            type="range"
            min={0}
            max={100}
            value={volume}
            onChange={handleVolume}
            aria-label="Music volume"
          />
          <span className="music-volume-value">{volume}</span>
        </label>
        {devMode && (
          <button className="btn btn-secondary" onClick={handleDebugGenerate}>
            Generate Phrase (Debug)
          </button>
        )}
      </div>

      {error && <div className="music-player-error">{error}</div>}

      {lastPhrase && (
        <div className="music-player-debug">
          <div>motif_id: {lastPhrase.state.motif_id}</div>
          <div>cadence_degree: {lastPhrase.state.cadence_degree}</div>
          <div>bpm: {lastPhrase.bpm}</div>
          <div className="music-player-notes">{compactPhrase}</div>
        </div>
      )}
    </div>
  )
}
