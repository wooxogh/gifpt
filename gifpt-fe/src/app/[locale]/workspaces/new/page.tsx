'use client'

import { useState, useRef, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import { Link, useRouter } from '@/i18n/navigation'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'
import { useAuth } from '@/context/AuthContext'
import { createWorkspace } from '@/lib/api'

export default function NewWorkspacePage() {
  const t = useTranslations('workspaces')
  const { auth } = useAuth()
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [title, setTitle] = useState('')
  const [prompt, setPrompt] = useState('')
  const [pdf, setPdf] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (auth.status === 'unauthenticated') router.push('/login')
  }, [auth.status, router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!pdf || auth.status !== 'authenticated') return
    setSubmitting(true)
    setError(null)
    try {
      const ws = await createWorkspace({ title, prompt, pdf }, auth.token)
      router.push(`/workspaces/${ws.id}`)
    } catch {
      setError(t('error_create'))
      setSubmitting(false)
    }
  }

  if (auth.status === 'loading') {
    return (
      <>
        <Nav />
        <main className="flex flex-1 items-center justify-center" style={{ minHeight: '60vh' }}>
          <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: 'var(--primary)', borderTopColor: 'transparent' }} />
        </main>
        <Footer />
      </>
    )
  }

  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col items-center pt-20 pb-24 px-6 md:px-8">
        <div className="w-full max-w-xl">

          {/* Back link */}
          <Link
            href="/workspaces"
            className="inline-flex items-center gap-1.5 text-sm mb-8 transition-colors hover:opacity-80"
            style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
          >
            <span className="material-symbols-outlined text-base">arrow_back</span>
            {t('back_to_list')}
          </Link>

          <h1
            className="text-4xl font-black tracking-tighter mb-2"
            style={{ fontFamily: 'var(--font-manrope)', color: 'var(--text-primary)' }}
          >
            {t('new_title')}
          </h1>
          <p className="text-sm mb-10" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
            {t('new_subtitle')}
          </p>

          {/* Error */}
          {error && (
            <div
              className="mb-6 px-4 py-3 rounded-xl text-sm"
              style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: 'var(--error)' }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            {/* Title */}
            <div className="flex flex-col gap-2">
              <label
                className="text-sm font-semibold"
                style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-space-grotesk)' }}
              >
                {t('form_title_label')}
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t('form_title_placeholder')}
                required
                disabled={submitting}
                className="h-12 px-4 rounded-xl text-sm outline-none transition-all duration-150 disabled:opacity-50"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-inter)',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--primary)' }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)' }}
              />
            </div>

            {/* Prompt */}
            <div className="flex flex-col gap-2">
              <label
                className="text-sm font-semibold"
                style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-space-grotesk)' }}
              >
                {t('form_prompt_label')}
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={t('form_prompt_placeholder')}
                required
                disabled={submitting}
                rows={4}
                className="px-4 py-3 rounded-xl text-sm outline-none resize-none transition-all duration-150 disabled:opacity-50"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-inter)',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--primary)' }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)' }}
              />
            </div>

            {/* PDF Upload */}
            <div className="flex flex-col gap-2">
              <label
                className="text-sm font-semibold"
                style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-space-grotesk)' }}
              >
                {t('form_pdf_label')}
              </label>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={submitting}
                className="h-24 rounded-xl flex flex-col items-center justify-center gap-2 transition-all duration-150 disabled:opacity-50"
                style={{
                  background: pdf ? 'rgba(128,131,255,0.06)' : 'var(--bg-surface)',
                  border: `1px dashed ${pdf ? 'rgba(128,131,255,0.4)' : 'var(--border)'}`,
                  color: pdf ? 'var(--primary)' : 'var(--text-muted)',
                }}
              >
                <span className="material-symbols-outlined text-2xl">
                  {pdf ? 'description' : 'upload_file'}
                </span>
                <span className="text-xs font-medium" style={{ fontFamily: 'var(--font-inter)' }}>
                  {pdf ? pdf.name : t('form_pdf_hint')}
                </span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting || !pdf}
              className="h-12 rounded-xl font-bold text-sm transition-all duration-200 active:scale-95 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
              style={{
                background: 'var(--primary)',
                color: 'var(--on-primary)',
                fontFamily: 'var(--font-space-grotesk)',
              }}
            >
              {submitting ? t('form_submitting') : t('form_submit')}
            </button>
          </form>
        </div>
      </main>
      <Footer />
    </>
  )
}
