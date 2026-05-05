'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useWeek } from '@/lib/hooks/useWeek'
import { useDashboard } from '@/lib/hooks/useDashboard'
import { formatPace } from '@/lib/api/types'
import type { WeekDay } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function WeekPage() {
  const { dashboard } = useDashboard()
  const planId = dashboard?.today.plan_id
  const currentWeek = dashboard?.this_week.week_index ?? 1
  const [weekIndex, setWeekIndex] = useState<number | undefined>(undefined)

  const effectiveWeek = weekIndex ?? currentWeek
  const { week, isLoading, error } = useWeek(planId, planId ? effectiveWeek : undefined)
  const { language, t } = useI18n()

  const totalWeeks = dashboard?.this_week.total_weeks ?? 1

  return (
    <div>
      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="between">
          <button
            className="hand"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--ink-faint)', padding: '0 4px' }}
            onClick={() => setWeekIndex(Math.max(1, effectiveWeek - 1))}
            disabled={effectiveWeek <= 1}
          >‹</button>

          <div style={{ textAlign: 'center' }}>
            <div className="hand" style={{ fontSize: 16, fontWeight: 700 }}>
              {language === 'zh' ? `${t.week.weekPrefix} ${effectiveWeek} 周` : `${t.week.weekPrefix} ${effectiveWeek}`}
              {week?.phase ? ` · ${week.phase}` : ''}
              {week?.is_recovery ? ' 🔄' : ''}
            </div>
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {language === 'zh' ? `${t.week.totalWeeksPrefix} ${totalWeeks} 周` : `${t.week.totalWeeksPrefix} ${totalWeeks} ${t.common.weeks}`}
            </div>
          </div>

          <button
            className="hand"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--ink-faint)', padding: '0 4px' }}
            onClick={() => setWeekIndex(Math.min(totalWeeks, effectiveWeek + 1))}
            disabled={effectiveWeek >= totalWeeks}
          >›</button>
        </div>
      </div>

      {/* ── Volume bar ─────────────────────────────────────── */}
      {week && (
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--rule-soft)' }}>
          <div className="between" style={{ marginBottom: 6 }}>
            <span className="hand" style={{ fontSize: 13 }}>
              {week.completed_km.toFixed(1)} km
              <span className="text-faint"> / {week.planned_km.toFixed(1)} km</span>
            </span>
            <span className="hand text-faint" style={{ fontSize: 12 }}>
              {week.completed_quality}/{week.planned_quality} {t.week.quality}
            </span>
          </div>
          <div style={{ height: 6, borderRadius: 'var(--radius)', background: 'var(--rule-soft)', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              borderRadius: 'var(--radius)',
              background: 'var(--accent)',
              width: `${Math.min(100, week.planned_km > 0 ? (week.completed_km / week.planned_km) * 100 : 0)}%`,
              transition: 'width 0.3s',
            }} />
          </div>
        </div>
      )}

      {/* ── Day rows ───────────────────────────────────────── */}
      {isLoading && (
        <div style={{ padding: '32px 16px', textAlign: 'center' }}>
          <span className="hand text-faint" style={{ fontSize: 14 }}>{t.common.loading}</span>
        </div>
      )}

      {error && (
        <div style={{ padding: '32px 16px', textAlign: 'center' }}>
          <span className="hand text-faint" style={{ fontSize: 14 }}>{error.message}</span>
        </div>
      )}

      {week?.days.map((day) => (
        <DayRow key={day.date} day={day} />
      ))}
    </div>
  )
}

function DayRow({ day }: { day: WeekDay }) {
  const isToday = day.date === new Date().toISOString().slice(0, 10)
  const { t } = useI18n()

  return (
    <Link
      href={`/workouts/${day.date}`}
      style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px 16px',
        borderBottom: '1px solid var(--rule-soft)',
        background: isToday ? 'var(--accent-light)' : undefined,
      }}>
        {/* weekday + date */}
        <div style={{ width: 36, flexShrink: 0, textAlign: 'center' }}>
          <div className="hand" style={{ fontSize: 15, fontWeight: isToday ? 700 : 400, color: isToday ? 'var(--accent)' : 'var(--ink)' }}>
            {t.week.weekdays[day.weekday]}
          </div>
          <div className="annot text-faint" style={{ fontSize: 11 }}>
            {day.date.slice(5).replace('-', '/')}
          </div>
        </div>

        {/* status dot */}
        <span className={`status-dot ${day.status}`} style={{ margin: '0 12px', flexShrink: 0 }} />

        {/* title + metrics */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="hand" style={{
            fontSize: 14,
            color: day.status === 'future' ? 'var(--ink-faint)' : 'var(--ink)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {day.title ?? (day.status === 'rest' ? t.week.rest : '—')}
          </div>
          {(day.distance_km || day.duration_min) && (
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {day.distance_km != null ? `${day.distance_km.toFixed(1)} km` : ''}
              {day.distance_km != null && day.duration_min != null ? ' · ' : ''}
              {day.duration_min != null ? `${day.duration_min} ${t.common.minutes}` : ''}
            </div>
          )}
        </div>

        {/* status label */}
        <div className="hand" style={{
          fontSize: 12,
          color: day.status === 'completed' ? 'var(--ink)' :
                 day.status === 'miss' ? 'var(--accent)' :
                 'var(--ink-faint)',
          flexShrink: 0,
          marginLeft: 8,
        }}>
          {t.week.status[day.status] ?? day.status}
        </div>

        <span style={{ color: 'var(--ink-faint)', marginLeft: 6, fontSize: 14 }}>›</span>
      </div>
    </Link>
  )
}
