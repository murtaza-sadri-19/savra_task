import React, { useState } from 'react'
import { RoutingBadge } from './RoutingBadge'

const LAYOUT_ACCENT = {
  title:      '#534AB7',
  content:    '#1D9E75',
  'two-column': '#EF9F27',
  summary:    '#E24B4A',
}

const s = {
  container: { padding: '28px 32px', overflowY: 'auto', height: '100%' },

  topBar: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 24,
    gap: 12,
    flexWrap: 'wrap',
  },
  presentationTitle: { fontSize: 18, fontWeight: 600, color: '#1a1a1a', lineHeight: 1.3 },
  meta: { fontSize: 13, color: '#888', marginTop: 3 },

  costCard: {
    background: '#F7F6F2',
    border: '1px solid rgba(0,0,0,0.07)',
    borderRadius: 12,
    padding: '14px 16px',
    marginBottom: 24,
  },
  costGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 12,
    marginTop: 12,
  },
  costCell: {
    background: '#fff',
    borderRadius: 8,
    padding: '10px 12px',
    textAlign: 'center',
  },
  costCellLabel: { fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: '0.04em' },
  costCellValue: { fontSize: 15, fontWeight: 600, color: '#1a1a1a', marginTop: 3 },

  tabs: { display: 'flex', gap: 4, marginBottom: 16 },
  tab: {
    padding: '6px 14px',
    borderRadius: 7,
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    transition: 'background 0.15s, color 0.15s',
  },

  slideCard: {
    background: '#fff',
    border: '1px solid rgba(0,0,0,0.08)',
    borderRadius: 12,
    marginBottom: 10,
    overflow: 'hidden',
  },
  slideHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '12px 16px',
    borderBottom: '1px solid rgba(0,0,0,0.06)',
  },
  slideAccentBar: {
    width: 3,
    height: 18,
    borderRadius: 9999,
    flexShrink: 0,
  },
  slideTitle: { fontSize: 14, fontWeight: 600, color: '#1a1a1a', flex: 1 },
  slideNum: { fontSize: 11, color: '#bbb', fontWeight: 500 },
  slideBody: { padding: '10px 16px 14px' },
  bullet: {
    display: 'flex',
    gap: 8,
    fontSize: 13,
    color: '#444',
    lineHeight: 1.55,
    marginBottom: 5,
    alignItems: 'flex-start',
  },
  bulletDot: { flexShrink: 0, marginTop: 3, fontSize: 10 },

  notesBox: {
    margin: '10px 16px 14px',
    padding: '10px 12px',
    background: '#EEEDFE',
    borderRadius: 8,
    fontSize: 12,
    color: '#3C3489',
    lineHeight: 1.6,
    fontStyle: 'italic',
  },

  resetBtn: {
    marginTop: 20,
    padding: '9px 20px',
    background: '#fff',
    border: '1px solid rgba(0,0,0,0.14)',
    borderRadius: 9,
    fontSize: 13,
    fontWeight: 500,
    color: '#555',
    cursor: 'pointer',
  },

  sectionLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 10,
  },

  routingDetail: {
    marginTop: 10,
    fontSize: 12,
    color: '#888',
    lineHeight: 1.6,
  },
}

export function SlidePreview({ job, onReset }) {
  const [tab, setTab] = useState('slides')

  const result   = job.result
  const routing  = job.routing ?? {}
  const isSmart  = routing.model?.includes('70b')
  const costINR  = job.cost_inr ?? 0
  const savedINR = (15 - costINR).toFixed(2)
  const genTime  = job.generation_time_ms
    ? `${(job.generation_time_ms / 1000).toFixed(1)}s`
    : '—'

  const slides = result?.slides ?? []

  return (
    <div style={s.container}>
      {/* Header */}
      <div style={s.topBar}>
        <div>
          <div style={s.presentationTitle}>{result?.title}</div>
          <div style={s.meta}>
            Grade {result?.grade} · {result?.subject} · {result?.total_slides} slides
          </div>
        </div>
        <RoutingBadge isSmart={isSmart} />
      </div>

      {/* Cost card */}
      <div style={s.costCard}>
        <div style={s.sectionLabel}>Cost breakdown</div>
        <div style={s.costGrid}>
          <div style={s.costCell}>
            <div style={s.costCellLabel}>Previous</div>
            <div style={{ ...s.costCellValue, color: '#E24B4A' }}>₹15.00</div>
          </div>
          <div style={s.costCell}>
            <div style={s.costCellLabel}>This request</div>
            <div style={{ ...s.costCellValue, color: '#534AB7' }}>₹{costINR}</div>
          </div>
          <div style={s.costCell}>
            <div style={s.costCellLabel}>Saved</div>
            <div style={{ ...s.costCellValue, color: '#1D9E75' }}>₹{savedINR}</div>
          </div>
        </div>
        <div style={s.routingDetail}>
          Model: <strong style={{ color: '#1a1a1a' }}>{routing.model}</strong>
          {' · '}Complexity score: <strong style={{ color: '#1a1a1a' }}>{routing.complexity_score}/10</strong>
          {' · '}Generated in: <strong style={{ color: '#1a1a1a' }}>{genTime}</strong>
          {job.cache_hit && (
            <span style={{
              marginLeft: 8,
              padding: '1px 7px',
              background: '#EAF3DE',
              color: '#3B6D11',
              borderRadius: 5,
              fontSize: 11,
              fontWeight: 600,
            }}>
              CACHE HIT
            </span>
          )}
          {routing.reasons?.length > 0 && (
            <div style={{ marginTop: 4, color: '#aaa' }}>
              {routing.reasons.join(' · ')}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={s.tabs}>
        {['slides', 'notes'].map(t => (
          <button
            key={t}
            style={{
              ...s.tab,
              background: tab === t ? '#EEEDFE' : 'transparent',
              color: tab === t ? '#534AB7' : '#888',
            }}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Slides */}
      {slides.map(slide => {
        const accent = LAYOUT_ACCENT[slide.layout] ?? '#7F77DD'
        return (
          <div key={slide.slide_number} style={s.slideCard}>
            <div style={s.slideHeader}>
              <div style={{ ...s.slideAccentBar, background: accent }} />
              <div style={s.slideTitle}>{slide.title}</div>
              <div style={s.slideNum}>{slide.slide_number} / {slides.length}</div>
            </div>

            {tab === 'slides' && (
              <div style={s.slideBody}>
                {slide.bullet_points.map((bp, i) => (
                  <div key={i} style={s.bullet}>
                    <span style={{ ...s.bulletDot, color: accent }}>●</span>
                    <span>{bp}</span>
                  </div>
                ))}
              </div>
            )}

            {tab === 'notes' && slide.speaker_notes && (
              <div style={s.notesBox}>{slide.speaker_notes}</div>
            )}

            {tab === 'notes' && !slide.speaker_notes && (
              <div style={{ ...s.notesBox, color: '#aaa', fontStyle: 'italic' }}>
                No speaker notes for this slide.
              </div>
            )}
          </div>
        )
      })}

      <button style={s.resetBtn} onClick={onReset}>
        ← New presentation
      </button>
    </div>
  )
}
