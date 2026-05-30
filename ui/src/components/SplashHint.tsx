import { useState, useEffect, useRef } from 'react'
import { hints } from '../data/hints'

const ROTATION_MS = 8_000
const FADE_MS = 400

function pickHint(exclude?: string): string {
  const pool = exclude != null && hints.length > 1
    ? hints.filter(h => h !== exclude)
    : hints
  return pool[Math.floor(Math.random() * pool.length)]
}

export default function SplashHint() {
  const [hint, setHint] = useState(() => pickHint())
  const [fading, setFading] = useState(false)
  const prevRef = useRef(hint)

  useEffect(() => {
    const id = setInterval(() => {
      setFading(true)
      const timerId = setTimeout(() => {
        const next = pickHint(prevRef.current)
        prevRef.current = next
        setHint(next)
        setFading(false)
      }, FADE_MS)
      return () => clearTimeout(timerId)
    }, ROTATION_MS)
    return () => clearInterval(id)
  }, [])

  return (
    <div
      className={`splash-hint${fading ? ' splash-hint--fade' : ''}`}
      data-testid="splash-hint"
    >
      {hint}
    </div>
  )
}
