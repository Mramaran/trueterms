/**
 * Sidebar.jsx — Left navigation with Search
 */

import { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { LANGUAGES } from '../i18n/index.js'
import { useTheme } from '../hooks/useTheme'
import {
  MessageSquarePlus, Settings2,
  ChevronLeft, ChevronRight,
  Trash2, MessageSquare, Bot, Search,
  Moon, Sun, HelpCircle, LogOut,
  MoreHorizontal, Star, Pencil, ShieldCheck
} from 'lucide-react'

export default function Sidebar({
  open, onToggle, chats, activeChatId,
  onNewChat, onSelectChat, onDeleteChat, onRenameChat
}) {
  const [hoveredId, setHoveredId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showLangMenu, setShowLangMenu] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [menuOpenId, setMenuOpenId] = useState(null)
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const [starredIds, setStarredIds] = useState(() => JSON.parse(localStorage.getItem('actus-starred') || '[]'))
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)
  const menuRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpenId(null)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])
  const navigate = useNavigate()
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const { theme, toggleTheme } = useTheme()

  const toggleStar = (id) => {
    const updated = starredIds.includes(id) ? starredIds.filter(s => s !== id) : [...starredIds, id]
    setStarredIds(updated)
    localStorage.setItem('actus-starred', JSON.stringify(updated))
    setMenuOpenId(null)
  }

  const startRename = (chat) => {
    setRenamingId(chat.id)
    setRenameValue(chat.title || '')
    setMenuOpenId(null)
  }

  const changeLanguage = (code) => {
    i18n.changeLanguage(code)
    localStorage.setItem('actus-lang', code)
    setShowLangMenu(false)
  }

  const currentLang = LANGUAGES.find(l => l.code === i18n.language) || LANGUAGES[0]

  // Filter chats by search — title AND message content
  const filteredChats = chats.filter(chat => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    if (chat.title?.toLowerCase().includes(q)) return true
    return chat.messages?.some(m => m.content?.toLowerCase().includes(q))
  })

  return (
    <>
      {!open && (
        <button className="sidebar-open-btn" onClick={onToggle}>
          <ChevronRight size={18} />
        </button>
      )}

      {/* Mobile overlay backdrop */}
      {open && (
        <div
          className="sidebar-backdrop"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar ${open ? 'open' : 'closed'}`}>

        {/* Header */}
        <div className="sidebar-header">
          <div className="sidebar-logo" onClick={() => navigate('/')}>
            <svg width="28" height="28" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" style={{flexShrink:0}}>
              <defs>
                <linearGradient id="sideOrbitGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#4F52D0" />
                  <stop offset="100%" stopColor="#818CF8" />
                </linearGradient>
                <linearGradient id="sideRingGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#6366F1" stopOpacity="1" />
                  <stop offset="60%" stopColor="#818CF8" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#C7D2FE" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              <circle cx="40" cy="40" r="37" stroke="url(#sideRingGrad)" strokeWidth="2" fill="none" />
              <circle cx="40" cy="40" r="30" stroke="#6366F1" strokeWidth="0.75" fill="none" strokeOpacity="0.25" strokeDasharray="3 5" />
              <circle cx="40" cy="3" r="3.5" fill="#6366F1" />
              <circle cx="71" cy="56" r="2.5" fill="#818CF8" fillOpacity="0.7" />
              <circle cx="9" cy="56" r="2.5" fill="#818CF8" fillOpacity="0.7" />
              <text
                x="40" y="47"
                textAnchor="middle"
                fontFamily="'Poppins', 'Inter', sans-serif"
                fontSize="24"
                fontWeight="800"
                letterSpacing="1"
                fill="url(#sideOrbitGrad)"
              >TT</text>
            </svg>
            <span className="logo-text">{t('appName')}</span>
          </div>
          <div style={{display:'flex',gap:'4px'}}>
            <button className="icon-btn" onClick={toggleTheme} title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <button className="icon-btn" onClick={onToggle} title="Collapse sidebar">
              <ChevronLeft size={18} />
            </button>
          </div>
        </div>

        {/* New Chat */}
        <button className="new-chat-btn" onClick={() => { onNewChat(); navigate('/') }}>
          <MessageSquarePlus size={16} />
          <span>{t('newChat')}</span>
        </button>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <NavItem icon={<Settings2 size={16} />} label={t('mcpConfig')} active={location.pathname.startsWith('/mcp')} onClick={() => navigate('/mcp')} />
          <NavItem icon={<ShieldCheck size={16} />} label={t('loanTruthCheck', 'Loan Truth Check')} active={location.pathname.startsWith('/loan-check')} onClick={() => navigate('/loan-check')} />

        </nav>

        <div className="sidebar-divider" />

        {/* Recent Chats */}
        <div className="sidebar-section">
          <p className="section-title">{t('recentChats')}</p>

          {/* Search bar */}
          <div className="search-bar">
            <Search size={13} className="search-icon" />
            <input
              className="search-input"
              placeholder={t('searchChats')}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="search-clear" onClick={() => setSearchQuery('')} title="Clear">
                ×
              </button>
            )}
          </div>
          {searchQuery && (
            <p className="search-result-count">
              {filteredChats.length} result{filteredChats.length !== 1 ? 's' : ''}
            </p>
          )}

          {filteredChats.length === 0 ? (
            <p className="no-chats">
              {searchQuery ? t('noChatsFound') : t('noChats')}
            </p>
          ) : (
            <ul className="chat-list">
              {[...filteredChats].reverse().map(chat => (
                <li
                  key={chat.id}
                  className={`chat-item ${chat.id === activeChatId ? 'active' : ''}`}
                  onClick={() => { if (renamingId !== chat.id) { onSelectChat(chat.id); navigate('/') } }}
                  onMouseEnter={() => setHoveredId(chat.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  {starredIds.includes(chat.id)
                    ? <Star size={13} className="chat-icon" style={{color:'#f59e0b', fill:'#f59e0b'}} />
                    : <MessageSquare size={13} className="chat-icon" />}

                  {renamingId === chat.id ? (
                    <input
                      className="rename-input"
                      value={renameValue}
                      autoFocus
                      onChange={e => setRenameValue(e.target.value)}
                      onBlur={() => {
                        if (renameValue.trim() && onRenameChat) onRenameChat(chat.id, renameValue.trim())
                        setRenamingId(null)
                      }}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          if (renameValue.trim() && onRenameChat) onRenameChat(chat.id, renameValue.trim())
                          setRenamingId(null)
                        }
                        if (e.key === 'Escape') setRenamingId(null)
                      }}
                      onClick={e => e.stopPropagation()}
                    />
                  ) : (
                    <span className="chat-title">{chat.title || 'New Chat'}</span>
                  )}

                  {(hoveredId === chat.id || menuOpenId === chat.id) && renamingId !== chat.id && (
                    <div style={{position:'relative'}} ref={menuOpenId === chat.id ? menuRef : null}>
                      <button
                        className="delete-btn"
                        onClick={e => { e.stopPropagation(); setMenuOpenId(menuOpenId === chat.id ? null : chat.id) }}
                        title="More options"
                      >
                        <MoreHorizontal size={13} />
                      </button>
                      {menuOpenId === chat.id && (
                        <div className="chat-context-menu" onClick={e => e.stopPropagation()}>
                          <button className="context-menu-item" onClick={() => toggleStar(chat.id)}>
                            <Star size={13} style={starredIds.includes(chat.id) ? {color:'#f59e0b',fill:'#f59e0b'} : {}} />
                            {starredIds.includes(chat.id) ? 'Unstar' : 'Star'}
                          </button>
                          <button className="context-menu-item" onClick={() => startRename(chat)}>
                            <Pencil size={13} /> Rename
                          </button>
                          <div className="context-menu-divider" />
                          <button className="context-menu-item danger" onClick={() => { setDeleteConfirmId(chat.id); setMenuOpenId(null) }}>
                            <Trash2 size={13} /> Delete
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer — Language Switcher + User */}
        <div className="sidebar-footer">
          {/* Language switcher */}
          <div className="lang-switcher">
            <button className="lang-btn" onClick={() => setShowLangMenu(p => !p)}>
              <span>{currentLang.flag}</span>
              <span className="lang-label">{currentLang.label}</span>
              <ChevronRight size={13} className={`lang-arrow ${showLangMenu ? 'open' : ''}`} />
            </button>
            {showLangMenu && (
              <div className="lang-menu">
                {LANGUAGES.map(lang => (
                  <button
                    key={lang.code}
                    className={`lang-option ${i18n.language === lang.code ? 'active' : ''}`}
                    onClick={() => changeLanguage(lang.code)}
                  >
                    <span>{lang.flag}</span>
                    <span>{lang.label}</span>
                    {i18n.language === lang.code && <span className="lang-check">✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* User profile button — opens settings popup */}
          <div className="user-menu-wrapper">
            <button className="user-badge user-badge-btn" onClick={() => setShowUserMenu(p => !p)}>
              <div className="user-avatar">
                {(localStorage.getItem('actus-user-name') || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="user-info">
                <span className="user-name">
                  {localStorage.getItem('actus-user-name') || 'User'}
                </span>
                <span className="user-plan">TrueTerms</span>
              </div>
            </button>

            {showUserMenu && (
              <div className="user-menu">
                {/* Name */}
                <div className="user-menu-email">
                  {localStorage.getItem('actus-user-name') || 'Set your name in Settings'}
                </div>
                <div className="user-menu-divider" />

                {/* Menu items */}
                <UserMenuItem icon={<Settings2 size={15}/>}   label="Settings"  shortcut="Ctrl+," onClick={() => { setShowUserMenu(false); navigate('/settings') }} />
                <UserMenuItem icon={<ChevronRight size={15}/>} label="Language"  hasArrow onClick={() => { setShowUserMenu(false); setShowLangMenu(true) }} />
                <UserMenuItem icon={<HelpCircle size={15}/>}   label="Get help"  onClick={() => { setShowUserMenu(false); navigate('/help') }} />

                <div className="user-menu-divider" />

                <UserMenuItem icon={<LogOut size={15}/>}       label="Log out"   danger onClick={() => setShowUserMenu(false)} />
              </div>
            )}
          </div>
        </div>

      </aside>

      {/* Delete confirmation dialog */}
      {deleteConfirmId && (
        <div className="confirm-overlay" onClick={() => setDeleteConfirmId(null)}>
          <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
            <div className="confirm-icon"><Trash2 size={22} className="confirm-trash-icon" /></div>
            <h3 className="confirm-title">Delete this chat?</h3>
            <p className="confirm-body">
              &#8220;{chats.find(c => c.id === deleteConfirmId)?.title || 'Untitled'}&#8221;<br/>
              This cannot be undone.
            </p>
            <div className="confirm-actions">
              <button className="confirm-cancel" onClick={() => setDeleteConfirmId(null)}>Cancel</button>
              <button
                className="confirm-delete"
                onClick={() => { onDeleteChat(deleteConfirmId); setDeleteConfirmId(null) }}
              >
                <Trash2 size={14}/> Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function NavItem({ icon, label, active, onClick }) {
  return (
    <button className={`nav-item ${active ? 'active' : ''}`} onClick={onClick}>
      {icon}
      <span>{label}</span>
    </button>
  )
}

function UserMenuItem({ icon, label, shortcut, hasArrow, danger, onClick }) {
  return (
    <button className={`user-menu-item ${danger ? 'danger' : ''}`} onClick={onClick}>
      <span className="user-menu-item-icon">{icon}</span>
      <span className="user-menu-item-label">{label}</span>
      {shortcut && <span className="user-menu-shortcut">{shortcut}</span>}
      {hasArrow && <ChevronRight size={13} className="user-menu-arrow" />}
    </button>
  )
}
