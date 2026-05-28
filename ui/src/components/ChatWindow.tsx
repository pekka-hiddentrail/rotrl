import { useEffect, useRef } from 'react'
import type { Message } from '../types'
import MessageBubble from './MessageBubble'

interface Props {
  messages: Message[]
  streaming: boolean
}

function ThinkingBubble() {
  return (
    <div className="bubble-row gm">
      <div className="bubble-label">GM</div>
      <div className="bubble bubble-gm thinking-bubble">
        <span className="thinking-dot" style={{ animationDelay: '0ms' }} />
        <span className="thinking-dot" style={{ animationDelay: '160ms' }} />
        <span className="thinking-dot" style={{ animationDelay: '320ms' }} />
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  const lastRole = messages[messages.length - 1]?.role
  // Show the animated thinking dots only when a player message is last
  // (not during the initial intro display — the intro card has its own indicator)
  const showThinking = streaming && lastRole === 'player'

  return (
    <div className="chat-window">
      {messages.map((msg, i) => (
        <MessageBubble
          key={i}
          message={msg}
          isLast={i === messages.length - 1}
          streaming={streaming}
        />
      ))}
      {showThinking && <ThinkingBubble />}
      <div ref={bottomRef} />
    </div>
  )
}
