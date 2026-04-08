'use client'

import { useTranslations } from 'next-intl'
import { useState, useEffect, useCallback } from 'react'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'
import { useAuth } from '@/context/AuthContext'
import {
  fetchGalleryTrending,
  fetchGalleryMine,
  type GalleryItem,
} from '@/lib/api'

type Tab = 'trending' | 'mine'

const GRADIENT_VARS = [
  'var(--gallery-card-gradient-1)',
  'var(--gallery-card-gradient-2)',
  'var(--gallery-card-gradient-3)',
  'var(--gallery-card-gradient-4)',
  'var(--gallery-card-gradient-5)',
  'var(--gallery-card-gradient-6)',
  'var(--gallery-card-gradient-7)',
  'var(--gallery-card-gradient-8)',
]

function pickGradient(id: number) {
  return GRADIENT_VARS[id % GRADIENT_VARS.length]
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function GalleryPage() {
  const t = useTranslations('gallery')
  const { auth } = useAuth()
  const isAuthed = auth.status === 'authenticated'

  const [tab, setTab] = useState<Tab>('trending')
  const [items, setItems] = useState<GalleryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const token = auth.status === 'authenticated' ? auth.token : null

  const loadPage = useCallback(
    async (pageNum: number, append = false) => {
      setLoading(true)
      try {
        const data =
          tab === 'mine' && token
            ? await fetchGalleryMine(token, pageNum)
            : await fetchGalleryTrending(pageNum)

        setItems((prev) => (append ? [...prev, ...data.content] : data.content))
        setHasMore(data.number + 1 < data.totalPages)
        setPage(pageNum)
      } catch {
        // silently fail — show empty
      } finally {
        setLoading(false)
      }
    },
    [tab, token],
  )

  // Reset on tab change
  useEffect(() => {
    setItems([])
    setExpandedId(null)
    loadPage(0)
  }, [tab, loadPage])

  function handleLoadMore() {
    loadPage(page + 1, true)
  }

  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col">
        {/* ── Header + Tabs ── */}
        <section className="relative pt-28 pb-8 px-8 overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                'radial-gradient(ellipse at 50% 0%, rgba(128, 131, 255, 0.12) 0%, transparent 70%)',
            }}
          />
          <div className="relative max-w-screen-2xl mx-auto flex flex-col md:flex-row md:items-end md:justify-between gap-6">
            <div>
              <h1
                className="text-4xl md:text-5xl font-black tracking-tighter mb-3"
                style={{ fontFamily: 'var(--font-manrope)' }}
              >
                {t('header_title_prefix')}{' '}
                <span className="hero-text-gradient">
                  {t('header_title_highlight')}
                </span>
              </h1>
              <p
                className="text-base max-w-lg"
                style={{
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-inter)',
                }}
              >
                {t('subtitle')}
              </p>
            </div>
            <div
              className="flex gap-1 p-1 rounded-lg w-fit shrink-0"
              style={{ background: 'var(--bg-surface)' }}
            >
            <button
              onClick={() => setTab('trending')}
              className="px-5 py-2 rounded-md text-sm font-medium transition-all duration-200"
              style={{
                fontFamily: 'var(--font-space-grotesk)',
                background:
                  tab === 'trending' ? 'var(--bg-elevated)' : 'transparent',
                color:
                  tab === 'trending'
                    ? 'var(--text-primary)'
                    : 'var(--text-muted)',
                boxShadow:
                  tab === 'trending'
                    ? '0 1px 3px rgba(0,0,0,0.3)'
                    : 'none',
              }}
            >
              {t('tab_trending')}
            </button>
            {isAuthed && (
              <button
                onClick={() => setTab('mine')}
                className="px-5 py-2 rounded-md text-sm font-medium transition-all duration-200"
                style={{
                  fontFamily: 'var(--font-space-grotesk)',
                  background:
                    tab === 'mine' ? 'var(--bg-elevated)' : 'transparent',
                  color:
                    tab === 'mine'
                      ? 'var(--text-primary)'
                      : 'var(--text-muted)',
                  boxShadow:
                    tab === 'mine'
                      ? '0 1px 3px rgba(0,0,0,0.3)'
                      : 'none',
                }}
              >
                {t('tab_my_gallery')}
              </button>
            )}
          </div>
          </div>
        </section>

        {/* ── Grid ── */}
        <section className="px-8 max-w-screen-2xl mx-auto w-full">
          {loading && items.length === 0 ? (
            <div className="flex justify-center py-24">
              <span
                className="material-symbols-outlined text-3xl animate-spin"
                style={{ color: 'var(--text-muted)' }}
              >
                progress_activity
              </span>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4">
              <span
                className="material-symbols-outlined text-5xl"
                style={{ color: 'var(--text-muted)', opacity: 0.4 }}
              >
                movie_filter
              </span>
              <p
                className="text-center text-lg"
                style={{
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-inter)',
                }}
              >
                {tab === 'mine' ? t('my_empty') : t('empty')}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 pb-8">
                {items.map((item) => (
                  <GalleryCard
                    key={item.id}
                    item={item}
                    expanded={expandedId === item.id}
                    onToggle={() =>
                      setExpandedId(
                        expandedId === item.id ? null : item.id,
                      )
                    }
                  />
                ))}
              </div>

              {hasMore && (
                <div className="flex justify-center pb-12">
                  <button
                    onClick={handleLoadMore}
                    disabled={loading}
                    className="px-6 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 active:scale-95"
                    style={{
                      background: 'var(--bg-elevated)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border)',
                      fontFamily: 'var(--font-space-grotesk)',
                      opacity: loading ? 0.6 : 1,
                    }}
                  >
                    {loading ? '...' : t('load_more')}
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </main>
      <Footer />
    </>
  )
}

/* ── Gallery Card ── */

function GalleryCard({
  item,
  expanded,
  onToggle,
}: {
  item: GalleryItem
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div
      className="rounded-xl overflow-hidden transition-all duration-200 cursor-pointer group"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'rgba(128,131,255,0.4)'
        e.currentTarget.style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--border)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
      onClick={onToggle}
    >
      {/* Thumbnail / Video */}
      <div className="relative" style={{ aspectRatio: '16/9' }}>
        {expanded && item.videoUrl ? (
          <video
            src={item.videoUrl}
            autoPlay
            muted
            playsInline
            controls
            className="w-full h-full object-cover"
            style={{ background: 'var(--bg-elevated)' }}
            onClick={(e) => e.stopPropagation()}
          />
        ) : item.videoUrl ? (
          <video
            src={item.videoUrl}
            muted
            playsInline
            preload="metadata"
            className="w-full h-full object-cover"
            style={{ background: 'var(--bg-elevated)' }}
          />
        ) : (
          <div
            className="w-full h-full flex items-center justify-center"
            style={{ background: pickGradient(item.id) }}
          >
            <span
              className="material-symbols-outlined text-4xl transition-transform duration-200 group-hover:scale-110"
              style={{ color: 'rgba(255,255,255,0.7)' }}
            >
              play_circle
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <h3
          className="text-sm font-semibold truncate"
          style={{
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-manrope)',
          }}
        >
          {item.algorithm}
        </h3>
        <p
          className="text-xs mt-1"
          style={{
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-inter)',
          }}
        >
          {formatDate(item.createdAt)}
        </p>
      </div>
    </div>
  )
}
