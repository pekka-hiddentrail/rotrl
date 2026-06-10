import * as Tone from 'tone'
import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchCalmPhrase, type CalmPhrase, type PhraseState } from '../api'
import { createCalmPhrasePlayer } from '../music/player'
import { startAudioContext } from '../music/synth'

const SWAP_BUFFER_MS = 500
const PREFETCH_TIMEOUT_MS = 3000
const PREFETCH_POLL_MS = 50
const VOLUME_STORAGE_KEY = 'rotrl.music.volume'
const DEFAULT_VOLUME = 70
const VOLUME_BOOST_DB = 12

function linearToDb(linear: number): number {
  if (linear === 0) return -Infinity
  return 20 * Math.log10(linear / 100) + VOLUME_BOOST_DB
}

interface MusicPlayerProps {
  sessionId: string | null
  devMode?: boolean
}

function getPhraseByBar(phrase: CalmPhrase): Array<{ bar: number; text: string }> {
  const barMap = new Map<number, string[]>()
  for (const event of phrase.events) {
    const events = barMap.get(event.bar) ?? []
    events.push(`${event.note}-${event.duration}`)
    barMap.set(event.bar, events)
  }
  return Array.from(barMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([bar, events]) => ({ bar, text: `B${bar}: ${events.join(' ')}` }))
}

export default function MusicPlayer({ sessionId, devMode = false }: MusicPlayerProps) {
  const [status, setStatus] = useState<'stopped' | 'playing' | 'error'>('stopped')
  const [volume, setVolume] = useState(DEFAULT_VOLUME)
  const [error, setError] = useState<string | null>(null)
  const [lastPhrase, setLastPhrase] = useState<CalmPhrase | null>(null)
  const [currentBar, setCurrentBar] = useState(0)

  const playerRef = useRef(createCalmPhrasePlayer())
  const previousStateRef = useRef<PhraseState | null>(null)
  const seedRef = useRef(1)
  const nextScheduleAtMsRef = useRef<number | null>(null)
  const playingRef = useRef(false)
  const prefetchedRef = useRef<CalmPhrase | null>(null)
  const prefetchingRef = useRef(false)
  const lastScheduledPhraseRef = useRef<CalmPhrase | null>(null)
  const swapTimerRef = useRef<number | null>(null)
  const volumeDbRef = useRef(linearToDb(DEFAULT_VOLUME))

  const phraseByBar = useMemo(() => {
    if (!lastPhrase) return []
    return getPhraseByBar(lastPhrase)
  }, [lastPhrase])

  useEffect(() => {
    const stored = window.localStorage.getItem(VOLUME_STORAGE_KEY)
    const initial = stored !== null ? Number(stored) : DEFAULT_VOLUME
    setVolume(initial)
    volumeDbRef.current = linearToDb(initial)
    Tone.getDestination().volume.value = linearToDb(initial)
  }, [])

  const clearSwapTimer = () => {
    if (swapTimerRef.current !== null) {
      window.clearTimeout(swapTimerRef.current)
      swapTimerRef.current = null
    }
  }

  const hardStop = () => {
    clearSwapTimer()
    playingRef.current = false
    prefetchingRef.current = false
    prefetchedRef.current = null
    nextScheduleAtMsRef.current = null
    playerRef.current.stop(0)
    setStatus('stopped')
    setCurrentBar(0)
  }

  const fadeStop = () => {
    clearSwapTimer()
    playingRef.current = false
    prefetchingRef.current = false
    prefetchedRef.current = null
    nextScheduleAtMsRef.current = null
    setStatus('stopped')
    setCurrentBar(0)
    playerRef.current.stop(0.5)
    // Restore volume after fade so the next Start isn't silent
    window.setTimeout(() => {
      Tone.getDestination().volume.value = volumeDbRef.current
    }, 600)
  }

  // Schedule a phrase at the next bar boundary and arm the swap timer.
  // Updates nextScheduleAtMsRef, previousStateRef, and lastScheduledPhraseRef.
  const scheduleAndContinue = (phrase: CalmPhrase) => {
    const nowMs = performance.now()
    if (nextScheduleAtMsRef.current === null || nextScheduleAtMsRef.current < nowMs) {
      nextScheduleAtMsRef.current = nowMs + 100
    }

    const startDelayMs = nextScheduleAtMsRef.current - nowMs
    const scheduled = playerRef.current.schedulePhrase(
      phrase,
      startDelayMs / 1000,
      (bar) => setCurrentBar(bar),
    )
    const durationMs = scheduled.duration_seconds * 1000

    previousStateRef.current = phrase.state
    lastScheduledPhraseRef.current = phrase
    nextScheduleAtMsRef.current += durationMs

    setLastPhrase(phrase)
    setStatus('playing')
    setError(null)

    clearSwapTimer()
    swapTimerRef.current = window.setTimeout(() => {
      void handleSwap()
    }, Math.max(0, startDelayMs + durationMs - SWAP_BUFFER_MS))
  }

  // Start a background fetch for the next phrase. No-ops if one is already in
  // flight or already buffered. Snapshots seed and previousState at call time.
  const triggerPrefetch = () => {
    if (prefetchingRef.current || prefetchedRef.current !== null || !playingRef.current) return
    prefetchingRef.current = true
    const seed = seedRef.current++
    const prevState = previousStateRef.current
    void (async () => {
      try {
        const phrase = await fetchCalmPhrase(sessionId, seed, prevState)
        if (playingRef.current) {
          prefetchedRef.current = phrase
        }
      } catch {
        // prefetchedRef stays null → fallback replay on swap
      } finally {
        prefetchingRef.current = false
      }
    })()
  }

  // Fires SWAP_BUFFER_MS before the current phrase ends. Waits up to
  // PREFETCH_TIMEOUT_MS for the pre-fetched phrase, then falls back to
  // replaying the last phrase rather than going silent.
  const handleSwap = async () => {
    if (!playingRef.current) return

    let waited = 0
    while (prefetchedRef.current === null && prefetchingRef.current && waited < PREFETCH_TIMEOUT_MS) {
      await new Promise<void>(resolve => window.setTimeout(resolve, PREFETCH_POLL_MS))
      waited += PREFETCH_POLL_MS
    }

    if (!playingRef.current) return

    const usedFallback = prefetchedRef.current === null
    const phrase = prefetchedRef.current ?? lastScheduledPhraseRef.current
    prefetchedRef.current = null

    if (!phrase) {
      hardStop()
      return
    }

    if (usedFallback) {
      setError('Phrase fetch timed out — replaying last phrase')
    }

    scheduleAndContinue(phrase)
    triggerPrefetch()
  }

  const handleStart = async () => {
    if (playingRef.current) return
    try {
      await startAudioContext()
      playingRef.current = true
      setError(null)

      const phrase = await fetchCalmPhrase(sessionId, seedRef.current++, null)
      if (!playingRef.current) return // stopped while fetching

      scheduleAndContinue(phrase)
      triggerPrefetch()
    } catch (e) {
      setStatus('error')
      setError(String(e))
      hardStop()
    }
  }

  const handleVolume = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(e.target.value)
    setVolume(next)
    volumeDbRef.current = linearToDb(next)
    Tone.getDestination().volume.value = linearToDb(next)
    window.localStorage.setItem(VOLUME_STORAGE_KEY, String(next))
  }

  const handleDebugGenerate = async () => {
    try {
      const phrase = await fetchCalmPhrase(sessionId, seedRef.current++, previousStateRef.current)
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
        <button className="btn btn-secondary" onClick={fadeStop} disabled={status !== 'playing'}>
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
        {lastPhrase && (
          <div className="music-player-debug">
            <span>motif: {lastPhrase.state.motif_id}</span>
            <span>cadence: {lastPhrase.state.cadence_degree}</span>
            <span>bpm: {lastPhrase.bpm}</span>
          </div>
        )}
      </div>

      {phraseByBar.length > 0 && (
        <>
          <div className="music-player-intent">
            <span className="music-intent-label">Intent:</span>
            {phraseByBar.map(({ bar }) => (
              <span key={bar} className={bar === currentBar ? 'music-intent-bar music-intent-bar-active' : 'music-intent-bar'}>
                B{bar}
              </span>
            ))}
          </div>
          <div className="music-player-notes">
            {phraseByBar.map(({ bar, text }, i) => (
              <span key={bar} className={bar === currentBar ? 'music-bar music-bar-active' : 'music-bar'}>
                {i > 0 && <span className="music-bar-sep"> | </span>}
                {text}
              </span>
            ))}
          </div>
        </>
      )}

      {error && <div className="music-player-error">{error}</div>}
    </div>
  )
}
