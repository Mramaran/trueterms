/**
 * useChat.js — Chat logic with:
 *   - stop / edit / regenerate
 *   - localStorage persistence
 *   - rate limiting (3s cooldown)
 *   - UUID-based IDs (no Date.now() collisions)
 *   - Active agent system context support
 */

import { useState, useCallback, useRef } from 'react'
import { sendChat, readFile, writeFile } from '../services/api'

// Keywords that indicate user wants to write/edit a file
const WRITE_KEYWORDS = [
  'write', 'create', 'save', 'edit', 'update', 'modify', 'change',
  'fix', 'refactor', 'add', 'append', 'overwrite', 'replace'
]

function isWriteIntent(query) {
  const q = query.toLowerCase()
  return WRITE_KEYWORDS.some(k => q.includes(k))
}

// Detect Windows or Unix file/folder paths in a query
const FILE_PATH_REGEX = /([A-Za-z]:\\[^\s"'<>|?*\x00-\x1f]+|(?:\/[\w.-]+){2,})/g

const SUPPORTED_EXTENSIONS = new Set([
  '.txt','.md','.json','.csv','.py','.js','.jsx','.ts','.tsx',
  '.html','.css','.yaml','.yml','.toml','.cfg','.ini','.log',
  '.java','.cpp','.c','.h','.rs','.go','.sql'
])

function extractFilePath(query) {
  const matches = query.match(FILE_PATH_REGEX)
  if (!matches) return null
  for (const m of matches) {
    const lastPart = m.split(/[\\/]/).pop() || ''
    const ext = lastPart.includes('.') ? lastPart.substring(lastPart.lastIndexOf('.')).toLowerCase() : ''
    // Accept if it has a supported extension OR has no extension (likely a folder)
    if (SUPPORTED_EXTENSIONS.has(ext) || ext === '') return m
  }
  return null
}

const STORAGE_KEY  = 'actus-chats'
const COOLDOWN_MS  = 3000  // 3 seconds between messages
const MAX_QUERY_LEN = 4000

// ── Helpers ──────────────────────────────────────────────────────────────────
function uid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

function loadChats() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] }
  catch { return [] }
}

const MAX_STORAGE_BYTES = 2_000_000 // 2MB limit for localStorage

function saveChats(chats) {
  try {
    // Truncate any message content that's too large before saving
    const safechats = chats.map(chat => ({
      ...chat,
      messages: chat.messages.map(msg => ({
        ...msg,
        content: msg.content.length > 10_000
          ? msg.content.slice(0, 10_000) + '\n\n... [truncated — too large to save]'
          : msg.content
      }))
    }))
    const serialized = JSON.stringify(safechats)
    if (serialized.length > MAX_STORAGE_BYTES) {
      // If still too large, only keep the last 10 chats
      const trimmed = safechats.slice(-10)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
    } else {
      localStorage.setItem(STORAGE_KEY, serialized)
    }
  } catch {}
}

function loadActiveAgent() {
  try {
    const raw = localStorage.getItem('actus-active-agent')
    if (!raw) return null
    const agent = JSON.parse(raw)
    // Basic sanity check — never trust localStorage blindly
    if (typeof agent?.name !== 'string' || typeof agent?.systemPrompt !== 'string') return null
    return agent
  } catch { return null }
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useChat() {
  const [chats, setChatsRaw]        = useState(loadChats)
  const [activeChatId, setActiveChatId] = useState(() => loadChats()[0]?.id || null)
  const [loading, setLoading]       = useState(false)
  const [activeAgent, setActiveAgent] = useState(loadActiveAgent)
  const abortRef    = useRef(null)
  const lastSentRef = useRef(0)   // timestamp of last sent message

  const setChats = useCallback((updater) => {
    setChatsRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      saveChats(next)
      return next
    })
  }, [])

  const activeMessages = chats.find(c => c.id === activeChatId)?.messages || []

  const createNewChat = useCallback(() => {
    const id = uid()
    setChats(prev => [...prev, { id, title: 'New Chat', messages: [] }])
    setActiveChatId(id)
    return id
  }, [setChats])

  const selectChat = useCallback((id) => setActiveChatId(id), [])

  const deleteChat = useCallback((id) => {
    setChats(prev => prev.filter(c => c.id !== id))
    setActiveChatId(prev => prev === id ? null : prev)
  }, [setChats])

  // ── Activate / clear agent ───────────────────────────────────────────────
  const activateAgent = useCallback((agent) => {
    localStorage.setItem('actus-active-agent', JSON.stringify(agent))
    setActiveAgent(agent)
  }, [])

  const clearAgent = useCallback(() => {
    localStorage.removeItem('actus-active-agent')
    setActiveAgent(null)
  }, [])

  // ── Stop ─────────────────────────────────────────────────────────────────
  const stopGeneration = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
  }, [])

  // ── Core send ─────────────────────────────────────────────────────────────
  const _send = useCallback(async (query, chatId, agentOverride) => {
    const agent = agentOverride ?? activeAgent
    const userMsg = { id: uid(), role: 'user', content: query }

    setChats(prev => prev.map(c =>
      c.id === chatId
        ? {
            ...c,
            title: c.messages.length === 0 ? query.slice(0, 40) : c.title,
            messages: [...c.messages, userMsg],
          }
        : c
    ))

    setLoading(true)
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const systemContext = agent?.systemPrompt || ''

      // If query is ONLY a path with no question, add default question
      const pathOnlyRegex = /^[A-Za-z]:\\[^\s]+$/
      const baseQuery = pathOnlyRegex.test(query.trim())
        ? `${query.trim()} — Describe what this is, what it contains, and what each file/folder does in detail.`
        : query

      const effectiveQuery = baseQuery

      // Auto-detect file path in query and read it
      let fileContext = ''
      let fileInfo = null
      const detectedPath = extractFilePath(effectiveQuery)
      const wantsWrite = detectedPath && !detectedPath.endsWith('\\') && isWriteIntent(effectiveQuery)

      if (detectedPath) {
        try {
          const fileResult = await readFile(detectedPath)
          if (fileResult.is_directory) {
            fileContext = `Folder listing for: ${fileResult.path}\n\n${fileResult.content}`
          } else {
            fileContext = `File: ${fileResult.filename} (${fileResult.lines} lines, ${Math.round(fileResult.size_bytes/1024*10)/10} KB)\n\n${fileResult.content}`
          }
          fileInfo = { name: fileResult.filename, lines: fileResult.lines, size: fileResult.size_bytes }
        } catch (fileErr) {
          fileContext = `[FILE READ ERROR: ${fileErr.message}]`
        }
      }

      // If write intent detected, ask Claude to produce new file content then write it
      if (wantsWrite && fileContext && !fileContext.startsWith('[FILE READ ERROR')) {
        const writePrompt = fileContext +
          `\n\nUser instruction: ${query}` +
          `\n\nPlease produce the COMPLETE updated file content based on the instruction above.` +
          `\nRespond with ONLY the file content — no explanation, no markdown fences, just the raw file content.`
        const writeData = await sendChat(writePrompt, controller.signal, 10, systemContext, '')
        if (!controller.signal.aborted && writeData?.answer) {
          try {
            await writeFile(detectedPath, writeData.answer, 'overwrite')
            // After writing, send a follow-up confirmation message
            fileContext = `[FILE SUCCESSFULLY WRITTEN: ${detectedPath}]\n\nNew content (${writeData.answer.split('\n').length} lines):\n\n${writeData.answer}`
          } catch (writeErr) {
            fileContext = fileContext + `\n\n[WRITE ERROR: ${writeErr.message}]`
          }
        }
      }

      const currentLang = localStorage.getItem('actus-lang') || 'en'

      // Build conversation history — last 8 messages (4 exchanges) excluding the one we just added
      const currentMessages = chats.find(c => c.id === chatId)?.messages || []
      const historyMessages = currentMessages
        .filter(m => !m.streaming)                     // skip in-progress messages
        .slice(-9, -1)                                  // last 8 before the new user msg
        .map(m => ({ role: m.role, content: m.content.slice(0, 2000) }))  // cap each at 2000 chars

      const data = await sendChat(effectiveQuery, controller.signal, 10, systemContext, fileContext, currentLang, historyMessages)
      if (controller.signal.aborted) return

      const fullText  = data.answer
      const msgId     = uid()

      // Insert placeholder with streaming flag
      const aiMsg = {
        id: msgId,
        role: 'assistant',
        content: '',
        streaming: true,
        agentName: agent?.name || null,
        meta: {
          route:      data.route_taken,
          docs_used:  data.documents_used,
          docs_total: data.documents_retrieved,
          grounded:   data.hallucination_check,
          iterations: data.iterations,
          sources:    data.sources || [],
        },
      }
      setChats(prev => prev.map(c =>
        c.id === chatId ? { ...c, messages: [...c.messages, aiMsg] } : c
      ))

      // Typewriter: reveal ~4 chars at a time every 12ms (fast but visible)
      await new Promise(resolve => {
        let pos = 0
        const CHUNK = 4
        const DELAY = 12
        const tick = () => {
          if (controller.signal.aborted) { resolve(); return }
          pos = Math.min(pos + CHUNK, fullText.length)
          const slice = fullText.slice(0, pos)
          setChats(prev => prev.map(c =>
            c.id === chatId
              ? { ...c, messages: c.messages.map(m =>
                  m.id === msgId ? { ...m, content: slice, streaming: pos < fullText.length } : m
                ) }
              : c
          ))
          if (pos < fullText.length) setTimeout(tick, DELAY)
          else resolve()
        }
        tick()
      })
    } catch (err) {
      if (err.name === 'AbortError') return
      const errMsg = {
        id: uid(),
        role: 'assistant',
        content: `❌ Error: ${err.message}\n\nMake sure backend is running:\n\`uvicorn api_server:app --reload --port 8000\``,
        meta: null,
      }
      setChats(prev => prev.map(c =>
        c.id === chatId ? { ...c, messages: [...c.messages, errMsg] } : c
      ))
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }, [setChats, activeAgent])

  // ── Send (with rate limit + length cap) ─────────────────────────────────
  const sendMessage = useCallback(async (query, _files, chatIdOverride) => {
    if (!query.trim() || loading) return

    // Rate limit
    const now = Date.now()
    if (now - lastSentRef.current < COOLDOWN_MS) {
      const wait = Math.ceil((COOLDOWN_MS - (now - lastSentRef.current)) / 1000)
      alert(`Please wait ${wait} second${wait !== 1 ? 's' : ''} before sending another message.`)
      return
    }
    lastSentRef.current = now

    // Length cap
    const safeQuery = query.slice(0, MAX_QUERY_LEN)

    let chatId = chatIdOverride || activeChatId
    if (!chatId) {
      chatId = uid()
      // Strip language prefix injected by frontend before using as title
      const cleanForTitle = safeQuery.replace(/^\[IMPORTANT:[^\]]*\]\s*/i, '').replace(/^\[LANGUAGE:[^\]]*\]\s*/i, '').trim()
      const title = cleanForTitle.slice(0, 45) + (cleanForTitle.length > 45 ? '...' : '')
      setChats(prev => [...prev, { id: chatId, title, messages: [] }])
      setActiveChatId(chatId)
    }
    await _send(safeQuery, chatId)
  }, [activeChatId, loading, _send, setChats])

  // ── Edit ─────────────────────────────────────────────────────────────────
  const editMessage = useCallback((msgId, newContent) => {
    const chat = chats.find(c => c.id === activeChatId)
    if (!chat) return
    const idx = chat.messages.findIndex(m => m.id === msgId)
    if (idx === -1) return
    const trimmed = chat.messages.slice(0, idx)
    setChats(prev => prev.map(c =>
      c.id === activeChatId ? { ...c, messages: trimmed } : c
    ))
    setTimeout(() => _send(newContent, activeChatId), 50)
  }, [chats, activeChatId, _send, setChats])

  // ── Regenerate ───────────────────────────────────────────────────────────
  const regenerate = useCallback((msgId) => {
    const chat = chats.find(c => c.id === activeChatId)
    if (!chat) return
    const idx = chat.messages.findIndex(m => m.id === msgId)
    if (idx <= 0) return
    const userMsg = [...chat.messages].slice(0, idx).reverse().find(m => m.role === 'user')
    if (!userMsg) return
    const trimmed = chat.messages.slice(0, idx)
    setChats(prev => prev.map(c =>
      c.id === activeChatId ? { ...c, messages: trimmed } : c
    ))
    setTimeout(() => _send(userMsg.content, activeChatId), 50)
  }, [chats, activeChatId, _send, setChats])

  const renameChat = useCallback((chatId, newTitle) => {
    setChats(prev => prev.map(c => c.id === chatId ? { ...c, title: newTitle } : c))
  }, [setChats])

  return {
    chats, activeChatId, activeMessages, loading,
    activeAgent, activateAgent, clearAgent,
    createNewChat, selectChat, deleteChat, renameChat,
    sendMessage, stopGeneration, editMessage, regenerate,
  }
}
