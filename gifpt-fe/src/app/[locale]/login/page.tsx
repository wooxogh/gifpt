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
  const [showPassword, setShowPassword] = useState(false)
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

  const inputBase: React.CSSProperties = {
    background: 'var(--bg-lowest)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-input)',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-inter)',
  }

  function onFocus(e: React.FocusEvent<HTMLInputElement>) {
    e.currentTarget.style.borderColor = 'var(--primary)'
    e.currentTarget.style.boxShadow = '0 0 0 1px var(--primary)'
  }
  function onBlur(e: React.FocusEvent<HTMLInputElement>) {
    e.currentTarget.style.borderColor = 'var(--border)'
    e.currentTarget.style.boxShadow = 'none'
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center pt-24 pb-12 px-6 relative overflow-hidden"
      style={{
        background: 'radial-gradient(circle at 50% 50%, rgba(111,0,190,0.08) 0%, transparent 70%)',
      }}
    >
      {/* Ambient blobs */}
      <div
        className="absolute -top-1/4 -right-1/4 w-96 h-96 rounded-full pointer-events-none"
        style={{ background: 'rgba(111,0,190,0.06)', filter: 'blur(100px)' }}
      />
      <div
        className="absolute -bottom-1/4 -left-1/4 w-96 h-96 rounded-full pointer-events-none"
        style={{ background: 'rgba(128,131,255,0.06)', filter: 'blur(100px)' }}
      />

      <div className="w-full max-w-md z-10">
        {/* Card */}
        <div
          className="p-8 md:p-12 rounded-xl shadow-2xl"
          style={{
            background: 'rgba(53,53,52,0.6)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(70,69,84,0.15)',
          }}
        >
          {/* Icon + Title */}
          <div className="text-center mb-10">
            <div
              className="inline-flex items-center justify-center w-16 h-16 rounded-xl mb-6"
              style={{
                background: '#1c1b1b',
                border: '1px solid rgba(70,69,84,0.15)',
              }}
            >
              <span
                className="material-symbols-outlined text-3xl"
                style={{
                  color: 'var(--primary)',
                  fontVariationSettings: "'FILL' 1",
                }}
              >
                auto_awesome
              </span>
            </div>
            <h1
              className="text-3xl font-extrabold tracking-tight mb-2"
              style={{ fontFamily: 'var(--font-manrope)', color: 'var(--text-primary)' }}
            >
              {t('login_welcome')}
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
              {t('login_subtitle')}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email */}
            <div className="space-y-2">
              <label
                className="block text-xs uppercase tracking-widest font-medium ml-1"
                style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-space-grotesk)' }}
              >
                {t('login_email_label')}
              </label>
              <div className="relative group">
                <span
                  className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-lg select-none transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                >
                  alternate_email
                </span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('login_email_placeholder')}
                  required
                  className="w-full py-3.5 pl-12 pr-4 text-sm outline-none transition-all"
                  style={inputBase}
                  onFocus={onFocus}
                  onBlur={onBlur}
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label
                className="block text-xs uppercase tracking-widest font-medium px-1"
                style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-space-grotesk)' }}
              >
                {t('login_password_label')}
              </label>
              <div className="relative group">
                <span
                  className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-lg select-none transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                >
                  lock
                </span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t('login_password_placeholder')}
                  required
                  className="w-full py-3.5 pl-12 pr-12 text-sm outline-none transition-all"
                  style={inputBase}
                  onFocus={onFocus}
                  onBlur={onBlur}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-primary)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)' }}
                >
                  <span className="material-symbols-outlined text-lg">
                    {showPassword ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
            </div>

            {error && (
              <p className="text-xs text-center" style={{ color: 'var(--error)' }}>{error}</p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 rounded-lg font-extrabold transition-all duration-300 active:scale-95"
              style={{
                background: 'var(--button-gradient)',
                color: 'var(--on-primary)',
                fontFamily: 'var(--font-manrope)',
                opacity: loading ? 0.7 : 1,
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: loading ? 'none' : '0 0 24px rgba(192,193,255,0.2)',
              }}
            >
              {loading ? t('logging_in') : t('login_submit')}
            </button>
          </form>

          <div className="mt-10 text-center">
            <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
              Don&apos;t have an account?{' '}
              <Link
                href="/signup"
                className="font-bold ml-1 transition-colors"
                style={{ color: 'var(--primary)' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--secondary)' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--primary)' }}
              >
                {t('signup_link')}
              </Link>
            </p>
          </div>
        </div>

        {/* Trust signal */}
        <div
          className="mt-8 flex justify-center items-center space-x-6 transition-all duration-500"
          style={{ opacity: 0.4, filter: 'grayscale(1)' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '1'
            e.currentTarget.style.filter = 'grayscale(0)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '0.4'
            e.currentTarget.style.filter = 'grayscale(1)'
          }}
        >
          <span
            className="text-xs uppercase tracking-tighter"
            style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-space-grotesk)' }}
          >
            {t('login_trust_signal')}
          </span>
          <div className="flex space-x-4" style={{ color: 'var(--text-muted)' }}>
            <span className="material-symbols-outlined text-xl">blur_on</span>
            <span className="material-symbols-outlined text-xl">all_inclusive</span>
            <span className="material-symbols-outlined text-xl">change_history</span>
          </div>
        </div>
      </div>
    </div>
  )
}
