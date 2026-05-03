import type { AffectedWorkout } from '@/lib/api/types'

interface Props {
  workout: AffectedWorkout
}

export default function AffectedWorkoutRow({ workout }: Props) {
  const date = new Date(workout.date)
  const dateStr = date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })

  return (
    <div style={{
      padding: '12px 16px',
      borderBottom: '1px solid var(--rule-soft)',
      display: 'flex', alignItems: 'flex-start', gap: 12,
    }}>
      <div style={{
        flexShrink: 0, width: 40, textAlign: 'center',
        paddingTop: 2,
      }}>
        <div className="hand" style={{ fontSize: 13, fontWeight: 700 }}>{dateStr}</div>
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="hand" style={{ fontSize: 14, marginBottom: 3 }}>
          {workout.title}
        </div>
        <div className="annot" style={{ fontSize: 12, color: 'var(--accent)' }}>
          {workout.change_summary}
        </div>
      </div>
    </div>
  )
}
