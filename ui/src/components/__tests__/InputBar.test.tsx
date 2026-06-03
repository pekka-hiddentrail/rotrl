import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InputBar from '../InputBar'

const noop = vi.fn()

describe('InputBar — baseline behaviour', () => {
  it('renders the textarea and Send button', () => {
    render(<InputBar onSend={noop} disabled={false} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('Send button is disabled when input is empty', () => {
    render(<InputBar onSend={noop} disabled={false} />)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('calls onSend with the typed text and clears the field', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} />)
    await user.type(screen.getByRole('textbox'), 'Hello world')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(onSend).toHaveBeenCalledOnce()
    expect(onSend).toHaveBeenCalledWith('Hello world', [])
    expect(screen.getByRole('textbox')).toHaveValue('')
  })

  it('sends on Enter key', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} />)
    await user.type(screen.getByRole('textbox'), 'Test{Enter}')
    expect(onSend).toHaveBeenCalledWith('Test', [])
  })

  it('does NOT send on Shift+Enter', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<InputBar onSend={onSend} disabled={false} />)
    await user.type(screen.getByRole('textbox'), 'Line1{Shift>}{Enter}{/Shift}Line2')
    expect(onSend).not.toHaveBeenCalled()
  })
})

describe('InputBar — speaker badge', () => {
  const speaker = { name: 'Yanyeeku', rune: 'ᚠ', color: '#a060d0' }

  it('shows no badge when activeSpeaker is null', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={null} />)
    expect(screen.queryByText(/Speaking as/i)).not.toBeInTheDocument()
  })

  it('shows badge with character name when activeSpeaker is set', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={speaker} />)
    expect(screen.getByText(/Speaking as/i)).toBeInTheDocument()
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
  })

  it('shows the character rune in the badge', () => {
    render(<InputBar onSend={noop} disabled={false} activeSpeaker={speaker} />)
    expect(screen.getByText('ᚠ')).toBeInTheDocument()
  })

  it('removes badge when activeSpeaker becomes null', () => {
    const { rerender } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={speaker} />)
    expect(screen.getByText(/Speaking as/i)).toBeInTheDocument()
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={null} />)
    expect(screen.queryByText(/Speaking as/i)).not.toBeInTheDocument()
  })

  it('updates badge when activeSpeaker changes to a different character', () => {
    const ani = { name: 'Ani', rune: 'ᚢ', color: '#60a0d0' }
    const { rerender } = render(<InputBar onSend={noop} disabled={false} activeSpeaker={speaker} />)
    expect(screen.getByText('Yanyeeku')).toBeInTheDocument()
    rerender(<InputBar onSend={noop} disabled={false} activeSpeaker={ani} />)
    expect(screen.getByText('Ani')).toBeInTheDocument()
    expect(screen.queryByText('Yanyeeku')).not.toBeInTheDocument()
  })
})

describe('InputBar — disabled state', () => {
  it('shows … on the Send button when disabled', () => {
    render(<InputBar onSend={noop} disabled={true} />)
    expect(screen.getByRole('button', { name: '…' })).toBeInTheDocument()
  })

  it('textarea is disabled when disabled=true', () => {
    render(<InputBar onSend={noop} disabled={true} />)
    expect(screen.getByRole('textbox')).toBeDisabled()
  })
})


