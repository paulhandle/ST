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
import Link from 'next/link'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function DashboardPage() {
  const { dashboard, isLoading, error } = useDashboard()
  const { language, t } = useI18n()

  if (isLoading) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>{t.common.loading}</span>
      </div>
    )
  }

  if (error || !dashboard) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>
          {error?.message ?? t.common.noData}
        </span>
      </div>
    )
  }

  // No plan yet — show onboarding CTA after header
  const noPlan = !dashboard.today.plan_id

  const { greeting, athlete, pending_adjustment, today, this_week, goal, volume_history, recent_activities, readiness, meta } = dashboard

  const greetingText =
    greeting.time_of_day === 'morning' ? t.dashboard.morning :
    greeting.time_of_day === 'afternoon' ? t.dashboard.afternoon :
    greeting.time_of_day === 'evening' ? t.dashboard.evening : t.dashboard.hello
  const weekLabel = language === 'zh'
    ? `${t.dashboard.weekPrefix} ${greeting.week_index} 周`
    : `${t.dashboard.weekPrefix} ${greeting.week_index}`

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
            {greeting.weekday_short} · {weekLabel}
            {greeting.week_phase ? ` · ${greeting.week_phase}` : ''}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {athlete.current_skill && (
              <SkillChip skill={athlete.current_skill} />
            )}
            <Link href="/settings" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', padding: 4 }}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="3" stroke="var(--ink-faint)" strokeWidth="1.5"/>
                <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.22 4.22l1.42 1.42M14.36 14.36l1.42 1.42M4.22 15.78l1.42-1.42M14.36 5.64l1.42-1.42" stroke="var(--ink-faint)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </Link>
          </div>
          {meta.last_sync_at && (
            <span className="annot text-faint" style={{ fontSize: 11 }}>
              {t.dashboard.synced} {new Date(meta.last_sync_at).toLocaleTimeString(language === 'zh' ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit' })}
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
