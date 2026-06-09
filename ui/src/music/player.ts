import * as Tone from 'tone'
import type { CalmPhrase } from '../api'
import { getMusicSynth } from './synth'

const BEATS_PER_BAR = 4

export interface ScheduledPhraseInfo {
  start_delay_seconds: number
  duration_seconds: number
}

export interface CalmPhrasePlayer {
  schedulePhrase: (phrase: CalmPhrase, startDelaySeconds?: number) => ScheduledPhraseInfo
  stop: () => void
}

function eventSort(a: { bar: number; beat: number }, b: { bar: number; beat: number }): number {
  if (a.bar !== b.bar) return a.bar - b.bar
  return a.beat - b.beat
}

export function createCalmPhrasePlayer(): CalmPhrasePlayer {
  let scheduledIds: number[] = []
  const transport = Tone.getTransport()

  const startTransport = () => {
    const anyTransport = transport as unknown as {
      state?: string
      start?: () => void
      pause?: () => void
      stop?: () => void
    }
    if (anyTransport.state !== 'started' && typeof anyTransport.start === 'function') {
      anyTransport.start()
    }
  }

  const stopTransport = () => {
    const anyTransport = transport as unknown as {
      pause?: () => void
      stop?: () => void
    }
    if (typeof anyTransport.stop === 'function') {
      anyTransport.stop()
      return
    }
    if (typeof anyTransport.pause === 'function') {
      anyTransport.pause()
    }
  }

  const schedulePhrase = (phrase: CalmPhrase, startDelaySeconds: number = 0): ScheduledPhraseInfo => {
    const synth = getMusicSynth()
    const safeDelay = Math.max(0, startDelaySeconds)
    const startAt = transport.seconds + safeDelay

    transport.bpm.value = phrase.bpm

    const sortedEvents = [...phrase.events].sort(eventSort)
    const beatSeconds = 60 / phrase.bpm

    for (const ev of sortedEvents) {
      const beatOffset = ((ev.bar - 1) * BEATS_PER_BAR) + (ev.beat - 1)
      const at = startAt + (beatOffset * beatSeconds)
      const id = transport.schedule((time) => {
        const freq = Tone.Frequency(ev.midi, 'midi').toFrequency()
        const velocity = Math.min(1, Math.max(0, ev.velocity / 127))
        synth.triggerAttackRelease(freq, ev.duration, time, velocity)
      }, at)
      scheduledIds.push(id)
    }

    startTransport()

    return {
      start_delay_seconds: safeDelay,
      duration_seconds: phrase.bars * BEATS_PER_BAR * beatSeconds,
    }
  }

  const stop = () => {
    for (const id of scheduledIds) transport.clear(id)
    scheduledIds = []
    stopTransport()
  }

  return { schedulePhrase, stop }
}
