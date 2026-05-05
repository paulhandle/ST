'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from '@/lib/auth'
import type { RunningAssessmentOut, HistoryImportOut, SkillManifestOut } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'
import type { AppCopy } from '@/lib/i18n/copy'

const ATHLETE_ID = 1

type Step = 1 | 2 | 3 | 4 | 5

interface GeneratedPlan {
  id: number
  title: string | null
  weeks: number
  start_date: string | null
  race_date: string | null
  target_time_sec: number | null
}

interface WizardState {
  step: Step
  loading: boolean
  error: string | null
  importResult: HistoryImportOut | null
  assessment: RunningAssessmentOut | null
  skills: SkillManifestOut[] | null
  selectedSkill: string
  targetH: number
  targetM: number
  planWeeks: number
  weeklyDays: number
  generatedPlan: GeneratedPlan | null
  syncResult: { synced_count: number; failed_count: number } | null
}

const INIT: WizardState = {
  step: 1,
  loading: true,
  error: null,
  importResult: null,
  assessment: null,
  skills: null,
  selectedSkill: 'marathon_st_default',
  targetH: 4,
  targetM: 0,
  planWeeks: 16,
  weeklyDays: 5,
  generatedPlan: null,
  syncResult: null,
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

function fallbackAssessment(message: string, t: AppCopy): RunningAssessmentOut {
  return {
    athlete_id: ATHLETE_ID,
    overall_score: 20,
    readiness_level: 'low',
    safe_weekly_distance_range_km: [15, 25],
    safe_training_days_range: [3, 4],
    long_run_capacity_km: 0,
    estimated_marathon_time_range_sec: [16200, 19800],
    goal_status: 'recommend_adjustment',
    limiting_factors: ['missing_history'],
    warnings: [message, t.planGenerate.fallbackWarning],
    confidence: 'low',
    summary: t.planGenerate.fallbackSummary,
  }
}

function authHdr(token: string | null) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function secToHM(s: number) {
  return { h: Math.floor(s / 3600), m: Math.floor((s % 3600) / 60) }
}

function hmToSec(h: number, m: number) {
  return h * 3600 + m * 60
}

function fmtTime(sec: number) {
  const { h, m } = secToHM(sec)
  return `${h}:${m.toString().padStart(2, '0')}`
}

function isUsableAssessment(value: unknown): value is RunningAssessmentOut {
  return (
    typeof value === 'object' &&
    value !== null &&
    Array.isArray((value as RunningAssessmentOut).estimated_marathon_time_range_sec)
  )
}

export default function PlanGeneratePage() {
  const router = useRouter()
  const [s, setS] = useState<WizardState>(INIT)
  const { t } = useI18n()

  function patch(p: Partial<WizardState>) {
    setS(prev => ({ ...prev, ...p }))
  }

  useEffect(() => { runStep1() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function runStep1() {
    const token = getToken()
    patch({ loading: true, error: null, step: 1 })
    let importResult: HistoryImportOut = {
      athlete_id: ATHLETE_ID,
      provider: 'coros',
      imported_count: 0,
      updated_count: 0,
      metric_count: 0,
      message: t.planGenerate.corosNotConnected,
    }
    let warning: string | null = null

    try {
      const importRes = await fetch(`/api/coros/import?athlete_id=${ATHLETE_ID}`, {
        method: 'POST',
        headers: authHdr(token),
        body: JSON.stringify({ device_type: 'coros' }),
      })
      if (importRes.ok) {
        importResult = await importRes.json()
      } else {
        warning = t.planGenerate.corosImportFailed
      }
    } catch {
      warning = t.planGenerate.corosImportFailed
    }

    let assessment: RunningAssessmentOut
    try {
      const assessRes = await fetch(
        `/api/athletes/${ATHLETE_ID}/assessment/run?target_time_sec=14400&plan_weeks=16&weekly_training_days=5`,
        { method: 'POST', headers: authHdr(token) },
      )
      if (!assessRes.ok) throw new Error(t.planGenerate.assessmentFailed)
      const parsedAssessment = await assessRes.json()
      if (!isUsableAssessment(parsedAssessment)) throw new Error(t.planGenerate.assessmentFailed)
      assessment = parsedAssessment
    } catch (e) {
      const message = e instanceof Error ? e.message : t.planGenerate.assessmentFailed
      warning = message
      assessment = fallbackAssessment(message, t)
    }

    let skills: SkillManifestOut[] = [DEFAULT_SKILL]
    try {
      const skillsRes = await fetch('/api/skills', { headers: authHdr(token) })
      if (!skillsRes.ok) throw new Error(t.planGenerate.skillsFailed)
      const loadedSkills: unknown = await skillsRes.json()
      skills = Array.isArray(loadedSkills) && loadedSkills.length > 0 ? loadedSkills : [DEFAULT_SKILL]
    } catch {
      warning = warning ?? t.planGenerate.skillsFailed
    }

    const range = assessment.estimated_marathon_time_range_sec
    const mid = range.length >= 2 ? Math.round((range[0] + range[1]) / 2) : 14400
    const { h, m } = secToHM(mid)

    patch({
      loading: false,
      step: 2,
      error: warning,
      importResult,
      assessment,
      skills,
      selectedSkill: skills[0]?.slug ?? 'marathon_st_default',
      targetH: h,
      targetM: m,
    })
  }

  async function generatePlan() {
    const token = getToken()
    patch({ loading: true, error: null, step: 4 })
    try {
      const res = await fetch('/api/marathon/plans/generate', {
        method: 'POST',
        headers: authHdr(token),
        body: JSON.stringify({
          athlete_id: ATHLETE_ID,
          target_time_sec: hmToSec(s.targetH, s.targetM),
          plan_weeks: s.planWeeks,
          skill_slug: s.selectedSkill,
          availability: {
            weekly_training_days: s.weeklyDays,
            preferred_long_run_weekday: 6,
          },
        }),
      })
      if (!res.ok) {
        const msg = await res.text().catch(() => t.planGenerate.generationFailed)
        throw new Error(msg)
      }
      const plan: GeneratedPlan = await res.json()
      patch({ loading: false, generatedPlan: plan, step: 5 })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : t.planGenerate.generationFailed, step: 3 })
    }
  }

  async function confirmAndSync() {
    if (!s.generatedPlan) return
    const token = getToken()
    patch({ loading: true, error: null })
    try {
      const cRes = await fetch(`/api/plans/${s.generatedPlan.id}/confirm`, {
        method: 'POST',
        headers: authHdr(token),
      })
      if (!cRes.ok) throw new Error(t.planGenerate.confirmFailed)

      const sRes = await fetch(`/api/plans/${s.generatedPlan.id}/sync/coros`, {
        method: 'POST',
        headers: authHdr(token),
      })
      const syncResult = sRes.ok ? await sRes.json() : { synced_count: 0, failed_count: 0 }
      patch({ loading: false, syncResult })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : t.planGenerate.syncFailed })
    }
  }

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--paper)', display: 'flex', flexDirection: 'column' }}>
      <div style={{
        padding: '16px 16px 12px',
        borderBottom: '1px solid var(--rule-soft)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <button
          onClick={() => router.back()}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: 22,
            color: 'var(--ink-faint)',
            padding: 0,
            lineHeight: 1,
          }}
        >
          ‹
        </button>
        <div className="hand" style={{ fontSize: 17, fontWeight: 700 }}>{t.planGenerate.title}</div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          {([1, 2, 3, 4, 5] as Step[]).map(n => (
            <div key={n} style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: n <= s.step ? 'var(--accent)' : 'var(--rule)',
            }} />
          ))}
        </div>
      </div>

      <div style={{
        flex: 1,
        padding: '24px 20px',
        maxWidth: 440,
        width: '100%',
        alignSelf: 'center',
        overflowY: 'auto',
      }}>
        {s.error && (
          <div style={{
            marginBottom: 16,
            padding: '10px 14px',
            borderRadius: 'var(--radius)',
            background: 'var(--accent-light)',
            border: '1px solid var(--accent)',
          }}>
            <span className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>{s.error}</span>
          </div>
        )}

        {s.step === 1 && <Step1Loading />}
        {s.step === 2 && s.assessment && s.importResult && (
          <Step2Status assessment={s.assessment} importResult={s.importResult} />
        )}
        {s.step === 3 && s.skills && (
          <Step3Config
            skills={s.skills}
            selectedSkill={s.selectedSkill}
            targetH={s.targetH}
            targetM={s.targetM}
            planWeeks={s.planWeeks}
            weeklyDays={s.weeklyDays}
            onChange={patch}
          />
        )}
        {s.step === 4 && <Step4Generating planWeeks={s.planWeeks} />}
        {s.step === 5 && s.generatedPlan && (
          <Step5Preview
            plan={s.generatedPlan}
            syncResult={s.syncResult}
            loading={s.loading}
            onConfirmSync={confirmAndSync}
            onDone={() => router.replace('/plan')}
          />
        )}
      </div>

      {!s.loading && (
        <div style={{ padding: '16px 20px 32px', maxWidth: 440, width: '100%', alignSelf: 'center' }}>
          {s.step === 2 && (
            <PrimaryBtn onClick={() => patch({ step: 3 })}>{t.planGenerate.setGoal} →</PrimaryBtn>
          )}
          {s.step === 3 && (
            <PrimaryBtn onClick={generatePlan}>{t.planGenerate.generatePlan} →</PrimaryBtn>
          )}
          {s.step === 5 && !s.syncResult && (
            <PrimaryBtn onClick={confirmAndSync} loading={s.loading}>
              {t.planGenerate.confirmAndSync} →
            </PrimaryBtn>
          )}
          {s.step === 5 && s.syncResult && (
            <PrimaryBtn onClick={() => router.replace('/plan')}>{t.planGenerate.viewPlan} →</PrimaryBtn>
          )}
        </div>
      )}
    </div>
  )
}

function Step1Loading() {
  const { t } = useI18n()
  return (
    <div style={{ textAlign: 'center', paddingTop: 60 }}>
      <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
        {t.planGenerate.analyzing}
      </div>
      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
        {t.planGenerate.analyzingText}
      </div>
    </div>
  )
}

function Step2Status({ assessment, importResult }: {
  assessment: RunningAssessmentOut
  importResult: HistoryImportOut
}) {
  const [lo, hi] = assessment.estimated_marathon_time_range_sec
  const { t } = useI18n()
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>{t.planGenerate.statusTitle}</div>
      <div className="hand text-faint" style={{ fontSize: 13, marginBottom: 20 }}>
        {t.planGenerate.basedOnHistory} {importResult.imported_count} {t.planGenerate.historyActivities}
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <StatBox label={t.planGenerate.score} value={`${assessment.overall_score}`} unit="/100" />
        <StatBox label={t.planGenerate.predictedFinish} value={fmtTime(lo)} unit={`- ${fmtTime(hi)}`} />
      </div>

      <div className="sk-card-soft" style={{ marginBottom: 16 }}>
        <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 4 }}>{t.planGenerate.assessmentConclusion}</div>
        <div className="hand" style={{ fontSize: 14, lineHeight: 1.6 }}>{assessment.summary}</div>
      </div>

      {assessment.limiting_factors.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 6 }}>{t.planGenerate.limiters}</div>
          {assessment.limiting_factors.map((factor, index) => (
            <div key={index} className="hand" style={{
              fontSize: 13,
              padding: '4px 0',
              borderBottom: '1px solid var(--rule-soft)',
            }}>
              · {factor}
            </div>
          ))}
        </div>
      )}

      {assessment.warnings.length > 0 && (
        <div style={{
          padding: '10px 14px',
          background: 'var(--accent-light)',
          border: '1px solid var(--accent)',
          borderRadius: 'var(--radius)',
        }}>
          {assessment.warnings.map((warning, index) => (
            <div key={index} className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>
              ⚠ {warning}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Step3Config({ skills, selectedSkill, targetH, targetM, planWeeks, weeklyDays, onChange }: {
  skills: SkillManifestOut[]
  selectedSkill: string
  targetH: number
  targetM: number
  planWeeks: number
  weeklyDays: number
  onChange: (p: Partial<WizardState>) => void
}) {
  const { t } = useI18n()
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>{t.planGenerate.setGoal}</div>

      <FormField label={t.planGenerate.targetTime}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            value={targetH}
            onChange={e => onChange({ targetH: Number(e.target.value) })}
            style={selectStyle}
            className="hand"
          >
            {[2, 3, 4, 5, 6].map(h => (
              <option key={h} value={h}>{h} {t.planGenerate.hours}</option>
            ))}
          </select>
          <select
            value={targetM}
            onChange={e => onChange({ targetM: Number(e.target.value) })}
            style={selectStyle}
            className="hand"
          >
            {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map(m => (
              <option key={m} value={m}>{m.toString().padStart(2, '0')} {t.planGenerate.minutesShort}</option>
            ))}
          </select>
        </div>
      </FormField>

      <FormField label={t.planGenerate.trainingWeeks}>
        <div style={{ display: 'flex', gap: 8 }}>
          {[12, 16, 20, 24].map(weeks => (
            <button
              key={weeks}
              onClick={() => onChange({ planWeeks: weeks })}
              className="hand"
              style={choiceButtonStyle(planWeeks === weeks)}
            >
              {weeks}{t.common.weeks}
            </button>
          ))}
        </div>
      </FormField>

      <FormField label={t.planGenerate.weeklyDays}>
        <div style={{ display: 'flex', gap: 8 }}>
          {[3, 4, 5, 6].map(days => (
            <button
              key={days}
              onClick={() => onChange({ weeklyDays: days })}
              className="hand"
              style={choiceButtonStyle(weeklyDays === days)}
            >
              {days}{t.planGenerate.daysShort}
            </button>
          ))}
        </div>
      </FormField>

      <FormField label={t.planGenerate.trainingSkill}>
        {skills.map(skill => (
          <div
            key={skill.slug}
            onClick={() => onChange({ selectedSkill: skill.slug })}
            style={{
              padding: '12px 14px',
              marginBottom: 10,
              borderRadius: 'var(--radius)',
              cursor: 'pointer',
              border: `1px solid ${selectedSkill === skill.slug ? 'var(--accent)' : 'var(--rule)'}`,
              background: selectedSkill === skill.slug ? 'var(--accent-light)' : 'var(--paper)',
            }}
          >
            <div className="hand" style={{ fontSize: 15, fontWeight: 700 }}>{skill.name}</div>
            <div className="hand text-faint" style={{ fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
              {skill.description}
            </div>
            {skill.tags.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {skill.tags.map(tag => (
                  <span key={tag} className="sk-pill" style={{ fontSize: 11 }}>{tag}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </FormField>
    </div>
  )
}

function Step4Generating({ planWeeks }: { planWeeks: number }) {
  const { t } = useI18n()
  return (
    <div style={{ textAlign: 'center', paddingTop: 60 }}>
      <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
        {t.planGenerate.generating}
      </div>
      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
        {t.planGenerate.generatingText} {planWeeks} {t.common.weeks}
      </div>
    </div>
  )
}

function Step5Preview({ plan, syncResult, loading, onConfirmSync, onDone }: {
  plan: GeneratedPlan
  syncResult: { synced_count: number; failed_count: number } | null
  loading: boolean
  onConfirmSync: () => void
  onDone: () => void
}) {
  const { t } = useI18n()
  void onDone
  if (syncResult) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 40 }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          {t.planGenerate.ready}
        </div>
        <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
          {syncResult.synced_count} {t.planGenerate.syncedToCoros}
          {syncResult.failed_count > 0 && `, ${syncResult.failed_count} ${t.planGenerate.syncFailures}`}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        {plan.title ?? t.planGenerate.defaultPlanTitle}
      </div>
      {plan.target_time_sec && (
        <div className="hand" style={{ fontSize: 14, color: 'var(--accent)', marginBottom: 16 }}>
          {t.planGenerate.target} sub-{fmtTime(plan.target_time_sec)}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
        <PreviewRow label={t.planGenerate.totalWeeks} value={`${plan.weeks} ${t.common.weeks}`} />
        {plan.start_date && <PreviewRow label={t.planGenerate.startDate} value={plan.start_date} />}
        {plan.race_date && <PreviewRow label={t.planGenerate.raceDate} value={plan.race_date} />}
      </div>

      <div className="hand text-faint" style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 8 }}>
        {t.planGenerate.confirmNotice}
      </div>
    </div>
  )
}

function StatBox({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div style={{
      flex: 1,
      padding: '12px 14px',
      background: 'var(--surface-low)',
      border: '1px solid var(--rule-soft)',
      borderRadius: 'var(--radius)',
      textAlign: 'center',
    }}>
      <div className="hand text-faint" style={{ fontSize: 11, marginBottom: 4 }}>{label}</div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {unit && <div className="hand text-faint" style={{ fontSize: 11, marginTop: 2 }}>{unit}</div>}
    </div>
  )
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      padding: '10px 0',
      borderBottom: '1px solid var(--rule-soft)',
    }}>
      <span className="hand text-faint" style={{ fontSize: 13 }}>{label}</span>
      <span className="hand" style={{ fontSize: 13 }}>{value}</span>
    </div>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 8 }}>{label}</div>
      {children}
    </div>
  )
}

function PrimaryBtn({ children, onClick, loading }: {
  children: React.ReactNode
  onClick: () => void
  loading?: boolean
}) {
  const { t } = useI18n()
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        width: '100%',
        padding: '14px',
        background: loading ? 'var(--rule)' : 'var(--accent)',
        color: '#050505',
        border: 'none',
        borderRadius: 'var(--radius)',
        fontFamily: 'var(--font-hand)',
        fontSize: 16,
        cursor: loading ? 'default' : 'pointer',
      }}
    >
      {loading ? t.planGenerate.processing : children}
    </button>
  )
}

function choiceButtonStyle(selected: boolean): React.CSSProperties {
  return {
    flex: 1,
    padding: '10px 4px',
    borderRadius: 'var(--radius)',
    fontSize: 13,
    cursor: 'pointer',
    border: `1px solid ${selected ? 'var(--accent)' : 'var(--rule)'}`,
    background: selected ? 'var(--accent)' : 'var(--paper)',
    color: selected ? '#050505' : 'var(--ink)',
  }
}

const selectStyle: React.CSSProperties = {
  flex: 1,
  padding: '10px 12px',
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  fontSize: 15,
  background: 'var(--paper)',
  color: 'var(--ink)',
  fontFamily: 'var(--font-hand)',
  outline: 'none',
}
