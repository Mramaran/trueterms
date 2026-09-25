/**
 * ContractGeneratorPage.jsx
 * ==========================
 * Dedicated page to generate ACTUS contracts
 * without typing in chat.
 */

import { useState, useEffect } from 'react'
import { generateContract, getContractTypes } from '../services/api'
import { useContractHistory } from '../hooks/useContractHistory'
import { FileText, Loader2, Copy, CheckCheck, ChevronDown } from 'lucide-react'

export default function ContractGeneratorPage() {
  const [contractTypes, setContractTypes] = useState([])
  const [selectedType, setSelectedType] = useState('')
  const [withRiskFactor, setWithRiskFactor] = useState(false)
  const [extraRequirements, setExtraRequirements] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const [loadingTypes, setLoadingTypes] = useState(true)
  const { addContract } = useContractHistory()

  // Load contract types on mount
  useEffect(() => {
    getContractTypes()
      .then(data => {
        setContractTypes(data.contract_types || [])
        if (data.contract_types?.length > 0) {
          setSelectedType(data.contract_types[0].acronym)
        }
      })
      .catch(() => setError('Failed to load contract types. Is the backend running?'))
      .finally(() => setLoadingTypes(false))
  }, [])

  const handleGenerate = async () => {
    if (!selectedType || loading) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await generateContract(selectedType, withRiskFactor, extraRequirements)
      setResult(data)
      // Save to shared history
      addContract({
        id: Date.now(),
        contractType: selectedType,
        withRiskFactor,
        generatedAt: new Date().toISOString(),
        contract: data.generated_contract,
        route: data.route_taken,
        grounded: data.hallucination_check,
        sources: data.sources || [],
      })
    } catch (err) {
      setError(`❌ Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (result?.generated_contract) {
      navigator.clipboard.writeText(result.generated_contract)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const selectedDesc = contractTypes.find(t => t.acronym === selectedType)?.description || ''

  return (
    <div className="page">
      <div className="page-header-simple">
        <h1 className="page-title">Contract Generator</h1>
        <p className="page-sub">Generate valid ACTUS contract JSON ready to POST to the ACTUS server</p>
      </div>

      <div className="gen-layout">

        {/* ── Left: Controls ── */}
        <div className="gen-controls">

          {/* Contract Type */}
          <div className="form-group">
            <label className="form-label">Contract Type</label>
            {loadingTypes ? (
              <div className="gen-loading-types">Loading types...</div>
            ) : (
              <div className="select-wrapper">
                <select
                  className="form-input gen-select"
                  value={selectedType}
                  onChange={e => setSelectedType(e.target.value)}
                  disabled={loading}
                >
                  {contractTypes.map(t => (
                    <option key={t.acronym} value={t.acronym}>
                      {t.acronym}
                    </option>
                  ))}
                </select>
                <ChevronDown size={15} className="select-arrow" />
              </div>
            )}

            {/* Description of selected type */}
            {selectedDesc && (
              <p className="gen-type-desc">{selectedDesc}</p>
            )}
          </div>

          {/* Risk Factor Toggle */}
          <div className="form-group">
            <label className="form-label">Risk Factor</label>
            <div className="gen-toggle-row">
              <div
                className={`gen-toggle ${withRiskFactor ? 'on' : 'off'}`}
                onClick={() => !loading && setWithRiskFactor(p => !p)}
              >
                <div className="gen-toggle-knob" />
              </div>
              <span className="gen-toggle-label">
                {withRiskFactor ? 'Include market rate / yield curve risk factor' : 'No risk factor'}
              </span>
            </div>
          </div>

          {/* Extra Requirements */}
          <div className="form-group">
            <label className="form-label">Additional Requirements <span className="gen-optional">(optional)</span></label>
            <textarea
              className="form-input gen-textarea"
              placeholder="e.g. 5-year maturity, floating rate, quarterly payments..."
              value={extraRequirements}
              onChange={e => setExtraRequirements(e.target.value)}
              disabled={loading}
              rows={3}
            />
          </div>

          {/* Generate Button */}
          <button
            className="gen-btn"
            onClick={handleGenerate}
            disabled={loading || !selectedType || loadingTypes}
          >
            {loading
              ? <><Loader2 size={16} className="spinning" /> Generating...</>
              : <><FileText size={16} /> Generate {selectedType} Contract</>
            }
          </button>

          {error && <p className="gen-error">{error}</p>}
        </div>

        {/* ── Right: Result ── */}
        <div className="gen-result-panel">
          {!result && !loading && (
            <div className="gen-placeholder">
              <FileText size={40} strokeWidth={1} />
              <p>Your generated contract will appear here</p>
            </div>
          )}

          {loading && (
            <div className="gen-placeholder">
              <Loader2 size={32} className="spinning" />
              <p>Generating {selectedType} contract...</p>
            </div>
          )}

          {result && (
            <div className="gen-result">
              {/* Header */}
              <div className="gen-result-header">
                <div>
                  <span className="gen-result-type">{result.contract_type}</span>
                  {result.with_risk_factor && (
                    <span className="gen-rf-badge">with Risk Factor</span>
                  )}
                </div>
                <button className="copy-btn gen-copy-btn" onClick={handleCopy}>
                  {copied ? <><CheckCheck size={13} /> Copied!</> : <><Copy size={13} /> Copy</>}
                </button>
              </div>

              {/* Meta info */}
              <div className="gen-meta-row">
                <span className="source-tag">Route: {result.route_taken}</span>
                <span className={`source-tag ${result.hallucination_check === 'GROUNDED' ? 'tag-green' : 'tag-red'}`}>
                  {result.hallucination_check === 'GROUNDED' ? '✅ Grounded' : '⚠️ ' + result.hallucination_check}
                </span>
                {result.sources?.slice(0, 2).map((s, i) => (
                  <span key={i} className="source-tag">{s}</span>
                ))}
              </div>

              {/* Contract JSON output */}
              <div className="code-block gen-code">
                <div className="code-lang">json</div>
                <pre><code>{result.generated_contract}</code></pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
