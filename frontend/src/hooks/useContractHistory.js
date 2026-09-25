/**
 * useContractHistory.js
 * Shared hook — persists generated contracts in localStorage
 */
import { useState, useCallback } from 'react'

const KEY = 'actus-contract-history'

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || [] }
  catch { return [] }
}

export function useContractHistory() {
  const [history, setHistoryRaw] = useState(load)

  const setHistory = useCallback((updater) => {
    setHistoryRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      localStorage.setItem(KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const addContract = useCallback((entry) => {
    setHistory(prev => [entry, ...prev])
  }, [setHistory])

  const removeContract = useCallback((id) => {
    setHistory(prev => prev.filter(c => c.id !== id))
  }, [setHistory])

  const clearAll = useCallback(() => {
    setHistory([])
  }, [setHistory])

  return { history, addContract, removeContract, clearAll }
}
