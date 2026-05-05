import Link from 'next/link'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  adjustment: { id: number; reason_headline: string }
}

export default function AdjustmentBanner({ adjustment }: Props) {
  const { t } = useI18n()
  return (
    <Link href={`/adjustments/${adjustment.id}`} style={{ textDecoration: 'none' }}>
      <div className="adj-banner">
        <span style={{ fontSize: 18 }}>⚡</span>
        <div style={{ flex: 1 }}>
          <div className="hand" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 700 }}>{t.dashboard.adjustmentSuggestion}</div>
          <div className="hand" style={{ fontSize: 12, color: 'var(--ink-mid)', marginTop: 2 }}>{adjustment.reason_headline}</div>
        </div>
        <span className="hand" style={{ fontSize: 14, color: 'var(--accent)' }}>›</span>
      </div>
    </Link>
  )
}
