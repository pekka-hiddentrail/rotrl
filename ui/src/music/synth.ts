import * as Tone from 'tone'

let synth: Tone.Synth | null = null

export async function startAudioContext(): Promise<void> {
  await Tone.start()
}

export function getMusicSynth(): Tone.Synth {
  if (!synth) {
    synth = new Tone.Synth({
      oscillator: { type: 'triangle' },
      envelope: {
        attack: 0.01,
        decay: 0.1,
        sustain: 0.3,
        release: 0.2,
      },
    }).toDestination()
  }
  return synth
}

export function disposeMusicSynth(): void {
  if (synth) {
    synth.dispose()
    synth = null
  }
}
