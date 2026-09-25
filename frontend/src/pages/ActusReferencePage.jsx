/**
 * ActusReferencePage.jsx
 * =======================
 * Quick-lookup cheat sheet for all 32 ACTUS contract types.
 * Searchable, grouped by family.
 */

import { useState, useEffect } from 'react'
import { getContractTypes } from '../services/api'
import { Search, BookOpen, Loader2 } from 'lucide-react'

// Contract family groupings
const FAMILIES = {
  'Basic / Fixed Income': ['PAM','ANN','LAM','NAM','ANX','LAX','NAX','CLM','UMP','PBN'],
  'Basic / Ownership':    ['CSH','STK','COM'],
  'Combined / Symmetric': ['FXOUT','SWAPS','SWPPV'],
  'Combined / Asymmetric':['OPTNS','FUTUR','CAPFL','BCS','BNDCP','BNDWR','CDSWP','CLNTE','TRSWP','EXOTi'],
  'Combined / Securitization': ['SCRCR','SCRMR'],
  'Credit Enhancement':   ['CEG','CEC','MAR','REP'],
}

const FAMILY_COLORS = {
  'Basic / Fixed Income':      '#2563eb',
  'Basic / Ownership':         '#16a34a',
  'Combined / Symmetric':      '#9333ea',
  'Combined / Asymmetric':     '#ea580c',
  'Combined / Securitization': '#0891b2',
  'Credit Enhancement':        '#dc2626',
}

export default function ActusReferencePage() {
  const [contractTypes, setContractTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    getContractTypes()
      .then(data => setContractTypes(data.contract_types || []))
      .catch(() => setError('Failed to load. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  const typeMap = Object.fromEntries(contractTypes.map(t => [t.acronym, t.description]))

  const filtered = contractTypes.filter(t =>
    t.acronym.toLowerCase().includes(search.toLowerCase()) ||
    t.description.toLowerCase().includes(search.toLowerCase())
  )

  const filteredAcronyms = new Set(filtered.map(t => t.acronym))

  return (
    <div className="page">
      <div className="page-header-simple">
        <h1 className="page-title">ACTUS Reference</h1>
        <p className="page-sub">All 32 ACTUS contract types — searchable cheat sheet</p>
      </div>

      {/* Search */}
      <div className="search-bar ref-search">
        <Search size={15} className="search-icon" />
        <input
          className="search-input"
          placeholder="Search by acronym or description..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && (
          <span className="ref-count">{filtered.length} found</span>
        )}
      </div>

      {loading && (
        <div className="gen-placeholder">
          <Loader2 size={28} className="spinning" />
          <p>Loading contract types...</p>
        </div>
      )}

      {error && <p className="gen-error">{error}</p>}

      {/* Grouped by family */}
      {!loading && !error && (
        <div className="ref-families">
          {Object.entries(FAMILIES).map(([family, acronyms]) => {
            const visible = acronyms.filter(a => filteredAcronyms.has(a))
            if (visible.length === 0) return null
            const color = FAMILY_COLORS[family]

            return (
              <div key={family} className="ref-family">
                <div className="ref-family-header" style={{ borderLeftColor: color }}>
                  <BookOpen size={15} style={{ color }} />
                  <span className="ref-family-name" style={{ color }}>{family}</span>
                  <span className="ref-family-count">{visible.length} types</span>
                </div>

                <div className="ref-cards">
                  {visible.map(acronym => (
                    <div key={acronym} className="ref-card">
                      <div className="ref-card-top">
                        <span className="ref-acronym" style={{ background: color + '18', color }}>
                          {acronym}
                        </span>
                      </div>
                      <p className="ref-desc">{typeMap[acronym] || ''}</p>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
