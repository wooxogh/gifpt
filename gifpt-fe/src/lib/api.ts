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

export async function fetchAnimate(algorithm: string, token?: string | null): Promise<{ ok: boolean; status: number; data: AnimateResponse }> {
  const res = await fetch(`/api/v1/animate?algorithm=${encodeURIComponent(algorithm)}`, {
    credentials: 'include',
    headers: authHeaders(token),
  })
  const data = await res.json()
  return { ok: res.ok, status: res.status, data }
}

export async function fetchJobStatus(jobId: number, token?: string | null): Promise<JobStatusResponse> {
  const res = await fetch(`/api/v1/animate/status/${jobId}`, {
    credentials: 'include',
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('Failed to fetch job status')
  return res.json()
}
