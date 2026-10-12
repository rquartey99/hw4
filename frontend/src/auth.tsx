import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { fetchCurrentUser, loginAccount, logoutAccount, registerAccount, type RegisterInput, type User } from './api.ts'
import { AuthContext } from './authContext.ts'

// The session itself lives in an HttpOnly cookie set by the backend; this only mirrors who it belongs to.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setUser(await loginAccount(email, password))
  }, [])

  const register = useCallback(async (input: RegisterInput) => {
    setUser(await registerAccount(input))
  }, [])

  const logout = useCallback(async () => {
    await logoutAccount()
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}
