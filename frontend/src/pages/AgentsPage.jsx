/**
 * AgentsPage.jsx — Create and manage custom ACTUS agents
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Bot, Trash2, Edit3, Play, X, Save, ChevronRight, Zap, BookOpen, FileText, Globe, CheckCircle, Braces } from 'lucide-react'

const STORAGE_KEY = 'actus-agents'

const TOOL_OPTIONS = [
  { id: 'actus',     label: '@actus',     icon: '📚', desc: 'ACTUS knowledge base' },
  { id: 'contract',  label: '@contract',  icon: '📄', desc: 'Contract generator' },
  { id: 'validator', label: '@validator', icon: '✅', desc: 'Contract validator' },
  { id: 'explain',   label: '@explain',   icon: '⚡', desc: 'Term explainer' },
  { id: 'json',      label: '@json',      icon: '{}', desc: 'JSON formatter' },
  { id: 'search',    label: '@search',    icon: '🌐', desc: 'Web search' },
]

const AVATAR_OPTIONS = ['🤖', '🧠', '📊', '💼', '🔬', '⚙️', '🏦', '📈', '🛡️', '🎯']

const DEFAULT_AGENTS = [
  {
    id: 'agent-1',
    name: 'ACTUS Expert',
    avatar: '🧠',
    description: 'Deep expert in ACTUS financial contract standards',
    systemPrompt: 'You are an expert in ACTUS financial contract standards. Always provide detailed, technically accurate answers with examples. Use markdown tables and structured responses. Reference specific ACTUS attributes and their applicability rules when relevant.',
    tools: ['actus', 'explain'],
    color: '#6366f1',
    builtIn: true,
  },
  {
    id: 'agent-2',
    name: 'Contract Builder',
    avatar: '📄',
    description: 'Specialized in generating and validating contracts',
    systemPrompt: 'You are a contract generation specialist. When asked, generate complete, valid ACTUS contract JSON. Always validate the generated contract and explain each field. Provide example use cases for each contract type.',
    tools: ['contract', 'validator', 'json'],
    color: '#10b981',
    builtIn: true,
  },
]

function loadAgents() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return saved || DEFAULT_AGENTS
  } catch { return DEFAULT_AGENTS }
}

function saveAgents(agents) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(agents)) } catch {}
}

export default function AgentsPage({ onActivateAgent }) {
  const [agents, setAgents]     = useState(loadAgents)
  const [editing, setEditing]   = useState(null)   // null | 'new' | agent object
  const [hoveredId, setHoveredId] = useState(null)
  const navigate = useNavigate()

  const persist = (updated) => { setAgents(updated); saveAgents(updated) }

  const handleDelete = (id) => {
    if (window.confirm('Delete this agent?')) {
      persist(agents.filter(a => a.id !== id))
    }
  }

  const handleUseAgent = (agent) => {
    onActivateAgent?.(agent)
    navigate('/')
  }

  return (
    <div className="page agents-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">🤖 Agents</h1>
          <p className="page-subtitle">Create custom AI agents with specific instructions and tools</p>
        </div>
        <button className="btn-primary" onClick={() => setEditing('new')}>
          <Plus size={16} /> New Agent
        </button>
      </div>

      {/* Agent grid */}
      <div className="agents-grid">
        {agents.map(agent => (
          <div
            key={agent.id}
            className="agent-card"
            onMouseEnter={() => setHoveredId(agent.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{ '--agent-color': agent.color }}
          >
            <div className="agent-card-top">
              <div className="agent-avatar" style={{ background: agent.color + '22', borderColor: agent.color + '44' }}>
                {agent.avatar}
              </div>
              <div className="agent-card-info">
                <div className="agent-name">
                  {agent.name}
                  {agent.builtIn && <span className="agent-built-in">Built-in</span>}
                </div>
                <div className="agent-desc">{agent.description}</div>
              </div>
            </div>

            {/* Tools */}
            <div className="agent-tools">
              {agent.tools.map(tid => {
                const t = TOOL_OPTIONS.find(x => x.id === tid)
                return t ? (
                  <span key={tid} className="agent-tool-badge">
                    {t.icon} {t.label}
                  </span>
                ) : null
              })}
            </div>

            {/* Actions */}
            <div className="agent-card-actions">
              <button className="agent-use-btn" onClick={() => handleUseAgent(agent)}
                style={{ background: agent.color, borderColor: agent.color }}>
                <Play size={13} /> Use Agent
              </button>
              {!agent.builtIn && (
                <>
                  <button className="agent-icon-btn" title="Edit" onClick={() => setEditing(agent)}>
                    <Edit3 size={14} />
                  </button>
                  <button className="agent-icon-btn danger" title="Delete" onClick={() => handleDelete(agent.id)}>
                    <Trash2 size={14} />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}

        {/* Create new card */}
        <button className="agent-create-card" onClick={() => setEditing('new')}>
          <Plus size={24} />
          <span>Create Agent</span>
        </button>
      </div>

      {/* Editor modal */}
      {editing && (
        <AgentEditor
          agent={editing === 'new' ? null : editing}
          onSave={(agent) => {
            if (editing === 'new') {
              persist([...agents, { ...agent, id: 'agent-' + Date.now() }])
            } else {
              persist(agents.map(a => a.id === agent.id ? agent : a))
            }
            setEditing(null)
          }}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}

function AgentEditor({ agent, onSave, onClose }) {
  const [name, setName]         = useState(agent?.name || '')
  const [avatar, setAvatar]     = useState(agent?.avatar || '🤖')
  const [description, setDesc]  = useState(agent?.description || '')
  const [systemPrompt, setPrompt] = useState(agent?.systemPrompt || '')
  const [tools, setTools]       = useState(agent?.tools || [])
  const [color, setColor]       = useState(agent?.color || '#6366f1')

  const toggleTool = (id) => {
    setTools(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id])
  }

  const handleSave = () => {
    if (!name.trim()) { alert('Please give your agent a name'); return }
    if (!systemPrompt.trim()) { alert('Please add a system prompt'); return }
    onSave({ ...agent, name, avatar, description, systemPrompt, tools, color })
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="agent-editor">
        <div className="agent-editor-header">
          <h2>{agent ? 'Edit Agent' : 'Create New Agent'}</h2>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="agent-editor-body">
          {/* Avatar picker */}
          <div className="editor-field">
            <label>Avatar</label>
            <div className="avatar-picker">
              {AVATAR_OPTIONS.map(emoji => (
                <button
                  key={emoji}
                  className={`avatar-option ${avatar === emoji ? 'selected' : ''}`}
                  onClick={() => setAvatar(emoji)}
                  style={avatar === emoji ? { borderColor: color, background: color + '22' } : {}}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>

          {/* Color */}
          <div className="editor-field">
            <label>Color</label>
            <div className="color-picker">
              {['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#14b8a6'].map(c => (
                <button
                  key={c}
                  className={`color-swatch ${color === c ? 'selected' : ''}`}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
          </div>

          {/* Name */}
          <div className="editor-field">
            <label>Name *</label>
            <input className="editor-input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. PAM Specialist" maxLength={40} />
          </div>

          {/* Description */}
          <div className="editor-field">
            <label>Description</label>
            <input className="editor-input" value={description} onChange={e => setDesc(e.target.value)} placeholder="Short description of this agent" maxLength={100} />
          </div>

          {/* System Prompt */}
          <div className="editor-field">
            <label>System Prompt *</label>
            <textarea
              className="editor-textarea"
              value={systemPrompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="Tell the agent how to behave, what to focus on, what tone to use..."
              rows={5}
            />
          </div>

          {/* Tools */}
          <div className="editor-field">
            <label>Tools</label>
            <div className="tool-selector">
              {TOOL_OPTIONS.map(tool => (
                <button
                  key={tool.id}
                  className={`tool-option ${tools.includes(tool.id) ? 'selected' : ''}`}
                  onClick={() => toggleTool(tool.id)}
                  style={tools.includes(tool.id) ? { borderColor: color, background: color + '18', color } : {}}
                >
                  <span>{tool.icon}</span>
                  <span>{tool.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="agent-editor-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} style={{ background: color, borderColor: color }}>
            <Save size={15} /> Save Agent
          </button>
        </div>
      </div>
    </div>
  )
}
