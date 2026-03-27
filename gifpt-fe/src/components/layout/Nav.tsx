'use client'

import { useTranslations } from 'next-intl'
import { useRouter, Link, usePathname } from '@/i18n/navigation'
import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'

export default function Nav() {
  const t = useTranslations('nav')
  const router = useRouter()
  const pathname = usePathname()
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
    <nav
      className="fixed top-0 w-full z-50"
      style={{
        background: 'rgba(19, 19, 19, 0.6)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: '0 8px 32px 0 rgba(128, 131, 255, 0.08)',
        borderBottom: '1px solid rgba(70,69,84,0.15)',
      }}
    >
      <div className="flex justify-between items-center px-8 h-20 w-full max-w-screen-2xl mx-auto">
        <Link
          href="/"
          className="text-2xl font-black tracking-tighter"
          style={{ fontFamily: 'var(--font-manrope)', color: 'var(--primary)' }}
        >
          GIFPT
        </Link>

        <div className="hidden md:flex items-center space-x-8" style={{ fontFamily: 'var(--font-manrope)', fontSize: '14px' }}>
          <Link
            href="/gallery"
            className="transition-colors relative"
            style={{ color: pathname === '/gallery' ? 'var(--primary)' : 'var(--text-muted)' }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--primary)' }}
            onMouseLeave={(e) => {
              if (pathname !== '/gallery') e.currentTarget.style.color = 'var(--text-muted)'
            }}
          >
            {t('gallery')}
            {pathname === '/gallery' && (
              <span
                className="absolute -bottom-1 left-0 right-0 h-0.5 rounded-full"
                style={{ background: 'var(--primary)' }}
              />
            )}
          </Link>

          {auth.status === 'authenticated' ? (
            <div className="flex items-center space-x-4">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {auth.email}
              </span>
              <button
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="px-5 py-2 rounded-lg font-bold transition-all duration-200 active:scale-95"
                style={{
                  background: 'var(--primary)',
                  color: '#0d0096',
                  opacity: isLoggingOut ? 0.7 : 1,
                }}
              >
                {isLoggingOut ? '...' : t('logout')}
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-4">
              <Link
                href="/login"
                className="transition-colors hover:opacity-80 active:scale-95 duration-150"
                style={{ color: 'var(--text-muted)' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--primary)' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)' }}
              >
                {t('login')}
              </Link>
              <Link
                href="/signup"
                className="px-5 py-2 rounded-lg font-bold hover:opacity-80 transition-all duration-300 active:scale-95"
                style={{ background: 'var(--primary)', color: '#0d0096' }}
              >
                {t('signup')}
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
