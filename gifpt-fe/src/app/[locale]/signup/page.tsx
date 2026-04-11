'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Link, useRouter } from '@/i18n/navigation'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'
import { useAuth } from '@/context/AuthContext'

export default function SignupPage() {
  const t = useTranslations('auth')
  const { signup } = useAuth()
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
      await signup(email, password)
      router.push('/')
    } catch (err) {
      const msg = err instanceof Error ? err.message : ''
      setError(msg === 'email already exists' ? t('email_taken') : t('signup_failed'))
    } finally {
      setLoading(false)
    }
  }

  const inputBase: React.CSSProperties = {
    background: 'var(--bg-lowest)',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius-input)',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-inter)',
  }

  function onFocus(e: React.FocusEvent<HTMLInputElement>) {
    e.currentTarget.style.borderColor = 'var(--accent)'
    e.currentTarget.style.boxShadow = '0 0 0 1px var(--accent)'
  }

  function onBlur(e: React.FocusEvent<HTMLInputElement>) {
    e.currentTarget.style.borderColor = 'var(--border-strong)'
    e.currentTarget.style.boxShadow = 'none'
  }

  return (
    <>
      <Nav />

      <main
        className="min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-12 relative overflow-hidden"
        style={{
          background: 'radial-gradient(circle at 50% 35%, rgba(111, 0, 190, 0.16) 0%, transparent 72%)',
        }}
      >
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(circle at center, rgba(111, 0, 190, 0.12) 0%, transparent 70%)',
          }}
        />
        <div
          className="absolute -top-1/4 -left-1/4 w-[28rem] h-[28rem] rounded-full pointer-events-none"
          style={{ background: 'rgba(111, 0, 190, 0.08)', filter: 'blur(120px)' }}
        />
        <div
          className="absolute -bottom-1/4 -right-1/4 w-[34rem] h-[34rem] rounded-full pointer-events-none"
          style={{ background: 'rgba(128, 131, 255, 0.08)', filter: 'blur(150px)' }}
        />

        <div className="w-full max-w-[480px] z-10">
          <div
            className="p-8 md:p-12 rounded-xl shadow-2xl relative"
            style={{
              background: 'rgba(28, 27, 27, 0.6)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              border: '1px solid var(--border)',
            }}
          >
            <div className="text-center mb-10">
              <div
                className="inline-flex items-center justify-center w-16 h-16 rounded-xl mb-6"
                style={{
                  background: 'var(--bg-highest)',
                  border: '1px solid rgba(70,69,84,0.2)',
                }}
              >
                <span
                  className="material-symbols-outlined text-3xl"
                  style={{ color: 'var(--primary)', fontVariationSettings: "'FILL' 1" }}
                >
                  auto_awesome
                </span>
              </div>

              <p
                className="text-xs uppercase tracking-[0.35em] mb-3"
                style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-space-grotesk)' }}
              >
                GIFPT
              </p>
              <h1
                className="text-3xl md:text-4xl font-extrabold tracking-tight mb-3"
                style={{ fontFamily: 'var(--font-manrope)', color: 'var(--text-primary)' }}
              >
                {t('signup_title')}
              </h1>
              <p
                className="text-sm md:text-base"
                style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
              >
                {t('signup_subtitle')}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label
                  className="block text-xs uppercase tracking-widest px-1"
                  style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {t('email')}
                </label>
                <div className="relative">
                  <span
                    className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-lg select-none"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    alternate_email
                  </span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    required
                    className="w-full py-3.5 pl-12 pr-4 text-sm outline-none transition-all"
                    style={inputBase}
                    onFocus={onFocus}
                    onBlur={onBlur}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  className="block text-xs uppercase tracking-widest px-1"
                  style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-space-grotesk)' }}
                >
                  {t('password')}
                </label>
                <div className="relative">
                  <span
                    className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-lg select-none"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    lock
                  </span>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    minLength={8}
                    className="w-full py-3.5 pl-12 pr-4 text-sm outline-none transition-all"
                    style={inputBase}
                    onFocus={onFocus}
                    onBlur={onBlur}
                  />
                </div>
              </div>



              {error && (
                <p className="text-xs text-center" style={{ color: 'var(--error)' }}>
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-4 rounded-lg font-extrabold transition-all duration-300 active:scale-[0.98] mt-4"
                style={{
                  background: 'linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%)',
                  color: 'var(--on-primary)',
                  fontFamily: 'var(--font-manrope)',
                  opacity: loading ? 0.7 : 1,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  boxShadow: loading ? 'none' : '0 0 24px rgba(192,193,255,0.2)',
                }}
              >
                {loading ? t('signing_up') : t('signup_title')}
              </button>
            </form>



          </div>

          <div className="text-center mt-8">
            <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
              {t('have_account')}{' '}
              <Link
                href="/login"
                className="font-semibold transition-colors"
                style={{ color: 'var(--secondary)' }}
              >
                {t('login_link')}
              </Link>
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </>
  )
}
