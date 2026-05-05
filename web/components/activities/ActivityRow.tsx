import type { AthleteActivityOut } from '@/lib/api/types'
import { formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  activity: AthleteActivityOut
}

export default function ActivityRow({ activity }: Props) {
  const { language, t } = useI18n()
  const date = new Date(activity.started_at)
  const dateStr = date.toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', { month: 'numeric', day: 'numeric' })

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '12px 16px',
      borderBottom: '1px solid var(--rule-soft)',
    }}>
      <span className={`status-dot ${activity.match_status}`} style={{ flexShrink: 0 }} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="hand" style={{
          fontSize: 14,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {activity.title}
        </div>
        <div className="annot text-faint" style={{ fontSize: 12 }}>
          {activity.distance_km != null ? `${activity.distance_km.toFixed(1)} km · ` : ''}{activity.duration_min} {t.common.minutes}
          {activity.avg_pace_sec_per_km
            ? ` · ${formatPace(activity.avg_pace_sec_per_km)}/km`
            : ''}
        </div>
      </div>

      <div style={{ flexShrink: 0, textAlign: 'right' }}>
        {activity.delta_summary && (
          <div className="hand" style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 2 }}>
            {activity.delta_summary}
          </div>
        )}
        <div className="annot text-faint" style={{ fontSize: 11 }}>{dateStr}</div>
      </div>
    </div>
  )
}
