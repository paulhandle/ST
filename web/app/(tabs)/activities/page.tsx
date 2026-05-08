'use client'

import { useState, useRef } from 'react'
import Link from 'next/link'
import { useCalendar } from '@/lib/hooks/useCalendar'
import MonthStrip from '@/components/activities/MonthStrip'
import type { CalendarDay } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

function getDateRange() {
  const from = new Date()
  from.setMonth(from.getMonth() - 2)
  from.setDate(1)
  const to = new Date()
  to.setMonth(to.getMonth() + 3, 0)
  return {
    fromDate: from.toISOString().slice(0, 10),
    toDate: to.toISOString().slice(0, 10),
  }
}

const { fromDate, toDate } = getDateRange()

const FILTER_KEYS = ['all', 'run', 'cycle', 'strength'] as const
const STATUS_FILTER_KEYS = ['all', 'completed', 'unmatched', 'planned', 'miss'] as const
type ActivitiesView = 'timeline' | 'calendar'

const STATUS_COLOR: Record<string, string> = {
  completed: 'var(--ink)',
  partial: 'var(--ink-mid)',
  miss: 'var(--accent)',
  unmatched: 'var(--ink-faint)',
  planned: 'rgba(255,77,0,0.55)',
}

export default function ActivitiesPage() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [view, setView] = useState<ActivitiesView>('timeline')
  const listRef = useRef<HTMLDivElement>(null)
  const { days, isLoading, error } = useCalendar(fromDate, toDate)
  const { language, t } = useI18n()

  const filtered = days.filter((d) => {
    const sportMatches = filter === 'all' || d.sport === filter
    const statusMatches = statusFilter === 'all' || d.status === statusFilter
    return sportMatches && statusMatches
  })
  const activityCount = filtered.filter((d) => d.activity_id != null).length
  const plannedCount = filtered.filter((d) => d.status === 'planned').length
  const totalDistance = filtered.reduce((sum, d) => sum + (d.activity_id != null ? d.distance_km ?? 0 : 0), 0)
  const totalDuration = filtered.reduce((sum, d) => sum + (d.activity_id != null ? d.duration_min ?? 0 : 0), 0)

  const byMonth: Record<string, CalendarDay[]> = {}
  for (const d of filtered) {
    const mk = d.date.slice(0, 7)
    ;(byMonth[mk] ??= []).push(d)
  }
  const monthKeys = Object.keys(byMonth).sort((a, b) => b.localeCompare(a))

  function handleSelectDate(date: string) {
    setSelectedDate(date)
    if (!listRef.current) return
    const target = listRef.current.querySelector(
      `[data-listdate="${date}"]`
    ) as HTMLElement | null
    if (target) {
      listRef.current.scrollTo({ top: target.offsetTop - 32, behavior: 'smooth' })
    } else {
      const monthEl = listRef.current.querySelector(
        `[data-listmonth="${date.slice(0, 7)}"]`
      ) as HTMLElement | null
      if (monthEl) listRef.current.scrollTo({ top: monthEl.offsetTop, behavior: 'smooth' })
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}>
      <div style={{ padding: '16px 16px 10px', flexShrink: 0,
                    borderBottom: '1px solid var(--rule-soft)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>{t.activities.title}</div>
          <div style={{ display: 'flex', border: '1px solid var(--rule)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
            {(['timeline', 'calendar'] as const).map((key) => (
              <button
                key={key}
                onClick={() => setView(key)}
                className="hand"
                style={{
                  border: 'none',
                  borderRight: key === 'timeline' ? '1px solid var(--rule)' : 'none',
                  padding: '5px 9px',
                  fontSize: 12,
                  cursor: 'pointer',
                  background: view === key ? 'var(--accent)' : 'var(--paper)',
                  color: view === key ? '#050505' : 'var(--ink-faint)',
                }}
              >
                {key === 'timeline' ? t.activities.timeline : t.activities.calendar}
              </button>
            ))}
          </div>
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
          gap: 8,
          marginTop: 12,
        }}>
          <SummaryMetric label={t.activities.summaryActivities} value={`${activityCount}`} />
          <SummaryMetric label={t.activities.summaryDistance} value={`${totalDistance.toFixed(1)} km`} />
          <SummaryMetric label={t.activities.summaryDuration} value={`${Math.round(totalDuration)} ${t.common.minutes}`} />
          <SummaryMetric label={t.activities.summaryPlanned} value={`${plannedCount}`} />
        </div>
      </div>

      {view === 'calendar' && (
        <div style={{ flexShrink: 0 }}>
          <MonthStrip days={days} selectedDate={selectedDate} onSelectDate={handleSelectDate} />
        </div>
      )}

      <div style={{
        display: 'flex', gap: 8, padding: '8px 16px 4px', flexShrink: 0,
        borderBottom: '1px solid var(--rule-soft)', overflowX: 'auto',
        scrollbarWidth: 'none',
      }}>
        {FILTER_KEYS.map(key => (
          <button
            key={key}
            aria-label={`Sport filter: ${t.activities.filters[key]}`}
            onClick={() => setFilter(key)}
            className="hand"
            style={{
              padding: '4px 12px', borderRadius: 'var(--radius)', fontSize: 12, cursor: 'pointer',
              border: `1px solid ${filter === key ? 'var(--accent)' : 'var(--rule)'}`,
              background: filter === key ? 'var(--accent)' : 'var(--paper)',
              color: filter === key ? '#050505' : 'var(--ink)',
              whiteSpace: 'nowrap', flexShrink: 0,
            }}
          >
            {t.activities.filters[key]}
          </button>
        ))}
      </div>
      <div style={{
        display: 'flex', gap: 8, padding: '4px 16px 8px', flexShrink: 0,
        borderBottom: '1px solid var(--rule-soft)', overflowX: 'auto',
        scrollbarWidth: 'none',
      }}>
        {STATUS_FILTER_KEYS.map(key => (
          <button
            key={key}
            aria-label={`Status filter: ${key === 'all' ? t.activities.filters.all : (t.activities.status[key] ?? key)}`}
            onClick={() => setStatusFilter(key)}
            className="hand"
            style={{
              padding: '4px 10px', borderRadius: 'var(--radius)', fontSize: 12, cursor: 'pointer',
              border: `1px solid ${statusFilter === key ? 'var(--accent)' : 'var(--rule)'}`,
              background: statusFilter === key ? 'var(--accent)' : 'var(--paper)',
              color: statusFilter === key ? '#050505' : 'var(--ink-faint)',
              whiteSpace: 'nowrap', flexShrink: 0,
            }}
          >
            {key === 'all' ? t.activities.filters.all : (t.activities.status[key] ?? key)}
          </button>
        ))}
      </div>

      {view === 'timeline' && monthKeys.length > 0 && (
        <div style={{
          display: 'flex', gap: 8, padding: '8px 16px', flexShrink: 0,
          borderBottom: '1px solid var(--rule-soft)', overflowX: 'auto',
          scrollbarWidth: 'none',
        }}>
          <span className="annot text-faint" style={{ fontSize: 11, alignSelf: 'center', whiteSpace: 'nowrap' }}>
            {t.activities.monthJump}
          </span>
          {monthKeys.map(mk => (
            <button key={mk} onClick={() => handleSelectDate(`${mk}-01`)} className="hand" style={{
              border: '1px solid var(--rule)',
              borderRadius: 'var(--radius)',
              background: 'var(--paper)',
              color: 'var(--ink)',
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}>
              {formatMonthLabel(mk, language)} · {byMonth[mk].length}
            </button>
          ))}
        </div>
      )}

      <div ref={listRef} style={{ flex: 1, overflowY: 'auto' }}>
        {isLoading && (
          <div className="hand text-faint"
               style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
            {t.common.loading}
          </div>
        )}
        {error && (
          <div className="hand text-faint"
               style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
            {error.message}
          </div>
        )}
        {!isLoading && !error && filtered.length === 0 && (
          <div className="hand text-faint"
               style={{ padding: '48px 16px', textAlign: 'center', fontSize: 14 }}>
            {t.activities.empty}
          </div>
        )}

        {monthKeys.map(mk => {
          const monthDays = [...byMonth[mk]].sort((a, b) => b.date.localeCompare(a.date))
          return (
            <div key={mk} data-listmonth={mk}>
              <div className="hand" style={{
                fontSize: 12, color: 'var(--ink-faint)',
                padding: '10px 16px 4px',
                background: 'var(--paper)',
                position: 'sticky', top: 0, zIndex: 1,
              }}>
                {formatMonthLabel(mk, language)}
              </div>
              {monthDays.map(day => (
                <DayRow key={day.date} day={day} isSelected={day.date === selectedDate} />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: '1px solid var(--rule-soft)', padding: '7px 8px', borderRadius: 'var(--radius)' }}>
      <div className="hand" style={{ fontSize: 14, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</div>
      <div className="annot text-faint" style={{ fontSize: 10, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</div>
    </div>
  )
}

function formatMonthLabel(monthKey: string, language: string) {
  const [year, month] = monthKey.split('-')
  if (language === 'zh') return `${year}年${parseInt(month)}月`
  return new Date(`${monthKey}-01T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

function DayRow({ day, isSelected }: { day: CalendarDay; isSelected: boolean }) {
  const { t } = useI18n()
  const meta = {
    color: STATUS_COLOR[day.status] ?? 'var(--ink-faint)',
    label: t.activities.status[day.status] ?? day.status,
  }
  const [, m, d] = day.date.split('-')
  const href = day.activity_id != null ? `/activities/${day.activity_id}` : `/workouts/${day.date}`

  return (
    <Link
      href={href}
      data-listdate={day.date}
      style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
    >
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '11px 16px',
        borderBottom: '1px solid var(--rule-soft)',
        background: isSelected ? 'var(--accent-light)' : undefined,
      }}>
        <div style={{ width: 30, textAlign: 'center', flexShrink: 0 }}>
          <div className="hand" style={{ fontSize: 16, fontWeight: 600, lineHeight: 1 }}>
            {parseInt(d)}
          </div>
          <div className="annot text-faint" style={{ fontSize: 10 }}>
            {parseInt(m)}{t.common.monthSuffix}
          </div>
        </div>

        <span style={{
          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
          background: meta.color,
        }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="hand" style={{
            fontSize: 14, lineHeight: 1.3,
            color: day.status === 'planned' ? 'var(--ink-faint)' : 'var(--ink)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {day.title ?? '—'}
          </div>
          {(day.distance_km != null || day.duration_min != null) && (
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {day.distance_km != null ? `${day.distance_km.toFixed(1)} km` : ''}
              {day.distance_km != null && day.duration_min != null ? ' · ' : ''}
              {day.duration_min != null ? `${day.duration_min} ${t.common.minutes}` : ''}
            </div>
          )}
        </div>

        <span className="hand" style={{ fontSize: 11, color: meta.color, flexShrink: 0 }}>
          {meta.label}
        </span>
        <span style={{ color: 'var(--ink-faint)', fontSize: 14 }}>›</span>
      </div>
    </Link>
  )
}
