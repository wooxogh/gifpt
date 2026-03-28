'use client'

import { useEffect, useState, useCallback } from 'react'
import { useTranslations } from 'next-intl'
import { Link, useRouter } from '@/i18n/navigation'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'
import { useAuth } from '@/context/AuthContext'
import { fetchWorkspaces, deleteWorkspace, type WorkspaceSummary, type WorkspaceStatus } from '@/lib/api'

function StatusBadge({ status }: { status: WorkspaceStatus }) {
  const t = useTranslations('workspaces')
  const styles: Record<WorkspaceStatus, { bg: string; color: string; label: string }> = {
    PENDING:  { bg: 'rgba(251,191,36,0.12)', color: 'var(--warning)',  label: t('status_pending') },
    RUNNING:  { bg: 'rgba(128,131,255,0.12)', color: 'var(--primary)', label: t('status_running') },
    SUCCESS:  { bg: 'rgba(74,222,128,0.12)', color: 'var(--success)',  label: t('status_success') },
    FAILED:   { bg: 'rgba(248,113,113,0.12)', color: 'var(--error)',   label: t('status_failed') },
  }
  const s = styles[status]
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
      style={{ background: s.bg, color: s.color }}
    >
      {(status === 'PENDING' || status === 'RUNNING') && (
        <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: s.color }} />
      )}
      {s.label}
    </span>
  )
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function WorkspacesPage() {
  const t = useTranslations('workspaces')
  const { auth } = useAuth()
  const router = useRouter()
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (auth.status !== 'authenticated') return
    setLoading(true)
    setError(null)
    try {
      const page = await fetchWorkspaces(auth.token)
      setWorkspaces(page.content)
    } catch {
      setError(t('error_load'))
    } finally {
      setLoading(false)
    }
  }, [auth, t])

  useEffect(() => {
    if (auth.status === 'unauthenticated') {
      router.push('/login')
      return
    }
    if (auth.status === 'authenticated') {
      load()
    }
  }, [auth.status, load, router])

  async function handleDelete(id: number) {
    if (!confirm(t('delete_confirm'))) return
    if (auth.status !== 'authenticated') return
    setDeletingId(id)
    try {
      await deleteWorkspace(id, auth.token)
      setWorkspaces((prev) => prev.filter((w) => w.id !== id))
    } catch {
      setError(t('error_delete'))
    } finally {
      setDeletingId(null)
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
      <main className="flex flex-1 flex-col pt-20 pb-24 px-6 md:px-8 max-w-screen-xl mx-auto w-full">

        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-10">
          <div>
            <h1
              className="text-4xl md:text-5xl font-black tracking-tighter mb-2"
              style={{ fontFamily: 'var(--font-manrope)', color: 'var(--text-primary)' }}
            >
              {t('page_title')}
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
              {t('page_subtitle')}
            </p>
          </div>
          <Link
            href="/workspaces/new"
            className="flex-shrink-0 px-5 py-2.5 rounded-xl font-bold text-sm transition-all duration-200 active:scale-95 hover:opacity-90"
            style={{ background: 'var(--primary)', color: 'var(--on-primary)', fontFamily: 'var(--font-space-grotesk)' }}
          >
            + {t('new_button')}
          </Link>
        </div>

        {/* Error */}
        {error && (
          <div
            className="mb-6 px-4 py-3 rounded-xl text-sm"
            style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: 'var(--error)' }}
          >
            {error}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex justify-center py-24">
            <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: 'var(--primary)', borderTopColor: 'transparent' }} />
          </div>
        ) : workspaces.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-32 text-center">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
              style={{ background: 'rgba(128,131,255,0.08)', border: '1px solid rgba(128,131,255,0.15)' }}
            >
              <span className="material-symbols-outlined text-3xl" style={{ color: 'var(--primary)' }}>folder_open</span>
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-manrope)' }}>
              {t('empty_title')}
            </h2>
            <p className="text-sm mb-8" style={{ color: 'var(--text-muted)' }}>{t('empty_subtitle')}</p>
            <Link
              href="/workspaces/new"
              className="px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-200 active:scale-95 hover:opacity-90"
              style={{ background: 'var(--primary)', color: 'var(--on-primary)', fontFamily: 'var(--font-space-grotesk)' }}
            >
              {t('empty_cta')}
            </Link>
          </div>
        ) : (
          /* Grid */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {workspaces.map((ws) => (
              <div
                key={ws.id}
                className="group flex flex-col rounded-2xl overflow-hidden transition-all duration-200"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(128,131,255,0.3)' }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)' }}
              >
                {/* Video thumbnail or placeholder */}
                <div
                  className="aspect-video relative overflow-hidden"
                  style={{ background: 'var(--bg-elevated)' }}
                >
                  {ws.videoUrl ? (
                    <video
                      src={ws.videoUrl}
                      className="w-full h-full object-cover"
                      muted
                      preload="metadata"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="material-symbols-outlined text-4xl" style={{ color: 'var(--text-muted)' }}>
                        {ws.status === 'FAILED' ? 'error_outline' : 'hourglass_empty'}
                      </span>
                    </div>
                  )}
                  <div className="absolute top-2 left-2">
                    <StatusBadge status={ws.status} />
                  </div>
                </div>

                {/* Content */}
                <div className="flex flex-col flex-1 p-4 gap-3">
                  <h3
                    className="font-semibold text-sm leading-snug line-clamp-2"
                    style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-manrope)' }}
                  >
                    {ws.title}
                  </h3>
                  {ws.summary && (
                    <p
                      className="text-xs line-clamp-2"
                      style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
                    >
                      {ws.summary}
                    </p>
                  )}
                  <p className="text-xs mt-auto" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
                    {t('created_at')} {formatDate(ws.createdAt)}
                  </p>
                  <div className="flex gap-2 pt-1">
                    <Link
                      href={`/workspaces/${ws.id}`}
                      className="flex-1 py-2 rounded-lg text-xs font-semibold text-center transition-all duration-150 active:scale-95 hover:opacity-90"
                      style={{ background: 'var(--primary)', color: 'var(--on-primary)', fontFamily: 'var(--font-space-grotesk)' }}
                    >
                      {t('view_button')}
                    </Link>
                    <button
                      onClick={() => handleDelete(ws.id)}
                      disabled={deletingId === ws.id}
                      className="px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-150 active:scale-95 hover:opacity-90 disabled:opacity-50"
                      style={{
                        background: 'rgba(248,113,113,0.08)',
                        border: '1px solid rgba(248,113,113,0.2)',
                        color: 'var(--error)',
                        fontFamily: 'var(--font-space-grotesk)',
                      }}
                    >
                      {deletingId === ws.id ? '...' : t('delete_button')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </>
  )
}
