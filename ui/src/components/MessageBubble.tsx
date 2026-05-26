import type { Message } from '../types'

interface Props {
  message: Message
  isLast: boolean
  streaming: boolean
}

// Render intro markdown with minimal formatting (bold, italic, hr, headings)
function renderIntro(text: string) {
  return text.split('\n').map((line, i) => {
    if (line.startsWith('# '))  return <h2 key={i} className="intro-h1">{line.slice(2)}</h2>
    if (line.startsWith('## ')) return <h3 key={i} className="intro-h2">{line.slice(3)}</h3>
    if (line === '---')          return <hr key={i} className="intro-hr" />
    if (line.trim() === '')      return <br key={i} />
    // inline bold + italic
    const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**'))
        return <strong key={j}>{part.slice(2, -2)}</strong>
      if (part.startsWith('*') && part.endsWith('*'))
        return <em key={j}>{part.slice(1, -1)}</em>
      return part
    })
    return <p key={i} className="intro-p">{parts}</p>
  })
}

export default function MessageBubble({ message, isLast, streaming }: Props) {
  if (message.role === 'intro') {
    return (
      <div className="intro-card">
        <div className="intro-card-body">{renderIntro(message.content)}</div>
        {isLast && streaming && (
          <div className="intro-card-footer">
            <span className="thinking-dot" style={{ animationDelay: '0ms' }} />
            <span className="thinking-dot" style={{ animationDelay: '160ms' }} />
            <span className="thinking-dot" style={{ animationDelay: '320ms' }} />
            <span className="intro-footer-text">Connecting to the GM…</span>
          </div>
        )}
      </div>
    )
  }

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
