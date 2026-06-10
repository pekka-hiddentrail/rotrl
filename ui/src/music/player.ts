import * as Tone from 'tone'
import type { CalmPhrase } from '../api'
import { getMusicSynth } from './synth'

const BEATS_PER_BAR = 4
// 150 ms minimum lookahead — enough margin for Tone.js to prepare notes without
// the first beat being treated as already-past on slower systems.
const MIN_SCHEDULE_AHEAD_S = 0.15

export interface ScheduledPhraseInfo {
  start_delay_seconds: number
  duration_seconds: number
}

export interface CalmPhrasePlayer {
  schedulePhrase: (
    phrase: CalmPhrase,
    startDelaySeconds?: number,
    onBarChange?: (bar: number) => void,
  ) => ScheduledPhraseInfo
  stop: (fadeSecs?: number) => void
}

function eventSort(a: { bar: number; beat: number }, b: { bar: number; beat: number }): number {
  if (a.bar !== b.bar) return a.bar - b.bar
  return a.beat - b.beat
}

export function createCalmPhrasePlayer(): CalmPhrasePlayer {
  let scheduledIds: number[] = []
  const transport = Tone.getTransport()
  let fadeTimer: number | null = null

  const startTransport = () => {
    const anyTransport = transport as unknown as { state?: string; start?: () => void }
    if (anyTransport.state !== 'started' && typeof anyTransport.start === 'function') {
      anyTransport.start()
    }
  }

  const stopTransport = () => {
    const anyTransport = transport as unknown as { pause?: () => void; stop?: () => void }
    if (typeof anyTransport.stop === 'function') {
      anyTransport.stop()
      return
    }
    if (typeof anyTransport.pause === 'function') {
      anyTransport.pause()
    }
  }

  const schedulePhrase = (
    phrase: CalmPhrase,
    startDelaySeconds: number = 0,
    onBarChange?: (bar: number) => void,
  ): ScheduledPhraseInfo => {
    // Cancel any pending fade-completion from a previous stop(fadeSecs) call so
    // the fade timer cannot cancel this new phrase's notes or stop the Transport.
    if (fadeTimer !== null) {
      window.clearTimeout(fadeTimer)
      fadeTimer = null
    }

    const synth = getMusicSynth()
    const safeDelay = Math.max(MIN_SCHEDULE_AHEAD_S, startDelaySeconds)
    const startAt = transport.seconds + safeDelay

    transport.bpm.value = phrase.bpm

    const sortedEvents = [...phrase.events].sort(eventSort)
    const beatSeconds = 60 / phrase.bpm

    // Flush any lingering release tail from the previous phrase 1 ms before this
    // phrase's first note fires. Prevents monophonic synth re-trigger artifacts.
    const boundaryId = transport.schedule(() => {
      synth.triggerRelease()
    }, startAt - 0.001)
    scheduledIds.push(boundaryId)

    for (const ev of sortedEvents) {
      const beatOffset = (ev.bar - 1) * BEATS_PER_BAR + (ev.beat - 1)
      const at = startAt + beatOffset * beatSeconds
      const id = transport.schedule((time) => {
        const freq = Tone.Frequency(ev.midi, 'midi').toFrequency()
        const velocity = Math.min(1, Math.max(0, ev.velocity / 127))
        synth.triggerAttackRelease(freq, ev.duration, time, velocity)
      }, at)
      scheduledIds.push(id)
    }

    // Schedule bar-change callbacks so the UI can highlight the active bar.
    if (onBarChange) {
      for (let bar = 1; bar <= phrase.bars; bar++) {
        const barStart = startAt + (bar - 1) * BEATS_PER_BAR * beatSeconds
        const id = transport.schedule(() => {
          onBarChange(bar)
        }, barStart)
        scheduledIds.push(id)
      }
    }

    startTransport()

    return {
      start_delay_seconds: safeDelay,
      duration_seconds: phrase.bars * BEATS_PER_BAR * beatSeconds,
    }
  }

  const stop = (fadeSecs: number = 0): void => {
    if (fadeTimer !== null) {
      window.clearTimeout(fadeTimer)
      fadeTimer = null
    }

    // Snapshot and clear scheduledIds immediately so that a new schedulePhrase
    // call that arrives before the fade completes does not get its IDs cancelled.
    const idsToCancel = [...scheduledIds]
    scheduledIds = []

    if (fadeSecs > 0) {
      Tone.getDestination().volume.rampTo(-60, fadeSecs)
      fadeTimer = window.setTimeout(() => {
        fadeTimer = null
        for (const id of idsToCancel) transport.clear(id)
        stopTransport()
      }, fadeSecs * 1000 + 50)
    } else {
      for (const id of idsToCancel) transport.clear(id)
      stopTransport()
    }
  }

  return { schedulePhrase, stop }
}
