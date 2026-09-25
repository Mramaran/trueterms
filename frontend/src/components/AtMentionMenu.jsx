/**
 * AtMentionMenu.jsx — @mention popup for invoking ACTUS tools
 */

import { useEffect, useRef } from 'react'
import { Search, FileText, CheckCircle, Braces, Globe, BookOpen, Zap } from 'lucide-react'

export const MENTION_TOOLS = [
  {
    id: 'actus',
    label: '@actus',
    description: 'Query the ACTUS knowledge base',
    icon: <BookOpen size={15} />,
    color: '#6366f1',
    prompt: '[ACTUS Query] ',
  },
  {
    id: 'contract',
    label: '@contract',
    description: 'Generate an ACTUS contract JSON',
    icon: <FileText size={15} />,
    color: '#10b981',
    prompt: '[Generate Contract] ',
  },
  {
    id: 'validator',
    label: '@validator',
    description: 'Validate a contract JSON for errors',
    icon: <CheckCircle size={15} />,
    color: '#f59e0b',
    prompt: '[Validate Contract] ',
  },
  {
    id: 'explain',
    label: '@explain',
    description: 'Explain an ACTUS attribute or term',
    icon: <Zap size={15} />,
    color: '#8b5cf6',
    prompt: '[Explain] ',
  },
  {
    id: 'json',
    label: '@json',
    description: 'Format or prettify a JSON block',
    icon: <Braces size={15} />,
    color: '#06b6d4',
    prompt: '[Format JSON] ',
  },
  {
    id: 'search',
    label: '@search',
    description: 'Search the web for ACTUS info',
    icon: <Globe size={15} />,
    color: '#ec4899',
    prompt: '[Web Search] ',
  },
]

export default function AtMentionMenu({ query, onSelect, onClose, position }) {
  const ref = useRef(null)

  const filtered = MENTION_TOOLS.filter(t =>
    !query || t.id.startsWith(query.toLowerCase()) || t.label.includes(query.toLowerCase())
  )

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  if (filtered.length === 0) return null

  return (
    <div className="mention-menu" ref={ref} style={position}>
      <div className="mention-menu-header">
        <Search size={12} />
        <span>Tools — select or keep typing</span>
      </div>
      {filtered.map((tool, i) => (
        <button
          key={tool.id}
          className="mention-item"
          onMouseDown={(e) => { e.preventDefault(); onSelect(tool) }}
        >
          <span className="mention-item-icon" style={{ color: tool.color, background: tool.color + '22' }}>
            {tool.icon}
          </span>
          <span className="mention-item-body">
            <span className="mention-item-label">{tool.label}</span>
            <span className="mention-item-desc">{tool.description}</span>
          </span>
        </button>
      ))}
    </div>
  )
}
