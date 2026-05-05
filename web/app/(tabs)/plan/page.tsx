'use client'

import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import { useDashboard } from '@/lib/hooks/useDashboard'
import type { VolumeCurveWeek } from '@/lib/api/types'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts'
import PendingAdjustmentSection from '@/components/plan/PendingAdjustmentSection'
import EmptyPlanState from '@/components/EmptyPlanState'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface PlanDetail {
  id: number
  title: string
  total_weeks: number
  start_date: string
  race_date: string
  is_confirmed: boolean
  goal_description: string | null
}

export default function PlanPage() {
  const { dashboard } = useDashboard()
  const planId = dashboard?.today.plan_id
  const { t } = useI18n()

  const { data: plan } = useSWR<PlanDetail>(
    planId ? `/api/marathon/plans/${planId}` : null,
    fetcher,
  )

  const { data: curve } = useSWR<VolumeCurveWeek[]>(
    planId ? `/api/plans/${planId}/volume-curve` : null,
    fetcher,
  )

  const currentWeek = dashboard?.this_week.week_index ?? 1

  // No plan yet — show empty state
  if (!planId && dashboard) {
    return <EmptyPlanState />
  }

  if (!plan) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>{t.common.loading}</span>
      </div>
    )
  }

  return (
    <div>
      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>{plan.title}</div>
        <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>
          {plan.start_date} → {plan.race_date} · {plan.total_weeks} {t.common.weeks}
        </div>
        {plan.goal_description && (
          <div className="hand" style={{ fontSize: 13, color: 'var(--accent)', marginTop: 4 }}>
            {t.plan.goal}: {plan.goal_description}
          </div>
        )}
      </div>

      {/* ── Phase strip ────────────────────────────────────── */}
      {curve && <PhaseStrip curve={curve} currentWeek={currentWeek} />}

      {/* ── Volume curve chart ─────────────────────────────── */}
      {curve && curve.length > 0 && (
        <div style={{ padding: '16px' }}>
          <div className="section-title" style={{ marginBottom: 12 }}>{t.plan.trainingVolume}</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={curve} barGap={2} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--rule-soft)" vertical={false} />
              <XAxis
                dataKey="week_index"
                tickLine={false}
                axisLine={false}
                tick={{ fontFamily: 'var(--font-annot)', fontSize: 11, fill: 'var(--ink-faint)' }}
                tickFormatter={(v) => `W${v}`}
                interval={Math.floor(curve.length / 6)}
              />
              <YAxis hide />
              <Bar dataKey="planned_km" fill="var(--rule)" radius={[2, 2, 0, 0]}>
                {curve.map((w) => (
                  <Cell
                    key={w.week_index}
                    fill={w.week_index === currentWeek ? 'var(--ink-faint)' : 'var(--rule)'}
                  />
                ))}
              </Bar>
              <Bar dataKey="executed_km" fill="var(--ink)" radius={[2, 2, 0, 0]}>
                {curve.map((w) => (
                  <Cell
                    key={w.week_index}
                    fill={w.is_recovery ? 'var(--ink-faint)' : 'var(--ink)'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Week list ──────────────────────────────────────── */}
      {curve && (
        <div>
          <div className="section-header">
            <span className="section-title">{t.plan.weeklyPlan}</span>
          </div>
          {curve.map((w) => (
            <WeekRow key={w.week_index} week={w} isCurrent={w.week_index === currentWeek} />
          ))}
        </div>
      )}

      {/* ── Pending adjustment ─────────────────────────────── */}
      {dashboard?.pending_adjustment && (
        <PendingAdjustmentSection adjustment={dashboard.pending_adjustment} />
      )}
    </div>
  )
}

function PhaseStrip({ curve, currentWeek }: { curve: VolumeCurveWeek[]; currentWeek: number }) {
  const { t } = useI18n()
  const phases = groupPhases(curve)
  return (
    <div style={{ padding: '8px 16px', display: 'flex', gap: 3, overflowX: 'auto' }}>
      {phases.map((p) => (
        <div
          key={(p.phase ?? 'null') + p.start}
          style={{
            flex: p.count,
            minWidth: 40,
            padding: '6px 8px',
            background: 'var(--surface-low)',
            border: '1px solid var(--rule-soft)',
            borderRadius: 'var(--radius)',
            textAlign: 'center',
          }}
        >
          <div className="hand" style={{ fontSize: 12, fontWeight: 700 }}>{p.phase ?? '—'}</div>
          <div className="annot text-faint" style={{ fontSize: 10 }}>{p.count}{t.common.weekShort}</div>
        </div>
      ))}
    </div>
  )
}

function groupPhases(curve: VolumeCurveWeek[]) {
  const groups: { phase: string | null; start: number; count: number }[] = []
  for (const w of curve) {
    const last = groups[groups.length - 1]
    if (last && last.phase === w.phase) { last.count++ }
    else { groups.push({ phase: w.phase, start: w.week_index, count: 1 }) }
  }
  return groups
}

function WeekRow({ week, isCurrent }: { week: VolumeCurveWeek; isCurrent: boolean }) {
  const { t } = useI18n()
  const pct = week.planned_km > 0 ? (week.executed_km / week.planned_km) * 100 : 0
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 16px',
      borderBottom: '1px solid var(--rule-soft)',
      background: isCurrent ? 'var(--accent-light)' : undefined,
    }}>
      <div style={{ width: 32, flexShrink: 0 }}>
        <div className="hand" style={{
          fontSize: 13,
          fontWeight: isCurrent ? 700 : 400,
          color: isCurrent ? 'var(--accent)' : 'var(--ink)',
        }}>
          W{week.week_index}
        </div>
        {week.is_recovery && (
          <div className="annot" style={{ fontSize: 10, color: 'var(--ink-faint)' }}>{t.plan.recovery}</div>
        )}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ height: 4, borderRadius: 'var(--radius)', background: 'var(--rule-soft)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 'var(--radius)',
            background: isCurrent ? 'var(--accent)' : 'var(--ink)',
            width: `${Math.min(100, pct)}%`,
          }} />
        </div>
      </div>

      <div className="hand text-faint" style={{ fontSize: 12, flexShrink: 0 }}>
        {week.executed_km > 0 ? `${week.executed_km.toFixed(0)}` : '—'}
        <span style={{ color: 'var(--rule)' }}>/{week.planned_km.toFixed(0)}</span> km
      </div>
    </div>
  )
}
