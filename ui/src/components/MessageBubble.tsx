import type { Message } from '../types'

interface Props {
  message: Message
  isLast: boolean
  streaming: boolean
}

export default function MessageBubble({ message, isLast, streaming }: Props) {
  const isGm = message.role === 'gm'

  return (
    <div className={`bubble-row ${isGm ? 'gm' : 'player'}`}>
      <div className="bubble-label">{isGm ? 'GM' : 'You'}</div>
      <div className={`bubble ${isGm ? 'bubble-gm' : 'bubble-player'}`}>
        {message.content}
        {isLast && streaming && isGm && <span className="cursor">▋</span>}
      </div>
    </div>
  )
}
