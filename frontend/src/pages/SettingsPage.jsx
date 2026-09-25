/**
 * SettingsPage.jsx — Claude-style Settings
 * Sections: General | Connectors | Extensions | Developer
 */

import { useState } from 'react'
import { useTheme } from '../hooks/useTheme'
import { useTranslation } from 'react-i18next'
import { LANGUAGES } from '../i18n/index.js'
import {
  ChevronLeft, Settings, Plug, Code, Terminal,
  Moon, Sun, Save, CheckCheck,
  Globe, Plus, Trash2, FolderOpen, RefreshCw,
  CheckCircle, XCircle, AlertCircle
} from 'lucide-react'
import ConnectorsMarketplace from '../components/ConnectorsMarketplace'
import { useNavigate } from 'react-router-dom'

const SECTIONS = [
  {
    group: null,
    items: [
      { id: 'general',    label: 'General' },
      { id: 'connectors', label: 'Connectors' },
      { id: 'extensions', label: 'Extensions' },
      { id: 'developer',  label: 'Developer' },
    ]
  },
  {
    group: 'Preferences',
    items: [
      { id: 'language', label: 'Language' },
    ]
  }
]

export default function SettingsPage() {
  const [active, setActive] = useState('general')
  const navigate = useNavigate()

  return (
    <div className="settings-page-full">
      {/* Left sidebar */}
      <div className="settings-sidebar">
        <button className="settings-back-btn" onClick={() => navigate('/')}>
          <ChevronLeft size={16} /> Settings
        </button>

        {SECTIONS.map((section, si) => (
          <div key={si} className="settings-nav-group">
            {section.group && <p className="settings-nav-group-label">{section.group}</p>}
            {section.items.map(item => (
              <button
                key={item.id}
                className={`settings-nav-item ${active === item.id ? 'active' : ''}`}
                onClick={() => setActive(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* Right content */}
      <div className="settings-main">
        {active === 'general'    && <GeneralSection />}
        {active === 'connectors' && <ConnectorsSection />}
        {active === 'extensions' && <ExtensionsSection />}
        {active === 'developer'  && <DeveloperSection />}
        {active === 'language'   && <LanguageSection />}
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   GENERAL
───────────────────────────────────────── */
function GeneralSection() {
  const { theme, toggleTheme } = useTheme()
  const [name, setName]         = useState(() => localStorage.getItem('actus-user-name') || '')
  const [nickname, setNickname] = useState(() => localStorage.getItem('actus-user-nickname') || '')
  const [saved, setSaved]       = useState(false)
  const save = () => {
    localStorage.setItem('actus-user-name', name)
    localStorage.setItem('actus-user-nickname', nickname)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="settings-content">
      <Block title="Profile">
        <div className="settings-profile-row">
          <div className="settings-avatar-lg">H</div>
          <div className="settings-profile-fields">
            <div className="settings-two-col">
              <FormField label="Full name">
                <input className="form-input" value={name} onChange={e => setName(e.target.value)} />
              </FormField>
              <FormField label="What should TrueTerms call you?">
                <input className="form-input" value={nickname} onChange={e => setNickname(e.target.value)} />
              </FormField>
            </div>
          </div>
        </div>
        <SaveBtn saved={saved} onClick={save} />
      </Block>

      <Block title="Appearance">
        <label className="form-label">Theme</label>
        <div className="theme-options">
          <ThemeCard value="light" current={theme} label="Light" icon={<Sun size={14}/>}  onSelect={() => theme !== 'light' && toggleTheme()} />
          <ThemeCard value="dark"  current={theme} label="Dark"  icon={<Moon size={14}/>} onSelect={() => theme !== 'dark'  && toggleTheme()} />
        </div>
      </Block>

      <Block title="Notifications">
        <Toggle label="Contract generated"    desc="Show a notice when a contract is successfully generated." on />
        <Toggle label="Error alerts"          desc="Notify when the backend returns an error." on />
        <Toggle label="Pipeline info"         desc="Show AI pipeline details on every response." on />
        <Toggle label="Auto-expand pipeline"  desc="Automatically expand pipeline info panel." />
      </Block>
    </div>
  )
}

/* ─────────────────────────────────────────
   CONNECTORS  (real filesystem, ACTUS server)
───────────────────────────────────────── */
function ConnectorsSection() {
  const [showMarketplace, setShowMarketplace] = useState(false)
  const [connectors, setConnectors] = useState([
    {
      id: 'filesystem',
      name: 'Filesystem',
      desc: 'Read and write files on your local machine',
      enabled: true,
      type: 'filesystem',
      config: {
        allowedPaths: [
          'C:\\TrueTerms'
        ],
        readOnly: false,
      }
    },
    {
      id: 'actus-server',
      name: 'ACTUS Web Service',
      desc: 'Connect to ACTUS server to simulate contract cash flows',
      enabled: false,
      type: 'http',
      config: { url: 'https://demo.actusfrf.org:8080', apiKey: '' }
    },
    {
      id: 'chromadb',
      name: 'ChromaDB (Local)',
      desc: 'Vector database for ACTUS knowledge retrieval',
      enabled: true,
      type: 'http',
      config: { url: 'http://localhost:8000', apiKey: '' }
    },
  ])

  const [editing, setEditing] = useState(null)

  const toggleEnabled = (id) =>
    setConnectors(prev => prev.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c))

  const saveConfig = (id, newConfig) => {
    setConnectors(prev => prev.map(c => c.id === id ? { ...c, config: newConfig } : c))
    setEditing(null)
  }

  return (
    <div className="settings-content">
      <Block title="Connectors">
        <p className="settings-desc">
          Connect TrueTerms to external services and local resources.
          Enable a connector then configure its settings.
        </p>
        <button className="marketplace-open-btn" onClick={() => setShowMarketplace(true)}>
          <Plug size={14}/> Browse Connectors
        </button>
        {showMarketplace && <ConnectorsMarketplace onClose={() => setShowMarketplace(false)} />}
        <div className="connectors-list">
          {connectors.map(conn => (
            <div key={conn.id} className="connector-card-new">
              <div className="connector-card-top">
                <div className="connector-card-left">
                  <div className="connector-name">{conn.name}</div>
                  <div className="connector-desc">{conn.desc}</div>
                  <ConnectorStatus enabled={conn.enabled} />
                </div>
                <div className="connector-card-actions">
                  <button
                    className="conn-config-btn"
                    onClick={() => setEditing(editing === conn.id ? null : conn.id)}
                    disabled={!conn.enabled}
                  >
                    Configure
                  </button>
                  <div className={`gen-toggle ${conn.enabled ? 'on' : 'off'}`} onClick={() => toggleEnabled(conn.id)}>
                    <div className="gen-toggle-knob" />
                  </div>
                </div>
              </div>

              {/* Inline config editor */}
              {editing === conn.id && conn.enabled && (
                <ConnectorConfig conn={conn} onSave={saveConfig} onCancel={() => setEditing(null)} />
              )}
            </div>
          ))}
        </div>
      </Block>
    </div>
  )
}

function ConnectorStatus({ enabled }) {
  if (!enabled) return <span className="conn-status off">● Disabled</span>
  return <span className="conn-status on">● Active</span>
}

function ConnectorConfig({ conn, onSave, onCancel }) {
  const [cfg, setCfg] = useState({ ...conn.config })

  const updatePath = (i, val) => {
    const paths = [...(cfg.allowedPaths || [])]
    paths[i] = val
    setCfg(p => ({ ...p, allowedPaths: paths }))
  }

  const addPath = () => setCfg(p => ({ ...p, allowedPaths: [...(p.allowedPaths || []), ''] }))
  const removePath = (i) => setCfg(p => ({ ...p, allowedPaths: p.allowedPaths.filter((_, idx) => idx !== i) }))

  return (
    <div className="conn-config-panel">
      {/* Filesystem config */}
      {conn.type === 'filesystem' && (
        <>
          <div className="conn-config-section">
            <label className="form-label">Allowed Paths</label>
            <p className="form-hint" style={{marginTop:0, marginBottom:8}}>
              TrueTerms can read/write files only within these folders.
            </p>
            {(cfg.allowedPaths || []).map((path, i) => (
              <div key={i} className="conn-path-row">
                <FolderOpen size={14} className="conn-path-icon" />
                <input
                  className="form-input conn-path-input"
                  value={path}
                  onChange={e => updatePath(i, e.target.value)}
                  placeholder="C:\path\to\folder"
                />
                <button className="conn-path-remove" onClick={() => removePath(i)} title="Remove path">
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
            <button className="conn-add-path-btn" onClick={addPath}>
              <Plus size={13} /> Add path
            </button>
          </div>
          <div className="conn-config-section">
            <label className="form-label">Access mode</label>
            <div className="conn-radio-row">
              <label className="conn-radio">
                <input type="radio" checked={!cfg.readOnly} onChange={() => setCfg(p => ({...p, readOnly: false}))} />
                <span>Read & Write</span>
              </label>
              <label className="conn-radio">
                <input type="radio" checked={!!cfg.readOnly} onChange={() => setCfg(p => ({...p, readOnly: true}))} />
                <span>Read only</span>
              </label>
            </div>
          </div>
        </>
      )}

      {/* HTTP connector config */}
      {conn.type === 'http' && (
        <>
          <FormField label="Server URL">
            <input className="form-input" value={cfg.url || ''} onChange={e => setCfg(p => ({...p, url: e.target.value}))} placeholder="https://..." />
          </FormField>
          <FormField label="API Key (optional)">
            <input className="form-input" type="password" value={cfg.apiKey || ''} onChange={e => setCfg(p => ({...p, apiKey: e.target.value}))} placeholder="Leave blank if not required" />
          </FormField>
        </>
      )}

      <div className="conn-config-footer">
        <button className="settings-save-btn" onClick={() => onSave(conn.id, cfg)}>
          <Save size={14}/> Save
        </button>
        <button className="conn-cancel-btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   EXTENSIONS  (MCP servers — real config)
───────────────────────────────────────── */
function ExtensionsSection() {
  const [extensions, setExtensions] = useState([
    {
      id: 'filesystem-mcp',
      name: 'Filesystem MCP',
      desc: 'Read, write, and manage files on your local machine via MCP protocol',
      active: true,
      command: 'node',
      args: ['C:\\Users\\DELL\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-filesystem\\dist\\index.js'],
      paths: ['C:\\TrueTerms']
    },
    {
      id: 'sequential-thinking',
      name: 'Sequential Thinking',
      desc: 'Step-by-step reasoning for complex ACTUS contract queries',
      active: true,
      command: 'node',
      args: ['C:\\Users\\DELL\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-sequential-thinking\\dist\\index.js'],
      paths: []
    },
    {
      id: 'pret-mcp',
      name: 'PRET MCP Server',
      desc: 'ZK-proof and GLEIF verification for financial contracts',
      active: true,
      command: 'python',
      args: ['C:\\ZK-PRET\\server.py'],
      paths: []
    },
  ])

  const [editing, setEditing] = useState(null)

  const toggleActive = (id) =>
    setExtensions(prev => prev.map(e => e.id === id ? { ...e, active: !e.active } : e))

  const saveExt = (id, updates) => {
    setExtensions(prev => prev.map(e => e.id === id ? { ...e, ...updates } : e))
    setEditing(null)
  }

  return (
    <div className="settings-content">
      <Block title="Extensions">
        <p className="settings-desc">
          MCP (Model Context Protocol) servers extend TrueTerms with real capabilities —
          filesystem access, reasoning tools, and blockchain verification.
        </p>
        <div className="connectors-list">
          {extensions.map(ext => (
            <div key={ext.id} className="connector-card-new">
              <div className="connector-card-top">
                <div className="connector-card-left">
                  <div className="connector-name">{ext.name}</div>
                  <div className="connector-desc">{ext.desc}</div>
                  <span className={`conn-status ${ext.active ? 'on' : 'off'}`}>
                    {ext.active ? '● Running' : '● Stopped'}
                  </span>
                </div>
                <div className="connector-card-actions">
                  <button className="conn-config-btn" onClick={() => setEditing(editing === ext.id ? null : ext.id)}>
                    Configure
                  </button>
                  <div className={`gen-toggle ${ext.active ? 'on' : 'off'}`} onClick={() => toggleActive(ext.id)}>
                    <div className="gen-toggle-knob" />
                  </div>
                </div>
              </div>

              {editing === ext.id && (
                <ExtensionConfig ext={ext} onSave={saveExt} onCancel={() => setEditing(null)} />
              )}
            </div>
          ))}
        </div>
      </Block>
    </div>
  )
}

function ExtensionConfig({ ext, onSave, onCancel }) {
  const [command, setCommand] = useState(ext.command || 'node')
  const [args, setArgs]       = useState((ext.args || []).join('\n'))
  const [paths, setPaths]     = useState((ext.paths || []).join('\n'))

  const save = () => onSave(ext.id, {
    command,
    args: args.split('\n').map(s => s.trim()).filter(Boolean),
    paths: paths.split('\n').map(s => s.trim()).filter(Boolean)
  })

  return (
    <div className="conn-config-panel">
      <FormField label="Command">
        <input className="form-input" value={command} onChange={e => setCommand(e.target.value)} placeholder="node / python / npx" />
      </FormField>
      <FormField label="Arguments (one per line)">
        <textarea
          className="form-input settings-textarea"
          value={args}
          onChange={e => setArgs(e.target.value)}
          rows={3}
          placeholder={'C:\\path\\to\\server.js\n--flag value'}
        />
      </FormField>
      {ext.id === 'filesystem-mcp' && (
        <FormField label="Allowed Paths (one per line)">
          <textarea
            className="form-input settings-textarea"
            value={paths}
            onChange={e => setPaths(e.target.value)}
            rows={3}
            placeholder="C:\\TrueTerms"
          />
          <p className="form-hint">The MCP server will only access files within these paths.</p>
        </FormField>
      )}
      <div className="conn-config-footer">
        <button className="settings-save-btn" onClick={save}><Save size={14}/> Save</button>
        <button className="conn-cancel-btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────
   DEVELOPER
───────────────────────────────────────── */
function DeveloperSection() {
  const [backendUrl, setBackendUrl] = useState(
    () => localStorage.getItem('actus-backend-url') || 'http://localhost:8000'
  )
  const [saved, setSaved] = useState(false)
  const save = () => {
    localStorage.setItem('actus-backend-url', backendUrl)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="settings-content">
      <Block title="Backend Connection">
        <FormField label="Backend API URL">
          <input className="form-input" value={backendUrl} onChange={e => setBackendUrl(e.target.value)} />
        </FormField>
        <div className="security-warning-box">
          <span>🔒</span>
          <div>
            <strong>API Key Security Notice</strong>
            <p>Your API key is stored in <code>frontend/.env</code> and is bundled into the browser JavaScript — meaning it is visible to anyone who opens DevTools. For production deployment, switch to session-based or cookie authentication on the backend instead of exposing the key to the browser.</p>
          </div>
        </div>
        <SaveBtn saved={saved} onClick={save} />
      </Block>

      <Block title="About">
        <div className="about-info-list">
          <AboutRow label="Version"    value="1.0.0" />
          <AboutRow label="Frontend"   value="React + Vite" />
          <AboutRow label="Backend"    value="Python FastAPI" />
          <AboutRow label="AI Engine"  value="Anthropic Claude Sonnet" />
          <AboutRow label="RAG"        value="LangGraph + ChromaDB" />
          <AboutRow label="MCP"        value="Model Context Protocol" />
          <AboutRow label="Developer"  value="EMBER SYNDICATE" />
        </div>
      </Block>
    </div>
  )
}

/* ─────────────────────────────────────────
   LANGUAGE
───────────────────────────────────────── */
function LanguageSection() {
  const { i18n } = useTranslation()
  return (
    <div className="settings-content">
      <Block title="Language">
        <p className="settings-desc">Choose your preferred UI language.</p>
        <div className="lang-grid">
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              className={`lang-grid-item ${i18n.language === lang.code ? 'active' : ''}`}
              onClick={() => { i18n.changeLanguage(lang.code); localStorage.setItem('actus-lang', lang.code) }}
            >
              <span className="lang-grid-flag">{lang.flag}</span>
              <span className="lang-grid-label">{lang.label}</span>
              {i18n.language === lang.code && <span className="lang-grid-check">✓</span>}
            </button>
          ))}
        </div>
      </Block>
    </div>
  )
}

/* ─────────────────────────────────────────
   SHARED COMPONENTS
───────────────────────────────────────── */
function Block({ title, children }) {
  return (
    <div className="settings-block">
      <h2 className="settings-block-title">{title}</h2>
      {children}
    </div>
  )
}

function FormField({ label, children }) {
  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      {children}
    </div>
  )
}

function SaveBtn({ saved, onClick }) {
  return (
    <button className="settings-save-btn" onClick={onClick}>
      {saved ? <><CheckCheck size={15}/> Saved!</> : <><Save size={15}/> Save changes</>}
    </button>
  )
}

function Toggle({ label, desc, on: defaultOn = false }) {
  const [on, setOn] = useState(defaultOn)
  return (
    <div className="notif-item">
      <div className="notif-info">
        <span className="notif-label">{label}</span>
        <span className="notif-desc">{desc}</span>
      </div>
      <div className={`gen-toggle ${on ? 'on' : 'off'}`} onClick={() => setOn(p => !p)}>
        <div className="gen-toggle-knob" />
      </div>
    </div>
  )
}

function ThemeCard({ value, current, label, icon, onSelect }) {
  return (
    <button className={`theme-option ${current === value ? 'active' : ''}`} onClick={onSelect}>
      <div className={`theme-preview ${value}-preview`}>
        <div className="tp-sidebar" /><div className="tp-main"><div className="tp-bubble" /><div className="tp-bubble short" /></div>
      </div>
      <div className="theme-option-label">{icon}<span>{label}</span></div>
      {current === value && <span className="theme-check">✓</span>}
    </button>
  )
}

function AboutRow({ label, value }) {
  return (
    <div className="about-row">
      <span className="about-row-label">{label}</span>
      <span className="about-row-value">{value}</span>
    </div>
  )
}
