/**
 * LoanCheckPage.jsx — TrueTerms "Loan Truth Check"
 * ================================================
 * AI reads a loan, the open ACTUS engine computes every rupee, and we compare it
 * with what the lender charged. Anchored on two RBI rules:
 *   • RBI circular, 29 Apr 2024: interest from the disbursal date (no sanction-date
 *     interest, no full-month interest for part months, no interest on advance EMIs)
 *   • RBI Key Facts Statement, 1 Oct 2024: APR computation sheet + repayment schedule
 *
 * Tab 1 "Check a loan offer": text / voice → Read offer → editable terms → Check
 * Tab 2 "Check a loan book":  demo or uploaded CSV → Run check → flagged loans
 */

import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ShieldCheck, Mic, MicOff, Loader2, FileText, Upload, Download, ChevronDown,
  ChevronRight, AlertTriangle, CheckCircle2, Database, Sparkles, Play, Scale, Info,
} from 'lucide-react'
import { useVoice, whisperLanguage } from '../hooks/useVoice'
import VoiceWaveform from '../components/VoiceWaveform'
import {
  parseLoanOffer, checkLoanOffer, getLoanKfs, getDemoLoanBook, checkLoanBook,
} from '../services/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAX_BOOK_ROWS = 5000

const EXAMPLES = [
  { label: 'RBI example', text: 'Rs 50,000 loan at 2% per month flat for 12 months with Rs 2,000 processing fee' },
  { label: '₹5 lakh personal loan', text: '₹5 lakh personal loan at 14% p.a. for 3 years, processing fee 1.5%' },
  { label: 'தமிழ்', text: 'ரூ.50,000 கடன், மாதம் 2% flat வட்டி, 12 மாதங்கள், ரூ.2,000 processing கட்டணம்' },
  { label: 'हिन्दी', text: '₹50,000 का लोन, 2% प्रति माह फ्लैट ब्याज, 12 महीने, ₹2,000 प्रोसेसिंग फीस' },
]

const PATTERNS = {
  sanction_date_interest: {
    short: 'Interest from sanction date',
    rule: 'Interest must run from the disbursal date, not the sanction date.',
    color: '#f59e0b',
  },
  full_month_interest: {
    short: 'Full-month interest',
    rule: 'Only the days actually outstanding may be charged for a part month.',
    color: '#8b5cf6',
  },
  advance_emi_full_principal: {
    short: 'Advance EMI, full principal',
    rule: 'Interest must be on the amount outstanding after EMIs collected in advance.',
    color: '#ef4444',
  },
  unexplained: {
    short: 'Unexplained',
    rule: 'Differs from the ACTUS figure but matches no known pattern.',
    color: '#64748b',
  },
}

// ── Formatting helpers ────────────────────────────────────────────────────────
const inr = (x, dp = 2) => (x == null || Number.isNaN(Number(x)) ? '—'
  : `₹${Number(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp })}`)
const pct = (x, dp = 2) => (x == null ? '—'
  : `${Number(x).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: dp })}%`)
const shortDate = (iso) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN',
  { day: '2-digit', month: 'short', year: 'numeric' }) : '—')

function tomorrowISO() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Script detection so a Tamil / Hindi offer is labelled correctly for the AI parser
function detectLanguage(text, uiLang) {
  if (/[\u0B80-\u0BFF]/.test(text)) return 'ta'
  if (/[\u0900-\u097F]/.test(text)) return 'hi'
  return ['ta', 'hi', 'tanglish'].includes(uiLang) ? uiLang : 'en'
}

function friendlyError(e) {
  const msg = e?.message || String(e)
  if (/failed to fetch|networkerror|load failed/i.test(msg)) {
    return `Cannot reach the backend at ${API_BASE}. Is uvicorn running?`
  }
  return msg
}

const csvCell = (v) => {
  const s = String(v ?? '')
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

function countCsvRows(text) {
  return String(text).split(/\r?\n/).slice(1).filter(line => line.trim()).length
}

const EMPTY_FORM = {
  principal: '', rate_pct: '', rate_period: 'year', rate_type: 'reducing',
  tenure_months: '', processing_fee: '0', disbursal_date: tomorrowISO(),
}

// ═════════════════════════════════════════════════════════════════════════════
export default function LoanCheckPage() {
  const [tab, setTab] = useState('offer')

  return (
    <div className="lt-page">
      <header className="lt-header">
        <div className="lt-title-row">
          <span className="lt-logo"><ShieldCheck size={22} /></span>
          <div>
            <h1 className="lt-title">Loan Truth Check</h1>
            <p className="lt-sub">
              <strong>TrueTerms</strong>: AI reads the loan, the open ACTUS engine computes every rupee,
              and we compare it with what the lender charged.
            </p>
          </div>
        </div>
        <div className="lt-rbi-chips">
          <span className="lt-chip"><Scale size={13} /> RBI circular, 29 Apr 2024: interest only from the disbursal date</span>
          <span className="lt-chip"><FileText size={13} /> RBI KFS, 1 Oct 2024: APR sheet + repayment schedule</span>
        </div>
      </header>

      <div className="lt-tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'offer'} className={`lt-tab ${tab === 'offer' ? 'active' : ''}`}
          onClick={() => setTab('offer')}>
          <Sparkles size={15} /> Check a loan offer
        </button>
        <button role="tab" aria-selected={tab === 'book'} className={`lt-tab ${tab === 'book' ? 'active' : ''}`}
          onClick={() => setTab('book')}>
          <Database size={15} /> Check a loan book
        </button>
      </div>

      {/* Both tabs stay mounted so switching keeps their state */}
      <div hidden={tab !== 'offer'}><OfferTab /></div>
      <div hidden={tab !== 'book'}><BookTab /></div>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
//  Tab 1 — Check a loan offer
// ═════════════════════════════════════════════════════════════════════════════
function OfferTab() {
  const { i18n } = useTranslation()
  const [text, setText] = useState('')
  const [parsing, setParsing] = useState(false)
  const [parseInfo, setParseInfo] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [extra, setExtra] = useState({})          // emi / sanction_date / lender_name from the parser
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState(null)
  const [showSchedule, setShowSchedule] = useState(false)
  const [showContract, setShowContract] = useState(false)
  const [kfsLoading, setKfsLoading] = useState(false)
  const [error, setError] = useState('')
  const [voiceAvailable, setVoiceAvailable] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/health/voice`)
      .then(r => r.json())
      .then(d => setVoiceAvailable(d.available === true))
      .catch(() => setVoiceAvailable(false))
  }, [])

  const { isRecording, isProcessing, errMsg: voiceErr, toggleRecording, analyserRef } = useVoice(
    (transcript) => setText(prev => (prev ? `${prev} ${transcript}` : transcript)),
  )
  const voiceLang = whisperLanguage(i18n.language)

  const setField = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  const readOffer = async () => {
    if (!text.trim()) return
    setParsing(true)
    setError('')
    try {
      const out = await parseLoanOffer(text, detectLanguage(text, i18n.language))
      const t = out.terms || {}
      setParseInfo(out)
      setForm(f => ({
        principal: t.principal ?? '',
        rate_pct: t.rate_pct ?? '',
        rate_period: t.rate_period || 'year',
        rate_type: t.rate_type || 'reducing',
        tenure_months: t.tenure_months ?? '',
        processing_fee: t.processing_fee ?? 0,
        disbursal_date: t.disbursal_date || f.disbursal_date || tomorrowISO(),
      }))
      setExtra({ emi: t.emi ?? null, sanction_date: t.sanction_date ?? null, lender_name: t.lender_name ?? null })
      setResult(null)
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setParsing(false)
    }
  }

  const formReady = Number(form.principal) > 0 && form.rate_pct !== '' && Number(form.rate_pct) >= 0
    && Number(form.tenure_months) >= 1

  const runCheck = async () => {
    if (!formReady) return
    setChecking(true)
    setError('')
    try {
      const terms = {
        principal: Number(form.principal),
        rate_pct: Number(form.rate_pct),
        rate_period: form.rate_period,
        rate_type: form.rate_type,
        tenure_months: Number(form.tenure_months),
        processing_fee: Number(form.processing_fee || 0),
        disbursal_date: form.disbursal_date || null,
        ...(extra.emi ? { emi: extra.emi } : {}),
        ...(extra.sanction_date ? { sanction_date: extra.sanction_date } : {}),
        ...(extra.lender_name ? { lender_name: extra.lender_name } : {}),
      }
      const r = await checkLoanOffer(terms)
      setResult(r)
      setShowSchedule(false)
      setShowContract(false)
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setChecking(false)
    }
  }

  const openKfs = async () => {
    if (!result) return
    // Open the tab synchronously (inside the click) so pop-up blockers allow it
    const win = window.open('', '_blank')
    if (win) {
      win.document.title = 'Key Facts Statement'
      win.document.body.innerHTML = '<p style="font-family:sans-serif;padding:24px">Preparing Key Facts Statement…</p>'
    }
    setKfsLoading(true)
    setError('')
    try {
      const { html } = await getLoanKfs(result.terms, result.terms?.lender_name || null)
      const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
      if (win && !win.closed) win.location.href = url
      else window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 120_000)
    } catch (e) {
      if (win && !win.closed) win.close()
      setError(friendlyError(e))
    } finally {
      setKfsLoading(false)
    }
  }

  const missing = new Set(parseInfo?.missing || [])
  const isNonEnglish = /[\u0B80-\u0BFF\u0900-\u097F]/.test(text)

  return (
    <div className="lt-stack">
      {/* ── Step 1: offer text / voice ─────────────────────────────────── */}
      <section className="lt-card">
        <div className="lt-card-head">
          <h2 className="lt-card-title"><span className="lt-step">1</span> Paste or speak the loan offer</h2>
          <span className="lt-muted">English, தமிழ் or हिन्दी</span>
        </div>

        <div className={`lt-offer-box ${isRecording ? 'listening' : ''}`}>
          <textarea
            className="lt-textarea"
            rows={3}
            maxLength={4000}
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) readOffer() }}
            placeholder={isRecording ? 'Listening… click the mic again to stop'
              : 'e.g. Rs 50,000 loan at 2% per month flat for 12 months with Rs 2,000 processing fee'}
            disabled={isProcessing}
          />
          <div className="lt-offer-actions">
            <button
              type="button"
              className={`lt-mic ${isRecording ? 'recording' : ''}`}
              onClick={toggleRecording}
              disabled={isProcessing || voiceAvailable !== true}
              title={voiceAvailable === false ? 'Voice needs openai-whisper on the backend'
                : isRecording ? 'Stop and transcribe' : `Speak the offer (${voiceLang.toUpperCase()})`}
              aria-label="Voice input"
            >
              {isProcessing ? <Loader2 size={17} className="spinning" /> : isRecording ? <MicOff size={17} /> : <Mic size={17} />}
            </button>
            {(isRecording || isProcessing)
              ? <VoiceWaveform analyserRef={analyserRef} isRecording={isRecording} isProcessing={isProcessing} />
              : <span className="lt-lang-badge" title="Voice language follows the app language">{voiceLang.toUpperCase()}</span>}
            <button className="lt-btn primary" onClick={readOffer} disabled={!text.trim() || parsing || isProcessing}>
              {parsing ? <Loader2 size={15} className="spinning" /> : <Sparkles size={15} />}
              {parsing ? 'Reading…' : 'Read offer'}
            </button>
          </div>
        </div>
        {voiceErr && <p className="lt-hint warn"><AlertTriangle size={13} /> {voiceErr}</p>}

        <div className="lt-examples">
          <span className="lt-muted">Try:</span>
          {EXAMPLES.map(ex => (
            <button key={ex.label} className="lt-example" onClick={() => { setText(ex.text); setParseInfo(null) }} title={ex.text}>
              {ex.label}
            </button>
          ))}
        </div>

        {parseInfo && (
          <div className="lt-parse-info">
            <span className={`lt-pill ${parseInfo.parser === 'llm' ? 'ai' : ''}`}>
              {parseInfo.parser === 'llm' ? 'Read by AI (Claude)' : 'Read by rule-based parser'}
            </span>
            {parseInfo.missing?.length > 0 && (
              <span className="lt-hint warn"><AlertTriangle size={13} /> Please fill in: {parseInfo.missing.map(fieldLabel).join(', ')}</span>
            )}
            {parseInfo.parser === 'rules' && isNonEnglish && parseInfo.missing?.length > 0 && (
              <span className="lt-hint"><Info size={13} /> Tamil / Hindi text is read by the AI parser (needs ANTHROPIC_API_KEY on the backend).</span>
            )}
            {parseInfo.assumptions?.length > 0 && (
              <ul className="lt-assumptions">
                {parseInfo.assumptions.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* ── Step 2: editable terms ─────────────────────────────────────── */}
      <section className="lt-card">
        <div className="lt-card-head">
          <h2 className="lt-card-title"><span className="lt-step">2</span> Confirm the terms</h2>
          {extra.emi ? <span className="lt-muted">Lender's stated EMI {inr(extra.emi)} will be used</span> : null}
        </div>
        <div className="lt-form">
          <Field label="Loan amount (₹)" missing={missing.has('principal')}>
            <input className="lt-input" type="number" min="1" step="1000" value={form.principal} onChange={setField('principal')} placeholder="50000" />
          </Field>
          <Field label="Interest rate (%)" missing={missing.has('rate_pct')}>
            <input className="lt-input" type="number" min="0" step="0.01" value={form.rate_pct} onChange={setField('rate_pct')} placeholder="2" />
          </Field>
          <Field label="Rate quoted">
            <select className="lt-input" value={form.rate_period} onChange={setField('rate_period')}>
              <option value="month">per month</option>
              <option value="year">per year</option>
            </select>
          </Field>
          <Field label="Rate type">
            <select className="lt-input" value={form.rate_type} onChange={setField('rate_type')}>
              <option value="flat">flat</option>
              <option value="reducing">reducing balance</option>
            </select>
          </Field>
          <Field label="Tenure (months)" missing={missing.has('tenure_months')}>
            <input className="lt-input" type="number" min="1" max="600" step="1" value={form.tenure_months} onChange={setField('tenure_months')} placeholder="12" />
          </Field>
          <Field label="Processing fee (₹)">
            <input className="lt-input" type="number" min="0" step="100" value={form.processing_fee} onChange={setField('processing_fee')} placeholder="0" />
          </Field>
          <Field label="Disbursal date">
            <input className="lt-input" type="date" value={form.disbursal_date} onChange={setField('disbursal_date')} />
          </Field>
          <div className="lt-field lt-field-action">
            <button className="lt-btn primary lt-btn-block" onClick={runCheck} disabled={!formReady || checking}>
              {checking ? <Loader2 size={15} className="spinning" /> : <ShieldCheck size={15} />}
              {checking ? 'Running on ACTUS…' : 'Check'}
            </button>
          </div>
        </div>
      </section>

      {error && <div className="lt-error"><AlertTriangle size={15} /> {error}</div>}

      {/* ── Step 3: the truth ──────────────────────────────────────────── */}
      {result && <OfferResult result={result} showSchedule={showSchedule} setShowSchedule={setShowSchedule}
        showContract={showContract} setShowContract={setShowContract} openKfs={openKfs} kfsLoading={kfsLoading} />}
    </div>
  )
}

function fieldLabel(key) {
  return { principal: 'loan amount', rate_pct: 'interest rate', tenure_months: 'tenure' }[key] || key
}

function Field({ label, missing, children }) {
  return (
    <label className={`lt-field ${missing ? 'missing' : ''}`}>
      <span className="lt-label">{label}{missing && <em> (not found)</em>}</span>
      {children}
    </label>
  )
}

function EngineBadge({ engine, note }) {
  if (engine === 'ACTUS') {
    return <span className="lt-engine ok"><ShieldCheck size={14} /> Computed by ACTUS engine</span>
  }
  return (
    <span className="lt-engine warn" title={note || ''}>
      <AlertTriangle size={14} /> Local fallback: ACTUS engine unreachable, computed locally with the same conventions
    </span>
  )
}

function OfferResult({ result: r, showSchedule, setShowSchedule, showContract, setShowContract, openKfs, kfsLoading }) {
  const [headline, approx] = String(r.advertised_rate_text || '').split(' ≈ ')
  const gap = r.apr_pct - r.advertised_annual_rate_pct

  return (
    <section className="lt-card lt-result">
      <div className="lt-card-head">
        <h2 className="lt-card-title"><span className="lt-step">3</span> The truth</h2>
        <EngineBadge engine={r.engine} note={r.engine_note} />
      </div>

      <div className="lt-compare">
        <div className="lt-big advertised">
          <span className="lt-big-label">Advertised</span>
          <span className="lt-big-value">{headline}</span>
          <span className="lt-big-sub">{approx ? `≈ ${approx}` : 'as quoted by the lender'}</span>
        </div>
        <div className="lt-vs">vs</div>
        <div className={`lt-big truth ${gap > 0.5 ? 'worse' : 'fair'}`}>
          <span className="lt-big-label">True APR</span>
          <span className="lt-big-value">{Number(r.apr_pct).toFixed(1)}%</span>
          <span className="lt-big-sub">RBI KFS method (monthly IRR × 12){r.fees > 0 ? `, incl. ${inr(r.fees, 0)} fees` : ''}</span>
        </div>
      </div>

      {gap > 0.5 && (
        <p className="lt-verdict">
          <AlertTriangle size={15} />
          {/* one span: bare text beside <strong> would become separate flex items and split into columns */}
          <span>
            The true annual cost is <strong>{gap.toFixed(1)} percentage points</strong> above
            the advertised yearly rate. You receive {inr(r.net_disbursed, 0)} and repay {inr(r.total_payable, 0)}.
          </span>
        </p>
      )}
      {gap <= 0.5 && (
        <p className="lt-verdict fair"><CheckCircle2 size={15} /> The APR is in line with the advertised rate.</p>
      )}

      <div className="lt-stats">
        <Stat label="EMI" value={inr(r.emi)} sub={`× ${r.tenure_months} months`} />
        <Stat label="Total payable" value={inr(r.total_payable)} sub={`principal ${inr(r.principal, 0)} + interest ${inr(r.total_interest, 0)}`} />
        <Stat label="Total cost of credit" value={inr(r.total_cost_of_credit)} sub={`interest + ${inr(r.fees, 0)} fees`} />
        <Stat label="Equivalent reducing rate" value={pct(r.equivalent_reducing_rate_pct)} sub="per year, before fees" />
        <Stat label="Net disbursed" value={inr(r.net_disbursed)} sub={`on ${shortDate(r.disbursal_date)}`} />
      </div>

      <div className="lt-result-actions">
        <button className="lt-btn primary" onClick={openKfs} disabled={kfsLoading}>
          {kfsLoading ? <Loader2 size={15} className="spinning" /> : <FileText size={15} />}
          Generate KFS
        </button>
        <span className="lt-muted">Opens an illustrative RBI-format Key Facts Statement you can print or save as PDF.</span>
      </div>

      <Collapsible open={showSchedule} onToggle={() => setShowSchedule(o => !o)}
        title={`Repayment schedule (${r.schedule?.length || 0} EMIs)`}>
        <div className="lt-table-wrap tall">
          <table className="lt-table">
            <thead>
              <tr><th>#</th><th>Date</th><th className="num">EMI</th><th className="num">Interest</th>
                <th className="num">Principal</th><th className="num">Balance</th></tr>
            </thead>
            <tbody>
              {(r.schedule || []).map(row => (
                <tr key={row.n}>
                  <td className="lt-dim">{row.n}</td>
                  <td>{shortDate(row.date)}</td>
                  <td className="num">{inr(row.emi)}</td>
                  <td className="num">{inr(row.interest)}</td>
                  <td className="num">{inr(row.principal)}</td>
                  <td className="num">{inr(row.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Collapsible>

      <Collapsible open={showContract} onToggle={() => setShowContract(o => !o)} title="ACTUS contract JSON">
        <p className="lt-muted lt-small">
          ANN contract at the equivalent reducing rate (30E360), processing fee as premiumDiscountAtIED.
          {r.actus_url ? ` Sent to ${r.actus_url}/eventsBatch.` : ''}
        </p>
        <pre className="lt-json">{JSON.stringify({ contracts: [r.actus_contract], riskFactors: [] }, null, 2)}</pre>
      </Collapsible>
    </section>
  )
}

function Stat({ label, value, sub, tone }) {
  return (
    <div className={`lt-stat ${tone || ''}`}>
      <span className="lt-stat-label">{label}</span>
      <span className="lt-stat-value">{value}</span>
      {sub && <span className="lt-stat-sub">{sub}</span>}
    </div>
  )
}

function Collapsible({ open, onToggle, title, children }) {
  return (
    <div className={`lt-collapsible ${open ? 'open' : ''}`}>
      <button className="lt-collapse-btn" onClick={onToggle} aria-expanded={open}>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />} {title}
      </button>
      {open && <div className="lt-collapse-body">{children}</div>}
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
//  Tab 2 — Check a loan book
// ═════════════════════════════════════════════════════════════════════════════
function BookTab() {
  const [file, setFile] = useState(null)
  const [rowCount, setRowCount] = useState(0)
  const [loadingDemo, setLoadingDemo] = useState(false)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState('')

  const acceptFile = async (f, text) => {
    const body = text ?? await f.text()
    const rows = countCsvRows(body)
    setFile(f)
    setRowCount(rows)
    setResult(null)
    setFilter('all')
    setError(rows > MAX_BOOK_ROWS ? `This file has ${rows.toLocaleString('en-IN')} loans; the limit is ${MAX_BOOK_ROWS.toLocaleString('en-IN')} per check.` : '')
  }

  const loadDemo = async () => {
    setLoadingDemo(true)
    setError('')
    try {
      const text = await getDemoLoanBook()
      await acceptFile(new File([text], 'demo_loan_book.csv', { type: 'text/csv' }), text)
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setLoadingDemo(false)
    }
  }

  const onUpload = async (e) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    if (!/\.csv$/i.test(f.name)) { setError('Please choose a .csv file.'); return }
    await acceptFile(f)
  }

  const run = async () => {
    if (!file || rowCount > MAX_BOOK_ROWS) return
    setRunning(true)
    setError('')
    try {
      setResult(await checkLoanBook(file))
      setFilter('all')
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setRunning(false)
    }
  }

  const flagged = useMemo(() => (result?.loans || [])
    .filter(l => l.status === 'flagged')
    .sort((a, b) => b.excess - a.excess), [result])
  const errors = useMemo(() => (result?.loans || []).filter(l => l.status === 'error'), [result])
  const shown = filter === 'all' ? flagged : flagged.filter(l => l.pattern === filter)

  const downloadFlagged = () => {
    const cols = ['loan_id', 'segment', 'pattern', 'charged', 'correct', 'excess', 'sanction_date',
      'disbursal_date', 'first_emi_date', 'advance_emis', 'explanation']
    const lines = [cols.join(','), ...flagged.map(l => cols.map(c => csvCell(l[c])).join(','))]
    const blob = new Blob([`${lines.join('\n')}\n`], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'flagged_loans.csv'
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000)
  }

  const s = result?.summary
  const patternRows = s ? Object.entries(s.by_pattern).filter(([k, v]) => v.count > 0 || k !== 'unexplained') : []
  const maxAmount = Math.max(1, ...patternRows.map(([, v]) => v.amount))

  return (
    <div className="lt-stack">
      <section className="lt-card">
        <div className="lt-card-head">
          <h2 className="lt-card-title"><Database size={17} /> Check a loan book</h2>
          <span className="lt-muted">Up to {MAX_BOOK_ROWS.toLocaleString('en-IN')} loans per CSV · 100 contracts per ACTUS call</span>
        </div>
        <p className="lt-muted lt-small">
          For every loan, ACTUS computes the first-period interest from the <strong>disbursal date</strong> (A365).
          We compare it with what the lender charged and name the RBI-circular pattern behind any overcharge.
        </p>
        <div className="lt-book-actions">
          <button className="lt-btn secondary" onClick={loadDemo} disabled={loadingDemo || running}>
            {loadingDemo ? <Loader2 size={15} className="spinning" /> : <Database size={15} />}
            Load demo book (500 loans)
          </button>
          <label className={`lt-btn secondary ${running ? 'disabled' : ''}`}>
            <Upload size={15} /> Upload CSV
            <input type="file" accept=".csv,text/csv" hidden onChange={onUpload} disabled={running} />
          </label>
          <button className="lt-btn primary" onClick={run} disabled={!file || running || rowCount > MAX_BOOK_ROWS}>
            {running ? <Loader2 size={15} className="spinning" /> : <Play size={15} />}
            {running ? 'Checking on ACTUS…' : 'Run check'}
          </button>
        </div>
        {file && (
          <div className="lt-file">
            <FileText size={14} /> <strong>{file.name}</strong>
            <span className="lt-muted">{rowCount.toLocaleString('en-IN')} loans ready</span>
          </div>
        )}
        <details className="lt-format">
          <summary>CSV format</summary>
          <code>loan_id, segment, principal, annual_rate_pct, tenure_months, sanction_date, disbursal_date,
            first_emi_date, advance_emis, emi_charged, first_interest_charged</code>
        </details>
      </section>

      {error && <div className="lt-error"><AlertTriangle size={15} /> {error}</div>}

      {s && (
        <>
          <div className="lt-summary">
            <Stat label="Loans checked" value={s.loans_checked.toLocaleString('en-IN')} sub={`${s.ok.toLocaleString('en-IN')} correct`} />
            <Stat label="Flagged" value={s.flagged.toLocaleString('en-IN')} sub={`${((s.flagged / Math.max(1, s.loans_checked)) * 100).toFixed(1)}% of the book`} tone="bad" />
            <Stat label="Total overcharged" value={inr(s.total_excess)} sub="first-period interest" tone="bad" />
            <div className="lt-stat">
              <span className="lt-stat-label">Engine</span>
              <EngineBadge engine={s.engine} note={s.engine_note} />
              <span className="lt-stat-sub">{s.actus_calls} ACTUS call{s.actus_calls === 1 ? '' : 's'} · {s.elapsed_seconds}s</span>
            </div>
          </div>

          <section className="lt-card">
            <div className="lt-card-head">
              <h2 className="lt-card-title">What went wrong</h2>
              {filter !== 'all' && <button className="lt-link" onClick={() => setFilter('all')}>Show all patterns</button>}
            </div>
            <div className="lt-patterns">
              {patternRows.map(([key, v]) => {
                const p = PATTERNS[key] || PATTERNS.unexplained
                return (
                  <button key={key} className={`lt-pattern ${filter === key ? 'active' : ''}`}
                    style={{ '--pc': p.color }} onClick={() => setFilter(f => (f === key ? 'all' : key))}
                    disabled={v.count === 0}>
                    <span className="lt-pattern-head">
                      <span className="lt-dot" />
                      <strong>{p.short}</strong>
                      <span className="lt-pattern-count">{v.count} loan{v.count === 1 ? '' : 's'}</span>
                      <span className="lt-pattern-amount">{inr(v.amount)}</span>
                    </span>
                    <span className="lt-bar"><span style={{ width: `${(v.amount / maxAmount) * 100}%` }} /></span>
                    <span className="lt-pattern-rule">{p.rule}</span>
                  </button>
                )
              })}
            </div>
          </section>

          <section className="lt-card">
            <div className="lt-card-head">
              <h2 className="lt-card-title">
                Flagged loans {filter !== 'all' && <span className="lt-muted">· {PATTERNS[filter]?.short}</span>}
              </h2>
              <button className="lt-btn secondary" onClick={downloadFlagged} disabled={!flagged.length}>
                <Download size={15} /> Download flagged loans CSV
              </button>
            </div>
            {shown.length === 0 ? (
              <p className="lt-muted"><CheckCircle2 size={14} /> No flagged loans.</p>
            ) : (
              <div className="lt-table-wrap tall">
                <table className="lt-table">
                  <thead>
                    <tr><th>Loan ID</th><th>Pattern</th><th className="num">Charged</th>
                      <th className="num">Correct (ACTUS)</th><th className="num">Excess</th><th>Explanation</th></tr>
                  </thead>
                  <tbody>
                    {shown.map(l => {
                      const p = PATTERNS[l.pattern] || PATTERNS.unexplained
                      return (
                        <tr key={l.loan_id}>
                          <td className="lt-mono">{l.loan_id}</td>
                          <td><span className="lt-tag" style={{ '--pc': p.color }}>{p.short}</span></td>
                          <td className="num">{inr(l.charged)}</td>
                          <td className="num">{inr(l.correct)}</td>
                          <td className="num lt-excess">{inr(l.excess)}</td>
                          <td className="lt-explain">{l.explanation}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {errors.length > 0 && (
            <section className="lt-card">
              <h2 className="lt-card-title"><AlertTriangle size={16} /> {errors.length} row{errors.length === 1 ? '' : 's'} could not be checked</h2>
              <ul className="lt-assumptions">
                {errors.slice(0, 50).map((l, i) => <li key={`${l.loan_id}-${i}`}><strong>{l.loan_id}</strong>: {l.explanation}</li>)}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}
