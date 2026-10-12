import { useCallback, useState, type ReactNode } from 'react'
import type { PageResults } from './api.ts'
import { ChatResultsContext, type ChatResults } from './chatResultsContext.ts'

const STORAGE_KEY = 'cc_chat_results'

function load(): ChatResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ChatResults) : null
  } catch {
    return null
  }
}

// Holds the latest chat search results. They're kept in sessionStorage so they survive opening a product
// page and pressing Back, or refreshing the page (they're cleared when the browser tab closes).
export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(load)

  const showResults = useCallback((pageResults: PageResults) => {
    const next = { ...pageResults, receivedAt: Date.now() }
    setResults(next)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }, [])

  const clearResults = useCallback(() => {
    setResults(null)
    sessionStorage.removeItem(STORAGE_KEY)
  }, [])

  return (
    <ChatResultsContext.Provider value={{ results, showResults, clearResults }}>{children}</ChatResultsContext.Provider>
  )
}
