import type { WorkoutStepOut } from '@/lib/api/types'
import { formatPace } from '@/lib/api/types'

interface Props {
  steps: WorkoutStepOut[]
}

const STEP_TYPE_LABEL: Record<string, string> = {
  warmup: '热身',
  work: '主课',
  rest: '间歇休',
  cooldown: '放松',
  easy: '轻松跑',
}

export default function WorkoutSteps({ steps }: Props) {
  return (
    <div style={{ padding: '0 16px 16px' }}>
      <div className="hand" style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>课程安排</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {steps.map((step, i) => (
          <StepRow key={i} step={step} />
        ))}
      </div>
    </div>
  )
}

function StepRow({ step }: { step: WorkoutStepOut }) {
  const label = STEP_TYPE_LABEL[step.step_type] ?? step.step_type
  const intensity = step.intensity_type === 'pace' && step.target_min && step.target_max
    ? `${formatPace(step.target_min)}–${formatPace(step.target_max)}/km`
    : step.intensity_type === 'hr' && step.target_min && step.target_max
    ? `${step.target_min}–${step.target_max} bpm`
    : step.rpe_min && step.rpe_max
    ? `RPE ${step.rpe_min}–${step.rpe_max}`
    : null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px',
      background: 'var(--paper)',
      border: '1px solid var(--rule-soft)',
      borderRadius: 6,
    }}>
      <span className="hand" style={{
        width: 32, textAlign: 'center', fontSize: 12,
        color: step.step_type === 'work' ? 'var(--ink)' : 'var(--ink-faint)',
        fontWeight: step.step_type === 'work' ? 700 : 400,
      }}>
        {label}
      </span>

      <span className="hand" style={{ fontSize: 13 }}>
        {step.duration_min} 分钟
        {step.distance_m ? ` · ${(step.distance_m / 1000).toFixed(1)} km` : ''}
      </span>

      {intensity && (
        <span className="annot text-faint" style={{ fontSize: 12, marginLeft: 'auto' }}>
          {intensity}
        </span>
      )}
    </div>
  )
}
