'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from '@/lib/auth'
import type { RunningAssessmentOut, HistoryImportOut, SkillManifestOut } from '@/lib/api/types'

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
  step: 1, loading: true, error: null,
  importResult: null, assessment: null, skills: null,
  selectedSkill: 'marathon_st_default',
  targetH: 4, targetM: 0,
  planWeeks: 16, weeklyDays: 5,
  generatedPlan: null, syncResult: null,
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

function hmToSec(h: number, m: number) { return h * 3600 + m * 60 }

function fmtTime(sec: number) {
  const { h, m } = secToHM(sec)
  return `${h}:${m.toString().padStart(2, '0')}`
}

export default function PlanGeneratePage() {
  const router = useRouter()
  const [s, setS] = useState<WizardState>(INIT)

  function patch(p: Partial<WizardState>) { setS(prev => ({ ...prev, ...p })) }

  useEffect(() => { runStep1() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function runStep1() {
    const token = getToken()
    patch({ loading: true, error: null })
    try {
      let importResult: HistoryImportOut = {
        athlete_id: ATHLETE_ID, provider: 'coros',
        imported_count: 0, updated_count: 0, metric_count: 0, message: '未连接 COROS',
      }
      const importRes = await fetch(`/api/coros/import?athlete_id=${ATHLETE_ID}`, {
        method: 'POST', headers: authHdr(token),
        body: JSON.stringify({ device_type: 'coros' }),
      })
      if (importRes.ok) importResult = await importRes.json()

      const assessRes = await fetch(
        `/api/athletes/${ATHLETE_ID}/assessment/run?target_time_sec=14400&plan_weeks=16&weekly_training_days=5`,
        { method: 'POST', headers: authHdr(token) },
      )
      if (!assessRes.ok) throw new Error('能力评估失败，请确认已有运动记录')
      const assessment: RunningAssessmentOut = await assessRes.json()

      const skillsRes = await fetch('/api/skills', { headers: authHdr(token) })
      if (!skillsRes.ok) throw new Error('获取训练方案失败')
      const skills: SkillManifestOut[] = await skillsRes.json()

      const range = assessment.estimated_marathon_time_range_sec
      const mid = range.length >= 2 ? Math.round((range[0] + range[1]) / 2) : 14400
      const { h, m } = secToHM(mid)

      patch({
        loading: false, step: 2,
        importResult, assessment, skills,
        selectedSkill: skills[0]?.slug ?? 'marathon_st_default',
        targetH: h, targetM: m,
      })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : '出错了，请重试' })
    }
  }

  async function generatePlan() {
    const token = getToken()
    patch({ loading: true, error: null, step: 4 })
    try {
      const res = await fetch('/api/marathon/plans/generate', {
        method: 'POST', headers: authHdr(token),
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
        const msg = await res.text().catch(() => '生成失败')
        throw new Error(msg)
      }
      const plan: GeneratedPlan = await res.json()
      patch({ loading: false, generatedPlan: plan, step: 5 })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : '生成失败', step: 3 })
    }
  }

  async function confirmAndSync() {
    if (!s.generatedPlan) return
    const token = getToken()
    patch({ loading: true, error: null })
    try {
      const cRes = await fetch(`/api/plans/${s.generatedPlan.id}/confirm`, {
        method: 'POST', headers: authHdr(token),
      })
      if (!cRes.ok) throw new Error('确认计划失败')

      const sRes = await fetch(`/api/plans/${s.generatedPlan.id}/sync/coros`, {
        method: 'POST', headers: authHdr(token),
      })
      const syncResult = sRes.ok ? await sRes.json() : { synced_count: 0, failed_count: 0 }
      patch({ loading: false, syncResult })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : '同步失败' })
    }
  }

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--paper)', display: 'flex',
                  flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--rule-soft)',
                    display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          onClick={() => router.back()}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 22, color: 'var(--ink-faint)', padding: 0, lineHeight: 1 }}
        >‹</button>
        <div className="hand" style={{ fontSize: 17, fontWeight: 700 }}>生成训练计划</div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          {([1, 2, 3, 4, 5] as Step[]).map(n => (
            <div key={n} style={{
              width: 6, height: 6, borderRadius: '50%',
              background: n <= s.step ? 'var(--ink)' : 'var(--rule)',
            }} />
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: '24px 20px', maxWidth: 440, width: '100%',
                    alignSelf: 'center', overflowY: 'auto' }}>
        {s.error && (
          <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 8,
                        background: 'var(--accent-light)', border: '1.5px solid var(--accent)' }}>
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
            targetH={s.targetH} targetM={s.targetM}
            planWeeks={s.planWeeks} weeklyDays={s.weeklyDays}
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

      {/* Footer CTA */}
      {!s.loading && (
        <div style={{ padding: '16px 20px 32px', maxWidth: 440, width: '100%', alignSelf: 'center' }}>
          {s.step === 2 && (
            <PrimaryBtn onClick={() => patch({ step: 3 })}>设定目标 →</PrimaryBtn>
          )}
          {s.step === 3 && (
            <PrimaryBtn onClick={generatePlan}>生成计划 →</PrimaryBtn>
          )}
          {s.step === 5 && !s.syncResult && (
            <PrimaryBtn onClick={confirmAndSync} loading={s.loading}>
              确认并同步到 COROS →
            </PrimaryBtn>
          )}
          {s.step === 5 && s.syncResult && (
            <PrimaryBtn onClick={() => router.replace('/plan')}>查看计划 →</PrimaryBtn>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Step components ───────────────────────────────────── */

function Step1Loading() {
  return (
    <div style={{ textAlign: 'center', paddingTop: 60 }}>
      <div style={{ fontSize: 40, marginBottom: 16 }}>⚙️</div>
      <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
        分析中…
      </div>
      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
        正在导入 COROS 数据并评估你的跑步能力
      </div>
    </div>
  )
}

function Step2Status({ assessment, importResult }: {
  assessment: RunningAssessmentOut
  importResult: HistoryImportOut
}) {
  const [lo, hi] = assessment.estimated_marathon_time_range_sec
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>你的状态</div>
      <div className="hand text-faint" style={{ fontSize: 13, marginBottom: 20 }}>
        基于 {importResult.imported_count} 条历史活动
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <StatBox label="综合评分" value={`${assessment.overall_score}`} unit="/100" />
        <StatBox
          label="预测完赛"
          value={fmtTime(lo)}
          unit={`– ${fmtTime(hi)}`}
        />
      </div>

      <div className="sk-card-soft" style={{ marginBottom: 16 }}>
        <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 4 }}>评估结论</div>
        <div className="hand" style={{ fontSize: 14, lineHeight: 1.6 }}>{assessment.summary}</div>
      </div>

      {assessment.limiting_factors.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 6 }}>限制因素</div>
          {assessment.limiting_factors.map((f, i) => (
            <div key={i} className="hand" style={{ fontSize: 13, padding: '4px 0',
                 borderBottom: '1px solid var(--rule-soft)' }}>
              · {f}
            </div>
          ))}
        </div>
      )}

      {assessment.warnings.length > 0 && (
        <div style={{ padding: '10px 14px', background: 'var(--accent-light)',
                      border: '1.5px solid var(--accent)', borderRadius: 8 }}>
          {assessment.warnings.map((w, i) => (
            <div key={i} className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>⚠ {w}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function Step3Config({ skills, selectedSkill, targetH, targetM, planWeeks, weeklyDays, onChange }: {
  skills: SkillManifestOut[]
  selectedSkill: string
  targetH: number; targetM: number
  planWeeks: number; weeklyDays: number
  onChange: (p: Partial<WizardState>) => void
}) {
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>设定目标</div>

      <FormField label="目标完赛时间">
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            value={targetH}
            onChange={e => onChange({ targetH: Number(e.target.value) })}
            style={selectStyle}
            className="hand"
          >
            {[2, 3, 4, 5, 6].map(h => (
              <option key={h} value={h}>{h} 小时</option>
            ))}
          </select>
          <select
            value={targetM}
            onChange={e => onChange({ targetM: Number(e.target.value) })}
            style={selectStyle}
            className="hand"
          >
            {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map(m => (
              <option key={m} value={m}>{m.toString().padStart(2, '0')} 分</option>
            ))}
          </select>
        </div>
      </FormField>

      <FormField label="训练周数">
        <div style={{ display: 'flex', gap: 8 }}>
          {[12, 16, 20, 24].map(w => (
            <button key={w} onClick={() => onChange({ planWeeks: w })} className="hand"
              style={{
                flex: 1, padding: '10px 4px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                border: `1.5px solid ${planWeeks === w ? 'var(--ink)' : 'var(--rule)'}`,
                background: planWeeks === w ? 'var(--ink)' : 'var(--paper)',
                color: planWeeks === w ? 'var(--paper)' : 'var(--ink)',
              }}>
              {w}周
            </button>
          ))}
        </div>
      </FormField>

      <FormField label="每周训练天数">
        <div style={{ display: 'flex', gap: 8 }}>
          {[3, 4, 5, 6].map(d => (
            <button key={d} onClick={() => onChange({ weeklyDays: d })} className="hand"
              style={{
                flex: 1, padding: '10px 4px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                border: `1.5px solid ${weeklyDays === d ? 'var(--ink)' : 'var(--rule)'}`,
                background: weeklyDays === d ? 'var(--ink)' : 'var(--paper)',
                color: weeklyDays === d ? 'var(--paper)' : 'var(--ink)',
              }}>
              {d}天
            </button>
          ))}
        </div>
      </FormField>

      <FormField label="训练方案">
        {skills.map(skill => (
          <div key={skill.slug} onClick={() => onChange({ selectedSkill: skill.slug })}
            style={{
              padding: '12px 14px', marginBottom: 10, borderRadius: 8, cursor: 'pointer',
              border: `1.5px solid ${selectedSkill === skill.slug ? 'var(--ink)' : 'var(--rule)'}`,
              background: selectedSkill === skill.slug ? 'var(--paper-warm)' : 'var(--paper)',
            }}>
            <div className="hand" style={{ fontSize: 15, fontWeight: 700 }}>{skill.name}</div>
            <div className="hand text-faint" style={{ fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
              {skill.description}
            </div>
            {skill.tags.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {skill.tags.map(t => (
                  <span key={t} className="sk-pill" style={{ fontSize: 11 }}>{t}</span>
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
  return (
    <div style={{ textAlign: 'center', paddingTop: 60 }}>
      <div style={{ fontSize: 40, marginBottom: 16 }}>🏗️</div>
      <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
        生成中…
      </div>
      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
        正在为你生成 {planWeeks} 周训练计划
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
  void onDone
  if (syncResult) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 40 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          计划已就绪
        </div>
        <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
          已同步 {syncResult.synced_count} 个训练到 COROS 手表
          {syncResult.failed_count > 0 && `，${syncResult.failed_count} 个失败`}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        {plan.title ?? '训练计划'}
      </div>
      {plan.target_time_sec && (
        <div className="hand" style={{ fontSize: 14, color: 'var(--accent)', marginBottom: 16 }}>
          目标 sub-{fmtTime(plan.target_time_sec)}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
        <PreviewRow label="总周数" value={`${plan.weeks} 周`} />
        {plan.start_date && (
          <PreviewRow label="开始日期" value={plan.start_date} />
        )}
        {plan.race_date && (
          <PreviewRow label="比赛日期" value={plan.race_date} />
        )}
      </div>

      <div className="hand text-faint" style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 8 }}>
        确认后计划将同步到你的 COROS 手表，开始后将每周生成调整建议。
      </div>
    </div>
  )
}

/* ── UI helpers ──────────────────────────────────────────── */

function StatBox({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div style={{ flex: 1, padding: '12px 14px', background: 'var(--paper-warm)',
                  borderRadius: 8, textAlign: 'center' }}>
      <div className="hand text-faint" style={{ fontSize: 11, marginBottom: 4 }}>{label}</div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {unit && <div className="hand text-faint" style={{ fontSize: 11, marginTop: 2 }}>{unit}</div>}
    </div>
  )
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between',
                  padding: '10px 0', borderBottom: '1px solid var(--rule-soft)' }}>
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
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        width: '100%', padding: '14px',
        background: loading ? 'var(--rule)' : 'var(--ink)',
        color: 'var(--paper)', border: 'none', borderRadius: 8,
        fontFamily: 'var(--font-hand)', fontSize: 16,
        cursor: loading ? 'default' : 'pointer',
      }}
    >
      {loading ? '处理中…' : children}
    </button>
  )
}

const selectStyle: React.CSSProperties = {
  flex: 1, padding: '10px 12px',
  border: '1.5px solid var(--rule)', borderRadius: 8,
  fontSize: 15, background: 'var(--paper)', color: 'var(--ink)',
  fontFamily: 'var(--font-hand)', outline: 'none',
}
