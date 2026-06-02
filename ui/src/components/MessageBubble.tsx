import { useState } from 'react'
import type { Message, MessageSpeaker } from '../types'

interface Props {
  message: Message
  isLast: boolean
  streaming: boolean
}

// ── Intro markdown renderer ───────────────────────────────────────────────────

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

// ── Player speaker label components ──────────────────────────────────────────

function CharacterLabel({ speaker }: { speaker: MessageSpeaker }) {
  const [imgOk, setImgOk] = useState(true)
  return (
    <div className="bubble-speaker">
      <span className="bubble-speaker-name" style={{ color: speaker.color }}>
        {speaker.name}
      </span>
      <div
        className="bubble-speaker-portrait"
        data-testid="bubble-speaker-portrait"
        style={{ borderColor: speaker.color, '--speaker-color': speaker.color } as React.CSSProperties}
      >
        {imgOk
          ? <img
              src={speaker.portrait}
              alt={speaker.name}
              className="bubble-speaker-img"
              onError={() => setImgOk(false)}
            />
          : <span className="bubble-speaker-rune" style={{ color: speaker.color }}>{speaker.rune}</span>
        }
      </div>
    </div>
  )
}

function PartyLabel() {
  return (
    <div className="bubble-speaker">
      <div className="bubble-speaker-party" data-testid="bubble-speaker-party">
        <span className="bubble-speaker-party-text">player</span>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function MessageBubble({ message, isLast, streaming }: Props) {
  if (message.role === 'ending') {
    return (
      <div className="ending-card">
        <span className="ending-dot" style={{ animationDelay: '0ms' }} />
        <span className="ending-dot" style={{ animationDelay: '160ms' }} />
        <span className="ending-dot" style={{ animationDelay: '320ms' }} />
        <span className="ending-text">{message.content}</span>
      </div>
    )
  }

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

  if (message.role === 'gm') {
    const showThinkingDots = isLast && streaming && message.content.trim() === ''
    return (
      <div className="bubble-row gm">
        <div className="bubble-label">GM</div>
        <div className={`bubble bubble-gm${showThinkingDots ? ' thinking-bubble' : ''}`}>
          {showThinkingDots && (
            <>
              <span className="thinking-dot" style={{ animationDelay: '0ms' }} />
              <span className="thinking-dot" style={{ animationDelay: '160ms' }} />
              <span className="thinking-dot" style={{ animationDelay: '320ms' }} />
            </>
          )}
          {message.content}
          {isLast && streaming && <span className="cursor">▋</span>}
        </div>
      </div>
    )
  }

  // Player message
  return (
    <div className="bubble-row player">
      {message.speaker
        ? <CharacterLabel speaker={message.speaker} />
        : <PartyLabel />
      }
      <div className="bubble bubble-player">
        {message.content}
      </div>
    </div>
  )
}

