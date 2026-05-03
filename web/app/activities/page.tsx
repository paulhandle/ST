'use client'

import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { AthleteActivityOut } from '@/lib/api/types'
import ActivityRow from '@/components/activities/ActivityRow'

const ATHLETE_ID = 1

const STATUS_SUMMARY: Record<string, { label: string; color: string }> = {
  completed:  { label: '完成', color: 'var(--ink)' },
  partial:    { label: '部分', color: 'var(--ink-mid)' },
  miss:       { label: '缺训', color: 'var(--accent)' },
  rest:       { label: '休息', color: 'var(--ink-faint)' },
  unmatched:  { label: '自由', color: 'var(--ink-faint)' },
}

export default function ActivitiesPage() {
  const { data: activities, isLoading, error } = useSWR<AthleteActivityOut[]>(
    `/api/athletes/${ATHLETE_ID}/history`,
    fetcher,
  )

  // Compute simple stats
  const total = activities?.length ?? 0
  const completed = activities?.filter(a => a.match_status === 'completed').length ?? 0
  const totalKm = activities?.reduce((s, a) => s + a.distance_km, 0) ?? 0

  return (
    <div>
      {/* Header */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>历史活动</div>
        {total > 0 && (
          <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>
            共 {total} 次 · {totalKm.toFixed(0)} km · 完成率 {total > 0 ? Math.round(completed / total * 100) : 0}%
          </div>
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 12, padding: '10px 16px', borderBottom: '1px solid var(--rule-soft)' }}>
        {Object.entries(STATUS_SUMMARY).map(([key, { label, color }]) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span className={`status-dot ${key}`} />
            <span className="annot" style={{ fontSize: 11, color }}>{label}</span>
          </div>
        ))}
      </div>

      {isLoading && (
        <div className="hand text-faint" style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
          加载中…
        </div>
      )}
      {error && (
        <div className="hand text-faint" style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
          {error.message}
        </div>
      )}
      {activities?.length === 0 && (
        <div className="hand text-faint" style={{ padding: '48px 16px', textAlign: 'center', fontSize: 14 }}>
          暂无活动记录
        </div>
      )}
      {activities?.map((a) => (
        <ActivityRow key={a.id} activity={a} />
      ))}
    </div>
  )
}
