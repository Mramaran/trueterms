/**
 * ToolsPanel.jsx
 * ===============
 * Claude-style tools panel with:
 * - Contract Validator
 * - JSON Formatter
 * - Share conversation
 * - Theme toggle
 */

import { useState } from 'react'
import {
  X, CheckCircle, Code2, Share2, Sun, Moon,
  Copy, CheckCheck, Download, Wrench
} from 'lucide-react'
import { useTheme } from '../hooks/useTheme'

export default function ToolsPanel({ onClose, messages }) {
  const [activeTool, setActiveTool] = useState(null)
  const { theme, toggleTheme } = useTheme()

  const tools = [
    { id: 'validator',  icon: <CheckCircle size={18} />, label: 'Contract Validator',  desc: 'Validate ACTUS contract JSON' },
    { id: 'formatter',  icon: <Code2 size={18} />,       label: 'JSON Formatter',      desc: 'Prettify or minify JSON' },
    { id: 'share',      icon: <Share2 size={18} />,       label: 'Share',               desc: 'Share this conversation' },
    { id: 'theme',      icon: theme === 'light' ? <Moon size={18} /> : <Sun size={18} />,
                                                          label: theme === 'light' ? 'Dark Mode' : 'Light Mode',
                                                          desc: 'Toggle dark / light theme' },
  ]

  const handleTool = (id) => {
    if (id === 'theme') { toggleTheme(); return }
    setActiveTool(activeTool === id ? null : id)
  }

  return (
    <div className="tools-panel">
      {/* Header */}
      <div className="tools-header">
        <div className="tools-title">
          <Wrench size={16} />
          <span>Tools</span>
        </div>
        <button className="icon-btn" onClick={onClose} title="Close tools">
          <X size={16} />
        </button>
      </div>

      {/* Tool buttons */}
      <div className="tools-list">
        {tools.map(tool => (
          <button
            key={tool.id}
            className={`tool-item ${activeTool === tool.id ? 'active' : ''}`}
            onClick={() => handleTool(tool.id)}
            title={tool.desc}
          >
            <div className="tool-icon">{tool.icon}</div>
            <div className="tool-info">
              <span className="tool-label">{tool.label}</span>
              <span className="tool-desc">{tool.desc}</span>
            </div>
          </button>
        ))}
      </div>

      {/* Active tool content */}
      {activeTool === 'validator' && <ContractValidator />}
      {activeTool === 'formatter'  && <JsonFormatter />}
      {activeTool === 'share'      && <ShareTool messages={messages} />}
    </div>
  )
}

/* ── Contract Validator ── */
function ContractValidator() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState(null)

  const REQUIRED_FIELDS = ['contractType', 'contractID', 'statusDate', 'contractRole']

  const validate = () => {
    try {
      const parsed = JSON.parse(input)
      const missing = REQUIRED_FIELDS.filter(f => !parsed[f] && !parsed.terms?.[f])
      const hasContractType = parsed.contractType || parsed.terms?.contractType

      if (missing.length === 0) {
        setResult({ ok: true, msg: `✅ Valid! Contract type: ${hasContractType}` })
      } else {
        setResult({ ok: false, msg: `⚠️ Missing fields: ${missing.join(', ')}` })
      }
    } catch {
      setResult({ ok: false, msg: '❌ Invalid JSON — check syntax' })
    }
  }

  return (
    <div className="tool-content">
      <p className="tool-content-title">Contract Validator</p>
      <textarea
        className="tool-textarea"
        placeholder='Paste contract JSON here...'
        value={input}
        onChange={e => setInput(e.target.value)}
        rows={6}
      />
      <button className="tool-run-btn" onClick={validate} disabled={!input.trim()}>
        Validate
      </button>
      {result && (
        <div className={`tool-result ${result.ok ? 'ok' : 'err'}`}>
          {result.msg}
        </div>
      )}
    </div>
  )
}

/* ── JSON Formatter ── */
function JsonFormatter() {
  const [input, setInput]   = useState('')
  const [output, setOutput] = useState('')
  const [copied, setCopied] = useState(false)
  const [mode, setMode]     = useState('pretty')

  const format = () => {
    try {
      const parsed = JSON.parse(input)
      setOutput(mode === 'pretty'
        ? JSON.stringify(parsed, null, 2)
        : JSON.stringify(parsed)
      )
    } catch {
      setOutput('❌ Invalid JSON')
    }
  }

  const copy = () => {
    navigator.clipboard.writeText(output)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="tool-content">
      <p className="tool-content-title">JSON Formatter</p>
      <div className="tool-mode-row">
        <button className={`tool-mode-btn ${mode === 'pretty' ? 'active' : ''}`} onClick={() => setMode('pretty')}>Prettify</button>
        <button className={`tool-mode-btn ${mode === 'minify' ? 'active' : ''}`} onClick={() => setMode('minify')}>Minify</button>
      </div>
      <textarea className="tool-textarea" placeholder="Paste JSON here..." value={input} onChange={e => setInput(e.target.value)} rows={5} />
      <button className="tool-run-btn" onClick={format} disabled={!input.trim()}>Format</button>
      {output && (
        <div className="tool-output-wrapper">
          <div className="tool-output-header">
            <span className="tool-content-title">Output</span>
            <button className="copy-btn" onClick={copy}>
              {copied ? <><CheckCheck size={12}/> Copied!</> : <><Copy size={12}/> Copy</>}
            </button>
          </div>
          <pre className="tool-output">{output}</pre>
        </div>
      )}
    </div>
  )
}

/* ── Share Tool ── */
function ShareTool({ messages }) {
  const [copied, setCopied] = useState(false)
  const [copiedText, setCopiedText] = useState(false)

  const generateShareHTML = () => {
    const title = messages[0]?.content?.slice(0, 60) || 'TrueTerms Chat'
    const rows = messages.map(m => {
      const isUser = m.role === 'user'
      const bg = isUser ? '#1e293b' : '#0f172a'
      const label = isUser ? '👤 You' : '🤖 TrueTerms'
      const content = m.content
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/\n/g,'<br/>')
      return `<div style="background:${bg};border-radius:12px;padding:16px 20px;margin-bottom:12px">
        <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;font-weight:600">${label}</div>
        <div style="color:#e2e8f0;font-size:14px;line-height:1.6">${content}</div>
      </div>`
    }).join('')

    return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} — TrueTerms</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#020817;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh}
.header{background:#0f172a;border-bottom:1px solid #1e293b;padding:16px 24px;display:flex;align-items:center;gap:12px}
.logo{color:#3b82f6;font-weight:700;font-size:18px}.sub{color:#64748b;font-size:13px;margin-left:auto}
.container{max-width:780px;margin:0 auto;padding:32px 16px}
.title{font-size:20px;font-weight:700;margin-bottom:24px;color:#f1f5f9}
.footer{text-align:center;color:#334155;font-size:12px;margin-top:32px;padding-top:16px;border-top:1px solid #1e293b}
</style></head><body>
<div class="header"><span class="logo">⚡ TrueTerms</span><span class="sub">Shared conversation · ${new Date().toLocaleDateString()}</span></div>
<div class="container"><p class="title">${title}</p>${rows}
<div class="footer">Shared from TrueTerms — AI-powered financial contract assistant</div></div>
</body></html>`
  }

  const shareAsPage = () => {
    const html = generateShareHTML()
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  }

  const downloadHTML = () => {
    const html = generateShareHTML()
    const blob = new Blob([html], { type: 'text/html' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `actus-chat-${Date.now()}.html`
    a.click()
  }

  const copyAsText = () => {
    const text = messages.map(m =>
      `${m.role === 'user' ? 'You' : 'TrueTerms'}:\n${m.content}`
    ).join('\n\n---\n\n')
    navigator.clipboard.writeText(text)
    setCopiedText(true)
    setTimeout(() => setCopiedText(false), 2000)
  }

  return (
    <div className="tool-content">
      <p className="tool-content-title">Share Conversation</p>
      <p className="tool-share-sub">{messages.length} message{messages.length !== 1 ? 's' : ''} in this conversation</p>
      <div className="tool-share-btns">
        <button className="tool-share-btn primary" onClick={shareAsPage}>
          <Share2 size={15}/> Open as shareable page
        </button>
        <button className="tool-share-btn" onClick={downloadHTML}>
          <Download size={15}/> Download as HTML
        </button>
        <button className="tool-share-btn" onClick={copyAsText}>
          {copiedText ? <CheckCheck size={15}/> : <Copy size={15}/>}
          {copiedText ? 'Copied!' : 'Copy as text'}
        </button>
      </div>
    </div>
  )
}
