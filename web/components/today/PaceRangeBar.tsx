import { formatPace } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  targetMin: number   // sec/km (slower end)
  targetMax: number   // sec/km (faster end)
  actualPace: number | null
}

export default function PaceRangeBar({ targetMin, targetMax, actualPace }: Props) {
  const { t } = useI18n()
  // targetMin > targetMax numerically (slower pace = higher sec/km)
  const [lo, hi] = targetMin > targetMax ? [targetMax, targetMin] : [targetMin, targetMax]
  const spread = hi - lo
  const padding = spread * 1.5

  const scale = (v: number) => {
    const total = (hi + padding) - (lo - padding)
    return ((v - (lo - padding)) / total) * 100
  }

  const inZone = actualPace ? actualPace >= lo && actualPace <= hi : null

  return (
    <div>
      <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 8 }}>{t.workout.paceRange}</div>

      <div style={{ position: 'relative', height: 32 }}>
        {/* track */}
        <div style={{
          position: 'absolute', top: '50%', left: 0, right: 0,
          height: 2, background: 'var(--rule-soft)', transform: 'translateY(-50%)',
          borderRadius: 1,
        }} />

        {/* target zone */}
        <div style={{
          position: 'absolute', top: '50%',
          left: `${scale(lo)}%`,
          width: `${scale(hi) - scale(lo)}%`,
          height: 8, background: 'var(--ink)',
          transform: 'translateY(-50%)',
          borderRadius: 2,
        }} />

        {/* actual pace marker */}
        {actualPace && (
          <div style={{
            position: 'absolute', top: '50%',
            left: `${scale(actualPace)}%`,
            width: 3, height: 20,
            background: inZone ? 'var(--ink)' : 'var(--accent)',
            transform: 'translate(-50%, -50%)',
            borderRadius: 1.5,
          }} />
        )}
      </div>

      {/* labels */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span className="annot text-faint" style={{ fontSize: 11 }}>
          {formatPace(lo)}/km {t.workout.fast}
        </span>
        <span className="annot text-faint" style={{ fontSize: 11 }}>
          {t.workout.slow} {formatPace(hi)}/km
        </span>
      </div>

      {actualPace && (
        <div className="hand" style={{
          fontSize: 13, marginTop: 8, textAlign: 'center',
          color: inZone ? 'var(--ink)' : 'var(--accent)',
        }}>
          {t.workout.actual} {formatPace(actualPace)}/km {inZone ? `✓ ${t.workout.inZone}` : `⚠ ${t.workout.outOfZone}`}
        </div>
      )}
    </div>
  )
}
