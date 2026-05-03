import Link from 'next/link'

interface Props {
  adjustment: { id: number; reason_headline: string }
}

export default function PendingAdjustmentSection({ adjustment }: Props) {
  return (
    <div style={{ margin: '16px 16px 8px' }}>
      <div className="between" style={{ marginBottom: 10 }}>
        <span className="hand" style={{ fontSize: 13, fontWeight: 700 }}>调整建议</span>
        <span
          className="hand"
          style={{
            fontSize: 11, padding: '2px 8px',
            background: 'var(--accent)', color: 'var(--paper)',
            borderRadius: 999,
          }}
        >
          1 待处理
        </span>
      </div>

      <Link href={`/adjustments/${adjustment.id}`} style={{ textDecoration: 'none', display: 'block' }}>
        <div style={{
          padding: '12px 14px',
          border: '1.5px solid var(--accent)',
          borderRadius: 8,
          background: 'var(--accent-light)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <span style={{ fontSize: 18, flexShrink: 0 }}>⚡</span>
          <div style={{ flex: 1 }}>
            <div className="hand" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 700, marginBottom: 2 }}>
              查看建议
            </div>
            <div className="hand" style={{ fontSize: 12, color: 'var(--ink-mid)' }}>
              {adjustment.reason_headline}
            </div>
          </div>
          <span className="hand" style={{ color: 'var(--accent)', fontSize: 16, flexShrink: 0 }}>›</span>
        </div>
      </Link>
    </div>
  )
}
