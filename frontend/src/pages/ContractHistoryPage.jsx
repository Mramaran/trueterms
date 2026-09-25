/**
 * ContractHistoryPage.jsx — reads from shared localStorage hook
 */

import { useState } from 'react'
import { useContractHistory } from '../hooks/useContractHistory'
import { Archive, Copy, CheckCheck, Trash2, Download, FileText } from 'lucide-react'

export default function ContractHistoryPage() {
  const { history, removeContract, clearAll } = useContractHistory()
  const [copiedId,    setCopiedId]    = useState(null)
  const [expandedId,  setExpandedId]  = useState(null)

  const handleCopy = (item) => {
    navigator.clipboard.writeText(item.contract)
    setCopiedId(item.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleDownload = (item) => {
    const blob = new Blob([item.contract], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `${item.contractType}_contract_${item.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatTime = (iso) => {
    try { return new Date(iso).toLocaleString() }
    catch { return iso }
  }

  if (history.length === 0) {
    return (
      <div className="page">
        <div className="page-header-simple">
          <h1 className="page-title">Contract History</h1>
          <p className="page-sub">All your generated contracts saved here</p>
        </div>
        <div className="empty-state">
          <Archive size={48} className="empty-icon" strokeWidth={1} />
          <h2>No Contracts Yet</h2>
          <p>Generate a contract from the Contract Generator page — it will appear here.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Contract History</h1>
          <p className="page-sub">{history.length} contract{history.length !== 1 ? 's' : ''} generated</p>
        </div>
        <button className="hist-clear-btn" onClick={clearAll}>
          <Trash2 size={14} /> Clear All
        </button>
      </div>

      <div className="hist-list">
        {history.map(item => (
          <div key={item.id} className="hist-card">
            <div className="hist-card-header">
              <div className="hist-card-left">
                <FileText size={18} className="hist-icon" />
                <div>
                  <div className="hist-type-row">
                    <span className="hist-type">{item.contractType}</span>
                    {item.withRiskFactor && <span className="gen-rf-badge">with Risk Factor</span>}
                    <span className={`source-tag ${item.grounded === 'GROUNDED' ? 'tag-green' : 'tag-red'}`}>
                      {item.grounded === 'GROUNDED' ? '✅ Grounded' : '⚠️ ' + item.grounded}
                    </span>
                  </div>
                  <p className="hist-time">{formatTime(item.generatedAt)}</p>
                </div>
              </div>
              <div className="hist-actions">
                <button className="icon-btn" onClick={() => setExpandedId(expandedId === item.id ? null : item.id)} title="View">
                  <FileText size={15} />
                </button>
                <button className="icon-btn" onClick={() => handleCopy(item)} title="Copy">
                  {copiedId === item.id ? <CheckCheck size={15} className="green" /> : <Copy size={15} />}
                </button>
                <button className="icon-btn" onClick={() => handleDownload(item)} title="Download">
                  <Download size={15} />
                </button>
                <button className="icon-btn danger" onClick={() => removeContract(item.id)} title="Delete">
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
            {expandedId === item.id && (
              <div className="code-block hist-code">
                <div className="code-lang">json</div>
                <pre><code>{item.contract}</code></pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
