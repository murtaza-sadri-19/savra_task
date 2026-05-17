import React, { useState } from 'react'
import { GenerateForm } from './components/GenerateForm'
import { JobTracker } from './components/JobTracker'
import { SlidePreview } from './components/SlidePreview'
import { submitJob } from './api/pptApi'
import { useJobPoller } from './hooks/useJobPoller'

// ─── Layout ──────────────────────────────────────────────────────────────────
// Two-column split: form (left, fixed 300px) + output panel (right, flex)
// On narrow screens the left panel sits on top.

const SIDEBAR_W = 300

const layout = {
  shell: {
    display: 'flex',
    height: '100%',
    background: '#F7F6F2',
  },
  sidebar: {
    width: SIDEBAR_W,
    minWidth: SIDEBAR_W,
    height: '100%',
    boxShadow: '2px 0 8px rgba(0,0,0,0.05)',
    flexShrink: 0,
    zIndex: 1,
  },
  main: {
    flex: 1,
    height: '100%',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  mainInner: {
    flex: 1,
    overflow: 'auto',
  },
  // Empty state
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 12,
    color: '#bbb',
    userSelect: 'none',
  },
  emptyIcon: { fontSize: 48, opacity: 0.5 },
  emptyTitle: { fontSize: 16, fontWeight: 500, color: '#999' },
  emptyDesc: { fontSize: 13, color: '#bbb', textAlign: 'center', maxWidth: 280, lineHeight: 1.6 },
  // Error state
  errorBox: {
    margin: 32,
    padding: '16px 20px',
    background: '#FCEBEB',
    border: '1px solid #F09595',
    borderRadius: 12,
    color: '#A32D2D',
    fontSize: 14,
  },
  errorLabel: { fontWeight: 600, marginBottom: 4 },
  retryBtn: {
    marginTop: 12,
    padding: '7px 16px',
    background: '#fff',
    border: '1px solid #E24B4A',
    borderRadius: 8,
    color: '#A32D2D',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
  },
}

// ─── App ─────────────────────────────────────────────────────────────────────

export function App() {
  const [jobId, setJobId]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const { job, error: pollError } = useJobPoller(jobId)

  const isDone   = job?.status === 'done'
  const isFailed = job?.status === 'failed'
  const error    = submitError ?? pollError ?? (isFailed ? job?.error : null)

  async function handleSubmit(form) {
    setSubmitError(null)
    setLoading(true)
    setJobId(null)
    try {
      const { job_id } = await submitJob(form)
      setJobId(job_id)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setJobId(null)
    setSubmitError(null)
    setLoading(false)
  }

  // ── right-panel content ────────────────────────────────────────────────────
  let rightContent

  if (error) {
    rightContent = (
      <div style={layout.errorBox}>
        <div style={layout.errorLabel}>Generation failed</div>
        <div>{error}</div>
        <button style={layout.retryBtn} onClick={handleReset}>← Try again</button>
      </div>
    )
  } else if (isDone && job?.result) {
    rightContent = <SlidePreview job={job} onReset={handleReset} />
  } else if (job || loading) {
    rightContent = <JobTracker job={job} />
  } else {
    rightContent = (
      <div style={layout.empty}>
        <span style={layout.emptyIcon}>🎞️</span>
        <div style={layout.emptyTitle}>Your slides will appear here</div>
        <div style={layout.emptyDesc}>
          Fill in the form and hit generate. You'll see live progress as the
          system routes, caches, and builds your presentation.
        </div>
      </div>
    )
  }

  return (
    <div style={layout.shell}>
      <div style={layout.sidebar}>
        <GenerateForm
          onSubmit={handleSubmit}
          loading={loading || (!!jobId && !isDone && !isFailed)}
        />
      </div>
      <main style={layout.main}>
        <div style={layout.mainInner}>
          {rightContent}
        </div>
      </main>
    </div>
  )
}
