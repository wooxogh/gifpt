'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'

export default function Hero() {
  const t = useTranslations('hero')
  const [input, setInput] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    // TODO: animate 요청
    if (process.env.NODE_ENV === 'development') {
      console.log('animate:', input.trim())
    }
  }

  return (
    <section className="flex flex-1 flex-col items-center justify-center px-6 pt-24 pb-16">
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
            className="flex-1 h-14 px-5 font-mono text-sm outline-none transition-all"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-input)',
              color: 'var(--text-primary)',
              caretColor: 'var(--accent)',
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
            className="h-14 px-6 font-medium text-sm whitespace-nowrap transition-colors"
            style={{
              background: 'var(--accent)',
              color: 'white',
              borderRadius: 'var(--radius-input)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--accent-hover)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--accent)'
            }}
          >
            {t('cta')}
          </button>
        </form>

        {/* 힌트 */}
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          {t('hint')}
        </p>
      </div>
    </section>
  )
}
