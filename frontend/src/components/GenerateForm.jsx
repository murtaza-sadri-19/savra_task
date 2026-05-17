import React, { useState, useEffect } from 'react'
import { computeRouting } from '../api/routingPreview'
import { RoutingBadge } from './RoutingBadge'

const SUBJECTS = [
  'General', 'Biology', 'Physics', 'Chemistry', 'Mathematics',
  'Computer Science', 'History', 'Geography', 'English',
  'Economics', 'Accountancy', 'Political Science',
]

const s = {
  panel: {
    background: '#fff',
    borderRight: '1px solid rgba(0,0,0,0.08)',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'auto',
  },
  panelHeader: {
    padding: '20px 24px 0',
    borderBottom: '1px solid rgba(0,0,0,0.07)',
    paddingBottom: 16,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  logoText: { fontSize: 17, fontWeight: 600, color: '#1a1a1a' },
  logoSub: { fontSize: 12, color: '#999', fontWeight: 400 },
  body: { padding: '20px 24px', flex: 1 },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 500,
    color: '#666',
    marginBottom: 5,
    letterSpacing: '0.03em',
    textTransform: 'uppercase',
  },
  input: {
    width: '100%',
    height: 38,
    padding: '0 10px',
    border: '1px solid rgba(0,0,0,0.14)',
    borderRadius: 8,
    fontSize: 14,
    color: '#1a1a1a',
    background: '#fff',
    outline: 'none',
    transition: 'border-color 0.15s, box-shadow 0.15s',
  },
  row2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  routingBox: {
    marginTop: 16,
    padding: '12px 14px',
    background: '#F7F6F2',
    borderRadius: 10,
    border: '1px solid rgba(0,0,0,0.07)',
  },
  routingRow: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  routingReasons: { fontSize: 12, color: '#888', marginTop: 6, lineHeight: 1.5 },
  costRow: { display: 'flex', gap: 14, marginTop: 8, flexWrap: 'wrap' },
  costChip: { fontSize: 12, color: '#666' },
  costHighlight: { fontWeight: 600, color: '#1D9E75' },
  divider: { height: 1, background: 'rgba(0,0,0,0.07)', margin: '16px 0' },
  submitBtn: {
    width: '100%',
    height: 42,
    background: '#534AB7',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'opacity 0.15s, transform 0.1s',
    marginTop: 4,
  },
  fieldGroup: { marginBottom: 14 },
}

export function GenerateForm({ onSubmit, loading }) {
  const [form, setForm] = useState({
    topic: 'Photosynthesis',
    grade: 7,
    slides: 8,
    subject: 'Biology',
  })
  const [routing, setRouting] = useState(null)
  const [focusedField, setFocusedField] = useState(null)

  useEffect(() => {
    const r = computeRouting(form.topic, form.grade, form.slides, form.subject)
    setRouting(r)
  }, [form])

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const inputStyle = (field) => ({
    ...s.input,
    borderColor: focusedField === field ? '#7F77DD' : 'rgba(0,0,0,0.14)',
    boxShadow: focusedField === field ? '0 0 0 3px rgba(127,119,221,0.12)' : 'none',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.topic.trim() || loading) return
    onSubmit(form)
  }

  return (
    <aside style={s.panel}>
      <div style={s.panelHeader}>
        <div style={s.logo}>
          <span style={{ fontSize: 22 }}>🎓</span>
          <div>
            <div style={s.logoText}>Savra</div>
            <div style={s.logoSub}>PPT Generator</div>
          </div>
        </div>
      </div>

      <form style={s.body} onSubmit={handleSubmit}>
        <div style={s.fieldGroup}>
          <label style={s.label} htmlFor="topic">Topic</label>
          <input
            id="topic"
            style={inputStyle('topic')}
            value={form.topic}
            onChange={e => set('topic', e.target.value)}
            onFocus={() => setFocusedField('topic')}
            onBlur={() => setFocusedField(null)}
            placeholder="e.g. Photosynthesis, Quadratic Equations…"
          />
        </div>

        <div style={{ ...s.fieldGroup, ...s.row2 }}>
          <div>
            <label style={s.label} htmlFor="grade">Grade</label>
            <select
              id="grade"
              style={inputStyle('grade')}
              value={form.grade}
              onChange={e => set('grade', +e.target.value)}
              onFocus={() => setFocusedField('grade')}
              onBlur={() => setFocusedField(null)}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map(g => (
                <option key={g} value={g}>Grade {g}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={s.label} htmlFor="slides">Slides</label>
            <select
              id="slides"
              style={inputStyle('slides')}
              value={form.slides}
              onChange={e => set('slides', +e.target.value)}
              onFocus={() => setFocusedField('slides')}
              onBlur={() => setFocusedField(null)}
            >
              {[5, 8, 10, 12, 15, 20].map(n => (
                <option key={n} value={n}>{n} slides</option>
              ))}
            </select>
          </div>
        </div>

        <div style={s.fieldGroup}>
          <label style={s.label} htmlFor="subject">Subject</label>
          <select
            id="subject"
            style={inputStyle('subject')}
            value={form.subject}
            onChange={e => set('subject', e.target.value)}
            onFocus={() => setFocusedField('subject')}
            onBlur={() => setFocusedField(null)}
          >
            {SUBJECTS.map(sub => <option key={sub} value={sub}>{sub}</option>)}
          </select>
        </div>

        {routing && (
          <div style={s.routingBox}>
            <div style={s.routingRow}>
              <span style={{ fontSize: 12, color: '#888' }}>Routes to:</span>
              <RoutingBadge isSmart={routing.isSmart} />
              <span style={{ fontSize: 12, color: '#bbb' }}>score {routing.score}/10</span>
            </div>
            <div style={s.routingReasons}>{routing.reasons.join(' · ')}</div>
            <div style={s.costRow}>
              <span style={s.costChip}>
                Cost: <strong style={{ color: '#1a1a1a' }}>₹{routing.costINR}</strong>
              </span>
              <span style={s.costChip}>
                Saves: <strong style={s.costHighlight}>{routing.savingsPct}%</strong> vs Gemini
              </span>
            </div>
          </div>
        )}

        <div style={s.divider} />

        <button
          type="submit"
          style={{
            ...s.submitBtn,
            opacity: loading || !form.topic.trim() ? 0.5 : 1,
            cursor: loading || !form.topic.trim() ? 'not-allowed' : 'pointer',
          }}
          disabled={loading || !form.topic.trim()}
        >
          {loading ? 'Generating…' : 'Generate presentation'}
        </button>
      </form>
    </aside>
  )
}
