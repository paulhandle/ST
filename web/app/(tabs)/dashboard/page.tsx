'use client'

import { useDashboard } from '@/lib/hooks/useDashboard'
import SkillChip from '@/components/SkillChip'
import AdjustmentBanner from '@/components/dashboard/AdjustmentBanner'
import TodayCard from '@/components/dashboard/TodayCard'
import GoalCard from '@/components/dashboard/GoalCard'
import VolumeCard from '@/components/dashboard/VolumeCard'
import WeekStrip from '@/components/dashboard/WeekStrip'
import RecentActivities from '@/components/dashboard/RecentActivities'
import ReadinessPanel from '@/components/dashboard/ReadinessPanel'
import EmptyPlanState from '@/components/EmptyPlanState'

export default function DashboardPage() {
  const { dashboard, isLoading, error } = useDashboard()

  if (isLoading) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>加载中…</span>
      </div>
    )
  }

  if (error || !dashboard) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>
          {error?.message ?? '暂无数据'}
        </span>
      </div>
    )
  }

  // No plan yet — show onboarding CTA after header
  const noPlan = !dashboard.today.plan_id

  const { greeting, athlete, pending_adjustment, today, this_week, goal, volume_history, recent_activities, readiness, meta } = dashboard

  const greetingText =
    greeting.time_of_day === 'morning' ? '早上好' :
    greeting.time_of_day === 'afternoon' ? '下午好' :
    greeting.time_of_day === 'evening' ? '晚上好' : '你好'

  return (
    <div>
      {/* ── Status bar ─────────────────────────────────────── */}
      <div style={{
        padding: '14px 16px 10px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--rule-soft)',
      }}>
        <div>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.2 }}>
            {greetingText}，{athlete.name.split('')[0]}
          </div>
          <div className="annot text-faint" style={{ fontSize: 13 }}>
            {greeting.weekday_short} · 第 {greeting.week_index} 周
            {greeting.week_phase ? ` · ${greeting.week_phase}` : ''}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          {athlete.current_skill && (
            <SkillChip skill={athlete.current_skill} />
          )}
          {meta.last_sync_at && (
            <span className="annot text-faint" style={{ fontSize: 11 }}>
              同步 {new Date(meta.last_sync_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>

      {/* ── No plan → empty state CTA ──────────────────────── */}
      {noPlan && <EmptyPlanState />}

      {/* ── Adjustment banner ──────────────────────────────── */}
      {!noPlan && pending_adjustment && (
        <AdjustmentBanner adjustment={pending_adjustment} />
      )}

      {/* ── Today compressed ───────────────────────────────── */}
      <TodayCard today={today} />

      {/* ── Week strip ─────────────────────────────────────── */}
      <WeekStrip week={this_week} />

      {/* ── Goal card ──────────────────────────────────────── */}
      {goal && <GoalCard goal={goal} />}

      {/* ── Volume card ────────────────────────────────────── */}
      {volume_history.length > 0 && <VolumeCard history={volume_history} />}

      {/* ── Readiness ──────────────────────────────────────── */}
      <ReadinessPanel readiness={readiness} />

      {/* ── Recent activities ──────────────────────────────── */}
      {recent_activities.length > 0 && <RecentActivities activities={recent_activities} />}

      {/* ── Footer ─────────────────────────────────────────── */}
      <div style={{ padding: '12px 16px 4px', textAlign: 'center' }}>
        <span className="annot text-faint" style={{ fontSize: 11 }}>
          {meta.skill_name} v{meta.skill_version}
        </span>
      </div>
    </div>
  )
}
