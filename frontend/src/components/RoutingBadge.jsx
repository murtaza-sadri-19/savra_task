import React from 'react'

const styles = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    padding: '3px 10px',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 500,
    letterSpacing: '0.01em',
    whiteSpace: 'nowrap',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    flexShrink: 0,
  },
}

export function RoutingBadge({ isSmart, model }) {
  const color = isSmart
    ? { bg: '#FAEEDA', text: '#854F0B', dot: '#EF9F27' }
    : { bg: '#EAF3DE', text: '#3B6D11', dot: '#639922' }

  const label = isSmart ? '70b-versatile' : '8b-instant'

  return (
    <span style={{ ...styles.badge, background: color.bg, color: color.text }}>
      <span style={{ ...styles.dot, background: color.dot }} />
      {label}
    </span>
  )
}
