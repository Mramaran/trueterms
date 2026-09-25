/**
 * App.jsx — Main app with routing
 */

import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import ChatPage from './pages/ChatPage'
import MCPServersPage from './pages/MCPServersPage'
import MCPCreatePage from './pages/MCPCreatePage'
import HelpPage from './pages/HelpPage'
import SettingsPage from './pages/SettingsPage'
import NotFoundPage from './pages/NotFoundPage'
import LoanCheckPage from './pages/LoanCheckPage'
import { useChat } from './hooks/useChat'
import './styles/index.css'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const {
    chats, activeChatId, activeMessages, loading,
    createNewChat, selectChat, deleteChat, renameChat, sendMessage,
    stopGeneration, editMessage, regenerate,
  } = useChat()

  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar
          open={sidebarOpen}
          onToggle={() => setSidebarOpen(o => !o)}
          chats={chats}
          activeChatId={activeChatId}
          onNewChat={createNewChat}
          onSelectChat={selectChat}
          onDeleteChat={deleteChat}
          onRenameChat={renameChat}
        />

        <main className={`main ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
          <Routes>
            <Route path="/" element={
              <ChatPage
                messages={activeMessages}
                loading={loading}
                onSend={sendMessage}
                onStop={stopGeneration}
                onEdit={editMessage}
                onRegenerate={regenerate}
              />
            }/>
            <Route path="/help"        element={<HelpPage />} />
            <Route path="/settings"    element={<SettingsPage />} />
            <Route path="/mcp"         element={<MCPServersPage />} />
            <Route path="/mcp/create"  element={<MCPCreatePage />} />
            <Route path="/loan-check"  element={<LoanCheckPage />} />
            <Route path="*"            element={<NotFoundPage />} />
          </Routes>
        </main>

      </div>
    </BrowserRouter>
  )
}
