'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'
import { Link } from '@/i18n/navigation'
import { useAnimate } from '@/hooks/useAnimate'
import { useAuth } from '@/context/AuthContext'

export default function Hero() {
  const t = useTranslations('hero')
  const te = useTranslations('errors')
  const { auth } = useAuth()
  const [input, setInput] = useState('')
  const token = auth.status === 'authenticated' ? auth.token : null
  const { state, animate, reset } = useAnimate(token)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return
    animate(trimmed)
  }

  const isSubmitting =
    state.phase === 'loading' ||
    state.phase === 'pending' ||
    state.phase === 'running'

  return (
    <section
      className="flex flex-col items-center justify-center px-6"
      style={{ minHeight: 'calc(100dvh - 64px)' }}
    >
      <div className="w-full max-w-2xl flex flex-col items-center gap-8 text-center">

        {/* 배지 */}
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-mono"
          style={{
            background: 'rgba(124, 106, 247, 0.1)',
            border: '1px solid rgba(124, 106, 247, 0.25)',
            color: 'var(--accent)',
          }}
        >
          <span style={{ fontSize: '8px' }}>●</span>
          Powered by Manim
        </div>

        {/* 헤드라인 */}
        <h1 className="text-6xl sm:text-7xl font-bold tracking-tight leading-[1.05]">
          <span style={{ color: 'var(--text-primary)' }}>Animate any{' '}</span>
          <span className="text-gradient">algorithm</span>
        </h1>

        {/* 서브타이틀 */}
        <p
          className="text-lg leading-relaxed max-w-md"
          style={{ color: 'var(--text-secondary)' }}
        >
          {t('subtitle')}
        </p>

        {/* 입력 폼 */}
        <form onSubmit={handleSubmit} className="w-full flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('placeholder')}
            disabled={isSubmitting}
            className="flex-1 h-14 px-5 font-mono text-sm outline-none transition-all"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-input)',
              color: 'var(--text-primary)',
              caretColor: 'var(--accent)',
              opacity: isSubmitting ? 0.6 : 1,
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)'
              e.currentTarget.style.boxShadow = '0 0 0 4px var(--accent-glow)'
              e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-strong)'
              e.currentTarget.style.boxShadow = 'none'
              e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
            }}
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="h-14 px-7 font-semibold text-sm whitespace-nowrap"
            style={{
              background: isSubmitting
                ? 'var(--accent)'
                : 'linear-gradient(135deg, #7c6af7 0%, #9585f8 100%)',
              color: 'white',
              borderRadius: 'var(--radius-input)',
              opacity: isSubmitting ? 0.7 : 1,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              boxShadow: isSubmitting ? 'none' : '0 0 24px rgba(124,106,247,0.3)',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!isSubmitting) {
                e.currentTarget.style.boxShadow = '0 0 32px rgba(124,106,247,0.5)'
                e.currentTarget.style.transform = 'translateY(-1px)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = '0 0 24px rgba(124,106,247,0.3)'
              e.currentTarget.style.transform = 'translateY(0)'
            }}
          >
            {isSubmitting ? t('animating') : t('cta')}
          </button>
        </form>

        {/* 상태 메시지 */}
        {state.phase === 'loading' && (
          <p className="text-sm animate-pulse" style={{ color: 'var(--text-secondary)' }}>
            {t('status_loading')}
          </p>
        )}

        {(state.phase === 'pending' || state.phase === 'running') && (
          <p className="text-sm animate-pulse" style={{ color: 'var(--accent)' }}>
            {state.phase === 'running' ? t('status_running') : t('status_pending')}
          </p>
        )}

        {state.phase === 'success' && (
          <div className="w-full flex flex-col items-center gap-4">
            {state.cached && (
              <span
                className="text-xs font-mono px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-secondary)',
                }}
              >
                ✦ cached
              </span>
            )}
            <video
              src={state.videoUrl}
              controls
              autoPlay
              loop
              className="w-full rounded-2xl"
              style={{
                background: 'var(--bg-surface)',
                maxHeight: '420px',
                border: '1px solid var(--border)',
              }}
            />
            <button
              onClick={reset}
              className="text-sm transition-colors"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-primary)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            >
              {t('try_another')}
            </button>
          </div>
        )}

        {state.phase === 'login_required' && (
          <div
            className="flex flex-col items-center gap-4 w-full max-w-sm px-6 py-5 rounded-2xl"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-strong)' }}
          >
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {te('login_required')}
            </p>
            <div className="flex gap-2 w-full">
              <Link
                href="/login"
                className="flex-1 h-10 flex items-center justify-center text-sm rounded-xl font-semibold"
                style={{ background: 'var(--accent)', color: 'white' }}
              >
                {t('login')}
              </Link>
              <button
                onClick={reset}
                className="flex-1 h-10 text-sm rounded-xl"
                style={{ border: '1px solid var(--border-strong)', color: 'var(--text-secondary)' }}
              >
                {t('cancel')}
              </button>
            </div>
          </div>
        )}

        {state.phase === 'error' && (
          <div className="flex flex-col items-center gap-3">
            <p className="text-sm" style={{ color: 'var(--error)' }}>
              {state.message === 'timeout'
                ? te('timeout')
                : state.message
                ? state.message
                : te('generation_failed')}
            </p>
            <button
              onClick={reset}
              className="text-sm"
              style={{ color: 'var(--text-secondary)' }}
            >
              {t('try_again')}
            </button>
          </div>
        )}

        {state.phase === 'idle' && (
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {t('hint')}
          </p>
        )}
      </div>
    </section>
  )
}
