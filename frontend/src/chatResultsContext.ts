import { createContext, useContext } from 'react'
import type { PageResults } from './api.ts'

// Search results from the chat that the Products page renders as product cards.
export interface ChatResults extends PageResults {
  receivedAt: number // when they arrived, so the page can tell new results from old ones
}

export interface ChatResultsState {
  results: ChatResults | null
  showResults: (results: PageResults) => void
  clearResults: () => void
}

export const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
