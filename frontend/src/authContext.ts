import { createContext, useContext } from 'react'
import type { RegisterInput, User } from './api.ts'

export interface AuthState {
  user: User | null
  loading: boolean // true until the first "who is logged in?" check finishes
  login: (email: string, password: string) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
