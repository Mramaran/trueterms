/**
 * ChatWindow.jsx — Messages display area with edit support
 */

import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'
import { FileText, Share2 } from 'lucide-react'

function downloadMarkdown(messages) {
  if (!messages.length) return
  const title = messages[0]?.content?.slice(0, 60) || 'ACTUS Chat'
  const lines = [`# ${title}`, `*Exported from TrueTerms — ${new Date().toLocaleString()}*`, '']
  messages.forEach(m => {
    lines.push(`## ${m.role === 'user' ? '👤 You' : '🤖 TrueTerms'}`)
    lines.push(m.content)
    lines.push('')
  })
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `actus-chat-${Date.now()}.md`
  a.click()
}

async function shareAsPage(messages, setShareState) {
  if (!messages.length) return
  const title = messages[0]?.content?.slice(0, 60) || 'TrueTerms Chat'
  setShareState('loading')
  try {
    const res = await fetch('http://localhost:8000/share', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages.map(m => ({ role: m.role, content: m.content })), title })
    })
    const data = await res.json()
    const url = `http://localhost:8000${data.url}`
    await navigator.clipboard.writeText(url)
    window.open(url, '_blank')
    setShareState('copied')
    setTimeout(() => setShareState('idle'), 3000)
  } catch {
    setShareState('idle')
    alert('Share failed — make sure backend is running')
  }
}

export default function ChatWindow({ messages, loading, onEdit, onRegenerate }) {
  const bottomRef = useRef(null)
  const [shareState, setShareState] = useState('idle') // idle | loading | copied

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="chat-window">
      {messages.length > 0 && (
        <div className="chat-window-actions">
          <button className="chat-action-btn" onClick={() => downloadMarkdown(messages)} title="Download as Markdown">
            <FileText size={15} />
          </button>
          <button className="chat-action-btn" onClick={() => shareAsPage(messages, setShareState)} title="Share conversation" disabled={shareState === 'loading'}>
            {shareState === 'copied' ? '✓ Link copied!' : shareState === 'loading' ? '...' : <Share2 size={15} />}
          </button>
        </div>
      )}
      <div className="messages-list">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} onEdit={onEdit} onRegenerate={onRegenerate} />
        ))}

        {/* Typing indicator — shown only while waiting for first token */}
        {loading && messages.length > 0 && messages[messages.length - 1]?.role === 'user' && (
          <div className="message assistant" style={{paddingBottom: 12}}>
            <div className="avatar assistant-avatar">A</div>
            <div className="bubble assistant-bubble">
              <div className="typing-indicator-row">
                <div className="typing-indicator"><span /><span /><span /></div>
                <span className="typing-label">TrueTerms is thinking…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
