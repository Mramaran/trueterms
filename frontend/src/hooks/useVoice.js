/**
 * useVoice.js — Whisper-backed voice input with ACTUS term auto-correction
 * =========================================================================
 * Features:
 *   - Real-time audio level via Web Audio API AnalyserNode
 *   - ACTUS term auto-correction (PAM, ANN, field names, cycle formats etc.)
 *   - Voice contract detection: if transcript contains contract intent → /voice-contract
 *   - Status: idle | recording | processing | coldstart | error
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import i18n from 'i18next'

const API_BASE = import.meta.env.VITE_API_BASE_URL   || 'http://localhost:8000'
const API_KEY  = import.meta.env.VITE_API_SECRET_KEY || ''

// ── Whisper language hint from the current UI language ────────────────────────
// ta → 'ta', hi → 'hi', tanglish → 'auto' (let Whisper detect), otherwise 'en'
const WHISPER_LANG = { ta: 'ta', hi: 'hi', tanglish: 'auto' }
export function whisperLanguage(lang = i18n.language) {
  return WHISPER_LANG[String(lang || 'en').toLowerCase()] || 'en'
}

// ── ACTUS term auto-correction dictionary ─────────────────────────────────────
// Whisper often mishears ACTUS-specific financial/technical terms.
// Sorted longest-first so multi-word phrases match before single words.
const ACTUS_CORRECTIONS = [
  // Multi-word phrases first (longest match priority)
  ['five point four percent',   '5.4%'],
  ['five point five percent',   '5.5%'],
  ['one hundred thousand',      '100000'],
  ['nominal interest rate',     'nominalInterestRate'],
  ['cycle of interest payment', 'cycleOfInterestPayment'],
  ['interest payment cycle',    'cycleOfInterestPayment'],
  ['cycle of rate reset',       'cycleOfRateReset'],
  ['initial exchange date',     'initialExchangeDate'],
  ['business day convention',   'businessDayConvention'],
  ['day count convention',      'dayCountConvention'],
  ['market object code',        'marketObjectCode'],
  ['notional principal',        'notionalPrincipal'],
  ['contract deal date',        'contractDealDate'],
  ['thirty e three sixty',      '30E360'],
  ['thirty three sixty',        '30E360'],
  ['p one m l zero',            'P1ML0'],
  ['p one y l zero',            'P1YL0'],
  ['linear amortizer',          'LAM'],
  ['negative amortizer',        'NAM'],
  ['principal at maturity',     'PAM'],
  ['annuity contract',          'ANN contract'],
  ['pam contract',              'PAM contract'],
  ['premium discount',          'premiumDiscountAtIED'],
  ['fifty thousand',            '50000'],
  ['twenty thousand',           '20000'],
  ['nominal interest',          'nominalInterestRate'],
  ['contract role',             'contractRole'],
  ['contract type',             'contractType'],
  ['contract id',               'contractID'],
  ['maturity date',             'maturityDate'],
  ['status date',               'statusDate'],
  ['risk factors',              'riskFactors'],
  ['risk factor',               'risk factor'],
  ['vector store',              'vectorstore'],
  ['chroma db',                 'ChromaDB'],
  ['lang graph',                'LangGraph'],
  ['lang chain',                'LangChain'],
  ['week day',                  'WEEKDAY'],
  ['ten thousand',              '10000'],
  ['day count',                 'dayCountConvention'],
  ['rate reset',                'rateReset'],
  ['five percent',              '5%'],
  ['three percent',             '3%'],
  ['four percent',              '4%'],
  ['six percent',               '6%'],
  ['fx out',                    'FXOUT'],
  ['30e 360',                   '30E360'],
  ['30 360',                    '30E360'],
  ['30 e 360',                  '30E360'],
  ['p 1 m l 0',                 'P1ML0'],
  ['p 1 y l 0',                 'P1YL0'],
  ['r p a',                     'RPA'],
  ['r p l',                     'RPL'],
  ['s c f',                     'SCF'],
  ['u s d',                     'USD'],
  ['p a m',                     'PAM'],
  ['a n n',                     'ANN'],
  ['l a m',                     'LAM'],
  // Single words
  ['actus',    'ACTUS'],
  ['ack tus',  'ACTUS'],
  ['ax tus',   'ACTUS'],
  ['act us',   'ACTUS'],
  ['palm',     'PAM'],
  ['p6ml0',    'P6ML0'],
  ['p3ml0',    'P3ML0'],
  ['p1ml0',    'P1ML0'],
  ['p1yl0',    'P1YL0'],
  ['weekday',  'WEEKDAY'],
  ['chroma',   'ChromaDB'],
  ['whisper',  'Whisper'],
  ['postman',  'Postman'],
  ['swppv',    'SWPPV'],
  ['futur',    'FUTUR'],
  ['optns',    'OPTNS'],
  ['capfl',    'CAPFL'],
  ['fxout',    'FXOUT'],
  ['swaps',    'SWAPS'],
]

/**
 * Applies ACTUS term corrections to a raw Whisper transcript.
 * Uses simple case-insensitive string replacement (longest phrases first).
 */
function correctActusTerms(text) {
  let result = text
  for (const [wrong, right] of ACTUS_CORRECTIONS) {
    // Simple case-insensitive replace — no regex special chars needed
    const idx = result.toLowerCase().indexOf(wrong.toLowerCase())
    if (idx === -1) continue
    // Replace all occurrences
    const re = new RegExp(wrong.replace(/[.+?^${}()|[\]\\]/g, String.raw`\$&`), 'gi')
    result = result.replace(re, right)
  }
  return result
}

// ── Contract intent detection ─────────────────────────────────────────────────
const CONTRACT_KEYWORDS = [
  'generate', 'create', 'make', 'build', 'produce', 'give me', 'i want',
  'pam contract', 'ann contract', 'lam contract', 'nam contract', 'clm contract',
  'annuity', 'principal at maturity', 'linear amortizer', 'contract with',
  'contract for', 'contract having', 'notional', 'interest rate for',
]

function hasContractIntent(text) {
  const lower = text.toLowerCase()
  return CONTRACT_KEYWORDS.some(kw => lower.includes(kw))
}

// ── Browser MIME type preference ──────────────────────────────────────────────
const MIME_PREFS = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
  '',
]

function getBestMime() {
  if (typeof MediaRecorder === 'undefined') return ''
  return MIME_PREFS.find(m => !m || MediaRecorder.isTypeSupported(m)) ?? ''
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useVoice(onResult, onVoiceContract) {
  const [status, setStatus] = useState('idle')
  const [errMsg, setErrMsg] = useState('')

  const recorderRef        = useRef(null)
  const chunksRef          = useRef([])
  const analyserRef        = useRef(null)
  const audioCtxRef        = useRef(null)
  const onResultRef        = useRef(onResult)
  const onVoiceContractRef = useRef(onVoiceContract)
  onResultRef.current        = onResult
  onVoiceContractRef.current = onVoiceContract

  useEffect(() => () => {
    audioCtxRef.current?.close().catch(() => {})
  }, [])

  // ── Start recording ────────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setErrMsg('')
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount:     1,
          sampleRate:       16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl:  true,
        }
      })
    } catch {
      setErrMsg('Microphone access denied. Please allow microphone access in your browser.')
      setStatus('error')
      return
    }

    try {
      const ctx  = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
      const src  = ctx.createMediaStreamSource(stream)
      const anal = ctx.createAnalyser()
      anal.fftSize               = 64
      anal.smoothingTimeConstant = 0.75
      src.connect(anal)
      audioCtxRef.current = ctx
      analyserRef.current = anal
    } catch (e) {
      console.warn('[VOICE] AudioContext unavailable:', e)
    }

    const mime = getBestMime()
    let recorder
    try {
      recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {})
    } catch {
      recorder = new MediaRecorder(stream)
    }

    chunksRef.current = []
    recorder.ondataavailable = (e) => { if (e.data?.size > 0) chunksRef.current.push(e.data) }

    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      audioCtxRef.current?.close().catch(() => {})
      audioCtxRef.current = null
      analyserRef.current = null
      const chunks = chunksRef.current
      if (!chunks.length) { setStatus('idle'); return }
      // Use the MIME type that was actually used to create the recorder,
      // falling back to the negotiated best MIME or a safe default.
      const effectiveMime = (recorder.mimeType && recorder.mimeType !== '')
        ? recorder.mimeType
        : (mime || 'audio/webm')
      const blob = new Blob(chunks, { type: effectiveMime })
      await sendToWhisper(blob, effectiveMime)
    }

    recorder.onerror = () => {
      stream.getTracks().forEach(t => t.stop())
      setStatus('error')
      setErrMsg('Recording error. Please try again.')
    }

    recorder.start(500)
    recorderRef.current = recorder
    setStatus('recording')
  }, [])

  // ── Stop recording ─────────────────────────────────────────────────────────
  const stopRecording = useCallback(() => {
    const r = recorderRef.current
    if (r && r.state !== 'inactive') {
      setStatus('processing')
      r.stop()
    }
  }, [])

  // ── Send to Whisper + apply ACTUS corrections ─────────────────────────────
  const sendToWhisper = useCallback(async (blob, mimeType) => {
    setStatus('processing')
    try {
      const form = new FormData()
      const ext  = mimeType.includes('ogg') ? '.ogg'
                 : mimeType.includes('mp4') ? '.mp4'
                 : mimeType.includes('wav') ? '.wav'
                 : '.webm'  // covers audio/webm and audio/webm;codecs=opus
      form.append('audio', blob, `recording${ext}`)
      form.append('language', whisperLanguage())   // read at send time, so it follows language switches

      const res = await fetch(`${API_BASE}/transcribe`, {
        method:  'POST',
        headers: { 'X-API-Key': API_KEY },
        body:    form,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        if (res.status === 503 || (err.detail || '').toLowerCase().includes('loading')) {
          setStatus('coldstart')
          setTimeout(() => setStatus('idle'), 4000)
          return
        }
        throw new Error(err.detail || `HTTP ${res.status}`)
      }

      const { transcript } = await res.json()
      if (!transcript?.trim()) { setStatus('idle'); return }

      // ✨ Apply ACTUS auto-correction before sending to UI
      const raw       = transcript.trim()
      const corrected = correctActusTerms(raw)

      if (corrected !== raw) {
        console.log('[VOICE] Auto-corrected:', raw, '→', corrected)
      }

      // Insert corrected transcript into the input box
      onResultRef.current(corrected)

      // ── Voice contract detection ──────────────────────────────────────────
      if (hasContractIntent(corrected) && onVoiceContractRef.current) {
        setStatus('processing')
        try {
          const cRes = await fetch(`${API_BASE}/voice-contract`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
            body:    JSON.stringify({ transcript: corrected }),
          })
          if (cRes.ok) {
            const cData = await cRes.json()
            if (cData.detected && cData.contract) {
              onVoiceContractRef.current(cData.contract, cData.params)
            }
          }
        } catch (e) {
          console.warn('[VOICE-CONTRACT]', e)
        }
      }
    } catch (e) {
      console.error('[WHISPER]', e)
      setErrMsg(e.message || 'Transcription failed. Make sure the backend is running.')
      setStatus('error')
      return
    }
    setStatus('idle')
  }, [])

  // ── Toggle ─────────────────────────────────────────────────────────────────
  const toggleRecording = useCallback(() => {
    if (status === 'recording') stopRecording()
    else if (status === 'idle' || status === 'error') startRecording()
  }, [status, startRecording, stopRecording])

  const isRecording  = status === 'recording'
  const isProcessing = status === 'processing' || status === 'coldstart'
  const isColdStart  = status === 'coldstart'
  const isActive     = isRecording || isProcessing

  return {
    status, isRecording, isProcessing, isColdStart, isActive,
    errMsg, toggleRecording, analyserRef,
  }
}
