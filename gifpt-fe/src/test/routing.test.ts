import { describe, it, expect } from 'vitest'
import { routing } from '@/i18n/routing'

describe('i18n routing config', () => {
  it('supports only en locale', () => {
    expect(routing.locales).toContain('en')
    expect(routing.locales).toHaveLength(1)
  })

  it('defaults to English', () => {
    expect(routing.defaultLocale).toBe('en')
  })

  it('never adds locale prefix to URLs', () => {
    expect(routing.localePrefix).toBe('never')
  })
})
