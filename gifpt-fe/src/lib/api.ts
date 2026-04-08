async function throwResponseError(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => ({}))
  throw new Error(body?.error ?? body?.message ?? fallback)
}

export type AnimateHitResponse = {
  status: 'SUCCESS'
  videoUrl: string
}

export type AnimatePendingResponse = {
  status: 'PENDING'
  jobId: number
}

export type AnimateErrorResponse = {
  error: 'login_required' | 'invalid_algorithm'
  message: string
}

export type AnimateResponse =
  | AnimateHitResponse
  | AnimatePendingResponse
  | AnimateErrorResponse

export type JobStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED'

export type JobStatusResponse = {
  jobId: number
  status: JobStatus
  resultUrl: string
  errorMessage: string
}

function authHeaders(token?: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetchAnimate(
  algorithm: string,
  token?: string | null,
  prompt?: string | null,
): Promise<{ ok: boolean; status: number; data: AnimateResponse }> {
  // Simple algorithm name → GET (cache-friendly)
  // Custom prompt → POST (rich pipeline)
  if (!prompt) {
    const res = await fetch(`/api/v1/animate?algorithm=${encodeURIComponent(algorithm)}`, {
      credentials: 'include',
      headers: authHeaders(token),
    })
    const data = await res.json()
    return { ok: res.ok, status: res.status, data }
  }

  const res = await fetch('/api/v1/animate', {
    method: 'POST',
    credentials: 'include',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ algorithm, prompt }),
  })
  const data = await res.json()
  return { ok: res.ok, status: res.status, data }
}

export async function fetchJobStatus(jobId: number, token?: string | null): Promise<JobStatusResponse> {
  const res = await fetch(`/api/v1/animate/status/${jobId}`, {
    credentials: 'include',
    headers: authHeaders(token),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to fetch job status')
  return res.json()
}

// ── Gallery types ────────────────────────────────────────────────────────────

export type GalleryItem = {
  id: number
  algorithm: string
  algorithmSlug: string
  videoUrl: string
  createdAt: string
}

export type PageResponse<T> = {
  content: T[]
  totalElements: number
  totalPages: number
  number: number
  size: number
}

// ── Gallery API ──────────────────────────────────────────────────────────────

export async function fetchGalleryTrending(
  page = 0,
  size = 12,
): Promise<PageResponse<GalleryItem>> {
  const res = await fetch(`/api/v1/gallery?page=${page}&size=${size}`, {
    credentials: 'include',
  })
  if (!res.ok) await throwResponseError(res, 'Failed to fetch gallery')
  return res.json()
}

export async function fetchGalleryMine(
  token: string,
  page = 0,
  size = 12,
): Promise<PageResponse<GalleryItem>> {
  const res = await fetch(`/api/v1/gallery/mine?page=${page}&size=${size}`, {
    credentials: 'include',
    headers: authHeaders(token),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to fetch my gallery')
  return res.json()
}
