/**
 * Chat display AC coverage.
 *
 * Covers chat-display.feature AC-002 through AC-005 and the visible pieces of
 * player-turn.feature AC-001/AC-005. App-level tests cover submit plumbing.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatWindow from '../ChatWindow'
import type { Message } from '../../types'

describe('ChatWindow - AC-002 thinking indicator', () => {
  it('shows three staggered dots while a player message is waiting for GM tokens', () => {
    const messages: Message[] = [{ role: 'player', content: 'I look around.' }]
    const { container } = render(<ChatWindow messages={messages} streaming={true} />)

    const dots = container.querySelectorAll('.thinking-bubble .thinking-dot')
    expect(dots).toHaveLength(3)
    expect(dots[0]).toHaveStyle({ animationDelay: '0ms' })
    expect(dots[1]).toHaveStyle({ animationDelay: '160ms' })
    expect(dots[2]).toHaveStyle({ animationDelay: '320ms' })
  })

  it('hides the thinking indicator after the first GM token creates a GM bubble', () => {
    const messages: Message[] = [
      { role: 'player', content: 'I look around.' },
      { role: 'gm', content: 'The ' },
    ]
    const { container } = render(<ChatWindow messages={messages} streaming={true} />)

    expect(container.querySelector('.thinking-bubble')).not.toBeInTheDocument()
  })

  it('shows three dots in an empty GM bubble while it is streaming', () => {
    const messages: Message[] = [{ role: 'gm', content: '' }]
    const { container } = render(<ChatWindow messages={messages} streaming={true} />)

    const dots = container.querySelectorAll('.bubble-gm.thinking-bubble .thinking-dot')
    expect(dots).toHaveLength(3)
  })
})

describe('ChatWindow - AC-003 token bubble and cursor', () => {
  it('shows the animated cursor on the last GM bubble while streaming', () => {
    const messages: Message[] = [{ role: 'gm', content: 'The tavern is quiet.' }]
    const { container } = render(<ChatWindow messages={messages} streaming={true} />)

    expect(screen.getByText(/The tavern is quiet/)).toBeInTheDocument()
    expect(container.querySelector('.cursor')).toBeInTheDocument()
  })

  it('removes the cursor when streaming completes', () => {
    const messages: Message[] = [{ role: 'gm', content: 'The tavern is quiet.' }]
    const { container } = render(<ChatWindow messages={messages} streaming={false} />)

    expect(container.querySelector('.cursor')).not.toBeInTheDocument()
  })
})

describe('ChatWindow - AC-004 intro markdown', () => {
  it('renders intro markdown headings, rule, bold, italic, and connecting footer', () => {
    const messages: Message[] = [
      {
        role: 'intro',
        content: '# Festival\n## Dawn\n---\nThis is **bold** and *bright*.',
      },
    ]
    const { container } = render(<ChatWindow messages={messages} streaming={true} />)

    expect(screen.getByRole('heading', { name: 'Festival', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dawn', level: 3 })).toBeInTheDocument()
    expect(container.querySelector('.intro-hr')).toBeInTheDocument()
    expect(container.querySelector('strong')).toHaveTextContent('bold')
    expect(container.querySelector('em')).toHaveTextContent('bright')
    expect(screen.getByText(/Connecting to the GM/)).toBeInTheDocument()
  })
})

describe('ChatWindow - AC-005 autoscroll', () => {
  it('scrolls to the bottom when messages change', () => {
    const spy = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView')
    const { rerender } = render(
      <ChatWindow messages={[{ role: 'gm', content: 'First' }]} streaming={false} />,
    )

    rerender(
      <ChatWindow
        messages={[
          { role: 'gm', content: 'First' },
          { role: 'gm', content: 'Second' },
        ]}
        streaming={false}
      />,
    )

    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('scrolls while streaming state changes', () => {
    const spy = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView')
    const messages: Message[] = [{ role: 'gm', content: 'Streaming text' }]
    const { rerender } = render(<ChatWindow messages={messages} streaming={false} />)

    rerender(<ChatWindow messages={messages} streaming={true} />)

    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })
})
