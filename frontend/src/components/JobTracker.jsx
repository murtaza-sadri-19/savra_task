import React from 'react'

const STEPS = [
  { key: 'route',  label: 'Computing complexity score',       subLabel: 'Deciding which model to use' },
  { key: 'cache',  label: 'Checking request cache',           subLabel: 'SHA-256 exact-match lookup' },
  { key: 'llm',    label: 'Calling Groq API',                 subLabel: 'Generating slide content as JSON' },
  { key: 'parse',  label: 'Validating output schema',         subLabel: 'Pydantic parse + structure check' },
  { key: 'store',  label: 'Storing result',                   subLabel: 'Cache write + job status update' },
]

function getStepState(index, progressPct) {
  const threshold = (index / STEPS.length) * 100
  if (progressPct >= threshold + 20) return 'done'
  if (progressPct >= threshold)      return 'active'
  return 'pending'
}

const s = {
  container: { padding: '28px 32px' },
  header: { marginBottom: 28 },
  title: { fontSize: 17, fontWeight: 600, color: '#1a1a1a' },
  sub: { fontSize: 13, color: '#888', marginTop: 3 },
  jobId: {
    display: 'inline-block',
    marginTop: 8,
    padding: '2px 8px',
    background: '#EEEDFE',
    color: '#534AB7',
    borderRadius: 5,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.05em',
  },
  progressTrack: {
    height: 6,
    background: '#F1EFE8',
    borderRadius: 9999,
    overflow: 'hidden',
    marginBottom: 28,
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #7F77DD, #534AB7)',
    borderRadius: 9999,
    transition: 'width 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
  },
  stepList: { display: 'flex', flexDirection: 'column', gap: 0 },
  step: {
    display: 'flex',
    gap: 14,
    padding: '14px 0',
    borderBottom: '1px solid rgba(0,0,0,0.06)',
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: 1,
  },
  stepText: { flex: 1 },
  stepLabel: { fontSize: 14, fontWeight: 500 },
  stepSub: { fontSize: 12, color: '#999', marginTop: 2 },
}

const stepColors = {
  done:    { bg: '#EAF3DE', color: '#3B6D11' },
  active:  { bg: '#EEEDFE', color: '#534AB7' },
  pending: { bg: '#F1EFE8', color: '#aaa' },
}

const stepIcons = {
  done:    '✓',
  active:  '◉',
  pending: '○',
}

export function JobTracker({ job }) {
  const pct = job?.progress_pct ?? 0
  const message = job?.message ?? 'Starting…'

  return (
    <div style={s.container}>
      <div style={s.header}>
        <div style={s.title}>Generating presentation</div>
        <div style={s.sub}>{message}</div>
        {job?.job_id && <div style={s.jobId}>JOB #{job.job_id.toUpperCase()}</div>}
      </div>

      <div style={s.progressTrack}>
        <div style={{ ...s.progressFill, width: `${pct}%` }} />
      </div>

      <div style={s.stepList}>
        {STEPS.map((step, i) => {
          const state = getStepState(i, pct)
          const colors = stepColors[state]
          return (
            <div key={step.key} style={s.step}>
              <div style={{ ...s.iconWrap, background: colors.bg }}>
                <span style={{ fontSize: 14, color: colors.color, fontWeight: 600 }}>
                  {state === 'active'
                    ? <PulsingDot color={colors.color} />
                    : stepIcons[state]}
                </span>
              </div>
              <div style={s.stepText}>
                <div style={{
                  ...s.stepLabel,
                  color: state === 'pending' ? '#bbb' : '#1a1a1a',
                }}>
                  {step.label}
                </div>
                <div style={s.stepSub}>{step.subLabel}</div>
              </div>
            </div>
          )
        })}
      </div>

      {job?.routing && (
        <div style={{
          marginTop: 24,
          padding: '12px 14px',
          background: '#F7F6F2',
          borderRadius: 10,
          fontSize: 13,
        }}>
          <span style={{ color: '#888' }}>Routing decision: </span>
          <strong style={{ color: '#534AB7' }}>{job.routing.model}</strong>
          <span style={{ color: '#bbb', marginLeft: 8 }}>
            score {job.routing.complexity_score}/10
          </span>
        </div>
      )}
    </div>
  )
}

function PulsingDot({ color }) {
  return (
    <span style={{
      display: 'inline-block',
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: color,
      animation: 'savra-pulse 1.2s ease-in-out infinite',
    }} />
  )
}
