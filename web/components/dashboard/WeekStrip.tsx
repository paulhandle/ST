import type { DashboardThisWeek, WeekDay } from '@/lib/api/types'

const WEEKDAY_SHORT = ['一', '二', '三', '四', '五', '六', '日']

interface Props {
  week: DashboardThisWeek
}

export default function WeekStrip({ week }: Props) {
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rule-soft)' }}>
      <div className="between" style={{ marginBottom: 8 }}>
        <span className="hand" style={{ fontSize: 13, fontWeight: 700 }}>本周</span>
        <span className="hand text-faint" style={{ fontSize: 12 }}>
          {week.completed_km.toFixed(0)}/{week.planned_km.toFixed(0)} km
        </span>
      </div>

      <div style={{ display: 'flex', gap: 4 }}>
        {week.days.map((day) => {
          const isToday = day.date === today
          return (
            <div
              key={day.date}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 4,
                padding: '6px 2px',
                borderRadius: 6,
                background: isToday ? 'var(--accent-light)' : undefined,
              }}
            >
              <span
                className="annot"
                style={{
                  fontSize: 11,
                  color: isToday ? 'var(--accent)' : 'var(--ink-faint)',
                  fontWeight: isToday ? 700 : 400,
                }}
              >
                {WEEKDAY_SHORT[day.weekday]}
              </span>
              <span className={`status-dot ${day.status}`} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
