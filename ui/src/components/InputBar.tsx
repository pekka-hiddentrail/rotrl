import { useEffect, useState } from 'react'
import type { KeyboardEvent } from 'react'

interface Props {
  onSend: (input: string) => void
  disabled: boolean
  injectedValue?: string | null
  injectionId?: number
}

export default function InputBar({ onSend, disabled, injectedValue = null, injectionId = 0 }: Props) {
  const [value, setValue] = useState('')

  useEffect(() => {
    if (!injectedValue || injectionId <= 0) return
    setValue(prev => {
      const trimmedPrev = prev.trim()
      return trimmedPrev ? `${trimmedPrev} ${injectedValue}` : injectedValue
    })
  }, [injectedValue, injectionId])

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
