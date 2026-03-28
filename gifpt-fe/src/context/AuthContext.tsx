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
  signup: (email: string, password: string, openaiApiKey: string) => Promise<void>
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
      .catch((err: unknown) => {
        const isAuthError = err instanceof Error && err.message === 'unauthorized'
        if (isAuthError) {
          clearToken()
          setAuth({ status: 'unauthenticated' })
        } else {
          // 5xx 등 일시적 오류 — 토큰 유지, 인증 상태 유지
          setAuth({ status: 'authenticated', email: '', token })
        }
      })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const token = await apiLogin(email, password)
    setToken(token)
    const me = await apiMe(token)
    setAuth({ status: 'authenticated', email: me.email, token })
  }, [])

  const signup = useCallback(async (email: string, password: string, openaiApiKey: string) => {
    const token = await apiSignup(email, password, openaiApiKey)
    setToken(token)
    const me = await apiMe(token)
    setAuth({ status: 'authenticated', email: me.email, token })
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } catch {
      // 네트워크 실패해도 로컬 로그아웃은 항상 수행
    } finally {
      clearToken()
      setAuth({ status: 'unauthenticated' })
    }
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
