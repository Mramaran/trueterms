/**
 * ConnectorsMarketplace.jsx
 * ==========================
 * Claude-style connectors popup with ACTUS-relevant connectors
 */

import { useState } from 'react'
import { X, Search, Check, Settings2, ExternalLink } from 'lucide-react'

const CONNECTORS = [
  {
    id: 'filesystem',
    name: 'Filesystem',
    icon: '🗂️',
    installs: '771K',
    desc: 'Let TrueTerms access your filesystem to read and write contract files.',
    category: 'Files',
    installed: true,
  },
  {
    id: 'windows-mcp',
    name: 'Windows MCP',
    icon: '🪟',
    installs: '2M',
    desc: 'MCP Server that enables TrueTerms to interact with your Windows OS.',
    category: 'Desktop',
    installed: false,
  },
  {
    id: 'desktop-commander',
    name: 'Desktop Commander',
    icon: '🖥️',
    installs: '413K',
    desc: 'Build, explore, and automate on your local machine with access to files and terminal.',
    category: 'Desktop',
    installed: true,
  },
  {
    id: 'pdf-tools',
    name: 'PDF Tools',
    icon: '📄',
    installs: '188K',
    desc: 'Let TrueTerms work with PDFs — read, analyze ACTUS documentation and contracts.',
    category: 'Files',
    installed: false,
  },
  {
    id: 'chromadb',
    name: 'ChromaDB',
    icon: '🔵',
    installs: '95K',
    desc: 'Local vector database for ACTUS knowledge retrieval and semantic search.',
    category: 'Database',
    installed: true,
  },
  {
    id: 'sequential-thinking',
    name: 'Sequential Thinking',
    icon: '🧠',
    installs: '320K',
    desc: 'Step-by-step reasoning for complex ACTUS financial contract queries.',
    category: 'AI',
    installed: true,
  },
  {
    id: 'pret-server',
    name: 'PRET MCP Server',
    icon: '🔐',
    installs: '12K',
    desc: 'ZK-proof and GLEIF verification for financial contracts and compliance.',
    category: 'Finance',
    installed: true,
  },
  {
    id: 'actus-web',
    name: 'ACTUS Web Service',
    icon: '📊',
    installs: '8K',
    desc: 'Connect to the ACTUS demo server to simulate contract cash flow events.',
    category: 'Finance',
    installed: false,
  },
]

const CATEGORIES = ['All', 'Files', 'Desktop', 'Database', 'AI', 'Finance']

export default function ConnectorsMarketplace({ onClose }) {
  const [search, setSearch]       = useState('')
  const [category, setCategory]   = useState('All')
  const [tab, setTab]             = useState('all')
  const [installed, setInstalled] = useState(
    () => new Set(CONNECTORS.filter(c => c.installed).map(c => c.id))
  )
  const [configuring, setConfiguring] = useState(null)

  const filtered = CONNECTORS.filter(c => {
    const matchSearch = c.name.toLowerCase().includes(search.toLowerCase()) ||
                        c.desc.toLowerCase().includes(search.toLowerCase())
    const matchCat    = category === 'All' || c.category === category
    const matchTab    = tab === 'all' || installed.has(c.id)
    return matchSearch && matchCat && matchTab
  })

  const toggle = (id) => {
    setInstalled(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div className="marketplace-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="marketplace-modal">
        {/* Header */}
        <div className="marketplace-header">
          <div>
            <h2 className="marketplace-title">Connectors</h2>
            <p className="marketplace-sub">
              Connect TrueTerms to your apps, files, and services.
            </p>
          </div>
          <button className="marketplace-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tabs + Search + Filter */}
        <div className="marketplace-toolbar">
          <div className="marketplace-tabs">
            <button className={`marketplace-tab ${tab === 'all' ? 'active' : ''}`} onClick={() => setTab('all')}>
              Featured
            </button>
            <button className={`marketplace-tab ${tab === 'installed' ? 'active' : ''}`} onClick={() => setTab('installed')}>
              Installed ({installed.size})
            </button>
          </div>

          <div className="marketplace-search-row">
            <div className="search-bar marketplace-searchbar">
              <Search size={14} className="search-icon" />
              <input
                className="search-input"
                placeholder="Search connectors..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>

            <select
              className="marketplace-cat-select"
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
        </div>

        {/* Grid */}
        <div className="marketplace-grid">
          {filtered.length === 0 && (
            <div className="marketplace-empty">No connectors found</div>
          )}
          {filtered.map(conn => (
            <div key={conn.id} className={`marketplace-card ${installed.has(conn.id) ? 'installed' : ''}`}>
              <div className="marketplace-card-top">
                <div className="marketplace-card-icon">{conn.icon}</div>
                <div className="marketplace-card-info">
                  <div className="marketplace-card-name">
                    {conn.name}
                    <span className="marketplace-card-installs">📦 {conn.installs}</span>
                  </div>
                  <p className="marketplace-card-desc">{conn.desc}</p>
                </div>
              </div>
              <div className="marketplace-card-footer">
                <span className="marketplace-card-cat">{conn.category}</span>
                <div className="marketplace-card-actions">
                  {installed.has(conn.id) && (
                    <button
                      className="marketplace-config-btn"
                      onClick={() => setConfiguring(conn.id)}
                      title="Configure"
                    >
                      <Settings2 size={13} />
                    </button>
                  )}
                  <button
                    className={`marketplace-install-btn ${installed.has(conn.id) ? 'installed' : ''}`}
                    onClick={() => toggle(conn.id)}
                  >
                    {installed.has(conn.id)
                      ? <><Check size={13}/> Connected</>
                      : 'Connect'
                    }
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="marketplace-footer">
          <a className="marketplace-browse-link" href="#" onClick={e => e.preventDefault()}>
            <ExternalLink size={13}/> Browse more extensions
          </a>
        </div>
      </div>
    </div>
  )
}
