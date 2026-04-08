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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
      router.push('/')
      setIsMobileMenuOpen(false)
    } finally {
      setIsLoggingOut(false)
    }
  }

  function closeMobileMenu() {
    setIsMobileMenuOpen(false)
  }

  return (
    <nav
      className="fixed top-0 w-full z-50"
      style={{
        background: 'var(--nav-bg)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: '0 8px 32px 0 var(--nav-shadow)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div className="flex justify-between items-center px-6 md:px-8 h-20 w-full max-w-screen-2xl mx-auto">
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
            className="relative transition-colors hover:text-primary focus-visible:text-primary"
            style={{ color: pathname === '/gallery' ? 'var(--primary)' : 'var(--text-muted)' }}
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
                  color: 'var(--on-primary)',
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
                style={{ background: 'var(--primary)', color: 'var(--on-primary)' }}
              >
                {t('signup')}
              </Link>
            </div>
          )}
        </div>

        <button
          type="button"
          className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-lg transition-colors"
          style={{
            color: 'var(--text-primary)',
            background: isMobileMenuOpen ? 'var(--bg-elevated)' : 'transparent',
          }}
          aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={isMobileMenuOpen}
          aria-controls="mobile-nav-menu"
          onClick={() => setIsMobileMenuOpen((open) => !open)}
        >
          <span className="material-symbols-outlined">
            {isMobileMenuOpen ? 'close' : 'menu'}
          </span>
        </button>
      </div>

      {isMobileMenuOpen && (
        <div
          id="mobile-nav-menu"
          className="md:hidden border-t"
          style={{
            background: 'var(--nav-bg)',
            borderTop: '1px solid var(--border)',
          }}
        >
          <div className="flex flex-col gap-3 px-6 py-4" style={{ fontFamily: 'var(--font-manrope)' }}>
            <Link
              href="/gallery"
              onClick={closeMobileMenu}
              className="px-4 py-3 rounded-lg transition-colors"
              style={{
                color: pathname === '/gallery' ? 'var(--primary)' : 'var(--text-secondary)',
                background: pathname === '/gallery' ? 'var(--bg-elevated)' : 'transparent',
              }}
            >
              {t('gallery')}
            </Link>

            {auth.status === 'authenticated' ? (
              <>
                <div className="px-4 py-2 text-sm" style={{ color: 'var(--text-muted)' }}>
                  {auth.email}
                </div>
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="px-4 py-3 rounded-lg font-bold transition-all duration-200 active:scale-95 text-left"
                  style={{
                    background: 'var(--primary)',
                    color: 'var(--on-primary)',
                    opacity: isLoggingOut ? 0.7 : 1,
                  }}
                >
                  {isLoggingOut ? '...' : t('logout')}
                </button>
              </>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <Link
                  href="/login"
                  onClick={closeMobileMenu}
                  className="px-4 py-3 rounded-lg text-center transition-colors"
                  style={{
                    color: 'var(--text-secondary)',
                    background: 'var(--bg-elevated)',
                  }}
                >
                  {t('login')}
                </Link>
                <Link
                  href="/signup"
                  onClick={closeMobileMenu}
                  className="px-4 py-3 rounded-lg text-center font-bold transition-all duration-200 active:scale-95"
                  style={{
                    background: 'var(--primary)',
                    color: 'var(--on-primary)',
                  }}
                >
                  {t('signup')}
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
