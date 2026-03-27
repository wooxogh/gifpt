'use client'

import { useTranslations, useLocale } from 'next-intl'
import { usePathname, useRouter, Link } from '@/i18n/navigation'
import { useTransition } from 'react'

export default function Nav() {
  const t = useTranslations('nav')
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [isPending, startTransition] = useTransition()

  function switchLocale(next: 'en' | 'ko') {
    startTransition(() => {
      // next-intl router가 자동으로 현재 경로의 로케일만 변경
      router.replace(pathname, { locale: next })
    })
  }

  return (
    <header
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
      }}
      className="fixed top-0 left-0 right-0 z-50 h-16"
    >
      <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
        {/* 로고 */}
        <Link
          href="/"
          className="font-mono text-lg font-semibold tracking-tight"
          style={{ color: 'var(--accent)' }}
        >
          GIFPT
        </Link>

        {/* 우측 액션 */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* 갤러리 링크 — 모바일에서 숨김 (공간 부족) */}
          <Link
            href="/gallery"
            className="hidden sm:flex items-center h-11 px-3 text-sm rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            {t('gallery')}
          </Link>

          {/* 언어 전환 — 44px 터치 타겟 */}
          <div
            className="flex items-center text-sm font-mono rounded-lg overflow-hidden h-11"
            style={{ border: '1px solid var(--border)' }}
          >
            <button
              onClick={() => switchLocale('en')}
              disabled={isPending}
              className="px-3 h-full transition-colors"
              style={{
                background: locale === 'en' ? 'var(--accent)' : 'transparent',
                color: locale === 'en' ? 'white' : 'var(--text-secondary)',
                cursor: locale === 'en' ? 'default' : 'pointer',
                minWidth: '44px',
              }}
            >
              EN
            </button>
            <button
              onClick={() => switchLocale('ko')}
              disabled={isPending}
              className="px-3 h-full transition-colors"
              style={{
                background: locale === 'ko' ? 'var(--accent)' : 'transparent',
                color: locale === 'ko' ? 'white' : 'var(--text-secondary)',
                cursor: locale === 'ko' ? 'default' : 'pointer',
                minWidth: '44px',
              }}
            >
              KO
            </button>
          </div>

          {/* 로그인 — 모바일에서 숨김 */}
          <Link
            href="/login"
            className="hidden sm:flex items-center h-11 px-4 text-sm rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            {t('login')}
          </Link>

          {/* 회원가입 — 항상 노출, 44px 터치 타겟 */}
          <Link
            href="/signup"
            className="flex items-center h-11 px-4 text-sm rounded-lg font-medium transition-colors"
            style={{ background: 'var(--accent)', color: 'white' }}
          >
            {t('signup')}
          </Link>
        </div>
      </div>
    </header>
  )
}
