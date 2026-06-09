import { AlertTriangle } from 'lucide-react'

export default function DuplicateAlert({ fraudCheck }) {
  if (!fraudCheck?.is_duplicate) return null

  const isHigh = fraudCheck.confidence > 0.9

  return (
    <div style={{
      background: isHigh ? '#fef2f2' : '#fffbeb',
      border: `1px solid ${isHigh ? '#fecaca' : '#fde68a'}`,
      borderRadius: 'var(--radius-sm)',
      padding: '10px 14px',
      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
    }}>
      <AlertTriangle size={16} color={isHigh ? '#dc2626' : '#d97706'} />
      <div>
        <p style={{ fontWeight: 600, fontSize: 13, color: isHigh ? '#991b1b' : '#92400e' }}>
          {isHigh ? 'Duplicate Invoice Detected' : 'Possible Duplicate'}
        </p>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 1 }}>
          {fraudCheck.message} • {(fraudCheck.confidence * 100).toFixed(0)}% match
        </p>
      </div>
    </div>
  )
}
