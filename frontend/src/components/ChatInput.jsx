/**
 * ChatInput.jsx — Text input with @mention tools, + menu, voice, stop
 *   ✦ Voice waveform visualiser while recording
 *   ✦ Voice contract detection banner
 *   ✦ Mic health-check (disables button if backend unavailable)
 *   ✦ "Listening…" / "Transcribing…" / "Preparing…" status labels
 */

import { useState, useRef, useEffect } from 'react'
import {
  Send, Mic, MicOff, Loader2, X, FileText,
  Plus, Wrench, FolderOpen, ImagePlus, Zap
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useVoice } from '../hooks/useVoice'
import VoiceWaveform from './VoiceWaveform'
import ToolsPanel from './ToolsPanel'
import AtMentionMenu from './AtMentionMenu'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Tooltip wrapper
function Tip({ label, children, disabled }) {
  return (
    <div className="tip-wrapper">
      {children}
      {label && <span className={`tooltip ${disabled ? 'tooltip-warn' : ''}`}>{label}</span>}
    </div>
  )
}

export default function ChatInput({ onSend, loading, messages, onStop, onVoiceContract }) {
  const [value,          setValue]          = useState('')
  const [showTools,      setShowTools]      = useState(false)
  const [showPlusMenu,   setShowPlusMenu]   = useState(false)
  const [mentionQuery,   setMentionQuery]   = useState(null)
  const [activeMention,  setActiveMention]  = useState(null)
  const [images,         setImages]         = useState([])

  // Voice contract pending notification
  const [pendingContract, setPendingContract] = useState(null)
  const [pendingParams,   setPendingParams]   = useState(null)

  // Mic health state: null=checking | true=ok | false=unavailable
  const [voiceAvailable, setVoiceAvailable] = useState(null)

  const textareaRef    = useRef(null)
  const plusMenuRef    = useRef(null)
  const fileInputRef   = useRef(null)
  const folderInputRef = useRef(null)
  const imageInputRef  = useRef(null)
  const { t } = useTranslation()

  // ── Check voice backend availability on mount ────────────────────────────
  useEffect(() => {
    fetch(`${API_BASE}/health/voice`)
      .then(r => r.json())
      .then(d => setVoiceAvailable(d.available === true))
      .catch(() => setVoiceAvailable(false))
  }, [])

  // ── Voice hook ────────────────────────────────────────────────────────────
  const {
    status: voiceStatus, isRecording, isProcessing, isColdStart,
    errMsg: voiceErr, toggleRecording, analyserRef
  } = useVoice(
    (transcript) => setValue(prev => prev ? prev + ' ' + transcript : transcript),
    (contract, params) => {
      setPendingContract(contract)
      setPendingParams(params)
    }
  )

  // ── Image handling ────────────────────────────────────────────────────────
  const addImageFile = (file) => {
    if (!file || !file.type.startsWith('image/')) return
    const reader = new FileReader()
    reader.onload = e => setImages(prev => [...prev, { dataUrl: e.target.result, name: file.name }])
    reader.readAsDataURL(file)
  }

  useEffect(() => {
    const handler = (e) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of items) {
        if (item.type.startsWith('image/')) { e.preventDefault(); addImageFile(item.getAsFile()) }
      }
    }
    document.addEventListener('paste', handler)
    return () => document.removeEventListener('paste', handler)
  }, [])

  // ── Close plus menu on outside click ─────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (plusMenuRef.current && !plusMenuRef.current.contains(e.target)) setShowPlusMenu(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ── File/folder path detection ────────────────────────────────────────────
  const FILE_PATH_RE = /([A-Za-z]:\\[^\s"'<>|?*]+)/
  const detectedFile = value.match(FILE_PATH_RE)?.[1] || null
  const isFolder     = detectedFile && !detectedFile.split(/[/\\]/).pop()?.includes('.')
  const WRITE_KW     = ['write','create','save','edit','update','modify','change','fix','refactor','add','append','overwrite','replace']
  const isWriteMode  = detectedFile && !isFolder && WRITE_KW.some(k => value.toLowerCase().includes(k))

  // ── Text change handler ───────────────────────────────────────────────────
  const handleChange = (e) => {
    const newVal = e.target.value
    setValue(newVal)
    const ta = textareaRef.current
    if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 200) + 'px' }
    const cursor = e.target.selectionStart
    const atMatch = newVal.slice(0, cursor).match(/@(\w*)$/)
    setMentionQuery(atMatch ? atMatch[1] : null)
  }

  const handleSelectMention = (tool) => {
    const cursor = textareaRef.current?.selectionStart || value.length
    const textUpToCursor = value.slice(0, cursor)
    const atIdx = textUpToCursor.lastIndexOf('@')
    setValue(value.slice(0, atIdx) + value.slice(cursor))
    setActiveMention(tool)
    setMentionQuery(null)
    textareaRef.current?.focus()
  }

  const MAX_LEN = 4000

  // ── Send handler ──────────────────────────────────────────────────────────
  const handleSend = () => {
    if (!value.trim() || loading) return
    let finalQuery = value.trim()

    if (activeMention?.id === 'validator') {
      try { JSON.parse(finalQuery); alert('✅ Valid JSON!') }
      catch (e) { alert('❌ Invalid JSON: ' + e.message) }
      return
    }
    if (activeMention?.id === 'json') {
      try {
        const formatted = JSON.stringify(JSON.parse(finalQuery), null, 2)
        setValue(formatted)
      } catch (e) { alert('❌ Cannot format — invalid JSON: ' + e.message) }
      setActiveMention(null)
      return
    }
    if (activeMention?.id === 'explain') finalQuery = 'Explain this ACTUS term or attribute: ' + finalQuery
    if (activeMention?.id === 'search')  finalQuery = 'Search and answer: ' + finalQuery

    onSend(finalQuery, images)
    setValue('')
    setImages([])
    setActiveMention(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape' && mentionQuery !== null) { setMentionQuery(null); return }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  // ── Voice contract insert ─────────────────────────────────────────────────
  const handleInsertVoiceContract = () => {
    if (pendingContract && onVoiceContract) {
      onVoiceContract(pendingContract, pendingParams)
      setPendingContract(null)
      setPendingParams(null)
      setValue('')   // clear the transcript from input box
    }
  }

  // ── Mic button label / tooltip ────────────────────────────────────────────
  const micTooltip = voiceAvailable === false
    ? 'Voice unavailable — start the backend: uvicorn api_server:app'
    : isRecording  ? 'Click to stop & transcribe'
    : isColdStart  ? 'Preparing voice recognition…'
    : isProcessing ? (pendingContract ? 'Generating contract…' : 'Transcribing…')
    : 'Voice input (English)'

  const micDisabled = loading || isProcessing || voiceAvailable === false || voiceAvailable === null

  // ── Voice status label ────────────────────────────────────────────────────
  const voiceLabel = isRecording  ? 'Listening…'
    : isColdStart  ? 'Preparing voice recognition…'
    : isProcessing ? (pendingContract ? 'Generating contract…' : 'Transcribing…')
    : null

  const plusMenuItems = [
    { icon: <ImagePlus  size={16}/>, label: 'Add photo',      hint: 'Upload or paste an image',          onClick: () => { setShowPlusMenu(false); imageInputRef.current?.click() } },
    { icon: <FileText   size={16}/>, label: 'Read a file',    hint: 'Paste a file path to read it',      onClick: () => { setShowPlusMenu(false); fileInputRef.current?.click() } },
    { icon: <FolderOpen size={16}/>, label: 'Read a folder',  hint: 'Paste a folder path to explore it', onClick: () => { setShowPlusMenu(false); folderInputRef.current?.click() } },
    { icon: <Wrench     size={16}/>, label: 'Tools',          hint: 'Open tools panel',                  onClick: () => { setShowTools(p => !p); setShowPlusMenu(false) } },
  ]

  return (
    <div className="chat-input-wrapper">

      {/* Hidden file pickers */}
      <input ref={imageInputRef}  type="file" accept="image/*" multiple style={{display:'none'}}
        onChange={e => { Array.from(e.target.files||[]).forEach(addImageFile); e.target.value='' }} />
      <input ref={fileInputRef}   type="file" style={{display:'none'}}
        onChange={e => { const f=e.target.files?.[0]; if(f){ setValue(f.path||f.name); textareaRef.current?.focus() } e.target.value='' }} />
      <input ref={folderInputRef} type="file" style={{display:'none'}} webkitdirectory="true"
        onChange={e => { const f=e.target.files?.[0]; if(f){ const folder=(f.path||f.webkitRelativePath||f.name).split(/[\/\\]/)[0]; setValue(folder); textareaRef.current?.focus() } e.target.value='' }} />

      {/* Tools Panel */}
      {showTools && <ToolsPanel onClose={() => setShowTools(false)} messages={messages||[]} />}

      {/* Voice contract notification */}
      {pendingContract && (
        <div className="voice-contract-notice">
          <span className="voice-contract-icon"><Zap size={15}/></span>
          <div className="voice-contract-info">
            <strong>{pendingContract.contractType} contract detected</strong>
            <span>
              {pendingContract.notionalPrincipal?.toLocaleString()} {pendingContract.currency}
              {pendingContract.nominalInterestRate != null && ` · ${(pendingContract.nominalInterestRate*100).toFixed(1)}% p.a.`}
            </span>
          </div>
          <button className="voice-contract-insert-btn" onClick={handleInsertVoiceContract}>
            ⚡ Insert contract
          </button>
          <button className="voice-contract-dismiss" onClick={() => setPendingContract(null)} title="Dismiss">
            <X size={13}/>
          </button>
        </div>
      )}

      {/* File/folder path badge */}
      {detectedFile && (
        <div className="mention-badge-row">
          <div className="mention-badge" style={{ borderColor:'#3b82f655', background:'#3b82f618' }}>
            <span style={{color:'#3b82f6'}}>{isFolder ? '📁' : '📄'}</span>
            <span style={{color:'#3b82f6', fontWeight:600, maxWidth:320, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
              {detectedFile.split(/[/\\]/).pop() || detectedFile}
            </span>
          </div>
          <span className="mention-badge-hint">
            {isFolder ? 'Folder contents will be listed as context' : isWriteMode ? '✏️ File will be read, edited by AI, and saved back' : 'File will be read and sent as context'}
          </span>
        </div>
      )}

      {/* Active @mention badge */}
      {activeMention && (
        <div className="mention-badge-row">
          <div className="mention-badge" style={{ borderColor: activeMention.color+'55', background: activeMention.color+'18' }}>
            <span style={{color:activeMention.color}}>{activeMention.icon}</span>
            <span style={{color:activeMention.color, fontWeight:600}}>{activeMention.label}</span>
            <button className="mention-badge-remove" onClick={() => setActiveMention(null)}><X size={11}/></button>
          </div>
          <span className="mention-badge-hint">This tool will be used for your next message</span>
        </div>
      )}

      {/* Image previews */}
      {images.length > 0 && (
        <div className="image-preview-row">
          {images.map((img,i) => (
            <div key={i} className="image-preview-thumb">
              <img src={img.dataUrl} alt={img.name}/>
              <button className="image-preview-remove" onClick={() => setImages(prev => prev.filter((_,j) => j!==i))}><X size={11}/></button>
            </div>
          ))}
        </div>
      )}

      {/* Main input box */}
      <div className={`chat-input-box ${isRecording ? 'listening' : ''}`}>

        {/* @mention menu */}
        {mentionQuery !== null && (
          <AtMentionMenu query={mentionQuery} onSelect={handleSelectMention} onClose={() => setMentionQuery(null)} />
        )}

        {/* + Button */}
        <div className="plus-menu-wrapper" ref={plusMenuRef}>
          <Tip label="Add files, photos or tools">
            <button className={`action-btn plus-btn ${showPlusMenu ? 'active' : ''}`}
              onClick={() => setShowPlusMenu(p => !p)} disabled={loading}>
              <Plus size={18}/>
            </button>
          </Tip>
          {showPlusMenu && (
            <div className="plus-menu">
              {plusMenuItems.map((item,i) => (
                <button key={i} className="plus-menu-item" onClick={item.onClick}>
                  <span className="plus-menu-icon">{item.icon}</span>
                  <div style={{display:'flex', flexDirection:'column', alignItems:'flex-start'}}>
                    <span className="plus-menu-label">{item.label}</span>
                    {item.hint && <span style={{fontSize:11, opacity:0.6}}>{item.hint}</span>}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={
            isRecording  ? '🔴 Listening... click mic to stop' :
            isColdStart  ? '⏳ Preparing voice recognition...' :
            isProcessing ? '⏳ Transcribing...' :
            activeMention ? `Ask anything with ${activeMention.label}...` :
            t('inputPlaceholder')
          }
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={loading || isProcessing}
          maxLength={MAX_LEN}
        />

        {/* Character counter */}
        {value.length > MAX_LEN * 0.8 && (
          <span className={`char-counter ${value.length >= MAX_LEN ? 'at-limit' : ''}`}>
            {value.length}/{MAX_LEN}
          </span>
        )}

        <div className="chat-input-actions">

          {/* ── Mic button group ─────────────────────────────────────────── */}
          <div className="voice-input-group">
            <Tip label={micTooltip} disabled={voiceAvailable === false}>
              <button
                className={`action-btn mic-btn ${
                  isRecording  ? 'active recording' :
                  isProcessing ? 'processing' : ''
                } ${voiceAvailable === false ? 'unavailable' : ''}`}
                onClick={toggleRecording}
                disabled={micDisabled}
                aria-label={micTooltip}
              >
                {isProcessing
                  ? <Loader2 size={18} className="spinning" />
                  : isRecording
                    ? <MicOff size={18} />
                    : <Mic size={18} />}
              </button>
            </Tip>

            {/* Waveform / status indicator */}
            {(isRecording || isProcessing) ? (
              <div className="voice-status-row">
                <VoiceWaveform
                  analyserRef={analyserRef}
                  isRecording={isRecording}
                  isProcessing={isProcessing}
                />
                {voiceLabel && <span className="voice-status-label">{voiceLabel}</span>}
              </div>
            ) : (
              <span className="voice-en-badge">{voiceAvailable === false ? '✕' : 'EN'}</span>
            )}
          </div>

          {/* ── Stop / Send ──────────────────────────────────────────────── */}
          {loading ? (
            <Tip label="Stop generating">
              <button className="action-btn stop-btn" onClick={onStop}>
                <div className="stop-icon"/>
              </button>
            </Tip>
          ) : (
            <Tip label="Send message (Enter)">
              <button
                className={`action-btn send-btn ${value.trim() ? 'active' : ''}`}
                onClick={handleSend}
                disabled={!value.trim()}
              >
                <Send size={18}/>
              </button>
            </Tip>
          )}
        </div>
      </div>

      {/* Voice error */}
      {voiceErr && <p className="voice-error-hint">⚠️ {voiceErr}</p>}

      <p className="input-hint">
        {t('inputHint')} · Type <kbd>@</kbd> to invoke tools · 🎤 Voice + ⚡ smart contracts
      </p>
    </div>
  )
}
