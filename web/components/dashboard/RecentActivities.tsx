import type { DashboardActivity } from '@/lib/api/types'
import { formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  activities: DashboardActivity[]
}

const STATUS_COLOR: Record<string, string> = {
  completed: 'var(--ink)',
  partial: 'var(--ink-mid)',
  miss: 'var(--accent)',
  rest: 'var(--ink-faint)',
  unmatched: 'var(--ink-faint)',
}

export default function RecentActivities({ activities }: Props) {
  const { language, t } = useI18n()
  return (
    <div style={{ margin: '0 0 8px' }}>
      <div className="section-header">
        <span className="section-title">{t.dashboard.recentActivities}</span>
      </div>

      {activities.map((a) => (
        <div
          key={a.id}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '10px 16px',
            borderBottom: '1px solid var(--rule-soft)',
          }}
        >
          <span
            className="status-dot"
            style={{ background: STATUS_COLOR[a.match_status] ?? 'var(--ink-faint)', flexShrink: 0 }}
          />

          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="hand" style={{ fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {a.title}
            </div>
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {a.distance_km.toFixed(1)} km · {a.duration_min} {t.common.minutes}
              {a.avg_pace_sec_per_km ? ` · ${formatPace(a.avg_pace_sec_per_km)}/km` : ''}
            </div>
          </div>

          <div style={{ flexShrink: 0, textAlign: 'right' }}>
            {a.delta_summary && (
              <div className="hand" style={{ fontSize: 12, color: 'var(--ink-faint)' }}>{a.delta_summary}</div>
            )}
            <div className="annot text-faint" style={{ fontSize: 11 }}>
              {new Date(a.started_at).toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', { month: 'numeric', day: 'numeric' })}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
