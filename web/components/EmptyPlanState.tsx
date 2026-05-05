import Link from 'next/link'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function EmptyPlanState() {
  const { t } = useI18n()
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center' }}>
      <div style={{ fontSize: 52, marginBottom: 16 }}>🏃</div>

      <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        {t.emptyPlan.title}
      </div>

      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
        {t.emptyPlan.body}
      </div>

      <Link
        href="/plan/generate"
        style={{
          display: 'inline-block',
          padding: '14px 32px',
          background: 'var(--accent)',
          color: '#050505',
          borderRadius: 'var(--radius)',
          fontFamily: 'var(--font-hand)',
          fontSize: 16,
          textDecoration: 'none',
        }}
      >
        {t.emptyPlan.action} →
      </Link>
    </div>
  )
}
