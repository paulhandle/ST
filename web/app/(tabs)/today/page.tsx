'use client'

import { useState } from 'react'
import { useToday } from '@/lib/hooks/useToday'
import { postJson } from '@/lib/api/client'
import { formatPace, formatKm } from '@/lib/api/types'
import SkillChip from '@/components/SkillChip'
import PaceRangeBar from '@/components/today/PaceRangeBar'
import WorkoutSteps from '@/components/today/WorkoutSteps'
import YesterdayCompare from '@/components/today/YesterdayCompare'

export default function TodayPage() {
  const { today, isLoading, error, refresh } = useToday()
  const [marking, setMarking] = useState(false)
  const [marked, setMarked] = useState<string | null>(null)

  async function mark(status: 'completed' | 'partial' | 'skipped') {
    if (!today?.workout || marking) return
    setMarking(true)
    try {
      await postJson(`/api/workouts/${today.workout.id}/feedback`, { status, rpe_actual: null, notes: null })
      setMarked(status)
      refresh()
    } finally {
      setMarking(false)
    }
  }

  if (isLoading) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>加载中…</span>
      </div>
    )
  }

  if (error || !today) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>{error?.message ?? '暂无数据'}</span>
      </div>
    )
  }

  const { workout, matched_activity, yesterday_workout, yesterday_activity, recovery_recommendation } = today
  const isRest = !workout

  return (
    <div>
      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="between">
          <span className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)' }}>
            第 {today.week_index} 周
          </span>
        </div>
      </div>

      {isRest ? (
        <RestDay recovery={recovery_recommendation} />
      ) : workout ? (
        <>
          {/* ── Workout header ─────────────────────────────── */}
          <div style={{ padding: '16px 16px 12px' }}>
            <div className="hand" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.2 }}>
              {workout.title}
            </div>
            <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>
              {workout.purpose}
            </div>
          </div>

          {/* ── Big numbers ────────────────────────────────── */}
          <div style={{ display: 'flex', gap: 0, padding: '0 16px 16px', borderBottom: '1px solid var(--rule-soft)' }}>
            {workout.distance_m && (
              <BigNum label="公里" value={formatKm(workout.distance_m)} />
            )}
            <BigNum label="分钟" value={`${workout.duration_min}`} />
            {workout.target_min != null && workout.target_max != null && (
              <BigNum
                label="配速"
                value={`${formatPace(workout.target_min)}–${formatPace(workout.target_max)}`}
              />
            )}
            {workout.rpe_min != null && workout.rpe_max != null && (
              <BigNum label="RPE" value={`${workout.rpe_min}–${workout.rpe_max}`} />
            )}
          </div>

          {/* ── Pace range viz ─────────────────────────────── */}
          {workout.target_min != null && workout.target_max != null && (
            <div style={{ padding: '16px' }}>
              <PaceRangeBar
                targetMin={workout.target_min}
                targetMax={workout.target_max}
                actualPace={matched_activity?.avg_pace_sec_per_km ?? null}
              />
            </div>
          )}

          {/* ── Adherence banner ───────────────────────────── */}
          {workout.adaptation_notes && (
            <div style={{ margin: '0 16px 16px', padding: '10px 14px', background: 'var(--accent-light)', border: '1.5px solid var(--accent)', borderRadius: 6 }}>
              <span className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>{workout.adaptation_notes}</span>
            </div>
          )}

          {/* ── Steps ──────────────────────────────────────── */}
          {workout.steps.length > 0 && (
            <WorkoutSteps steps={workout.steps} />
          )}

          {/* ── Yesterday compare ──────────────────────────── */}
          {yesterday_workout && (
            <YesterdayCompare
              workout={yesterday_workout}
              activity={yesterday_activity}
            />
          )}

          {/* ── Mark done ──────────────────────────────────── */}
          {!matched_activity && (
            <div style={{ padding: '16px', display: 'flex', gap: 10, flexDirection: 'column' }}>
              <div className="hand text-faint" style={{ fontSize: 12, textAlign: 'center' }}>完成了吗？</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <MarkBtn
                  label="完成 ✓"
                  disabled={marking || !!marked}
                  active={marked === 'completed'}
                  onClick={() => mark('completed')}
                  variant="primary"
                />
                <MarkBtn
                  label="部分"
                  disabled={marking || !!marked}
                  active={marked === 'partial'}
                  onClick={() => mark('partial')}
                  variant="outline"
                />
                <MarkBtn
                  label="跳过"
                  disabled={marking || !!marked}
                  active={marked === 'skipped'}
                  onClick={() => mark('skipped')}
                  variant="ghost"
                />
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}

function BigNum({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ flex: 1, textAlign: 'center' }}>
      <div className="hand" style={{ fontSize: 28, fontWeight: 700, lineHeight: 1.1 }}>{value}</div>
      <div className="annot text-faint" style={{ fontSize: 12 }}>{label}</div>
    </div>
  )
}

function MarkBtn({
  label, onClick, disabled, active, variant,
}: {
  label: string; onClick: () => void; disabled: boolean; active: boolean; variant: 'primary' | 'outline' | 'ghost'
}) {
  const styles: React.CSSProperties = {
    flex: 1,
    padding: '10px',
    borderRadius: 8,
    fontFamily: 'var(--font-hand)',
    fontSize: 14,
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled && !active ? 0.5 : 1,
    transition: 'all 0.15s',
    border: variant === 'ghost' ? 'none' : '1.5px solid var(--ink)',
    background: variant === 'primary' || active ? 'var(--ink)' : 'var(--paper)',
    color: variant === 'primary' || active ? 'var(--paper)' : 'var(--ink)',
  }
  return (
    <button style={styles} onClick={onClick} disabled={disabled}>{label}</button>
  )
}

function RestDay({ recovery }: { recovery: import('@/lib/api/types').RecoveryRecommendation | null }) {
  return (
    <div style={{ padding: '40px 24px', textAlign: 'center' }}>
      <div className="hand" style={{ fontSize: 48, marginBottom: 12 }}>🌿</div>
      <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>今日休息</div>

      {recovery ? (
        <>
          <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 16, lineHeight: 1.6 }}>
            最近状态不佳，今天做个轻松练习
          </div>
          <div style={{ padding: '12px 16px', background: 'var(--accent-light)', border: '1.5px solid var(--accent)', borderRadius: 8, textAlign: 'left' }}>
            <div className="hand" style={{ fontSize: 13, marginBottom: 6, color: 'var(--accent)', fontStyle: 'italic' }}>
              "{recovery.ethos_quote}"
            </div>
            <div className="hand text-faint" style={{ fontSize: 12 }}>
              {recovery.degraded_workout.title} · {recovery.degraded_workout.duration_min} 分钟
            </div>
          </div>
        </>
      ) : (
        <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
          好好恢复，明天见 💪
        </div>
      )}
    </div>
  )
}
