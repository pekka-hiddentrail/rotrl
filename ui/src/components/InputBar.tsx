import { useState } from 'react'
import type { KeyboardEvent } from 'react'

interface ActiveSpeaker {
  name: string
  rune: string
  color: string
}

interface Props {
  onSend: (input: string) => void
  disabled: boolean
  activeSpeaker?: ActiveSpeaker | null
}

export default function InputBar({ onSend, disabled, activeSpeaker = null }: Props) {
  const [value, setValue] = useState('')

  const submit = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="input-bar">
      <div className="input-main">
        {activeSpeaker && (
          <div className="speaker-badge" style={{ '--speaker-color': activeSpeaker.color } as React.CSSProperties}>
            <span className="speaker-badge-rune" aria-hidden="true">{activeSpeaker.rune}</span>
            <span className="speaker-badge-label">Speaking as <strong>{activeSpeaker.name}</strong></span>
          </div>
        )}
        <textarea
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="What do you do?  (Enter to send · Shift+Enter for newline)"
          className="input-area"
          rows={2}
          autoFocus
        />
      </div>
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="btn btn-send"
      >
        {disabled ? '…' : 'Send'}
      </button>
    </div>
  )
}
