import { formatPace } from '@/lib/api/types'

interface Props {
  targetMin: number   // sec/km (slower end)
  targetMax: number   // sec/km (faster end)
  actualPace: number | null
}

export default function PaceRangeBar({ targetMin, targetMax, actualPace }: Props) {
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
      <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 8 }}>配速区间</div>

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
          {formatPace(lo)}/km 快
        </span>
        <span className="annot text-faint" style={{ fontSize: 11 }}>
          慢 {formatPace(hi)}/km
        </span>
      </div>

      {actualPace && (
        <div className="hand" style={{
          fontSize: 13, marginTop: 8, textAlign: 'center',
          color: inZone ? 'var(--ink)' : 'var(--accent)',
        }}>
          实际 {formatPace(actualPace)}/km {inZone ? '✓ 在区间内' : '⚠ 超出区间'}
        </div>
      )}
    </div>
  )
}
