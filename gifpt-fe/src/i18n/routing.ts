import { defineRouting } from 'next-intl/routing'

export const routing = defineRouting({
  locales: ['en', 'ko'],
  defaultLocale: 'en',
  // /en/... 대신 / 으로 — 영어는 prefix 없음
  localePrefix: 'as-needed',
})
