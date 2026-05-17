const BASE = import.meta.env.VITE_API_URL ?? ''

/**
 * Submit a new PPT generation job.
 * Returns immediately with { job_id, status: 'queued' }
 */
export async function submitJob({ topic, grade, slides, subject }) {
  const res = await fetch(`${BASE}/api/ppt/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, grade, slides, subject }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Server error ${res.status}`)
  }
  return res.json()
}

/**
 * Poll a job's current status + result.
 */
export async function getJobStatus(jobId) {
  const res = await fetch(`${BASE}/api/ppt/status/${jobId}`)
  if (!res.ok) throw new Error(`Job ${jobId} not found`)
  return res.json()
}

/**
 * Cache stats for the debug panel.
 */
export async function getCacheStats() {
  const res = await fetch(`${BASE}/api/cache/stats`)
  if (!res.ok) return null
  return res.json()
}
