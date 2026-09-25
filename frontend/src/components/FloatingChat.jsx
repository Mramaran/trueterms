/**
 * FloatingChat.jsx — Lightweight floating popup chat window
 */

import { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Minus, Maximize2, Bot } from 'lucide-react'
import { sendChat } from '../services/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function FloatingChat() {
  const [open, setOpen]       = useState(false)
  const [minimized, setMin]   = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [unread, setUnread]   = useState(0)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  useEffect(() => {
    if (open) {
      setUnread(0)
      setMin(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const q = input.trim()
    setInput('')

    const userMsg = { id: Date.now(), role: 'user', content: q }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const data = await sendChat(q)
      const aiMsg = { id: Date.now() + 1, role: 'assistant', content: data.answer }
      setMessages(prev => [...prev, aiMsg])
      if (!open || minimized) setUnread(n => n + 1)
    } catch (err) {
      const errMsg = { id: Date.now() + 1, role: 'assistant', content: `❌ ${err.message}` }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const clearChat = () => setMessages([])

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          className="floating-chat-btn"
          onClick={() => setOpen(true)}
          title="Quick Chat"
        >
          <MessageCircle size={22} />
          {unread > 0 && <span className="floating-badge">{unread}</span>}
        </button>
      )}

      {/* Chat window */}
      {open && (
        <div className={`floating-chat ${minimized ? 'minimized' : ''}`}>

          {/* Header */}
          <div className="floating-chat-header" onClick={() => minimized && setMin(false)}>
            <div className="floating-chat-title">
              <Bot size={16} />
              <span>Quick Chat</span>
              {loading && <span className="floating-typing">typing…</span>}
            </div>
            <div className="floating-chat-controls">
              {messages.length > 0 && !minimized && (
                <button className="float-ctrl-btn" onClick={clearChat} title="Clear chat">
                  🗑
                </button>
              )}
              <button className="float-ctrl-btn" onClick={() => setMin(p => !p)} title={minimized ? 'Expand' : 'Minimize'}>
                {minimized ? <Maximize2 size={14} /> : <Minus size={14} />}
              </button>
              <button className="float-ctrl-btn" onClick={() => setOpen(false)} title="Close">
                <X size={14} />
              </button>
            </div>
          </div>

          {!minimized && (
            <>
              {/* Messages */}
              <div className="floating-messages">
                {messages.length === 0 && (
                  <div className="floating-empty">
                    <Bot size={28} style={{ opacity: 0.3 }} />
                    <p>Quick questions about ACTUS?<br />Ask me anything!</p>
                  </div>
                )}

                {messages.map(msg => (
                  <div key={msg.id} className={`floating-msg ${msg.role}`}>
                    {msg.role === 'assistant' ? (
                      <div className="floating-msg-bubble assistant">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <div className="floating-msg-bubble user">{msg.content}</div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="floating-msg assistant">
                    <div className="floating-msg-bubble assistant">
                      <div className="typing-indicator"><span /><span /><span /></div>
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>

              {/* Input */}
              <div className="floating-input-area">
                <textarea
                  ref={inputRef}
                  className="floating-textarea"
                  placeholder="Ask a quick question…"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  rows={1}
                  disabled={loading}
                />
                {loading && (
                  <button className="floating-stop-btn" onClick={handleStop} title="Stop generating">
                    <div className="stop-icon" />
                  </button>
                )}
                {!loading && (
                  <button
                    className={`floating-send-btn ${input.trim() ? 'active' : ''}`}
                    onClick={handleSend}
                    disabled={!input.trim()}
                  >
                    <Send size={15} />
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}
