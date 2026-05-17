import { useState, useEffect, useRef } from 'react'
import { getJobStatus } from '../api/pptApi'

const POLL_INTERVAL_MS = 2000

/**
 * Polls a job ID every 2s until status is 'done' or 'failed'.
 * Returns the latest JobResponse object.
 *
 * Why polling over WebSockets:
 *   - Works on all hosting tiers (Railway free, Render, Vercel)
 *   - Survives page refresh — job is still there, just re-poll
 *   - No extra server infrastructure needed
 *   - 2s interval is imperceptible UX-wise for a 3–10s job
 */
export function useJobPoller(jobId) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!jobId) return

    const poll = async () => {
      try {
        const data = await getJobStatus(jobId)
        setJob(data)
        if (data.status === 'done' || data.status === 'failed') {
          clearInterval(intervalRef.current)
        }
      } catch (err) {
        setError(err.message)
        clearInterval(intervalRef.current)
      }
    }

    poll() // immediate first fetch
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS)

    return () => clearInterval(intervalRef.current)
  }, [jobId])

  return { job, error }
}
