'use client'

import { useTranslations } from 'next-intl'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'

export default function GalleryPage() {
  const t = useTranslations('gallery')

  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col">
        <section className="relative pt-20 pb-16 px-8 text-center overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse at 50% 0%, rgba(128, 131, 255, 0.12) 0%, transparent 70%)',
            }}
          />
          <div className="relative max-w-screen-2xl mx-auto">
            <div
              className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs uppercase tracking-widest mb-8"
              style={{
                background: 'rgba(128,131,255,0.08)',
                border: '1px solid rgba(128,131,255,0.2)',
                color: 'var(--primary)',
                fontFamily: 'var(--font-space-grotesk)',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: 'var(--primary)', boxShadow: '0 0 6px var(--primary)' }}
              />
              <span>{t('header_badge')}</span>
            </div>

            <h1
              className="text-5xl md:text-7xl font-black tracking-tighter mb-6"
              style={{ fontFamily: 'var(--font-manrope)' }}
            >
              {t('header_title_prefix')}{' '}
              <span className="hero-text-gradient">{t('header_title_highlight')}</span>
            </h1>
            <p
              className="text-lg max-w-xl mx-auto mb-12"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
            >
              {t('subtitle')}
            </p>
          </div>
        </section>

        <section className="px-8 pb-24 max-w-screen-2xl mx-auto w-full">
          <div className="flex flex-col items-center justify-center py-24 space-y-4">
            <span
              className="material-symbols-outlined text-5xl"
              style={{ color: 'var(--text-muted)', opacity: 0.4 }}
            >
              movie_filter
            </span>
            <p
              className="text-center text-lg"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
            >
              {t('empty')}
            </p>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
