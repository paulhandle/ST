import type { StructuredWorkoutOut, TodayMatchedActivity } from '@/lib/api/types'
import { formatKm, formatPace } from '@/lib/api/types'

interface Props {
  workout: StructuredWorkoutOut
  activity: TodayMatchedActivity | null
}

export default function YesterdayCompare({ workout, activity }: Props) {
  return (
    <div style={{ margin: '0 16px 16px', padding: '12px 14px', background: 'var(--surface-low)', borderRadius: 'var(--radius)', border: '1px solid var(--rule-soft)' }}>
      <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 8 }}>昨天</div>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        {/* plan */}
        <div>
          <div className="hand" style={{ fontSize: 14 }}>{workout.title}</div>
          <div className="annot text-faint" style={{ fontSize: 12 }}>
            计划 {workout.distance_m ? formatKm(workout.distance_m) + ' km' : ''} · {workout.duration_min} 分钟
          </div>
        </div>

        {/* actual */}
        {activity ? (
          <div style={{ textAlign: 'right' }}>
            <span className={`sk-pill ${activity.status === 'completed' ? '' : 'sk-pill--accent'}`} style={{ fontSize: 11 }}>
              {activity.status === 'completed' ? '完成' :
               activity.status === 'partial' ? '部分' : '缺训'}
            </span>
            <div className="annot text-faint" style={{ fontSize: 12, marginTop: 4 }}>
              {formatKm(activity.distance_m)} km
              {activity.avg_pace_sec_per_km ? ` · ${formatPace(activity.avg_pace_sec_per_km)}/km` : ''}
            </div>
          </div>
        ) : (
          <span className="sk-pill sk-pill--accent" style={{ fontSize: 11 }}>缺训</span>
        )}
      </div>
    </div>
  )
}
