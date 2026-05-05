'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useWorkoutByDate } from '@/lib/hooks/useWorkoutByDate'
import { postJson } from '@/lib/api/client'
import { formatPace, formatKm } from '@/lib/api/types'
import PaceRangeBar from '@/components/today/PaceRangeBar'
import WorkoutSteps from '@/components/today/WorkoutSteps'
import YesterdayCompare from '@/components/today/YesterdayCompare'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function WorkoutDetailPage({ params }: { params: { date: string } }) {
  const { date } = params
  const router = useRouter()
  const { workout: data, isLoading, error, refresh } = useWorkoutByDate(date)
  const [marking, setMarking] = useState(false)
  const [marked, setMarked] = useState<string | null>(null)
  const { language, t } = useI18n()

  const displayDate = (() => {
    try {
      return new Date(date + 'T00:00:00').toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', {
        month: 'long', day: 'numeric', weekday: 'short',
      })
    } catch { return date }
  })()

  async function mark(status: 'completed' | 'partial' | 'skipped') {
    if (!data?.workout || marking) return
    setMarking(true)
    try {
      await postJson(`/api/workouts/${data.workout.id}/feedback`, {
        status, rpe_actual: null, notes: null,
      })
      setMarked(status)
      refresh()
    } finally {
      setMarking(false)
    }
  }

  if (isLoading) {
    return (
      <div style={{ minHeight: '100dvh', display: 'flex', alignItems: 'center',
                    justifyContent: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>{t.common.loading}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 16 }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>{error.message}</span>
        <button onClick={() => router.back()} className="hand"
          style={{ background: 'none', border: 'none', color: 'var(--ink-faint)',
                   cursor: 'pointer', fontSize: 14 }}>
          ← {t.common.back}
        </button>
      </div>
    )
  }

  const workout = data?.workout ?? null
  const yesterday_workout = data?.yesterday_workout ?? null
  const yesterday_activity = data?.yesterday_activity ?? null
  const recovery_recommendation = data?.recovery_recommendation ?? null

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--paper)' }}>
      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--rule-soft)',
                    display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => router.back()}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 22, color: 'var(--ink-faint)', padding: 0, lineHeight: 1 }}>
          ‹
        </button>
        <div>
          <div className="hand" style={{ fontSize: 16, fontWeight: 700 }}>{displayDate}</div>
          {data?.week_index && (
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {language === 'zh' ? `${t.workout.weekPrefix} ${data.week_index} 周` : `${t.workout.weekPrefix} ${data.week_index}`}
            </div>
          )}
        </div>
      </div>

      {!workout ? (
        <div style={{ padding: '48px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🌿</div>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            {t.workout.restDay}
          </div>
          {recovery_recommendation ? (
            <div style={{ padding: '12px 16px', background: 'var(--accent-light)',
                          border: '1px solid var(--accent)', borderRadius: 'var(--radius)', textAlign: 'left',
                          margin: '0 16px' }}>
              <div className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>
                &quot;{recovery_recommendation.ethos_quote}&quot;
              </div>
            </div>
          ) : (
            <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
              {t.workout.recoverWell}
            </div>
          )}
        </div>
      ) : (
        <>
          {/* ── Workout title ───────────────────────────────── */}
          <div style={{ padding: '16px 16px 12px' }}>
            <div className="hand" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.2 }}>
              {workout.title}
            </div>
            <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>
              {workout.purpose}
            </div>
          </div>

          {/* ── Big numbers ─────────────────────────────────── */}
          <div style={{ display: 'flex', padding: '0 16px 16px',
                        borderBottom: '1px solid var(--rule-soft)' }}>
            {workout.distance_m && (
              <BigNum label={t.workout.distance} value={formatKm(workout.distance_m)} />
            )}
            <BigNum label={t.workout.duration} value={`${workout.duration_min}`} />
            {workout.target_min != null && workout.target_max != null && (
              <BigNum
                label={t.workout.pace}
                value={`${formatPace(workout.target_min)}–${formatPace(workout.target_max)}`}
              />
            )}
            {workout.rpe_min != null && workout.rpe_max != null && (
              <BigNum label="RPE" value={`${workout.rpe_min}–${workout.rpe_max}`} />
            )}
          </div>

          {/* ── Pace bar ────────────────────────────────────── */}
          {workout.target_min != null && workout.target_max != null && (
            <div style={{ padding: '16px' }}>
              <PaceRangeBar
                targetMin={workout.target_min}
                targetMax={workout.target_max}
                actualPace={null}
              />
            </div>
          )}

          {/* ── Adaptation notes ────────────────────────────── */}
          {workout.adaptation_notes && (
            <div style={{ margin: '0 16px 16px', padding: '10px 14px',
                          background: 'var(--accent-light)',
                          border: '1px solid var(--accent)', borderRadius: 'var(--radius)' }}>
              <span className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>
                {workout.adaptation_notes}
              </span>
            </div>
          )}

          {/* ── Steps ───────────────────────────────────────── */}
          {workout.steps.length > 0 && <WorkoutSteps steps={workout.steps} />}

          {/* ── Yesterday compare ───────────────────────────── */}
          {yesterday_workout && (
            <YesterdayCompare workout={yesterday_workout} activity={yesterday_activity} />
          )}

          {/* ── Mark done ───────────────────────────────────── */}
          <div style={{ padding: '16px', display: 'flex', gap: 10, flexDirection: 'column' }}>
            <div className="hand text-faint" style={{ fontSize: 12, textAlign: 'center' }}>
              {t.workout.doneQuestion}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['completed', 'partial', 'skipped'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => mark(s)}
                  disabled={marking || !!marked}
                  style={{
                    flex: 1, padding: '10px', borderRadius: 'var(--radius)',
                    fontFamily: 'var(--font-hand)', fontSize: 14,
                    cursor: (marking || !!marked) ? 'default' : 'pointer',
                    opacity: (marking || !!marked) && marked !== s ? 0.5 : 1,
                    border: s === 'skipped' ? 'none' : '1px solid var(--accent)',
                    background: (s === 'completed' || marked === s) ? 'var(--accent)' : 'var(--paper)',
                    color: (s === 'completed' || marked === s) ? '#050505' : 'var(--ink)',
                  }}
                >
                  {s === 'completed' ? `${t.workout.complete} ✓` : s === 'partial' ? t.workout.partial : t.workout.skip}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
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
