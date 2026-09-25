/**
 * MessageBubble.jsx — with Markdown + Edit + Copy + Regenerate
 */

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ChevronDown, ChevronUp, CheckCircle, XCircle,
  Database, Globe, Copy, Check, Pencil, RotateCcw,
  ThumbsUp, ThumbsDown, Share2
} from 'lucide-react'
import ActusRunner from './ActusRunner'

// ACTUS contract types list for detection
const ACTUS_TYPES = ['PAM','ANN','LAM','LAX','CLM','UMP','CSH','STK','COM','SWAPS',
  'SWPPV','FXOUT','CAPFL','FUTUR','OPTNS','CEG','CEC','MRGNG']

function extractActusContract(code) {
  try {
    const parsed = JSON.parse(code)
    // Handle { contracts: [...], riskFactors: [...] } wrapper (Postman format)
    if (parsed?.contracts && Array.isArray(parsed.contracts) && parsed.contracts.length > 0) {
      const inner = parsed.contracts[0]
      const ct = (inner?.contractType || inner?.ContractType || '').toUpperCase()
      if (ACTUS_TYPES.includes(ct)) {
        // Return full payload so riskFactors are preserved
        return { contract: inner, riskFactors: parsed.riskFactors || [] }
      }
    }
    // Handle array of contracts
    const obj = Array.isArray(parsed) ? parsed[0] : parsed
    if (!obj || typeof obj !== 'object') return null
    const ct = (obj.contractType || obj.ContractType || '').toUpperCase()
    if (ACTUS_TYPES.includes(ct)) return { contract: obj, riskFactors: [] }
    // Nested contractTerms
    if (obj.contractTerms) {
      const ct2 = (obj.contractTerms.contractType || '').toUpperCase()
      if (ACTUS_TYPES.includes(ct2)) return { contract: obj.contractTerms, riskFactors: [] }
    }
    return null
  } catch { return null }
}

export default function MessageBubble({ message, onEdit, onRegenerate }) {
  const [showMeta, setShowMeta] = useState(false)
  const [copied,   setCopied]   = useState(false)
  const [liked,    setLiked]    = useState(null)  // null | 'up' | 'down'
  const [editing,  setEditing]  = useState(false)
  const [editVal,  setEditVal]  = useState(message.content)
  const isUser    = message.role === 'user'
  const isStreaming = message.streaming === true

  const copyMessage = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const shareMessage = () => {
    if (navigator.share) navigator.share({ text: message.content }).catch(() => {})
    else navigator.clipboard.writeText(message.content)
  }

  const submitEdit = () => {
    if (editVal.trim() && editVal !== message.content) onEdit?.(message.id, editVal.trim())
    setEditing(false)
  }

  const cancelEdit = () => { setEditVal(message.content); setEditing(false) }

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="avatar assistant-avatar">A</div>}

      <div className="bubble-wrapper">

        {editing ? (
          <div className="edit-box">
            <textarea
              className="edit-textarea"
              value={editVal}
              onChange={e => setEditVal(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitEdit() }
                if (e.key === 'Escape') cancelEdit()
              }}
              autoFocus
              rows={3}
            />
            <div className="edit-actions">
              <button className="edit-send-btn" onClick={submitEdit}>Send</button>
              <button className="edit-cancel-btn" onClick={cancelEdit}>Cancel</button>
            </div>
          </div>
        ) : (
          <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
            {isUser
              ? <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
              : <MarkdownContent content={message.content} isStreaming={isStreaming} />
            }
          </div>
        )}

        {/* Bottom action bar — pure CSS hover reveal; hide while streaming */}
        {!editing && !isStreaming && (
          <div className={`msg-action-bar ${isUser ? 'bar-user' : 'bar-assistant'}`}>
            {/* Assistant actions */}
            {!isUser && (
              <>
                <button
                  className={`msg-icon-btn ${copied ? 'active-green' : ''}`}
                  onClick={copyMessage}
                  title="Copy"
                >
                  {copied ? <Check size={14}/> : <Copy size={14}/>}
                </button>
                <div className="msg-bar-divider" />
                <button
                  className={`msg-icon-btn ${liked === 'up' ? 'active-blue' : ''}`}
                  onClick={() => setLiked(p => p === 'up' ? null : 'up')}
                  title="Good response"
                >
                  <ThumbsUp size={14}/>
                </button>
                <button
                  className={`msg-icon-btn ${liked === 'down' ? 'active-red' : ''}`}
                  onClick={() => setLiked(p => p === 'down' ? null : 'down')}
                  title="Bad response"
                >
                  <ThumbsDown size={14}/>
                </button>
                {onRegenerate && (
                  <>
                    <div className="msg-bar-divider" />
                    <button
                      className="msg-icon-btn"
                      onClick={() => onRegenerate(message.id)}
                      title="Regenerate"
                    >
                      <RotateCcw size={14}/>
                    </button>
                  </>
                )}
                <button className="msg-icon-btn" onClick={shareMessage} title="Share">
                  <Share2 size={14}/>
                </button>
              </>
            )}
            {/* User actions */}
            {isUser && (
              <>
                <button
                  className={`msg-icon-btn ${copied ? 'active-green' : ''}`}
                  onClick={copyMessage}
                  title="Copy"
                >
                  {copied ? <Check size={14}/> : <Copy size={14}/>}
                </button>
                <button
                  className="msg-icon-btn"
                  onClick={() => { setEditVal(message.content); setEditing(true) }}
                  title="Edit"
                >
                  <Pencil size={14}/>
                </button>
              </>
            )}
          </div>
        )}

        {/* Pipeline metadata */}
        {!isUser && message.meta && (
          <div className="meta-section">
            <button className="meta-toggle" onClick={() => setShowMeta(p => !p)}>
              {showMeta ? <ChevronUp size={13}/> : <ChevronDown size={13}/>}
              <span>Pipeline info</span>
            </button>
            {showMeta && (
              <div className="meta-details">
                <div className="meta-item">
                  {message.meta.route === 'vectorstore' ? <Database size={13}/> : <Globe size={13}/>}
                  <span>Route: <strong>{message.meta.route}</strong></span>
                </div>
                <div className="meta-item">
                  <span>Docs: <strong>{message.meta.docs_used}/{message.meta.docs_total}</strong></span>
                </div>
                <div className="meta-item">
                  {message.meta.grounded === 'yes'
                    ? <CheckCircle size={13} className="green"/>
                    : <XCircle size={13} className="red"/>}
                  <span>Grounded: <strong>{message.meta.grounded === 'yes' ? 'Yes ✅' : 'No ❌'}</strong></span>
                </div>
                <div className="meta-item">
                  <span>Iterations: <strong>{message.meta.iterations}</strong></span>
                </div>
                {message.meta.sources?.length > 0 && (
                  <div className="meta-sources">
                    <span>Sources:</span>
                    {message.meta.sources.map((s, i) => <span key={i} className="source-tag">{s}</span>)}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {isUser && <div className="avatar user-avatar">H</div>}
    </div>
  )
}

/* ── Markdown renderer with collapse for long content ── */
const COLLAPSE_THRESHOLD = 3000  // chars — collapse anything longer than this

function MarkdownContent({ content, isStreaming }) {
  const isLong = content.length > COLLAPSE_THRESHOLD
  const [expanded, setExpanded] = useState(!isLong)
  const displayContent = expanded ? content : content.slice(0, COLLAPSE_THRESHOLD) + '...'

  return (
    <div className="markdown-body">
      {isStreaming && <span className="streaming-cursor" />}
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const code = String(children).replace(/\n$/, '')
            // Treat as inline if: explicitly inline, no newlines, or short (table cells, field names)
            const isInline = inline || (!code.includes('\n') && code.length < 80)
            if (isInline) return <code className="inline-code" {...props}>{code}</code>
            const lang = (className || '').replace('language-', '')
            return <CodeBlock code={code} lang={lang} />
          },
          a({ href, children }) {
            return <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">{children}</a>
          },
        }}
      >
        {displayContent}
      </ReactMarkdown>
      {isLong && (
        <button
          onClick={() => setExpanded(p => !p)}
          className="show-full-btn"
          style={{
            display: 'flex', alignItems: 'center', gap: 6
          }}
        >
          {expanded ? <>▲ Collapse response</> : <>▼ Show full response ({Math.round(content.length/1000)}K chars)</>}
        </button>
      )}
    </div>
  )
}

function CodeBlock({ code, lang }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Only show ActusRunner if the code is a COMPLETE standalone generated contract.
  // NEVER show ActusRunner for example JSONs inside explanations/definitions.
  const actusContract = (lang === 'json' || !lang) ? extractActusContract(code) : null

  // A standalone generated contract MUST have ALL of these fields.
  // Example JSONs in explanations often use placeholder/past dates or missing fields.
  const isStandaloneContract = actusContract &&
    actusContract.contract?.contractID &&
    actusContract.contract?.statusDate &&
    actusContract.contract?.maturityDate &&
    actusContract.contract?.notionalPrincipal &&
    actusContract.contract?.nominalInterestRate &&
    actusContract.contract?.dayCountConvention &&
    actusContract.contract?.contractRole &&
    actusContract.contract?.currency &&
    // Key guard: generated contracts have contractDealDate; example JSONs usually don't
    actusContract.contract?.contractDealDate &&
    // Key guard: generated contracts always have cycleOfInterestPayment
    actusContract.contract?.cycleOfInterestPayment

  // If this is a complete standalone ACTUS contract, show ActusRunner
  if (isStandaloneContract) {
    return <ActusRunner contractJson={actusContract.contract} riskFactors={actusContract.riskFactors} />
  }

  return (
    <div className="code-block">
      {lang && <div className="code-lang">{lang}</div>}
      <pre><code>{code}</code></pre>
      <button className="copy-btn" onClick={copy}>
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}
