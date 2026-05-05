import Link from 'next/link'
import type { DashboardToday } from '@/lib/api/types'
import { formatKm, formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  today: DashboardToday
}

export default function TodayCard({ today }: Props) {
  const { workout, matched_activity } = today
  const isRest = !workout
  const { t } = useI18n()

  return (
    <Link href={`/workouts/${new Date().toISOString().slice(0, 10)}`} style={{ textDecoration: 'none', display: 'block' }}>
      <div style={{ margin: '12px 16px', padding: '12px 14px' }} className="sk-card">
        <div className="between" style={{ marginBottom: 8 }}>
          <span className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)' }}>{t.dashboard.today}</span>
          <span className="hand" style={{ fontSize: 12, color: 'var(--accent)' }}>›</span>
        </div>

        {isRest ? (
          <div className="hand" style={{ fontSize: 16 }}>{t.dashboard.restDay}</div>
        ) : workout ? (
          <div>
            <div className="hand" style={{ fontSize: 17, fontWeight: 700, marginBottom: 4 }}>
              {workout.title}
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              {workout.distance_m && (
                <span className="hand" style={{ fontSize: 13 }}>
                  {formatKm(workout.distance_m)} km
                </span>
              )}
              <span className="hand text-faint" style={{ fontSize: 13 }}>
                {workout.duration_min} {t.common.minutes}
              </span>
              {workout.target_min && workout.target_max && (
                <span className="hand text-faint" style={{ fontSize: 12 }}>
                  {formatPace(workout.target_min)}–{formatPace(workout.target_max)} /km
                </span>
              )}

              {matched_activity && (
                <span className="sk-pill sk-pill--accent" style={{ fontSize: 11 }}>
                  {matched_activity.status === 'completed' ? t.dashboard.completed : t.dashboard.inProgress}
                </span>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </Link>
  )
}
