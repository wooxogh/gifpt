'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { fetchAnimate, fetchJobStatus } from '@/lib/api'

export type AnimateState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'pending'; jobId: number }
  | { phase: 'running'; jobId: number }
  | { phase: 'success'; videoUrl: string; cached: boolean }
  | { phase: 'login_required' }
  | { phase: 'error'; message: string }

const POLL_INTERVAL_MS = 3000
const MAX_POLLS = 20 // 최대 1분 (20 × 3초)

export function useAnimate(token?: string | null) {
  const [state, setState] = useState<AnimateState>({ phase: 'idle' })
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollCount = useRef(0)
  const isMountedRef = useRef(true)
  const tokenRef = useRef(token)
  tokenRef.current = token

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      if (pollRef.current) {
        clearTimeout(pollRef.current)
        pollRef.current = null
      }
    }
  }, [])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current)
      pollRef.current = null
    }
    pollCount.current = 0
  }, [])

  const poll = useCallback((jobId: number) => {
    pollRef.current = setTimeout(async () => {
      if (!isMountedRef.current) return // Guard against unmounted component

      if (pollCount.current >= MAX_POLLS) {
        stopPolling()
        if (isMountedRef.current) {
          setState({ phase: 'error', message: 'timeout' })
        }
        return
      }
      pollCount.current++

      try {
        const job = await fetchJobStatus(jobId, tokenRef.current)
        
        if (!isMountedRef.current) return // Guard after async operation
        
        if (job.status === 'SUCCESS') {
          stopPolling()
          setState({ phase: 'success', videoUrl: job.resultUrl, cached: false })
        } else if (job.status === 'FAILED') {
          stopPolling()
          setState({ phase: 'error', message: job.errorMessage || 'generation_failed' })
        } else {
          setState({ phase: job.status === 'RUNNING' ? 'running' : 'pending', jobId })
          poll(jobId)
        }
      } catch {
        if (!isMountedRef.current) return
        stopPolling()
        setState({ phase: 'error', message: 'generation_failed' })
      }
    }, POLL_INTERVAL_MS)
  }, [stopPolling])

  const animate = useCallback(async (algorithm: string, prompt?: string | null) => {
    stopPolling()
    setState({ phase: 'loading' })

    try {
      const { status, data } = await fetchAnimate(algorithm, tokenRef.current, prompt)

      if (!isMountedRef.current) return // Guard after async operation

      if (status === 200 && 'videoUrl' in data) {
        setState({ phase: 'success', videoUrl: data.videoUrl, cached: true })
        return
      }

      if (status === 401) {
        setState({ phase: 'login_required' })
        return
      }

      if (status === 202 && 'jobId' in data) {
        setState({ phase: 'pending', jobId: data.jobId })
        poll(data.jobId)
        return
      }

      setState({ phase: 'error', message: 'generation_failed' })
    } catch {
      if (!isMountedRef.current) return
      setState({ phase: 'error', message: 'generation_failed' })
    }
  }, [poll, stopPolling])

  const reset = useCallback(() => {
    stopPolling()
    if (isMountedRef.current) {
      setState({ phase: 'idle' })
    }
  }, [stopPolling])

  return { state, animate, reset }
}
