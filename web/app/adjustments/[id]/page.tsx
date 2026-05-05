'use client'

import { use, useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { fetcher, postJson } from '@/lib/api/client'
import type { PlanAdjustmentOut } from '@/lib/api/types'
import AffectedWorkoutRow from '@/components/adjustments/AffectedWorkoutRow'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function AdjustmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const [acting, setActing] = useState(false)
  const [done, setDone] = useState<'accepted' | 'rejected' | null>(null)
  const { t } = useI18n()

  const { data: adj, isLoading, error } = useSWR<PlanAdjustmentOut>(
    `/api/plan-adjustments/${id}`,
    fetcher,
  )

  async function accept() {
    setActing(true)
    try {
      await postJson(`/api/plan-adjustments/${id}/apply`, {})
      setDone('accepted')
      setTimeout(() => router.back(), 1200)
    } finally {
      setActing(false)
    }
  }

  async function reject() {
    setActing(true)
    try {
      await postJson(`/api/plan-adjustments/${id}/reject`, {})
      setDone('rejected')
      setTimeout(() => router.back(), 1200)
    } finally {
      setActing(false)
    }
  }

  return (
    <div>
      {/* Header */}
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--rule-soft)' }}>
        <button
          onClick={() => router.back()}
          className="hand text-faint"
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14 }}
        >
          ‹ {t.common.back}
        </button>
      </div>

      {isLoading && (
        <div className="hand text-faint" style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>{t.common.loading}</div>
      )}
      {error && (
        <div className="hand text-faint" style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>{error.message}</div>
      )}

      {done && (
        <div style={{ padding: '32px 16px', textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>{done === 'accepted' ? '✓' : '✗'}</div>
          <div className="hand" style={{ fontSize: 18 }}>
            {done === 'accepted' ? t.adjustment.accepted : t.adjustment.rejected}
          </div>
        </div>
      )}

      {adj && !done && (
        <>
          {/* Reason */}
          <div style={{ padding: '16px 16px 12px' }}>
            <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
              {adj.reason_headline}
            </div>
            {adj.recommendation_text && (
              <div className="hand" style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--ink-mid)' }}>
                {adj.recommendation_text}
              </div>
            )}
          </div>

          {/* Affected workouts */}
          {adj.affected_workouts.length > 0 && (
            <div>
              <div className="section-header">
                <span className="section-title">{t.adjustment.affectedWorkouts}</span>
                <span className="annot text-faint" style={{ fontSize: 12 }}>
                  {adj.affected_workouts.length} {t.adjustment.sessions}
                </span>
              </div>
              {adj.affected_workouts.map((w) => (
                <AffectedWorkoutRow key={w.workout_id} workout={w} />
              ))}
            </div>
          )}

          {/* Actions */}
          {adj.status === 'pending' && (
            <div style={{ padding: '20px 16px', display: 'flex', gap: 10 }}>
              <button
                onClick={reject}
                disabled={acting}
                className="hand"
                style={{
                  flex: 1, padding: '13px',
                  border: '1px solid var(--rule)',
                  borderRadius: 'var(--radius)', background: 'none',
                  color: 'var(--ink)',
                  fontSize: 15, cursor: acting ? 'default' : 'pointer',
                }}
              >
                {t.adjustment.reject}
              </button>
              <button
                onClick={accept}
                disabled={acting}
                className="hand"
                style={{
                  flex: 2, padding: '13px',
                  background: 'var(--accent)', color: '#050505',
                  border: 'none', borderRadius: 'var(--radius)',
                  fontSize: 15, cursor: acting ? 'default' : 'pointer',
                  opacity: acting ? 0.7 : 1,
                }}
              >
                {acting ? t.adjustment.acting : t.adjustment.accept}
              </button>
            </div>
          )}

          {adj.status !== 'pending' && (
            <div className="hand text-faint" style={{ padding: '20px 16px', textAlign: 'center', fontSize: 13 }}>
              {adj.status === 'confirmed' ? t.adjustment.alreadyAccepted : t.adjustment.alreadyRejected}
            </div>
          )}
        </>
      )}
    </div>
  )
}
