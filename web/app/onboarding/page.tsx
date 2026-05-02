'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from '@/lib/auth'

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

const WEEKDAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']

/* ── Page ───────────────────────────────────────────────────────────── */

export default function OnboardingPage() {
  const router = useRouter()
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
          name: '我',
          sport: 'marathon',
          level: state.experienceLevel === 'none' ? 'beginner' : state.experienceLevel,
          weekly_training_days: state.weeklyDays,
        }),
      })
      if (!athleteRes.ok) throw new Error('创建运动档案失败')

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
            description: state.targetTime ? `sub-${state.targetTime}` : '完赛',
          }),
        })
      }

      router.replace('/dashboard')
    } catch (e) {
      setError(e instanceof Error ? e.message : '出错了，请重试')
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
              background: s <= step ? 'var(--ink)' : 'var(--rule-soft)',
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
                background: 'var(--ink)', color: 'var(--paper)',
                border: 'none', borderRadius: 8,
                fontFamily: 'var(--font-hand)', fontSize: 16, cursor: 'pointer',
              }}
            >
              下一步
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
                跳过，暂不连接 COROS
              </button>
            )}
          </>
        ) : (
          <button
            onClick={finish}
            disabled={loading}
            style={{
              width: '100%', padding: '14px',
              background: 'var(--ink)', color: 'var(--paper)',
              border: 'none', borderRadius: 8,
              fontFamily: 'var(--font-hand)', fontSize: 16,
              cursor: loading ? 'default' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? '创建中…' : '开始训练 →'}
          </button>
        )}
      </div>
    </div>
  )
}

/* ── Step components ────────────────────────────────────────────────── */

function StepCoros({ state, update }: { state: OnboardingState; update: (p: Partial<OnboardingState>) => void }) {
  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>连接 COROS</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        导入你的历史训练记录，帮助我们更好地了解你的状态。
      </div>

      <Field label="COROS 账号（手机号或邮箱）">
        <input
          type="text"
          placeholder="COROS 账号"
          value={state.corosUsername}
          onChange={e => update({ corosUsername: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <Field label="COROS 密码">
        <input
          type="password"
          placeholder="密码"
          value={state.corosPassword}
          onChange={e => update({ corosPassword: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <div className="hand text-faint" style={{ fontSize: 11, marginTop: 8 }}>
        密码仅用于 COROS 数据同步，加密存储，不会分享给第三方。
      </div>
    </div>
  )
}

function StepGoal({ state, update }: { state: OnboardingState; update: (p: Partial<OnboardingState>) => void }) {
  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>设定目标</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        你想在什么时候完成马拉松？
      </div>

      <Field label="目标比赛日期">
        <input
          type="date"
          value={state.targetRaceDate}
          onChange={e => update({ targetRaceDate: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <Field label="目标完赛时间（选填）">
        <input
          type="text"
          placeholder="例如 4:00（小时:分钟），留空表示完赛"
          value={state.targetTime}
          onChange={e => update({ targetTime: e.target.value })}
          style={inputStyle}
          className="hand"
        />
      </Field>

      <Field label="跑步经验">
        <div style={{ display: 'flex', gap: 8 }}>
          {([
            ['none', '零基础'],
            ['beginner', '跑过但不规律'],
            ['intermediate', '有训练基础'],
          ] as const).map(([val, label]) => (
            <button
              key={val}
              onClick={() => update({ experienceLevel: val })}
              className="hand"
              style={{
                flex: 1, padding: '10px 4px',
                border: `1.5px solid ${state.experienceLevel === val ? 'var(--ink)' : 'var(--rule)'}`,
                borderRadius: 8,
                background: state.experienceLevel === val ? 'var(--ink)' : 'var(--paper)',
                color: state.experienceLevel === val ? 'var(--paper)' : 'var(--ink)',
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
  function toggleDay(d: number) {
    const cur = state.selectedWeekdays
    const next = cur.includes(d) ? cur.filter(x => x !== d) : [...cur, d].sort()
    update({ selectedWeekdays: next, weeklyDays: next.length })
  }

  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>训练安排</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        选择你通常可以训练的日子。
      </div>

      <div className="hand" style={{ fontSize: 13, marginBottom: 12 }}>每周训练日</div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 24 }}>
        {WEEKDAY_LABELS.map((label, i) => {
          const selected = state.selectedWeekdays.includes(i)
          return (
            <button
              key={i}
              onClick={() => toggleDay(i)}
              className="hand"
              style={{
                flex: 1, padding: '10px 0',
                border: `1.5px solid ${selected ? 'var(--ink)' : 'var(--rule)'}`,
                borderRadius: 8,
                background: selected ? 'var(--ink)' : 'var(--paper)',
                color: selected ? 'var(--paper)' : 'var(--ink)',
                fontSize: 13, cursor: 'pointer',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      <div className="hand text-faint" style={{ fontSize: 13 }}>
        已选 {state.selectedWeekdays.length} 天 / 周
      </div>
    </div>
  )
}

function StepConfirm({ state }: { state: OnboardingState }) {
  return (
    <div>
      <div className="hand" style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>确认一下</div>
      <div className="hand text-faint" style={{ fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>
        我们根据这些信息为你生成初始训练计划。
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <ConfirmRow label="COROS" value={state.corosSkipped ? '暂不连接' : (state.corosUsername || '—')} />
        <ConfirmRow label="目标比赛" value={state.targetRaceDate || '未设定'} />
        <ConfirmRow label="完赛目标" value={state.targetTime ? `sub-${state.targetTime}` : '完赛'} />
        <ConfirmRow
          label="训练日"
          value={state.selectedWeekdays.map(d => ['一','二','三','四','五','六','日'][d]).join(' ')}
        />
        <ConfirmRow
          label="经验"
          value={state.experienceLevel === 'none' ? '零基础' : state.experienceLevel === 'beginner' ? '有跑步经验' : '有训练基础'}
        />
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
  border: '1.5px solid var(--rule)',
  borderRadius: 8,
  fontSize: 15,
  background: 'var(--paper)',
  color: 'var(--ink)',
  fontFamily: 'var(--font-hand)',
  outline: 'none',
  boxSizing: 'border-box',
}
