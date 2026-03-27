'use client'

import Link from 'next/link'
import { useTranslations, useLocale } from 'next-intl'
import { usePathname, useRouter } from 'next/navigation'
import { useTransition } from 'react'

export default function Nav() {
  const t = useTranslations('nav')
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [isPending, startTransition] = useTransition()

  function switchLocale(next: 'en' | 'ko') {
    // 현재 pathname에서 locale prefix 교체
    startTransition(() => {
      const segments = pathname.split('/')
      if (segments[1] === 'ko' || segments[1] === 'en') {
        segments[1] = next === 'en' ? '' : next
        const newPath = segments.filter(Boolean).join('/') || '/'
        router.push(next === 'en' ? `/${newPath}` : `/${next}/${newPath.replace(/^\//, '')}`)
      } else {
        router.push(next === 'ko' ? `/ko${pathname}` : pathname)
      }
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
        <div className="flex items-center gap-2">
          {/* 갤러리 링크 */}
          <Link
            href="/gallery"
            className="px-3 py-1.5 text-sm rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            {t('gallery')}
          </Link>

          {/* 언어 전환 */}
          <div
            className="flex items-center text-sm font-mono rounded-lg overflow-hidden"
            style={{ border: '1px solid var(--border)' }}
          >
            <button
              onClick={() => switchLocale('en')}
              disabled={isPending}
              className="px-3 py-1.5 transition-colors"
              style={{
                background: locale === 'en' ? 'var(--accent)' : 'transparent',
                color: locale === 'en' ? 'white' : 'var(--text-secondary)',
                cursor: locale === 'en' ? 'default' : 'pointer',
              }}
            >
              EN
            </button>
            <button
              onClick={() => switchLocale('ko')}
              disabled={isPending}
              className="px-3 py-1.5 transition-colors"
              style={{
                background: locale === 'ko' ? 'var(--accent)' : 'transparent',
                color: locale === 'ko' ? 'white' : 'var(--text-secondary)',
                cursor: locale === 'ko' ? 'default' : 'pointer',
              }}
            >
              KO
            </button>
          </div>

          {/* 로그인 */}
          <Link
            href="/login"
            className="px-4 py-1.5 text-sm rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            {t('login')}
          </Link>

          {/* 회원가입 */}
          <Link
            href="/signup"
            className="px-4 py-1.5 text-sm rounded-lg font-medium transition-colors"
            style={{ background: 'var(--accent)', color: 'white' }}
          >
            {t('signup')}
          </Link>
        </div>
      </div>
    </header>
  )
}
