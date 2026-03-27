'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Link, useRouter } from '@/i18n/navigation'
import { useAuth } from '@/context/AuthContext'

export default function SignupPage() {
  const t = useTranslations('auth')
  const { signup } = useAuth()
  const router = useRouter()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signup(email, password, displayName)
      router.push('/')
    } catch (err) {
      const msg = err instanceof Error ? err.message : ''
      setError(msg === 'email already exists' ? t('email_taken') : t('signup_failed'))
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius-input)',
    color: 'var(--text-primary)',
  }

  function onFocus(e: React.FocusEvent<HTMLInputElement>) {
    e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)'
    e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-glow)'
  }
  function onBlur(e: React.FocusEvent<HTMLInputElement>) {
    e.currentTarget.style.borderColor = 'var(--border-strong)'
    e.currentTarget.style.boxShadow = 'none'
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
        <div className="text-center flex flex-col gap-2">
          <span className="font-mono text-lg font-semibold" style={{ color: 'var(--accent)' }}>
            GIFPT
          </span>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {t('signup_title')}
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={t('display_name')}
            required
            className="h-12 px-4 text-sm outline-none transition-all"
            style={inputStyle}
            onFocus={onFocus}
            onBlur={onBlur}
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('email')}
            required
            className="h-12 px-4 text-sm outline-none transition-all"
            style={inputStyle}
            onFocus={onFocus}
            onBlur={onBlur}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('password')}
            required
            minLength={8}
            className="h-12 px-4 text-sm outline-none transition-all"
            style={inputStyle}
            onFocus={onFocus}
            onBlur={onBlur}
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
            {loading ? t('signing_up') : t('signup_title')}
          </button>
        </form>

        <p className="text-xs text-center" style={{ color: 'var(--text-secondary)' }}>
          {t('have_account')}{' '}
          <Link href="/login" style={{ color: 'var(--accent)' }}>
            {t('login_link')}
          </Link>
        </p>
      </div>
    </div>
  )
}
