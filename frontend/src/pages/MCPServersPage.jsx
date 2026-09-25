/**
 * MCPServersPage.jsx — MCP Servers list
 * =======================================
 * Shows all configured MCP servers
 * Like better-chatbot /mcp page
 */

import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Server, Circle } from 'lucide-react'
import { useMCPConfig } from '../hooks/useMCPConfig'

export default function MCPServersPage() {
  const navigate = useNavigate()
  const { servers, removeServer, toggleStatus } = useMCPConfig()

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <h1 className="page-title">MCP Servers</h1>
        <button className="primary-btn" onClick={() => navigate('/mcp/create')}>
          <Plus size={16} />
          Add Server
        </button>
      </div>

      {servers.length === 0 ? (
        /* Empty state */
        <div className="empty-state">
          <Server size={48} className="empty-icon" />
          <h2>Connect Your First Server</h2>
          <p>Add MCP servers to unlock powerful AI integrations</p>
          <button className="primary-btn large" onClick={() => navigate('/mcp/create')}>
            <Plus size={16} />
            Add Server ↗
          </button>

          {/* Pre-built suggestions */}
          <div className="suggestions">
            <div className="suggestion-chip" onClick={() => navigate('/mcp/create')}>
              🤖 trueterms
            </div>
          </div>
        </div>
      ) : (
        /* Server list */
        <div className="server-list">
          {servers.map((server, i) => (
            <div key={i} className="server-card">
              <div className="server-card-left">
                <Server size={20} className="server-icon" />
                <div className="server-info">
                  <div className="server-name-row">
                    <span className="server-name">{server.name}</span>
                    <span className={`status-badge ${server.status}`}>
                      <Circle size={8} fill="currentColor" />
                      {server.status}
                    </span>
                  </div>
                  <div className="server-meta">
                    <span className="server-meta-label">Command</span>
                    <span className="server-meta-value">
                      {(() => {
                        try {
                          const cfg = JSON.parse(server.config)
                          return `${cfg.command} ${(cfg.args || []).join(' ')}`
                        } catch {
                          return 'Invalid config'
                        }
                      })()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="server-card-actions">
                <button
                  className="toggle-btn"
                  onClick={() => toggleStatus(server.name)}
                >
                  {server.status === 'running' ? 'Stop' : 'Start'}
                </button>
                <button
                  className="icon-btn danger"
                  onClick={() => removeServer(server.name)}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
