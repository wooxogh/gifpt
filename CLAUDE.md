# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Monorepo Structure

```
gifpt/
├── gifpt-fe/        # Next.js 16 frontend (Vercel)
├── GIFPT_BE/        # Spring Boot 3.5 backend (Java 17)
├── GIFPT_AI/        # Django + Celery AI worker (Python)
├── nginx/           # Reverse proxy config
├── docker-compose.yml
├── DESIGN.md        # Design system spec — read before touching UI
└── TODOS.md
```

## Frontend (`gifpt-fe`)

### Commands
```bash
cd gifpt-fe
npm run dev          # Dev server at http://localhost:3000
npm run build        # Production build (runs tsc + next build)
npm run lint         # ESLint
npm test             # Vitest (run once)
npm run test:watch   # Vitest watch mode
```

Run a single test file:
```bash
npx vitest run src/test/routing.test.ts
```

### Key Architecture

**Framework:** Next.js 16.2.1 (App Router). This version has breaking changes from Next.js 13-14 — read `node_modules/next/dist/docs/` before writing code. `middleware.ts` is deprecated; use `proxy.ts`.

**Routing:** `src/app/[locale]/` is the root layout segment. `next-intl` handles i18n with `localePrefix: 'never'` (English only, no `/en/` prefix). Locale type is derived from `routing.locales` via `export type Locale`.

**Auth flow:**
- JWT access token stored in `localStorage` via `src/lib/auth.ts`
- `AuthContext` (`src/context/AuthContext.tsx`) wraps the entire app, validates token on mount via `GET /api/v1/auth/me`
- On 401/403 → clear token + logout. On 5xx → keep token (transient failure).

**API calls:** All `/api/*` requests are proxied by Next.js to `BACKEND_URL` (env var). Set `BACKEND_URL=http://localhost:80` in `.env.local` for local dev. No CORS needed — server-to-server.

**Animate flow** (`src/hooks/useAnimate.ts`):
1. `GET /api/v1/animate?algorithm=...` with Bearer token
2. 200 → cache HIT, show video immediately
3. 401 → login_required state
4. 202 → job dispatched, poll `GET /api/v1/animate/status/{jobId}` every 3s (max 20 polls)

**Styling:** Tailwind v4 with CSS custom properties. Design tokens live in `src/app/globals.css`. Prefer CSS variables (e.g. `var(--accent)`, `var(--text-primary)`) over raw hex values in production components; direct hex usage is acceptable when defining new tokens or in clearly marked mock/demo styles. See `DESIGN.md` for the full design system.

**i18n messages:** `messages/en.json` only. Namespaces: `nav`, `hero`, `auth`, `status`, `canvas`, `gallery`, `errors`, `meta`.

**Tests:** Vitest + jsdom + `@testing-library/react`. `vitest.config.ts` is excluded from `tsconfig.json` (Next.js tsc would fail on it).

---

## Backend (`GIFPT_BE`)

### Commands
```bash
cd GIFPT_BE
./gradlew bootRun                    # Run with local profile
./gradlew build                      # Build JAR
./gradlew test                       # Run all tests
./gradlew test --tests "*.AnimateControllerTest"  # Single test class
```

### Key Architecture

**Package structure:** `com.gifpt.{analysis,file,security,user,workspace,config,healthcheck}`

**Auth:** JWT via `JwtAuthFilter`. Access token in `Authorization: Bearer` header (1h TTL). Refresh token in `HttpOnly` cookie (14d TTL). `CustomUserPrincipal` carries the authenticated user in controllers via `@AuthenticationPrincipal`.

**Animate API** (`/api/v1/animate`):
- Cache check: SHA-256 hash of normalized slug → S3 key `animations/{hash}.mp4`
- Cache HIT → 200 + `videoUrl`. Cache MISS + anonymous → 401. Cache MISS + auth → 202 + `jobId`, dispatches to Django AI server.
- `normalizeSlug()` must stay in sync with Python `normalize_slug()` — both sides compute the same S3 key.

**Job lifecycle:** `AnalysisStatus`: `PENDING → RUNNING → SUCCESS | FAILED`. Django worker calls back `POST /api/v1/analysis/{jobId}/complete` when done.

---

## AI Worker (`GIFPT_AI`)

### Commands
```bash
cd GIFPT_AI
python manage.py runserver           # Django dev server
celery -A GIFPT_AI worker -l info -Q gifpt.default  # Celery worker
```

### Key Architecture

Django handles incoming requests (`/animate`, `/analyze`, `/chat`). Heavy work (PDF → Vision → Manim → S3) is offloaded to Celery workers via Redis broker. After rendering, the worker calls back Spring at `SPRING_CALLBACK_BASE/api/v1/analysis/{jobId}/complete`.

---

## Infrastructure

**Local full stack:** `docker-compose up` starts Spring (8080), Django (8000), Celery worker, Redis, Nginx (80).

**Production:**
- Frontend → Vercel (auto-deploy on push to main). `vercel.json` in repo root configures the monorepo build.
- Backend → AWS EC2 at `3.90.161.150` via Docker Compose + Nginx.
- Videos stored in S3 bucket `gifpt-demo` (ap-northeast-1).

**Nginx CORS:** Only `https://gifpt-front.vercel.app` is whitelisted. Requests from Next.js server-side (rewrites) bypass CORS entirely.

**Vercel env vars required:** `BACKEND_URL` pointing to the EC2 server.
