'use client'

import Link from 'next/link'
import { useActivityDetail } from '@/lib/hooks/useActivityDetail'
import { formatKm, formatPace, formatTime } from '@/lib/api/types'
import type { ActivityDetailSampleOut } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function ActivityDetailPage({ params }: { params: { id: string } }) {
  const { activity: detail, isLoading, error } = useActivityDetail(params.id)
  const { t } = useI18n()

  if (isLoading) {
    return <StateText text={t.common.loading} />
  }
  if (error) {
    return <StateText text={error.message} />
  }
  if (!detail) {
    return <StateText text={t.activityDetail.noDetail} />
  }

  const activity = detail.activity
  const gpsCount = detail.samples.filter((sample) => sample.latitude != null && sample.longitude != null).length
  const title = activity.feedback_text || activity.title || activity.discipline || t.activityDetail.title
  const distance = activity.distance_m ?? (activity.distance_km != null ? activity.distance_km * 1000 : null)
  const duration = activity.duration_sec ?? (activity.duration_min != null ? activity.duration_min * 60 : 0)

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--paper)' }}>
      <header style={{ padding: '14px 16px 12px', borderBottom: '1px solid var(--rule-soft)' }}>
        <Link href="/activities" className="annot text-faint" style={{ textDecoration: 'none', fontSize: 12 }}>
          {t.common.back}
        </Link>
        <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginTop: 8 }}>{title}</div>
        <div className="annot text-faint" style={{ fontSize: 12, marginTop: 3 }}>
          {new Date(activity.started_at).toLocaleString()}
        </div>
      </header>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', borderBottom: '1px solid var(--rule-soft)' }}>
        <Metric label={t.activityDetail.distance} value={`${formatKm(distance ?? null)} km`} />
        <Metric label={t.activityDetail.duration} value={formatTime(duration)} />
        <Metric label={t.activityDetail.avgPace} value={`${formatPace(activity.avg_pace_sec_per_km ?? null)}/km`} />
        <Metric label={t.activityDetail.avgHr} value={activity.avg_hr ? `${Math.round(activity.avg_hr)}` : '--'} />
      </section>

      <section style={{ padding: 16, borderBottom: '1px solid var(--rule-soft)' }}>
        <SectionTitle title={t.activityDetail.route} meta={`${gpsCount} ${t.activityDetail.gpsPoints}`} />
        <RouteChart samples={detail.samples} emptyText={t.activityDetail.noRoute} />
      </section>

      <section style={{ padding: 16, borderBottom: '1px solid var(--rule-soft)' }}>
        <SectionTitle title={t.activityDetail.metrics} meta={`${detail.returned_sample_count} ${t.activityDetail.samples}`} />
        <div style={{ display: 'grid', gap: 12 }}>
          <SeriesChart label={t.activityDetail.heartRate} samples={detail.samples} getValue={(sample) => sample.heart_rate} suffix="bpm" color="var(--accent)" />
          <SeriesChart label={t.activityDetail.pace} samples={detail.samples} getValue={(sample) => sample.pace_sec_per_km} formatValue={(value) => `${formatPace(value)}/km`} color="var(--ink)" invert />
          <SeriesChart label={t.activityDetail.elevation} samples={detail.samples} getValue={(sample) => sample.altitude_m} suffix="m" color="var(--ink-mid)" />
          <SeriesChart label={t.activityDetail.cadence} samples={detail.samples} getValue={(sample) => sample.cadence} suffix="spm" color="var(--ink-faint)" />
        </div>
      </section>

      <section style={{ padding: 16, borderBottom: '1px solid var(--rule-soft)' }}>
        <SectionTitle title={t.activityDetail.laps} meta={`${detail.laps.length}`} />
        <div style={{ borderTop: '1px solid var(--rule-soft)' }}>
          {detail.laps.map((lap) => (
            <div key={lap.lap_index} style={{ display: 'grid', gridTemplateColumns: '44px 1fr 1fr 1fr', gap: 8, padding: '10px 0', borderBottom: '1px solid var(--rule-soft)', alignItems: 'center' }}>
              <div className="hand" style={{ fontSize: 13 }}>{lap.lap_index + 1}</div>
              <div className="annot" style={{ fontSize: 12 }}>{formatKm(lap.distance_m)} km</div>
              <div className="annot" style={{ fontSize: 12 }}>{lap.duration_sec ? formatTime(lap.duration_sec) : '--'}</div>
              <div className="annot" style={{ fontSize: 12 }}>{lap.avg_speed_mps ? `${formatPace(1000 / lap.avg_speed_mps)}/km` : '--'}</div>
            </div>
          ))}
        </div>
      </section>

      <section style={{ padding: 16, borderBottom: '1px solid var(--rule-soft)' }}>
        <SectionTitle title={t.activityDetail.interpretation} />
        <div style={{ display: 'grid', gap: 8 }}>
          {Object.values(detail.interpretation).map((line) => (
            <p key={line} className="annot" style={{ margin: 0, fontSize: 13, lineHeight: 1.45, color: 'var(--ink-mid)' }}>{line}</p>
          ))}
        </div>
      </section>

      <section style={{ padding: '16px 16px 84px' }}>
        <SectionTitle title={t.activityDetail.source} />
        {detail.source ? (
          <div className="annot text-faint" style={{ fontSize: 12, lineHeight: 1.6 }}>
            <div>{t.activityDetail.file}: {detail.source.source_format.toUpperCase()} · {(detail.source.file_size_bytes / 1024).toFixed(1)} KB · {detail.source.stored_sample_count} {t.activityDetail.samples} · {detail.source.stored_lap_count} {t.activityDetail.laps}</div>
            <div>{t.activityDetail.parsed}: {detail.source.parsed_at ? new Date(detail.source.parsed_at).toLocaleString() : '--'}</div>
            <div>sha256: {detail.source.payload_hash.slice(0, 16)}...</div>
          </div>
        ) : (
          <div className="annot text-faint" style={{ fontSize: 12 }}>{t.activityDetail.noDetail}</div>
        )}
      </section>
    </div>
  )
}

function StateText({ text }: { text: string }) {
  return <div className="hand text-faint" style={{ padding: 32, textAlign: 'center' }}>{text}</div>
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: '12px 10px', borderRight: '1px solid var(--rule-soft)', minWidth: 0 }}>
      <div className="annot text-faint" style={{ fontSize: 10, marginBottom: 4 }}>{label}</div>
      <div className="hand" style={{ fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</div>
    </div>
  )
}

function SectionTitle({ title, meta }: { title: string; meta?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', marginBottom: 10 }}>
      <h2 className="hand" style={{ margin: 0, fontSize: 16 }}>{title}</h2>
      {meta && <span className="annot text-faint" style={{ fontSize: 11 }}>{meta}</span>}
    </div>
  )
}

function RouteChart({ samples, emptyText }: { samples: ActivityDetailSampleOut[]; emptyText: string }) {
  const points = samples.filter((sample) => sample.latitude != null && sample.longitude != null)
  if (points.length < 2) return <ChartEmpty text={emptyText} />
  const lat = points.map((p) => p.latitude as number)
  const lon = points.map((p) => p.longitude as number)
  const minLat = Math.min(...lat)
  const maxLat = Math.max(...lat)
  const minLon = Math.min(...lon)
  const maxLon = Math.max(...lon)
  const path = points.map((p) => {
    const x = scale(p.longitude as number, minLon, maxLon, 12, 388)
    const y = scale(p.latitude as number, maxLat, minLat, 12, 188)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg viewBox="0 0 400 200" role="img" aria-label="GPS route" style={{ width: '100%', height: 'auto', background: 'var(--paper-soft)', border: '1px solid var(--rule-soft)' }}>
      <polyline points={path} fill="none" stroke="var(--accent)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={path.split(' ')[0].split(',')[0]} cy={path.split(' ')[0].split(',')[1]} r="4" fill="var(--ink)" />
      <circle cx={path.split(' ').at(-1)?.split(',')[0]} cy={path.split(' ').at(-1)?.split(',')[1]} r="4" fill="var(--accent)" />
    </svg>
  )
}

function SeriesChart({
  label,
  samples,
  getValue,
  formatValue,
  suffix = '',
  color,
  invert = false,
}: {
  label: string
  samples: ActivityDetailSampleOut[]
  getValue: (sample: ActivityDetailSampleOut) => number | null
  formatValue?: (value: number) => string
  suffix?: string
  color: string
  invert?: boolean
}) {
  const values = samples.map((sample, index) => ({ index, value: getValue(sample) })).filter((item): item is { index: number; value: number } => item.value != null && Number.isFinite(item.value))
  if (values.length < 2) return null
  const nums = values.map((item) => item.value)
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const points = values.map((item, i) => {
    const x = scale(i, 0, values.length - 1, 4, 296)
    const y = invert ? scale(item.value, min, max, 16, 64) : scale(item.value, min, max, 64, 16)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const last = values[values.length - 1].value
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span className="annot" style={{ fontSize: 12 }}>{label}</span>
        <span className="annot text-faint" style={{ fontSize: 11 }}>{formatValue ? formatValue(last) : `${Math.round(last)}${suffix}`}</span>
      </div>
      <svg viewBox="0 0 300 80" style={{ width: '100%', height: 80, background: 'var(--paper-soft)', border: '1px solid var(--rule-soft)' }}>
        <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

function ChartEmpty({ text }: { text: string }) {
  return <div className="annot text-faint" style={{ padding: 24, border: '1px solid var(--rule-soft)', background: 'var(--paper-soft)', textAlign: 'center' }}>{text}</div>
}

function scale(value: number, fromMin: number, fromMax: number, toMin: number, toMax: number) {
  if (fromMax === fromMin) return (toMin + toMax) / 2
  return toMin + ((value - fromMin) / (fromMax - fromMin)) * (toMax - toMin)
}
