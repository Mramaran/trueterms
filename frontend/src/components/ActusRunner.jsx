/**
 * ActusRunner.jsx
 * Flow:
 *  1. Contract JSON appears → automatically calls ACTUS server
 *  2. ACTUS response (cash flow events) shown in table ✅
 *  3. User clicks "Export as XBRL Report" (optional)
 *  4. XBRL downloads + Charts appear ✅
 */

import { useState, useMemo, useEffect } from 'react'
import { Copy, Check, FileDown, Loader } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, LineChart, Line, ResponsiveContainer
} from 'recharts'

const API_BASE  = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_KEY   = import.meta.env.VITE_API_SECRET_KEY || ''
const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7']

// ── Step 1: Auto-run ACTUS when contract JSON appears ──────────────────────
async function runActus(contractJson, riskFactors, setActusState, setActusEvents, setActusRawResponse) {
  setActusState('running')
  try {
    const res = await fetch(`${API_BASE}/run-contract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
      body: JSON.stringify({ contract: { contracts: [contractJson], riskFactors } })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'ACTUS run failed')
    const events = data.events || []
    setActusEvents(events)
    setActusRawResponse(data.results)
    setActusState('done')
    return events  // ← return so button can use directly
  } catch (err) {
    console.error('[ACTUS Auto-Run]', err)
    setActusState('error')
    return []
  }
}

// ── Step 2: Generate XBRL report (NO auto-download) ──────────────────────
async function generateXBRL(contractJson, actusEvents, setXbrlState, setXbrlData, setChartEvents, setReportSummary) {
  if (!actusEvents.length) return
  setXbrlState('running')
  try {
    const res = await fetch(`${API_BASE}/generate-xbrl-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
      body: JSON.stringify({ actus_events: actusEvents, contract_info: contractJson, taxonomy: 'both' })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'XBRL generation failed')

    // Save XML data for manual download — DO NOT auto-download
    const today      = new Date().toISOString().slice(0, 10)
    const contractId = contractJson.contractID || contractJson.contractType || 'contract'
    setXbrlData({
      ifrs_xml:   data.ifrs_xml,
      usgaap_xml: data.usgaap_xml,
      ifrs_filename:   `${contractId}_ifrs_${today}.xml`,
      usgaap_filename: `${contractId}_usgaap_${today}.xml`,
    })

    if (data.mapped_events?.length) setChartEvents(data.mapped_events)
    if (data.summary)               setReportSummary(data.summary)

    setXbrlState('done')
  } catch (err) {
    console.error('[XBRL Generate]', err)
    setXbrlState('error')
    setTimeout(() => setXbrlState('idle'), 4000)
  }
}

// ── Step 3: Manual download — only when user clicks download button ────────
function downloadXML(content, filename) {
  const blob = new Blob([content], { type: 'application/xml' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

// ── Charts Component ────────────────────────────────────────────────────────
function ActusCharts({ events }) {
  const barData = useMemo(() => {
    const grouped = {}
    events.forEach(ev => {
      if (ev.actus_event === 'IED') return
      const month = String(ev.date || '').slice(0, 7)
      if (!month) return
      if (!grouped[month]) grouped[month] = { month, principal: 0, interest: 0 }
      const amt = Math.abs(parseFloat(ev.amount || 0))
      if (ev.actus_event === 'IP') grouped[month].interest  += amt
      else                         grouped[month].principal += amt
    })
    return Object.values(grouped)
  }, [events])

  const pieData = useMemo(() => {
    const counts = {}
    events.forEach(ev => { const t = ev.actus_event || 'OTHER'; counts[t] = (counts[t] || 0) + 1 })
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [events])

  const lineData = useMemo(() =>
    events
      .filter(ev => ev.actus_event === 'IP')
      .map(ev => ({ date: String(ev.date || '').slice(0, 7), interest: Math.abs(parseFloat(ev.amount || 0)) }))
  , [events])

  const tickFmt = val => {
    if (!val) return ''
    if (val.slice(5, 7) === '01') return val.slice(0, 4)
    if (val.slice(5, 7) === '07') return 'Mid-' + val.slice(2, 4)
    return ''
  }
  const ttStyle = { background: '#1e1e2e', border: '1px solid #3d3d4d', borderRadius: 8, fontSize: 11 }

  return (
    <div style={{ padding: '16px 14px', background: '#0f172a', borderTop: '1px solid #1e293b' }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 16 }}>
        📊 Cash Flow Visualizations — {events.length} ACTUS Events
      </div>

      {/* Bar Chart */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6, fontWeight: 600 }}>
          💰 Monthly Cash Flows (Principal + Interest)
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={barData} margin={{ top: 5, right: 10, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#64748b' }} tickFormatter={tickFmt} interval={0} />
            <YAxis tick={{ fontSize: 9, fill: '#64748b' }} width={50} />
            <Tooltip contentStyle={ttStyle} labelStyle={{ color: '#ccc' }} />
            <Legend wrapperStyle={{ fontSize: 10, paddingTop: 8 }} />
            <Bar dataKey="principal" name="Principal Repaid" fill="#6366f1" radius={[2,2,0,0]} />
            <Bar dataKey="interest"  name="Interest Paid"   fill="#22c55e" radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Pie + Line */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6, fontWeight: 600 }}>🥧 Event Type Breakdown</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" outerRadius={70} dataKey="value"
                label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`} labelLine>
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={ttStyle} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6, fontWeight: 600 }}>📉 Interest Payments Over Time</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={lineData} margin={{ top: 5, right: 10, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#64748b' }} tickFormatter={tickFmt} interval={0} />
              <YAxis tick={{ fontSize: 9, fill: '#64748b' }} width={45} />
              <Tooltip contentStyle={ttStyle} labelStyle={{ color: '#ccc' }} />
              <Line type="monotone" dataKey="interest" stroke="#6366f1" strokeWidth={2} dot={false} name="Interest" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ── Main Component ──────────────────────────────────────────────────────────
export default function ActusRunner({ contractJson, riskFactors = [] }) {
  const [copied,        setCopied]        = useState(false)
  const [actusState,       setActusState]       = useState('idle')
  const [actusEvents,      setActusEvents]      = useState([])      // extracted events
  const [actusRawResponse, setActusRawResponse] = useState(null)    // raw ACTUS server response
  const [showRawResponse,  setShowRawResponse]  = useState(false)   // toggle raw JSON view
  const [xbrlState,     setXbrlState]     = useState('idle')  // idle|running|done|error
  const [xbrlData,      setXbrlData]      = useState(null)    // generated XBRL xml data
  const [chartEvents,   setChartEvents]   = useState([])      // mapped events for charts
  const [reportSummary, setReportSummary] = useState(null)

  const contractType = contractJson?.contractType || contractJson?.ContractType || 'Contract'
  const fullPayload  = { contracts: [contractJson], riskFactors }

  // ── ACTUS runs only when user clicks the button ──

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(fullPayload, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{ marginTop: 12, border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', background: 'var(--bg-white)', fontSize: 13 }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: '#1e1e1e' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: '#888', fontWeight: 600 }}>Postman URL:</span>
          <a href="https://shmitha-ai-1512460.postman.co/workspace/testing~c9388058-9405-468c-88c0-8a81b8fac8fa"
            target="_blank" rel="noopener noreferrer"
            style={{ fontFamily: 'monospace', fontSize: 12, color: '#f97316', textDecoration: 'underline' }}>
            http://34.203.247.32:8083/eventsBatch
          </a>
        </div>
        <span style={{ background: '#2563eb', color: 'white', fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20 }}>
          {contractType}
        </span>
      </div>

      {/* ── JSON Body ── */}
      <div style={{ background: '#1e1e1e', maxHeight: 300, overflowY: 'auto', position: 'relative' }}>
        <button onClick={copyJson} style={{ position: 'absolute', top: 8, right: 8, display: 'flex', alignItems: 'center', gap: 4, background: '#3d3d3d', color: '#ccc', border: 'none', borderRadius: 4, padding: '4px 8px', fontSize: 11, cursor: 'pointer' }}>
          {copied ? <><Check size={11}/> Copied</> : <><Copy size={11}/> Copy</>}
        </button>
        <pre style={{ padding: '14px 16px', margin: 0, fontSize: 12, color: '#d4d4d4', fontFamily: 'Consolas, Monaco, monospace', lineHeight: 1.6 }}>
          {JSON.stringify(fullPayload, null, 2)}
        </pre>
      </div>

      {/* ── ACTUS Cash Flow Events (AUTO — appears when contract JSON loads) ── */}
      <div style={{ borderTop: '1px solid #1e293b' }}>

        {/* Status bar */}
        <div style={{ padding: '8px 14px', background: '#0d1b2a', display: 'flex', alignItems: 'center', gap: 8 }}>
          {actusState === 'running' && <Loader size={13} style={{ animation: 'spin 1s linear infinite', color: '#60a5fa' }} />}
          {actusState === 'done'    && <Check  size={13} style={{ color: '#22c55e' }} />}
          {actusState === 'error'   && <span>⚠️</span>}
          <span style={{ fontSize: 11, fontWeight: 600,
            color: actusState === 'done'    ? '#22c55e' :
                   actusState === 'error'   ? '#ef4444' :
                   actusState === 'running' ? '#60a5fa' : '#94a3b8' }}>
            {actusState === 'running' ? '⚡ Running on ACTUS server (34.203.247.32:8083)...' :
             actusState === 'done'    ? `⚡ ACTUS Response — ${actusEvents.length} Cash Flow Events` :
             actusState === 'error'   ? '⚡ ACTUS server error — check connection' :
             '⚡ ACTUS Cash Flow Events'}
          </span>
          {actusState === 'error' && (
            <button onClick={() => runActus(contractJson, riskFactors, setActusState, setActusEvents)}
              style={{ marginLeft: 'auto', background: '#dc2626', color: 'white', border: 'none', borderRadius: 4, padding: '3px 8px', fontSize: 11, cursor: 'pointer' }}>
              Retry
            </button>
          )}
        </div>

        {/* Events Table — shows ACTUS response */}
        {actusEvents.length > 0 && (
          <div style={{ background: '#060f1e', overflowX: 'auto', maxHeight: 240, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
              <thead style={{ position: 'sticky', top: 0 }}>
                <tr style={{ background: '#0f2744' }}>
                  {['#', 'Event Type', 'Date', 'Amount', 'Currency'].map(h => (
                    <th key={h} style={{ padding: '7px 12px', textAlign: 'left', color: '#7dd3fc', fontWeight: 600, borderBottom: '1px solid #1e3a5f' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {actusEvents.map((ev, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #0f1e33', background: i % 2 === 0 ? '#060f1e' : '#080d1a' }}>
                    <td style={{ padding: '5px 12px', color: '#475569' }}>{i + 1}</td>
                    <td style={{ padding: '5px 12px' }}>
                      <span style={{ background: '#1e3a5f', color: '#7dd3fc', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700 }}>
                        {ev.type || ev.actus_event || ev.eventType || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '5px 12px', color: '#94a3b8', fontFamily: 'monospace' }}>
                      {String(ev.time || ev.date || '').slice(0, 10)}
                    </td>
                    <td style={{ padding: '5px 12px', fontWeight: 600, fontFamily: 'monospace',
                      color: parseFloat(ev.payoff ?? ev.amount ?? 0) >= 0 ? '#22c55e' : '#ef4444' }}>
                      {parseFloat(ev.payoff ?? ev.amount ?? 0).toFixed(2)}
                    </td>
                    <td style={{ padding: '5px 12px', color: '#475569' }}>
                      {ev.currency || contractJson?.currency || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Raw ACTUS Response Toggle ── */}
      {actusRawResponse && (
        <div style={{ borderTop: '1px solid #1e293b', background: '#060f1e' }}>
          <button
            onClick={() => setShowRawResponse(p => !p)}
            style={{ width: '100%', padding: '7px 14px', background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, color: '#64748b', fontSize: 11 }}>
            <span style={{ fontSize: 10 }}>{showRawResponse ? '▲' : '▼'}</span>
            <span>ACTUS Raw Server Response (JSON)</span>
            <span style={{ marginLeft: 'auto', background: '#1e3a5f', color: '#7dd3fc', padding: '1px 8px', borderRadius: 10, fontSize: 9 }}>
              {Array.isArray(actusRawResponse) ? actusRawResponse[0]?.status || 'processed' : 'processed'}
            </span>
          </button>
          {showRawResponse && (
            <pre style={{ margin: 0, padding: '12px 14px', fontSize: 10, color: '#7dd3fc', fontFamily: 'Consolas, monospace', background: '#030a14', maxHeight: 200, overflowY: 'auto', borderTop: '1px solid #0f1e33' }}>
              {JSON.stringify(actusRawResponse, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* ── Export as XBRL Button — hide when done ── */}
      {xbrlState !== 'done' && (
      <div style={{ padding: '10px 14px', background: '#111827', borderTop: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, color: '#64748b' }}>
          Natural Language → ACTUS → XBRL Compliance Report
        </span>
        <button
          onClick={async () => {
            const events = await runActus(contractJson, riskFactors, setActusState, setActusEvents, setActusRawResponse)
            if (events?.length) generateXBRL(contractJson, events, setXbrlState, setXbrlData, setChartEvents, setReportSummary)
          }}
          disabled={xbrlState === 'running' || actusState === 'running'}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: xbrlState === 'done'    ? '#059669' :
                        xbrlState === 'error'   ? '#dc2626' :
                        actusState === 'running' ? '#374151' : '#2563eb',
            color: 'white', border: 'none', borderRadius: 6,
            padding: '6px 14px', fontSize: 12, fontWeight: 600,
            cursor: (xbrlState === 'running' || actusState === 'running') ? 'not-allowed' : 'pointer',
            opacity: (xbrlState === 'running' || actusState === 'running') ? 0.6 : 1,
            transition: 'background 0.2s'
          }}>
          {(actusState === 'running' || xbrlState === 'running') && <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />}
          {actusState === 'idle' && xbrlState === 'idle' && <FileDown size={13} />}
          {xbrlState === 'error' && '⚠️'}
          {actusState === 'running' ? ' Running ACTUS...' :
           xbrlState === 'running' ? ' Generating XBRL...' :
           xbrlState === 'error'   ? ' Failed — Retry' :
                                     ' Export as XBRL Report'}
        </button>
      </div>

      )}

      {/* ── XBRL Report Summary ── */}
      {reportSummary && (
        <div style={{ padding: '14px 16px', background: '#0a1628', borderTop: '1px solid #1e3a5f' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#7dd3fc', marginBottom: 10 }}>📋 XBRL Compliance Report Generated</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {[
              { label: 'Total Events',   value: reportSummary.total_events },
              { label: 'Event Types',    value: (reportSummary.event_types || []).join(', ') },
              { label: 'Taxonomies',     value: (reportSummary.taxonomies_mapped || []).join(' + ') },
              { label: 'Currency',       value: reportSummary.currency },
              { label: 'Total Interest', value: reportSummary.total_interest_payments?.toLocaleString() },
              { label: 'Reporting Date', value: reportSummary.reporting_date },
            ].map((item, i) => (
              <div key={i} style={{ background: '#0f2744', borderRadius: 6, padding: '8px 10px' }}>
                <div style={{ fontSize: 9, color: '#64748b', marginBottom: 2 }}>{item.label}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#e2e8f0' }}>{item.value || '—'}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: '#22c55e' }}>
            ✅ IFRS XML + US-GAAP XML downloaded — ready for RBI / SEC regulators
          </div>
        </div>
      )}

      {/* ── Download Buttons — only after XBRL is generated ── */}
      {xbrlData && (
        <div style={{ padding: '12px 16px', background: '#0a1628', borderTop: '1px solid #1e3a5f', display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: '#64748b', marginRight: 4 }}>Download:</span>
          <button
            onClick={() => downloadXML(xbrlData.ifrs_xml, xbrlData.ifrs_filename)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#065A82', color: 'white', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
            📥 IFRS XML
          </button>
          <button
            onClick={() => downloadXML(xbrlData.usgaap_xml, xbrlData.usgaap_filename)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#22c55e', color: 'white', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
            📥 US-GAAP XML
          </button>
          <button
            onClick={() => { downloadXML(xbrlData.ifrs_xml, xbrlData.ifrs_filename); setTimeout(() => downloadXML(xbrlData.usgaap_xml, xbrlData.usgaap_filename), 500) }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#6366f1', color: 'white', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
            📥 Download Both
          </button>
        </div>
      )}

      {/* ── Charts ── */}
      {chartEvents.length > 0 && <ActusCharts events={chartEvents} />}

    </div>
  )
}
