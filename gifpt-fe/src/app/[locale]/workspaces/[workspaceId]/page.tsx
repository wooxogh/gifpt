'use client'

import { use, useEffect, useState, useRef, useCallback } from 'react'
import { useTranslations } from 'next-intl'
import { Link, useRouter } from '@/i18n/navigation'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'
import { useAuth } from '@/context/AuthContext'
import { fetchWorkspace, chatOnWorkspace, type WorkspaceDetail, type WorkspaceStatus } from '@/lib/api'

const POLL_INTERVAL_MS = 4000
const MAX_POLLS = 60

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
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
      style={{ background: s.bg, color: s.color }}
    >
      {(status === 'PENDING' || status === 'RUNNING') && (
        <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: s.color }} />
      )}
      {s.label}
    </span>
  )
}

type ChatMessage = { role: 'user' | 'assistant'; content: string }

export default function WorkspaceDetailPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const t = useTranslations('workspaces')
  const { auth } = useAuth()
  const router = useRouter()
  const { workspaceId: workspaceIdStr } = use(params)
  const workspaceId = Number(workspaceIdStr)
  const hasValidWorkspaceId = Number.isFinite(workspaceId) && workspaceId > 0

  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const pollCount = useRef(0)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async (poll = false) => {
    if (auth.status !== 'authenticated' || !hasValidWorkspaceId) return
    try {
      const ws = await fetchWorkspace(workspaceId, auth.token)
      setWorkspace(ws)
      if (!poll) setLoading(false)

      if (ws.status === 'PENDING' || ws.status === 'RUNNING') {
        pollCount.current += 1
        if (pollCount.current < MAX_POLLS) {
          pollTimer.current = setTimeout(() => load(true), POLL_INTERVAL_MS)
        }
      }
    } catch {
      if (!poll) {
        setLoadError('Failed to load workspace.')
        setLoading(false)
      }
    }
  }, [auth, workspaceId, hasValidWorkspaceId])

  useEffect(() => {
    if (auth.status === 'unauthenticated') { router.push('/login'); return }
    if (!hasValidWorkspaceId) {
      setLoadError('Not found.')
      setLoading(false)
      return
    }
    if (auth.status === 'authenticated') load()
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current) }
  }, [auth.status, hasValidWorkspaceId, load, router])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleChat(e: React.FormEvent) {
    e.preventDefault()
    const msg = chatInput.trim()
    if (!msg || chatSending || auth.status !== 'authenticated') return
    setChatInput('')
    setChatSending(true)
    setChatError(null)
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    try {
      const { answer } = await chatOnWorkspace(workspaceId, msg, auth.token)
      setMessages((prev) => [...prev, { role: 'assistant', content: answer }])
    } catch {
      setChatError(t('error_chat'))
    } finally {
      setChatSending(false)
    }
  }

  if (auth.status === 'loading' || loading) {
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

  if (loadError || !workspace) {
    return (
      <>
        <Nav />
        <main className="flex flex-1 flex-col items-center justify-center gap-4 pt-20" style={{ minHeight: '60vh' }}>
          <p className="text-sm" style={{ color: 'var(--error)' }}>{loadError ?? 'Not found.'}</p>
          <Link href="/workspaces" className="text-sm underline" style={{ color: 'var(--primary)' }}>
            {t('back_to_list')}
          </Link>
        </main>
        <Footer />
      </>
    )
  }

  const isProcessing = workspace.status === 'PENDING' || workspace.status === 'RUNNING'
  const chatEnabled = workspace.status === 'SUCCESS'

  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col pt-20 pb-24 px-6 md:px-8 max-w-screen-xl mx-auto w-full gap-8">

        {/* Back + title */}
        <div>
          <Link
            href="/workspaces"
            className="inline-flex items-center gap-1.5 text-sm mb-6 transition-colors hover:opacity-80"
            style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
          >
            <span className="material-symbols-outlined text-base">arrow_back</span>
            {t('back_to_list')}
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1
              className="text-3xl md:text-4xl font-black tracking-tighter"
              style={{ fontFamily: 'var(--font-manrope)', color: 'var(--text-primary)' }}
            >
              {workspace.title}
            </h1>
            <StatusBadge status={workspace.status} />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left column: video + summary */}
          <div className="flex flex-col gap-6">

            {/* Video player */}
            <div
              className="rounded-2xl overflow-hidden aspect-video relative"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
            >
              {workspace.videoUrl ? (
                <video
                  src={workspace.videoUrl}
                  controls
                  className="w-full h-full object-contain"
                  style={{ background: '#000' }}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  {workspace.status === 'FAILED' ? (
                    <>
                      <span className="material-symbols-outlined text-4xl" style={{ color: 'var(--error)' }}>error_outline</span>
                      <p className="text-sm" style={{ color: 'var(--error)' }}>{t('detail_failed')}</p>
                    </>
                  ) : (
                    <>
                      <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: 'var(--primary)', borderTopColor: 'transparent' }} />
                      <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{t('detail_processing')}</p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Summary */}
            <div
              className="rounded-2xl p-5"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
            >
              <h2
                className="text-sm font-semibold mb-3"
                style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-space-grotesk)', textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                {t('detail_summary_title')}
              </h2>
              {workspace.summary ? (
                <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-inter)' }}>
                  {workspace.summary}
                </p>
              ) : (
                <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
                  {isProcessing ? t('detail_summary_empty') : '—'}
                </p>
              )}
            </div>
          </div>

          {/* Right column: chat */}
          <div
            className="flex flex-col rounded-2xl overflow-hidden"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              minHeight: '480px',
            }}
          >
            <div className="px-5 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
              <h2
                className="text-sm font-semibold"
                style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-space-grotesk)', textTransform: 'uppercase', letterSpacing: '0.05em' }}
              >
                {t('detail_chat_title')}
              </h2>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4" style={{ maxHeight: '380px' }}>
              {messages.length === 0 && (
                <p className="text-xs text-center mt-8" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
                  {chatEnabled ? t('detail_chat_placeholder') : (isProcessing ? t('detail_processing') : t('detail_failed'))}
                </p>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className="max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed"
                    style={
                      msg.role === 'user'
                        ? { background: 'var(--primary)', color: 'var(--on-primary)', fontFamily: 'var(--font-inter)' }
                        : { background: 'var(--bg-elevated)', color: 'var(--text-primary)', fontFamily: 'var(--font-inter)', border: '1px solid var(--border)' }
                    }
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {chatSending && (
                <div className="flex justify-start">
                  <div
                    className="px-4 py-2.5 rounded-2xl flex items-center gap-1"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                  >
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full animate-bounce"
                        style={{ background: 'var(--text-muted)', animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Chat error */}
            {chatError && (
              <p className="px-5 text-xs" style={{ color: 'var(--error)' }}>{chatError}</p>
            )}

            {/* Input */}
            <form
              onSubmit={handleChat}
              className="px-4 py-3 border-t flex gap-2"
              style={{ borderColor: 'var(--border)' }}
            >
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={chatEnabled ? t('detail_chat_placeholder') : '...'}
                disabled={!chatEnabled || chatSending}
                className="flex-1 h-10 px-3 rounded-xl text-sm outline-none disabled:opacity-50 transition-all duration-150"
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-inter)',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--primary)' }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)' }}
              />
              <button
                type="submit"
                disabled={!chatEnabled || chatSending || !chatInput.trim()}
                className="h-10 px-4 rounded-xl text-sm font-semibold transition-all duration-150 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
                style={{
                  background: 'var(--primary)',
                  color: 'var(--on-primary)',
                  fontFamily: 'var(--font-space-grotesk)',
                }}
              >
                {chatSending ? t('detail_chat_sending') : t('detail_chat_send')}
              </button>
            </form>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
