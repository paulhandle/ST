import type { WorkoutStepOut } from '@/lib/api/types'
import { formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  steps: WorkoutStepOut[]
}

export default function WorkoutSteps({ steps }: Props) {
  const { t } = useI18n()
  return (
    <div style={{ padding: '0 16px 16px' }}>
      <div className="hand" style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{t.workout.steps}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {steps.map((step, i) => (
          <StepRow key={i} step={step} />
        ))}
      </div>
    </div>
  )
}

function StepRow({ step }: { step: WorkoutStepOut }) {
  const { t } = useI18n()
  const label = step.step_type in t.workout.stepTypes
    ? t.workout.stepTypes[step.step_type as keyof typeof t.workout.stepTypes]
    : step.step_type
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
      background: 'var(--surface-low)',
      border: '1px solid var(--rule-soft)',
      borderRadius: 'var(--radius)',
    }}>
      <span className="hand" style={{
        width: 32, textAlign: 'center', fontSize: 12,
        color: step.step_type === 'work' ? 'var(--ink)' : 'var(--ink-faint)',
        fontWeight: step.step_type === 'work' ? 700 : 400,
      }}>
        {label}
      </span>

      <span className="hand" style={{ fontSize: 13 }}>
        {step.duration_min} {t.common.minutes}
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
