import type { DashboardReadiness } from '@/lib/api/types'
import { formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  readiness: DashboardReadiness
}

function TrendArrow({ val }: { val: number | null }) {
  if (!val) return null
  return <span style={{ color: val > 0 ? 'var(--accent)' : 'var(--ink-faint)', fontSize: 11, marginLeft: 2 }}>{val > 0 ? '↑' : '↓'}</span>
}

export default function ReadinessPanel({ readiness }: Props) {
  const { t } = useI18n()
  const items = [
    {
      label: t.dashboard.restingHr,
      value: readiness.resting_hr ? `${readiness.resting_hr} bpm` : '--',
      trend: readiness.resting_hr_trend,
    },
    {
      label: t.dashboard.trainingLoad7d,
      value: readiness.weekly_training_load ? `${Math.round(readiness.weekly_training_load)}` : '--',
      trend: readiness.weekly_training_load_trend,
    },
    {
      label: 'LTHR',
      value: readiness.lthr ? `${readiness.lthr} bpm` : '--',
      trend: null,
    },
    {
      label: 'LTSP',
      value: readiness.ltsp_sec_per_km ? formatPace(readiness.ltsp_sec_per_km) + '/km' : '--',
      trend: null,
    },
  ]

  return (
    <div style={{ margin: '12px 16px' }} className="sk-card-soft">
      <div className="hand" style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{t.dashboard.readiness}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {items.map((item) => (
          <div key={item.label}>
            <div className="hand" style={{ fontSize: 18, fontWeight: 700 }}>
              {item.value}
              <TrendArrow val={item.trend ?? null} />
            </div>
            <div className="annot text-faint" style={{ fontSize: 11 }}>{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
