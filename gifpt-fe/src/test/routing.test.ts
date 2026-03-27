import { describe, it, expect } from 'vitest'
import { routing } from '@/i18n/routing'

describe('i18n routing config', () => {
  it('supports en and ko locales', () => {
    expect(routing.locales).toContain('en')
    expect(routing.locales).toContain('ko')
    expect(routing.locales).toHaveLength(2)
  })

  it('defaults to English', () => {
    expect(routing.defaultLocale).toBe('en')
  })

  it('uses as-needed prefix so /en/ does not appear in English URLs', () => {
    expect(routing.localePrefix).toBe('as-needed')
  })
})
