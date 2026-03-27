import createMiddleware from 'next-intl/middleware'
import { routing } from './i18n/routing'

export default createMiddleware(routing)

export const config = {
  matcher: [
    // 모든 경로에 적용, 단 _next, api, 정적 파일 제외
    '/((?!_next|api|.*\\..*).*)',
  ],
}
