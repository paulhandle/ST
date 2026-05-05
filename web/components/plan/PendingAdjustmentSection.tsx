import Link from 'next/link'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  adjustment: { id: number; reason_headline: string }
}

export default function PendingAdjustmentSection({ adjustment }: Props) {
  const { t } = useI18n()
  return (
    <div style={{ margin: '16px 16px 8px' }}>
      <div className="between" style={{ marginBottom: 10 }}>
        <span className="hand" style={{ fontSize: 13, fontWeight: 700 }}>{t.plan.pendingAdjustments}</span>
        <span
          className="hand"
          style={{
            fontSize: 11, padding: '2px 8px',
            background: 'var(--accent)', color: '#050505',
            borderRadius: 'var(--radius)',
          }}
        >
          {t.plan.pendingCount}
        </span>
      </div>

      <Link href={`/adjustments/${adjustment.id}`} style={{ textDecoration: 'none', display: 'block' }}>
        <div style={{
          padding: '12px 14px',
          border: '1px solid var(--accent)',
          borderRadius: 'var(--radius)',
          background: 'var(--accent-light)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <span style={{ fontSize: 18, flexShrink: 0 }}>⚡</span>
          <div style={{ flex: 1 }}>
            <div className="hand" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 700, marginBottom: 2 }}>
              {t.plan.viewSuggestion}
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
