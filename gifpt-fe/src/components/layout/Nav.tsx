'use client'

import { useTranslations } from 'next-intl'
import { useRouter, Link } from '@/i18n/navigation'
import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'

export default function Nav() {
  const t = useTranslations('nav')
  const router = useRouter()
  const { auth, logout } = useAuth()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
      router.push('/')
    } finally {
      setIsLoggingOut(false)
    }
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
        <Link
          href="/"
          className="font-mono text-lg font-semibold tracking-tight"
          style={{ color: 'var(--accent)' }}
        >
          GIFPT
        </Link>

        <div className="flex items-center gap-1 sm:gap-2">
          <Link
            href="/gallery"
            className="hidden sm:flex items-center h-11 px-3 text-sm rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            {t('gallery')}
          </Link>

          {auth.status === 'authenticated' ? (
            <>
              <span
                className="hidden sm:flex items-center h-11 px-3 text-sm"
                style={{ color: 'var(--text-secondary)' }}
              >
                {auth.email}
              </span>
              <button
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="flex items-center h-11 px-4 text-sm rounded-lg font-medium"
                style={{ border: '1px solid var(--border)', color: 'var(--text-secondary)', opacity: isLoggingOut ? 0.6 : 1 }}
              >
                {isLoggingOut ? '...' : t('logout')}
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden sm:flex items-center h-11 px-4 text-sm rounded-lg transition-colors"
                style={{ color: 'var(--text-secondary)' }}
              >
                {t('login')}
              </Link>
              <Link
                href="/signup"
                className="flex items-center h-11 px-4 text-sm rounded-lg font-medium transition-colors"
                style={{ background: 'var(--accent)', color: 'white' }}
              >
                {t('signup')}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
