import type { StructuredWorkoutOut, TodayMatchedActivity } from '@/lib/api/types'
import { formatKm, formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  workout: StructuredWorkoutOut
  activity: TodayMatchedActivity | null
}

export default function YesterdayCompare({ workout, activity }: Props) {
  const { t } = useI18n()
  return (
    <div style={{ margin: '0 16px 16px', padding: '12px 14px', background: 'var(--surface-low)', borderRadius: 'var(--radius)', border: '1px solid var(--rule-soft)' }}>
      <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 8 }}>{t.workout.yesterday}</div>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        {/* plan */}
        <div>
          <div className="hand" style={{ fontSize: 14 }}>{workout.title}</div>
          <div className="annot text-faint" style={{ fontSize: 12 }}>
            {t.workout.planned} {workout.distance_m ? formatKm(workout.distance_m) + ' km' : ''} · {workout.duration_min} {t.common.minutes}
          </div>
        </div>

        {/* actual */}
        {activity ? (
          <div style={{ textAlign: 'right' }}>
            <span className={`sk-pill ${activity.status === 'completed' ? '' : 'sk-pill--accent'}`} style={{ fontSize: 11 }}>
              {activity.status === 'completed' ? t.activities.status.completed :
               activity.status === 'partial' ? t.activities.status.partial : t.activities.status.miss}
            </span>
            <div className="annot text-faint" style={{ fontSize: 12, marginTop: 4 }}>
              {formatKm(activity.distance_m)} km
              {activity.avg_pace_sec_per_km ? ` · ${formatPace(activity.avg_pace_sec_per_km)}/km` : ''}
            </div>
          </div>
        ) : (
          <span className="sk-pill sk-pill--accent" style={{ fontSize: 11 }}>{t.activities.status.miss}</span>
        )}
      </div>
    </div>
  )
}
