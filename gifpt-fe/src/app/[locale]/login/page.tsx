'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Link, useRouter } from '@/i18n/navigation'
import { useAuth } from '@/context/AuthContext'

export default function LoginPage() {
  const t = useTranslations('auth')
  const { login } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      router.push('/')
    } catch {
      setError(t('invalid_credentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div
        className="w-full max-w-sm flex flex-col gap-6 p-8 rounded-2xl"
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid var(--border-strong)',
          boxShadow: '0 0 80px rgba(124,106,247,0.06)',
        }}
      >
        {/* 로고 */}
        <div className="text-center flex flex-col gap-2">
          <span className="font-mono text-lg font-semibold" style={{ color: 'var(--accent)' }}>
            GIFPT
          </span>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {t('login_title')}
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('email')}
            required
            className="h-12 px-4 text-sm outline-none transition-all"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-input)',
              color: 'var(--text-primary)',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)'
              e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-glow)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-strong)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('password')}
            required
            className="h-12 px-4 text-sm outline-none transition-all"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-input)',
              color: 'var(--text-primary)',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)'
              e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-glow)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-strong)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          />

          {error && (
            <p className="text-xs text-center" style={{ color: 'var(--error)' }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="h-12 font-semibold text-sm mt-1"
            style={{
              background: 'linear-gradient(135deg, #7c6af7 0%, #9585f8 100%)',
              color: 'white',
              borderRadius: 'var(--radius-input)',
              opacity: loading ? 0.7 : 1,
              boxShadow: loading ? 'none' : '0 0 24px rgba(124,106,247,0.25)',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? t('logging_in') : t('login_title')}
          </button>
        </form>

        <p className="text-xs text-center" style={{ color: 'var(--text-secondary)' }}>
          {t('no_account')}{' '}
          <Link href="/signup" style={{ color: 'var(--accent)' }}>
            {t('signup_link')}
          </Link>
        </p>
      </div>
    </div>
  )
}
