import '@testing-library/jest-dom'
import { vi } from 'vitest'

// jsdom does not implement scrollIntoView — stub it so ChatWindow's autoscroll
// effect does not throw in any test that renders the chat area.
window.HTMLElement.prototype.scrollIntoView = function () {}

// Tone.js is not available in jsdom. Stub the parts MusicPlayer touches so any
// test that renders App (which renders MusicPlayer) does not throw.
vi.mock('tone', () => ({
  getDestination: () => ({ volume: { value: 0, rampTo: vi.fn() } }),
  getTransport: () => ({
    state: 'stopped',
    seconds: 0,
    bpm: { value: 120 },
    schedule: vi.fn(() => 0),
    clear: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  }),
  Synth: vi.fn().mockImplementation(() => ({
    toDestination: vi.fn().mockReturnThis(),
    triggerAttackRelease: vi.fn(),
    dispose: vi.fn(),
  })),
  Frequency: vi.fn(() => ({ toFrequency: vi.fn(() => 440) })),
  start: vi.fn().mockResolvedValue(undefined),
}))
