/**
 * useMCPConfig.js — MCP Configuration hook
 * ==========================================
 * Handles:
 * - Save/load MCP server configs (localStorage)
 * - Validate JSON config
 * - Track server running/stopped status
 */

import { useState, useCallback } from 'react'

const STORAGE_KEY = 'actus_mcp_servers'

// Default trueterms config
const DEFAULT_CONFIG = {
  name: 'trueterms',
  config: JSON.stringify({
    command: 'py',
    args: [
      '-3.11',
      'C:\\TrueTerms\\backend\\mcp_server.py'
    ]
  }, null, 2),
  status: 'running',
}

export function useMCPConfig() {
  const [servers, setServers] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      return saved ? JSON.parse(saved) : [DEFAULT_CONFIG]
    } catch {
      return [DEFAULT_CONFIG]
    }
  })

  const [error, setError] = useState(null)

  // Save servers to localStorage
  const persistServers = useCallback((updated) => {
    setServers(updated)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  }, [])

  // Add new server
  const addServer = useCallback((name, configStr) => {
    setError(null)
    try {
      JSON.parse(configStr) // validate JSON
    } catch {
      setError('Invalid JSON config. Please check the format.')
      return false
    }

    const newServer = {
      name: name.trim(),
      config: configStr,
      status: 'running',
    }

    const updated = [...servers, newServer]
    persistServers(updated)
    return true
  }, [servers, persistServers])

  // Remove server
  const removeServer = useCallback((name) => {
    const updated = servers.filter(s => s.name !== name)
    persistServers(updated)
  }, [servers, persistServers])

  // Toggle server status
  const toggleStatus = useCallback((name) => {
    const updated = servers.map(s =>
      s.name === name
        ? { ...s, status: s.status === 'running' ? 'stopped' : 'running' }
        : s
    )
    persistServers(updated)
  }, [servers, persistServers])

  return {
    servers,
    error,
    addServer,
    removeServer,
    toggleStatus,
  }
}
