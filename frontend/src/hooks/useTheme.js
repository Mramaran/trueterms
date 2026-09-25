/**
 * useTheme.js — Dark / Light theme hook
 */
import { useState, useEffect } from 'react'

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    // Clear any saved dark preference — always start light
    const saved = localStorage.getItem('actus-theme')
    if (!saved || saved === 'dark') {
      localStorage.setItem('actus-theme', 'light')
      return 'light'
    }
    return saved
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('actus-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  return { theme, toggleTheme }
}
