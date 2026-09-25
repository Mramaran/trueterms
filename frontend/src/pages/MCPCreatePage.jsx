/**
 * MCPCreatePage.jsx — Add MCP Server
 * =====================================
 * JSON editor + live preview + save
 * Like better-chatbot /mcp/create page
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMCPConfig } from '../hooks/useMCPConfig'

const PLACEHOLDER_CONFIG = `{
  "command": "python",
  "args": [
    "mcp_server.py"
  ]
}`

export default function MCPCreatePage() {
  const navigate = useNavigate()
  const { addServer, error } = useMCPConfig()

  const [name, setName] = useState('')
  const [config, setConfig] = useState(PLACEHOLDER_CONFIG)
  const [preview, setPreview] = useState(null)
  const [previewError, setPreviewError] = useState(null)

  // Live preview
  const handleConfigChange = (val) => {
    setConfig(val)
    try {
      const parsed = JSON.parse(val)
      setPreview(parsed)
      setPreviewError(null)
    } catch {
      setPreview(null)
      setPreviewError('Invalid JSON')
    }
  }

  // Save
  const handleSave = () => {
    if (!name.trim()) {
      alert('Please enter a server name')
      return
    }
    const success = addServer(name, config)
    if (success) {
      navigate('/mcp')
    }
  }

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header-simple">
        <button className="back-btn" onClick={() => navigate('/mcp')}>
          ← Back
        </button>
        <h1 className="page-title">MCP Configuration</h1>
        <p className="page-sub">Configure your MCP server connection settings</p>
      </div>

      <div className="mcp-create-body">
        {/* Left — Form */}
        <div className="mcp-form">
          {/* Name */}
          <div className="form-group">
            <label className="form-label">Name</label>
            <input
              className="form-input"
              placeholder="Enter MCP server name"
              value={name}
              onChange={e => setName(e.target.value)}
            />
          </div>

          {/* Config editor */}
          <div className="form-group">
            <label className="form-label">Config</label>
            <div className="config-editor-wrapper">
              <textarea
                className="config-editor"
                value={config}
                onChange={e => handleConfigChange(e.target.value)}
                spellCheck={false}
                rows={14}
              />
            </div>
            {error && <p className="form-error">{error}</p>}
          </div>

          {/* Save button */}
          <button className="save-btn" onClick={handleSave}>
            Save Configuration
          </button>
        </div>

        {/* Right — Preview */}
        <div className="mcp-preview">
          <p className="preview-label">preview</p>
          {previewError ? (
            <p className="preview-error">{previewError}</p>
          ) : preview ? (
            <div className="preview-content">
              <div className="preview-row">
                <span className="preview-key">command:</span>
                <span className="preview-val">{preview.command}</span>
              </div>
              {preview.args && (
                <div className="preview-row">
                  <span className="preview-key">args:</span>
                  <span className="preview-val">{preview.args.join(' ')}</span>
                </div>
              )}
              {preview.env && (
                <div className="preview-row">
                  <span className="preview-key">env:</span>
                  <span className="preview-val">{JSON.stringify(preview.env)}</span>
                </div>
              )}
            </div>
          ) : (
            <p className="preview-undefined">undefined</p>
          )}
        </div>
      </div>
    </div>
  )
}
