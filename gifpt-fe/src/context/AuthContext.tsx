'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getToken, setToken, clearToken, apiLogin, apiSignup, apiLogout, apiMe } from '@/lib/auth'

type AuthState =
  | { status: 'loading' }
  | { status: 'authenticated'; email: string; token: string }
  | { status: 'unauthenticated' }

type AuthContextValue = {
  auth: AuthState
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, displayName: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ status: 'loading' })

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setAuth({ status: 'unauthenticated' })
      return
    }
    apiMe(token)
      .then(({ email }) => setAuth({ status: 'authenticated', email, token }))
      .catch(() => {
        clearToken()
        setAuth({ status: 'unauthenticated' })
      })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const token = await apiLogin(email, password)
    setToken(token)
    setAuth({ status: 'authenticated', email, token })
  }, [])

  const signup = useCallback(async (email: string, password: string, displayName: string) => {
    const token = await apiSignup(email, password, displayName)
    setToken(token)
    const me = await apiMe(token)
    setAuth({ status: 'authenticated', email: me.email, token })
  }, [])

  const logout = useCallback(async () => {
    await apiLogout()
    setAuth({ status: 'unauthenticated' })
  }, [])

  return (
    <AuthContext.Provider value={{ auth, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
