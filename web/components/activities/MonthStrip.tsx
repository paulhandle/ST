'use client'

import { useRef, useEffect } from 'react'
import type { CalendarDay } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  days: CalendarDay[]
  selectedDate: string | null
  onSelectDate: (date: string) => void
}

function buildDateRange(): string[] {
  const result: string[] = []
  const cur = new Date()
  cur.setMonth(cur.getMonth() - 2)
  cur.setDate(1)
  const end = new Date()
  end.setMonth(end.getMonth() + 3, 0)
  while (cur <= end) {
    result.push(cur.toISOString().slice(0, 10))
    cur.setDate(cur.getDate() + 1)
  }
  return result
}

const ALL_DATES = buildDateRange()

export default function MonthStrip({ days, selectedDate, onSelectDate }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const today = new Date().toISOString().slice(0, 10)
  const dayMap = new Map(days.map(d => [d.date, d]))
  const { t } = useI18n()

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const todayEl = el.querySelector(`[data-date="${today}"]`) as HTMLElement | null
    if (todayEl) {
      el.scrollLeft = todayEl.offsetLeft - el.offsetWidth / 2 + todayEl.offsetWidth / 2
    }
  }, [today])

  return (
    <div
      ref={scrollRef}
      style={{
        display: 'flex',
        overflowX: 'auto',
        scrollbarWidth: 'none',
        padding: '6px 0 8px',
        borderBottom: '1px solid var(--rule-soft)',
      }}
    >
      {ALL_DATES.map((d, i) => {
        const prev = i > 0 ? ALL_DATES[i - 1] : null
        const isFirstOfMonth = !prev || d.slice(0, 7) !== prev.slice(0, 7)
        const info = dayMap.get(d)
        const isToday = d === today
        const isSelected = d === selectedDate
        const dayNum = parseInt(d.slice(8))
        const monthNum = parseInt(d.slice(5, 7))

        return (
          <button
            key={d}
            data-date={d}
            onClick={() => onSelectDate(d)}
            style={{
              width: 34, flexShrink: 0,
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 3,
              padding: '0 0 4px',
              background: 'none', border: 'none', cursor: 'pointer',
            }}
          >
            {/* Month label — only on first day of month */}
            <div className="annot" style={{
              fontSize: 9,
              color: isFirstOfMonth ? 'var(--ink-faint)' : 'transparent',
              lineHeight: 1.4,
              userSelect: 'none',
            }}>
              {isFirstOfMonth ? `${monthNum}${t.common.monthSuffix}` : '·'}
            </div>

            {/* Day number block */}
            <div style={{
              width: 26, height: 26, borderRadius: 'var(--radius)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: isSelected ? 'var(--accent)' : 'transparent',
              border: isToday && !isSelected ? '1px solid var(--accent)' : 'none',
            }}>
              <span className="hand" style={{
                fontSize: 12, lineHeight: 1,
                color: isSelected ? '#050505' : isToday ? 'var(--accent)' : 'var(--ink-faint)',
                fontWeight: isToday || isSelected ? 700 : 400,
              }}>
                {dayNum}
              </span>
            </div>

            <div
              aria-label={info ? t.activities.status[info.status] : undefined}
              className={info ? `month-status-mark month-status-mark--${info.status}` : 'month-status-mark'}
            />
          </button>
        )
      })}
    </div>
  )
}
