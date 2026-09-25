/**
 * PipelineStatsPage.jsx
 * ======================
 * Dashboard showing query stats, routes, hallucination rates etc.
 * Stats are tracked in memory during the session.
 */

import { useState, useEffect } from 'react'
import { BarChart2, Database, Globe, CheckCircle, XCircle, RefreshCw, Zap } from 'lucide-react'

// Shared in-memory stats store
export const pipelineStats = {
  totalQueries: 0,
  vectorstoreCount: 0,
  webSearchCount: 0,
  groundedCount: 0,
  hallucinatedCount: 0,
  totalIterations: 0,
  recentQueries: [], // last 20
}

export default function PipelineStatsPage() {
  const [stats, setStats] = useState({ ...pipelineStats })

  // Refresh stats every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setStats({ ...pipelineStats })
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const groundRate = stats.totalQueries > 0
    ? Math.round((stats.groundedCount / stats.totalQueries) * 100)
    : 0

  const vectorRate = stats.totalQueries > 0
    ? Math.round((stats.vectorstoreCount / stats.totalQueries) * 100)
    : 0

  const avgIterations = stats.totalQueries > 0
    ? (stats.totalIterations / stats.totalQueries).toFixed(1)
    : '0'

  const handleClear = () => {
    Object.assign(pipelineStats, {
      totalQueries: 0, vectorstoreCount: 0, webSearchCount: 0,
      groundedCount: 0, hallucinatedCount: 0, totalIterations: 0,
      recentQueries: [],
    })
    setStats({ ...pipelineStats })
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Pipeline Stats</h1>
          <p className="page-sub">Live session statistics — resets on page refresh</p>
        </div>
        <button className="hist-clear-btn" onClick={handleClear}>
          <RefreshCw size={14} /> Reset Stats
        </button>
      </div>

      {stats.totalQueries === 0 ? (
        <div className="empty-state">
          <BarChart2 size={48} className="empty-icon" strokeWidth={1} />
          <h2>No Data Yet</h2>
          <p>Start chatting — your pipeline stats will appear here in real time.</p>
        </div>
      ) : (
        <>
          {/* Stat Cards */}
          <div className="stats-grid">
            <StatCard
              icon={<Zap size={22} color="#2563eb" />}
              label="Total Queries"
              value={stats.totalQueries}
              bg="#eff6ff"
            />
            <StatCard
              icon={<Database size={22} color="#16a34a" />}
              label="Vectorstore"
              value={`${stats.vectorstoreCount} (${vectorRate}%)`}
              bg="#f0fdf4"
            />
            <StatCard
              icon={<Globe size={22} color="#9333ea" />}
              label="Web Search"
              value={stats.webSearchCount}
              bg="#faf5ff"
            />
            <StatCard
              icon={<CheckCircle size={22} color="#16a34a" />}
              label="Grounded"
              value={`${stats.groundedCount} (${groundRate}%)`}
              bg="#f0fdf4"
            />
            <StatCard
              icon={<XCircle size={22} color="#dc2626" />}
              label="Hallucinated"
              value={stats.hallucinatedCount}
              bg="#fef2f2"
            />
            <StatCard
              icon={<RefreshCw size={22} color="#ea580c" />}
              label="Avg Iterations"
              value={avgIterations}
              bg="#fff7ed"
            />
          </div>

          {/* Grounded progress bar */}
          <div className="stats-bar-section">
            <div className="stats-bar-label">
              <span>Grounded Rate</span>
              <span className="green">{groundRate}%</span>
            </div>
            <div className="stats-bar-track">
              <div className="stats-bar-fill green-fill" style={{ width: `${groundRate}%` }} />
            </div>
          </div>

          <div className="stats-bar-section">
            <div className="stats-bar-label">
              <span>Vectorstore vs Web Search</span>
              <span style={{ color: '#2563eb' }}>{vectorRate}% vectorstore</span>
            </div>
            <div className="stats-bar-track">
              <div className="stats-bar-fill blue-fill" style={{ width: `${vectorRate}%` }} />
            </div>
          </div>

          {/* Recent Queries */}
          {stats.recentQueries.length > 0 && (
            <div className="stats-recent">
              <p className="section-title" style={{ marginBottom: 12 }}>Recent Queries</p>
              <div className="stats-query-list">
                {[...stats.recentQueries].reverse().map((q, i) => (
                  <div key={i} className="stats-query-item">
                    <div className="stats-query-text">{q.query}</div>
                    <div className="stats-query-meta">
                      <span className="source-tag">{q.route}</span>
                      <span className={`source-tag ${q.grounded === 'GROUNDED' ? 'tag-green' : 'tag-red'}`}>
                        {q.grounded === 'GROUNDED' ? '✅' : '⚠️'} {q.grounded}
                      </span>
                      <span className="source-tag">{q.iterations} iter</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StatCard({ icon, label, value, bg }) {
  return (
    <div className="stat-card" style={{ background: bg }}>
      <div className="stat-card-icon">{icon}</div>
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
    </div>
  )
}
