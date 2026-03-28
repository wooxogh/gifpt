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

// ── Workspace types ──────────────────────────────────────────────────────────

export type WorkspaceStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED'

export type WorkspaceSummary = {
  id: number
  title: string
  status: WorkspaceStatus
  summary: string | null
  videoUrl: string | null
  createdAt: string
  updatedAt: string
}

export type WorkspaceDetail = {
  id: number
  title: string
  prompt: string
  pdfPath: string
  summary: string | null
  videoUrl: string | null
  status: WorkspaceStatus
  createdAt: string
  updatedAt: string
}

export type PageResponse<T> = {
  content: T[]
  totalElements: number
  totalPages: number
  number: number
  size: number
}

export type FileUploadResponse = {
  fileId: number
  fileName: string
}

// ── Workspace API ─────────────────────────────────────────────────────────────

export async function createWorkspace(
  data: { title: string; prompt: string; pdf: File },
  token: string,
): Promise<WorkspaceDetail> {
  const form = new FormData()
  form.append('title', data.title)
  form.append('prompt', data.prompt)
  form.append('pdf', data.pdf)
  const res = await fetch('/api/v1/workspaces', {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders(token),
    body: form,
  })
  if (!res.ok) await throwResponseError(res, 'Failed to create workspace')
  return res.json()
}

export async function createWorkspaceFromFile(
  data: { title: string; fileId: number; userPrompt: string },
  token: string,
): Promise<WorkspaceDetail> {
  const res = await fetch('/api/v1/workspaces/from-file', {
    method: 'POST',
    credentials: 'include',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to create workspace from file')
  return res.json()
}

export async function fetchWorkspaces(
  token: string,
  page = 0,
  size = 12,
): Promise<PageResponse<WorkspaceSummary>> {
  const res = await fetch(`/api/v1/workspaces?page=${page}&size=${size}&sort=createdAt,DESC`, {
    credentials: 'include',
    headers: authHeaders(token),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to fetch workspaces')
  return res.json()
}

export async function fetchWorkspace(id: number, token: string): Promise<WorkspaceDetail> {
  const res = await fetch(`/api/v1/workspaces/${id}`, {
    credentials: 'include',
    headers: authHeaders(token),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to fetch workspace')
  return res.json()
}

export async function chatOnWorkspace(
  id: number,
  message: string,
  token: string,
): Promise<{ answer: string }> {
  const res = await fetch(`/api/v1/workspaces/${id}/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to send chat message')
  return res.json()
}

export async function deleteWorkspace(id: number, token: string): Promise<void> {
  const res = await fetch(`/api/v1/workspaces/${id}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders(token),
  })
  if (!res.ok) await throwResponseError(res, 'Failed to delete workspace')
}

// ── File upload ───────────────────────────────────────────────────────────────

export async function uploadFile(file: File, prompt: string, token: string): Promise<FileUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('prompt', prompt)
  const res = await fetch('/api/v1/file/upload', {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders(token),
    body: form,
  })
  if (!res.ok) await throwResponseError(res, 'Failed to upload file')
  return res.json()
}
