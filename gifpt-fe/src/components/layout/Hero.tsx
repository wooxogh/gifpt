'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'
import Link from 'next/link'
import { useAnimate } from '@/hooks/useAnimate'

export default function Hero() {
  const t = useTranslations('hero')
  const te = useTranslations('errors')
  const [input, setInput] = useState('')
  const { state, animate, reset } = useAnimate()

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
        {/* 헤드라인 */}
        <h1
          className="text-5xl font-bold tracking-tight leading-tight"
          style={{ color: 'var(--text-primary)' }}
        >
          {t('title')}
        </h1>

        {/* 서브타이틀 */}
        <p
          className="text-lg leading-relaxed max-w-lg"
          style={{ color: 'var(--text-secondary)' }}
        >
          {t('subtitle')}
        </p>

        {/* 입력 폼 */}
        <form onSubmit={handleSubmit} className="w-full flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('placeholder')}
            disabled={isSubmitting}
            className="flex-1 h-14 px-5 font-mono text-sm outline-none transition-all"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-input)',
              color: 'var(--text-primary)',
              caretColor: 'var(--accent)',
              opacity: isSubmitting ? 0.6 : 1,
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent)'
              e.currentTarget.style.boxShadow = '0 0 0 4px var(--accent-glow)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="h-14 px-6 font-medium text-sm whitespace-nowrap transition-colors"
            style={{
              background: 'var(--accent)',
              color: 'white',
              borderRadius: 'var(--radius-input)',
              opacity: isSubmitting ? 0.7 : 1,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
            }}
            onMouseEnter={(e) => {
              if (!isSubmitting) e.currentTarget.style.background = 'var(--accent-hover)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--accent)'
            }}
          >
            {isSubmitting ? t('animating') : t('cta')}
          </button>
        </form>

        {/* 결과 영역 */}
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
                className="text-xs font-mono px-2 py-1 rounded"
                style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}
              >
                {t('cached')}
              </span>
            )}
            <video
              src={state.videoUrl}
              controls
              autoPlay
              loop
              className="w-full rounded-xl"
              style={{ background: 'var(--bg-surface)', maxHeight: '400px' }}
            />
            <button
              onClick={reset}
              className="text-sm"
              style={{ color: 'var(--text-secondary)' }}
            >
              {t('try_another')}
            </button>
          </div>
        )}

        {state.phase === 'login_required' && (
          <div className="flex flex-col items-center gap-3">
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {te('login_required')}
            </p>
            <div className="flex gap-2">
              <Link
                href="/login"
                className="h-10 px-5 text-sm rounded-lg flex items-center font-medium"
                style={{ background: 'var(--accent)', color: 'white' }}
              >
                {t('login')}
              </Link>
              <button
                onClick={reset}
                className="h-10 px-5 text-sm rounded-lg"
                style={{ border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
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

        {/* 힌트 — idle 상태에서만 표시 */}
        {state.phase === 'idle' && (
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            {t('hint')}
          </p>
        )}
      </div>
    </section>
  )
}
