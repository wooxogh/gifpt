const TOKEN_KEY = 'gifpt_access_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
}

export async function apiLogin(email: string, password: string): Promise<string> {
  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.error ?? 'login_failed')
  }
  const data = await res.json()
  return data.accessToken
}

export async function apiSignup(email: string, password: string, displayName: string): Promise<string> {
  const res = await fetch('/api/v1/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password, displayName }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.error ?? 'signup_failed')
  }
  const data = await res.json()
  return data.accessToken
}

export async function apiLogout(): Promise<void> {
  try {
    await fetch('/api/v1/auth/logout', {
      method: 'POST',
      credentials: 'include',
    })
  } finally {
    clearToken()
  }
}

export async function apiMe(token: string): Promise<{ email: string }> {
  const res = await fetch('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  })
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) throw new Error('unauthorized')
    throw new Error(`request_failed_${res.status}`)
  }
  return res.json()
}
