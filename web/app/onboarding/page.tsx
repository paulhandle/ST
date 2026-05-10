'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getToken, handleStaleSession, readApiErrorDetail, saveAthleteId } from '@/lib/auth'
import { useI18n } from '@/lib/i18n/I18nProvider'
import type { SkillManifestOut } from '@/lib/api/types'

type Step = 1 | 2 | 3 | 4 | 5
const TOTAL = 5

/* ── Step data ──────────────────────────────────────────────────────── */

interface OnboardingState {
  // Step 2: Goal
  targetRaceDate: string
  targetTime: string          // "3:30" format, empty = finish only
  experienceLevel: 'none' | 'beginner' | 'intermediate'
  // Step 3: Availability
  weeklyDays: number
  selectedWeekdays: number[]  // 0=Mon…6=Sun
  // Step 4: Skill
  selectedSkill: string
  planWeeks: number
}

const INIT: OnboardingState = {
  targetRaceDate: '',
  targetTime: '',
  experienceLevel: 'none',
  weeklyDays: 3,
  selectedWeekdays: [1, 3, 6],
  selectedSkill: 'marathon_st_default',
  planWeeks: 16,
}

const DEFAULT_SKILL: SkillManifestOut = {
  slug: 'marathon_st_default',
  name: 'PerformanceProtocol Marathon Plan',
  version: '1.0.0',
  sport: 'marathon',
  author: null,
  tags: ['default'],
  description: 'Conservative default marathon cycle.',
  is_active: true,
}

/* ── Page ───────────────────────────────────────────────────────────── */

export default function OnboardingPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [step, setStep] = useState<Step>(1)
  const [state, setState] = useState<OnboardingState>(INIT)
  const [skills, setSkills] = useState<SkillManifestOut[]>([DEFAULT_SKILL])
  const [skillsLoading, setSkillsLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadSkills() {
      const token = getToken()
      try {
        const res = await fetch('/api/skills', {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        if (!res.ok) throw new Error('skills')
        const loaded = await res.json()
        if (Array.isArray(loaded) && loaded.length > 0) {
          setSkills(loaded)
          setState(s => ({ ...s, selectedSkill: loaded[0].slug ?? s.selectedSkill }))
        }
      } catch {
        setSkills([DEFAULT_SKILL])
      } finally {
        setSkillsLoading(false)
      }
    }
    loadSkills()
  }, [])

  function update(patch: Partial<OnboardingState>) {
    setState(s => ({ ...s, ...patch }))
  }

  function next() {
    if (step < TOTAL) setStep((s) => (s + 1) as Step)
  }

  function back() {
    if (step > 1) setStep((s) => (s - 1) as Step)
  }

  async function createAthleteProfile(token: string | null) {
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
    if (!athleteRes.ok) {
      throw new Error(await responseErrorMessage(athleteRes, t.onboarding.createAthleteFailed))
    }

    const athlete = await athleteRes.json()
    saveAthleteId(athlete.id)
    return athlete
  }

  async function enterWithoutPlan() {
    setLoading(true)
    setError(null)
    const token = getToken()

    try {
      await createAthleteProfile(token)
      router.replace('/dashboard')
    } catch (e) {
      setError(e instanceof Error ? e.message : t.onboarding.genericError)
    } finally {
      setLoading(false)
    }
  }

  async function finish() {
    setLoading(true)
    setError(null)
    const token = getToken()

    try {
      // 1. Create athlete profile
      const athlete = await createAthleteProfile(token)

      // 2. Create a structured marathon goal when provided.
      let raceGoalId: number | null = null
      if (state.targetRaceDate) {
        const goalRes = await fetch('/api/marathon/goals', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            athlete_id: athlete.id,
            sport: 'marathon',
            race_date: state.targetRaceDate,
            target_time_sec: parseTargetTimeSec(state.targetTime),
            plan_weeks: state.planWeeks,
            availability: availabilityPayload(state),
          }),
        })
        if (goalRes.ok) {
          const goal = await goalRes.json()
          raceGoalId = goal.id
        }
      }

      // 3. Generate and confirm the selected skill's plan. This is the core product flow.
      const planRes = await fetch('/api/marathon/plans/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          athlete_id: athlete.id,
          race_goal_id: raceGoalId,
          target_time_sec: parseTargetTimeSec(state.targetTime),
          race_date: state.targetRaceDate || null,
          plan_weeks: state.planWeeks,
          availability: availabilityPayload(state),
          skill_slug: state.selectedSkill,
          use_llm: false,
        }),
      })
      if (!planRes.ok) {
        throw new Error(await responseErrorMessage(planRes, t.onboarding.planFailed))
      }
      const plan = await planRes.json()

      const confirmRes = await fetch(`/api/plans/${plan.id}/confirm`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (!confirmRes.ok) throw new Error(t.onboarding.planFailed)

      router.replace('/plan')
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
          {([1, 2, 3, 4, 5] as Step[]).map(s => (
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
        {step === 1 && <StepIntro />}
        {step === 2 && <StepGoal state={state} update={update} />}
        {step === 3 && <StepAvailability state={state} update={update} />}
        {step === 4 && <StepSkill state={state} update={update} skills={skills} loading={skillsLoading} />}
        {step === 5 && <StepConfirm state={state} skills={skills} />}
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
        <button
          onClick={enterWithoutPlan}
          disabled={loading}
          className="hand"
          style={{
            width: '100%',
            padding: '12px',
            background: 'transparent',
            color: 'var(--ink-faint)',
            border: '1px solid var(--rule)',
            borderRadius: 'var(--radius)',
            fontSize: 14,
            cursor: loading ? 'default' : 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          {t.onboarding.enterWithoutPlan}
        </button>
      </div>
    </div>
  )
}

/* ── Step components ────────────────────────────────────────────────── */

function StepIntro() {
  const { t } = useI18n()
  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{t.onboarding.introTitle}</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        {t.onboarding.introText}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {t.onboarding.introSteps.map((item, index) => (
          <div key={item} style={{
            display: 'grid',
            gridTemplateColumns: '32px 1fr',
            gap: 10,
            alignItems: 'center',
            padding: '12px 0',
            borderBottom: '1px solid var(--rule-soft)',
          }}>
            <span className="annot" style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 800 }}>
              {String(index + 1).padStart(2, '0')}
            </span>
            <span className="hand" style={{ fontSize: 14, lineHeight: 1.4 }}>{item}</span>
          </div>
        ))}
      </div>
      <div className="hand text-faint" style={{ fontSize: 12, lineHeight: 1.6, marginTop: 22 }}>
        {t.onboarding.corosLaterText}
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

function StepSkill({ state, update, skills, loading }: {
  state: OnboardingState
  update: (p: Partial<OnboardingState>) => void
  skills: SkillManifestOut[]
  loading: boolean
}) {
  const { t } = useI18n()
  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{t.onboarding.chooseSkill}</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 24, lineHeight: 1.6 }}>
        {t.onboarding.skillText}
      </div>

      <Field label={t.planGenerate.trainingWeeks}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {[12, 16, 20, 24].map(weeks => (
            <button
              key={weeks}
              onClick={() => update({ planWeeks: weeks })}
              className="hand"
              style={choiceButtonStyle(state.planWeeks === weeks)}
            >
              {weeks}{t.common.weeks}
            </button>
          ))}
        </div>
      </Field>

      {loading ? (
        <div className="hand text-faint" style={{ fontSize: 13 }}>{t.common.loading}</div>
      ) : (
        <div>
          {skills.map(skill => (
            <button
              key={skill.slug}
              onClick={() => update({ selectedSkill: skill.slug })}
              className="hand"
              style={{
                width: '100%',
                textAlign: 'left',
                padding: '12px 14px',
                marginBottom: 10,
                borderRadius: 'var(--radius)',
                cursor: 'pointer',
                border: `1px solid ${state.selectedSkill === skill.slug ? 'var(--accent)' : 'var(--rule)'}`,
                background: state.selectedSkill === skill.slug ? 'var(--accent-light)' : 'var(--paper)',
                color: 'var(--ink)',
                fontFamily: 'var(--font-hand)',
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 700 }}>{skill.name}</div>
              <div className="text-faint" style={{ fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
                {skill.description}
              </div>
              {skill.tags.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {skill.tags.map(tag => <span key={tag} className="sk-pill" style={{ fontSize: 11 }}>{tag}</span>)}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function StepConfirm({ state, skills }: { state: OnboardingState; skills: SkillManifestOut[] }) {
  const { t } = useI18n()
  const weekdaySummary = state.selectedWeekdays.map(d => t.week.weekdaysShort[d]).join(' ')
  const selectedSkill = skills.find(skill => skill.slug === state.selectedSkill)
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
        <ConfirmRow label={t.onboarding.race} value={state.targetRaceDate || t.onboarding.unset} />
        <ConfirmRow label={t.onboarding.finishTarget} value={state.targetTime ? `sub-${state.targetTime}` : t.onboarding.finishOnly} />
        <ConfirmRow label={t.onboarding.trainingDays} value={weekdaySummary} />
        <ConfirmRow label={t.onboarding.experienceLabel} value={experienceSummary} />
        <ConfirmRow label={t.planGenerate.trainingSkill} value={selectedSkill?.name ?? state.selectedSkill} />
        <ConfirmRow label={t.planGenerate.trainingWeeks} value={`${state.planWeeks}${t.common.weeks}`} />
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

function parseTargetTimeSec(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const [h, m = '0'] = trimmed.split(':')
  const hours = Number(h)
  const minutes = Number(m)
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null
  return hours * 3600 + minutes * 60
}

async function responseErrorMessage(res: Response, fallback: string): Promise<string> {
  const detail = await readApiErrorDetail(res)
  handleStaleSession(detail)
  if (detail?.message && detail.reason) {
    return `${fallback}: ${detail.message} (${detail.reason})`
  }
  if (detail?.message) return `${fallback}: ${detail.message}`
  if (detail?.reason) return `${fallback}: ${detail.reason}`
  return fallback
}

function availabilityPayload(state: OnboardingState) {
  return {
    weekly_training_days: Math.max(2, state.weeklyDays),
    preferred_long_run_weekday: state.selectedWeekdays.includes(6) ? 6 : state.selectedWeekdays.at(-1) ?? 6,
    unavailable_weekdays: [0, 1, 2, 3, 4, 5, 6].filter(day => !state.selectedWeekdays.includes(day)),
  }
}

function choiceButtonStyle(active: boolean): React.CSSProperties {
  return {
    flex: 1,
    padding: '10px 4px',
    border: `1px solid ${active ? 'var(--accent)' : 'var(--rule)'}`,
    borderRadius: 'var(--radius)',
    background: active ? 'var(--accent)' : 'var(--paper)',
    color: active ? '#050505' : 'var(--ink)',
    fontSize: 12,
    cursor: 'pointer',
    fontFamily: 'var(--font-hand)',
  }
}
