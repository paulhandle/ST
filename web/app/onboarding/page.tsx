'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from '@/lib/auth'
import { useI18n } from '@/lib/i18n/I18nProvider'

type Step = 1 | 2 | 3 | 4
const TOTAL = 4

/* ── Step data ──────────────────────────────────────────────────────── */

interface OnboardingState {
  // Step 1: COROS
  corosUsername: string
  corosPassword: string
  corosSkipped: boolean
  // Step 2: Goal
  targetRaceDate: string
  targetTime: string          // "3:30" format, empty = finish only
  experienceLevel: 'none' | 'beginner' | 'intermediate'
  // Step 3: Availability
  weeklyDays: number
  selectedWeekdays: number[]  // 0=Mon…6=Sun
}

const INIT: OnboardingState = {
  corosUsername: '',
  corosPassword: '',
  corosSkipped: false,
  targetRaceDate: '',
  targetTime: '',
  experienceLevel: 'none',
  weeklyDays: 3,
  selectedWeekdays: [1, 3, 6],
}

/* ── Page ───────────────────────────────────────────────────────────── */

export default function OnboardingPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [step, setStep] = useState<Step>(1)
  const [state, setState] = useState<OnboardingState>(INIT)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function update(patch: Partial<OnboardingState>) {
    setState(s => ({ ...s, ...patch }))
  }

  function next() {
    if (step < TOTAL) setStep((s) => (s + 1) as Step)
  }

  function back() {
    if (step > 1) setStep((s) => (s - 1) as Step)
  }

  async function finish() {
    setLoading(true)
    setError(null)
    const token = getToken()

    try {
      // 1. Create athlete profile
      const athleteRes = await fetch('/api/athletes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: 'Me',
          sport: 'marathon',
          level: state.experienceLevel === 'none' ? 'beginner' : state.experienceLevel,
          weekly_training_days: state.weeklyDays,
        }),
      })
      if (!athleteRes.ok) throw new Error(t.onboarding.createAthleteFailed)

      const athlete = await athleteRes.json()

      // 2. Connect COROS if credentials provided
      if (!state.corosSkipped && state.corosUsername && state.corosPassword) {
        await fetch('/api/coros/connect', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            athlete_id: athlete.id,
            username: state.corosUsername,
            password: state.corosPassword,
          }),
        })
        // Don't block onboarding if COROS fails — user can connect later
      }

      // 3. Set race goal if provided
      if (state.targetRaceDate) {
        await fetch(`/api/athletes/${athlete.id}/goals`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            sport: 'marathon',
            race_date: state.targetRaceDate,
            target_time: state.targetTime || null,
            description: state.targetTime ? `sub-${state.targetTime}` : t.onboarding.finishOnly,
          }),
        })
      }

      router.replace('/dashboard')
    } catch (e) {
      setError(e instanceof Error ? e.message : t.onboarding.genericError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--paper)',
      padding: '0 24px',
    }}>
      {/* Progress */}
      <div style={{ padding: '20px 0 0', display: 'flex', alignItems: 'center', gap: 8 }}>
        {step > 1 && (
          <button
            onClick={back}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--ink-faint)', paddingRight: 8 }}
          >‹</button>
        )}
        <div style={{ flex: 1, display: 'flex', gap: 4 }}>
          {([1, 2, 3, 4] as Step[]).map(s => (
            <div key={s} style={{
              flex: 1, height: 3, borderRadius: 2,
              background: s <= step ? 'var(--accent)' : 'var(--rule-soft)',
              transition: 'background 0.2s',
            }} />
          ))}
        </div>
        <span className="annot text-faint" style={{ fontSize: 12, marginLeft: 8 }}>{step} / {TOTAL}</span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, paddingTop: 32, maxWidth: 400, width: '100%', alignSelf: 'center' }}>
        {step === 1 && <StepCoros state={state} update={update} />}
        {step === 2 && <StepGoal state={state} update={update} />}
        {step === 3 && <StepAvailability state={state} update={update} />}
        {step === 4 && <StepConfirm state={state} />}
      </div>

      {/* Error */}
      {error && (
        <div className="hand" style={{ color: 'var(--accent)', fontSize: 13, textAlign: 'center', padding: '8px 0' }}>
          {error}
        </div>
      )}

      {/* Navigation */}
      <div style={{ padding: '16px 0 32px', display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 400, width: '100%', alignSelf: 'center' }}>
        {step < TOTAL ? (
          <>
            <button
              onClick={next}
              style={{
                width: '100%', padding: '14px',
                background: 'var(--accent)', color: '#050505',
                border: 'none', borderRadius: 'var(--radius)',
                fontFamily: 'var(--font-hand)', fontSize: 16, cursor: 'pointer',
              }}
            >
              {t.onboarding.next}
            </button>
            {step === 1 && (
              <button
                onClick={() => { update({ corosSkipped: true }); next() }}
                style={{
                  background: 'none', border: 'none',
                  fontFamily: 'var(--font-hand)', fontSize: 13,
                  color: 'var(--ink-faint)', cursor: 'pointer',
                }}
              >
                {t.onboarding.skipCoros}
              </button>
            )}
          </>
        ) : (
          <button
            onClick={finish}
            disabled={loading}
            style={{
              width: '100%', padding: '14px',
              background: 'var(--accent)', color: '#050505',
              border: 'none', borderRadius: 'var(--radius)',
              fontFamily: 'var(--font-hand)', fontSize: 16,
              cursor: loading ? 'default' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? t.onboarding.creating : `${t.onboarding.startTraining} →`}
          </button>
        )}
      </div>
    </div>
  )
}

/* ── Step components ────────────────────────────────────────────────── */

function StepCoros({ state, update }: { state: OnboardingState; update: (p: Partial<OnboardingState>) => void }) {
  const { t } = useI18n()
  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{t.onboarding.connectCoros}</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        {t.onboarding.corosText}
      </div>

      <Field label={t.onboarding.corosAccount}>
        <input
          type="text"
          placeholder={t.onboarding.corosAccountPlaceholder}
          value={state.corosUsername}
          onChange={e => update({ corosUsername: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <Field label={t.onboarding.corosPassword}>
        <input
          type="password"
          placeholder={t.onboarding.passwordPlaceholder}
          value={state.corosPassword}
          onChange={e => update({ corosPassword: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <div className="hand text-faint" style={{ fontSize: 11, marginTop: 8 }}>
        {t.onboarding.passwordNote}
      </div>
    </div>
  )
}

function StepGoal({ state, update }: { state: OnboardingState; update: (p: Partial<OnboardingState>) => void }) {
  const { t } = useI18n()
  const experienceOptions = [
    ['none', t.onboarding.expNone],
    ['beginner', t.onboarding.expBeginner],
    ['intermediate', t.onboarding.expIntermediate],
  ] as const

  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{t.onboarding.setGoal}</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        {t.onboarding.goalText}
      </div>

      <Field label={t.onboarding.raceDate}>
        <input
          type="date"
          value={state.targetRaceDate}
          onChange={e => update({ targetRaceDate: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <Field label={t.onboarding.targetTime}>
        <input
          type="text"
          placeholder={t.onboarding.targetTimePlaceholder}
          value={state.targetTime}
          onChange={e => update({ targetTime: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <Field label={t.onboarding.experience}>
        <div style={{ display: 'flex', gap: 8 }}>
          {experienceOptions.map(([val, label]) => (
            <button
              key={val}
              onClick={() => update({ experienceLevel: val })}
              className="hand"
              style={{
                flex: 1, padding: '10px 4px',
                border: `1px solid ${state.experienceLevel === val ? 'var(--accent)' : 'var(--rule)'}`,
                borderRadius: 'var(--radius)',
                background: state.experienceLevel === val ? 'var(--accent)' : 'var(--paper)',
                color: state.experienceLevel === val ? '#050505' : 'var(--ink)',
                fontSize: 12, cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </Field>
    </div>
  )
}

function StepAvailability({ state, update }: { state: OnboardingState; update: (p: Partial<OnboardingState>) => void }) {
  const { t } = useI18n()
  function toggleDay(d: number) {
    const cur = state.selectedWeekdays
    const next = cur.includes(d) ? cur.filter(x => x !== d) : [...cur, d].sort()
    update({ selectedWeekdays: next, weeklyDays: next.length })
  }

  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{t.onboarding.availability}</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        {t.onboarding.availabilityText}
      </div>

      <div className="hand" style={{ fontSize: 13, marginBottom: 12 }}>{t.onboarding.weeklyTrainingDays}</div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 24 }}>
        {t.week.weekdaysShort.map((label, i) => {
          const selected = state.selectedWeekdays.includes(i)
          return (
            <button
              key={i}
              onClick={() => toggleDay(i)}
              className="hand"
              style={{
                flex: 1, padding: '10px 0',
                border: `1px solid ${selected ? 'var(--accent)' : 'var(--rule)'}`,
                borderRadius: 'var(--radius)',
                background: selected ? 'var(--accent)' : 'var(--paper)',
                color: selected ? '#050505' : 'var(--ink)',
                fontSize: 13, cursor: 'pointer',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      <div className="hand text-faint" style={{ fontSize: 13 }}>
        {t.onboarding.selectedDays} {state.selectedWeekdays.length} {t.common.days} / {t.common.weeks}
      </div>
    </div>
  )
}

function StepConfirm({ state }: { state: OnboardingState }) {
  const { t } = useI18n()
  const weekdaySummary = state.selectedWeekdays.map(d => t.week.weekdaysShort[d]).join(' ')
  const experienceSummary =
    state.experienceLevel === 'none' ? t.onboarding.expNone :
    state.experienceLevel === 'beginner' ? t.onboarding.expBeginnerSummary :
    t.onboarding.expIntermediateSummary

  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{t.onboarding.confirm}</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        {t.onboarding.confirmText}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <ConfirmRow label="COROS" value={state.corosSkipped ? t.onboarding.notConnected : (state.corosUsername || '—')} />
        <ConfirmRow label={t.onboarding.race} value={state.targetRaceDate || t.onboarding.unset} />
        <ConfirmRow label={t.onboarding.finishTarget} value={state.targetTime ? `sub-${state.targetTime}` : t.onboarding.finishOnly} />
        <ConfirmRow label={t.onboarding.trainingDays} value={weekdaySummary} />
        <ConfirmRow label={t.onboarding.experienceLabel} value={experienceSummary} />
      </div>
    </div>
  )
}

/* ── UI helpers ─────────────────────────────────────────────────────── */

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)', marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}

function ConfirmRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--rule-soft)' }}>
      <span className="hand text-faint" style={{ fontSize: 13 }}>{label}</span>
      <span className="hand" style={{ fontSize: 13 }}>{value}</span>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  fontSize: 15,
  background: 'var(--paper)',
  color: 'var(--ink)',
  fontFamily: 'var(--font-hand)',
  outline: 'none',
  boxSizing: 'border-box',
}
