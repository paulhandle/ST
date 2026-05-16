'use client'

import { useEffect, useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { fetcher, postJson } from '@/lib/api/client'
import type { CorosStatusOut, DeviceAccountOut, ProviderSyncEventOut, ProviderSyncJobOut } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'
import { getAthleteId } from '@/lib/auth'
import { ArrowLeft, X } from 'lucide-react'

function suggestedDaysBack(lastImportAt: string | null | undefined): number {
  if (!lastImportAt) return 365
  const daysSince = Math.ceil((Date.now() - new Date(lastImportAt).getTime()) / (1000 * 86400))
  if (daysSince <= 30) return 30
  if (daysSince <= 90) return 90
  if (daysSince <= 365) return 365
  return 3650
}

function completedThroughLabel(message: string | null | undefined): string | null {
  if (!message) return null
  const match = message.match(/through\s+(\d{4}-\d{2}-\d{2})/i)
  return match ? match[1] : null
}

export default function CorosSettingsPage() {
  const { t, language } = useI18n()
  const c = t.settings.corosSettings
  const athleteId = getAthleteId()
  const { data: status, isLoading, mutate } = useSWR<CorosStatusOut>(
    `/api/coros/status?athlete_id=${athleteId}`,
    fetcher,
  )

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [startingSync, setStartingSync] = useState(false)
  const [showConnectForm, setShowConnectForm] = useState(false)
  const [syncDaysBack, setSyncDaysBack] = useState(365)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<number | null>(null)

  const { data: syncJob, mutate: mutateJob } = useSWR<ProviderSyncJobOut>(
    jobId ? `/api/coros/sync/jobs/${jobId}` : null,
    fetcher,
    { refreshInterval: latest => isActiveJob(latest) ? 1200 : 0 },
  )
  const { data: syncEvents, mutate: mutateEvents } = useSWR<ProviderSyncEventOut[]>(
    jobId ? `/api/coros/sync/jobs/${jobId}/events?limit=8` : null,
    fetcher,
    { refreshInterval: () => isActiveJob(syncJob) ? 1600 : 0 },
  )

  useEffect(() => {
    if (!syncJob) return
    if (syncJob.status === 'succeeded' || syncJob.status === 'failed') {
      mutate()
      mutateEvents()
    }
  }, [mutate, mutateEvents, syncJob])

  useEffect(() => {
    if (status?.connected) setShowConnectForm(false)
  }, [status?.connected])

  useEffect(() => {
    if (status?.last_import_at) {
      setSyncDaysBack(-1)
    }
  }, [status?.last_import_at])

  async function connectCoros() {
    setConnecting(true)
    setError(null)
    setMessage(null)
    try {
      const account = await postJson<DeviceAccountOut>('/api/coros/connect', {
        athlete_id: athleteId,
        username,
        password,
      })
      await mutate()
      if (account.auth_status !== 'connected') {
        setError(account.last_error || c.connectFailed)
        return
      }
      setPassword('')
      setShowConnectForm(false)
      setMessage(c.connectSuccess)
    } catch (e) {
      setError(formatError(e, c.connectFailed))
    } finally {
      setConnecting(false)
    }
  }

  async function startFullSync() {
    setStartingSync(true)
    setError(null)
    setMessage(null)
    const resolvedDaysBack = syncDaysBack === -1
      ? suggestedDaysBack(status?.last_import_at)
      : syncDaysBack
    try {
      const job = await postJson<ProviderSyncJobOut>('/api/coros/sync/start', {
        athlete_id: athleteId,
        days_back: resolvedDaysBack,
      })
      setJobId(job.id)
      setMessage(c.importSuccess)
      await mutateJob()
      await mutateEvents()
    } catch (e) {
      setError(formatError(e, c.importFailed))
    } finally {
      setStartingSync(false)
    }
  }

  const connected = status?.connected ?? false
  const showCredentials = !connected || showConnectForm
  const statusLabel = statusLabelFor(status, c)
  const statusColor = connected ? 'var(--ink)' : status?.auth_status === 'failed' ? 'var(--accent)' : 'var(--ink-faint)'
  const progress = syncJob ? progressFor(syncJob) : 0
  const syncTitle = syncTitleFor(syncJob, c)
  const events = syncEvents ? [...syncEvents].reverse() : []

  return (
    <div>
      <div style={{
        padding: '16px 16px 12px',
        borderBottom: '1px solid var(--rule-soft)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <Link
          href="/settings"
          aria-label={t.common.back}
          className="settings-back-link"
          style={{
            color: 'var(--ink)',
          }}
        >
          <ArrowLeft size={16} aria-hidden="true" />
          <span>{t.common.back}</span>
        </Link>
        <div>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>{c.title}</div>
          <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>{c.subtitle}</div>
        </div>
        <Link
          href="/settings"
          aria-label={t.common.close}
          style={{
            marginLeft: 'auto',
            color: 'var(--ink-faint)',
            textDecoration: 'none',
            display: 'inline-flex',
            width: 34,
            height: 34,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <X size={18} aria-hidden="true" />
        </Link>
      </div>

      <section style={{ borderBottom: '1px solid var(--rule-soft)' }}>
        <SectionLabel>{c.status}</SectionLabel>
        <InfoRow label={c.status} value={isLoading ? t.common.loading : statusLabel} valueColor={statusColor} />
        <InfoRow label={c.mode} value={status?.automation_mode === 'real' ? c.realMode : c.fakeMode} valueColor={status?.automation_mode === 'real' ? 'var(--ink)' : 'var(--accent)'}/>
        <InfoRow label={c.account} value={status?.username || c.never} />
        <InfoRow label={c.lastLogin} value={formatDateTime(status?.last_login_at, language, c.never)} />
        <InfoRow label={c.lastImport} value={formatDateTime(status?.last_import_at, language, c.never)} />
        <InfoRow label={c.lastSync} value={formatDateTime(status?.last_sync_at, language, c.never)} />
        {(() => {
          const through = completedThroughLabel(syncJob?.message)
          return through
            ? <InfoRow label={c.syncedThrough} value={through} />
            : null
        })()}
        {status?.last_error && <InfoRow label={c.failed} value={status.last_error} valueColor="var(--accent)" />}
      </section>

      <section style={{ borderBottom: '1px solid var(--rule-soft)', paddingBottom: 16 }}>
        <SectionLabel>{connected ? c.connectedTitle : c.connectTitle}</SectionLabel>
        {connected && !showCredentials && (
          <div style={{ padding: '0 16px', display: 'grid', gap: 12 }}>
            <div className="hand" style={{ fontSize: 14, lineHeight: 1.5 }}>
              {c.connectedSummary}
            </div>
            <button
              onClick={() => {
                setUsername(status?.username || '')
                setPassword('')
                setShowConnectForm(true)
              }}
              style={secondaryButtonStyle(true)}
            >
              {c.reconnect}
            </button>
          </div>
        )}
        {showCredentials && (
          <div style={{ padding: '0 16px', display: 'grid', gap: 12 }}>
            <Field label={c.username}>
              <input
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder={c.usernamePlaceholder}
                autoComplete="username"
                className="hand"
                style={inputStyle}
              />
            </Field>
            <Field label={c.password}>
              <input
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder={c.passwordPlaceholder}
                autoComplete="current-password"
                type="password"
                className="hand"
                style={inputStyle}
              />
            </Field>
            <div className="annot text-faint" style={{ fontSize: 12, lineHeight: 1.5 }}>{c.passwordNote}</div>
            <button
              onClick={connectCoros}
              disabled={!username.trim() || !password || connecting}
              style={primaryButtonStyle(Boolean(username.trim() && password) && !connecting)}
            >
              {connecting ? c.connecting : c.connect}
            </button>
          </div>
        )}
      </section>

      <section style={{ padding: '16px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 16, fontWeight: 700 }}>{syncTitle}</div>
        <div className="annot text-faint" style={{ fontSize: 12, lineHeight: 1.5, marginTop: 6 }}>
          {syncJob?.message || c.syncIdle}
        </div>
        <Field label={c.syncPeriod}>
          <select
            value={syncDaysBack}
            onChange={event => setSyncDaysBack(Number(event.target.value))}
            className="hand"
            style={{ ...inputStyle, marginTop: 12 }}
            disabled={startingSync || isActiveJob(syncJob)}
          >
            {status?.last_import_at && (
              <option value={-1}>
                {c.syncSinceLast} ({suggestedDaysBack(status.last_import_at)} {language === 'zh' ? '天' : 'days'})
              </option>
            )}
            <option value={30}>{c.sync30}</option>
            <option value={90}>{c.sync90}</option>
            <option value={365}>{c.sync365}</option>
            <option value={3650}>{c.syncAll}</option>
          </select>
        </Field>
        {syncJob && (
          <>
            <div
              aria-label={c.syncTitle}
              style={{ height: 8, background: 'var(--surface-low)', borderRadius: 4, marginTop: 14, overflow: 'hidden' }}
            >
              <div style={{ width: `${progress}%`, height: '100%', background: 'var(--accent)' }} />
            </div>
            <div className="hand" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              fontSize: 12,
              color: 'var(--ink-faint)',
              marginTop: 12,
            }}>
              <Stat label={c.importSummary} value={syncJob.imported_count} />
              <Stat label={c.updatedSummary} value={syncJob.updated_count} />
              <Stat label={c.metricsSummary} value={syncJob.metric_count} />
              <Stat label={c.rawSummary} value={syncJob.raw_record_count} />
              <Stat label={c.failedSummary} value={syncJob.failed_count} />
              <Stat label={syncJob.phase} value={`${syncJob.processed_count}/${syncJob.total_count || '...'}`} />
            </div>
          </>
        )}
        <button
          onClick={startFullSync}
          disabled={!connected || startingSync || isActiveJob(syncJob)}
          style={{ ...secondaryButtonStyle(connected && !startingSync && !isActiveJob(syncJob)), marginTop: 16 }}
        >
          {startingSync ? c.importing : c.importHistory}
        </button>
      </section>

      {events.length > 0 && (
        <section style={{ padding: '16px' }}>
          <SectionLabelInline>{c.syncEvents}</SectionLabelInline>
          <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
            {events.map(event => (
              <div key={event.id} className="hand" style={{ fontSize: 12, lineHeight: 1.5, color: event.level === 'error' ? 'var(--accent)' : 'var(--ink-faint)' }}>
                <span style={{ color: 'var(--ink)' }}>{event.phase}</span> · {event.message}
              </div>
            ))}
          </div>
        </section>
      )}

      {(message || error) && (
        <div style={{ padding: '0 16px 24px' }}>
          <div className="hand" style={{
            fontSize: 13,
            color: error ? 'var(--accent)' : 'var(--ink)',
            borderTop: '1px solid var(--rule-soft)',
            paddingTop: 12,
          }}>
            {error || message}
          </div>
        </div>
      )}
    </div>
  )
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div className="hand text-faint" style={{ fontSize: 12, padding: '14px 16px 6px', textTransform: 'uppercase', letterSpacing: 0.5 }}>
      {children}
    </div>
  )
}

function SectionLabelInline({ children }: { children: string }) {
  return (
    <div className="hand text-faint" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
      {children}
    </div>
  )
}

function InfoRow({ label, value, valueColor = 'var(--ink)' }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      gap: 16,
      padding: '12px 16px',
      borderTop: '1px solid var(--rule-soft)',
    }}>
      <div className="hand text-faint" style={{ fontSize: 13 }}>{label}</div>
      <div className="hand" style={{ fontSize: 13, color: valueColor, textAlign: 'right', overflowWrap: 'anywhere' }}>{value}</div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'grid', gap: 6 }}>
      <span className="hand text-faint" style={{ fontSize: 13 }}>{label}</span>
      {children}
    </label>
  )
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div style={{ border: '1px solid var(--rule-soft)', borderRadius: 'var(--radius)', padding: 8 }}>
      <div style={{ color: 'var(--ink)', fontWeight: 700 }}>{value}</div>
      <div>{label}</div>
    </div>
  )
}

function statusLabelFor(status: CorosStatusOut | undefined, c: ReturnType<typeof useI18n>['t']['settings']['corosSettings']) {
  if (!status) return c.disconnected
  if (status.connected) return c.connected
  if (status.auth_status === 'failed') return c.failed
  return c.disconnected
}

function syncTitleFor(job: ProviderSyncJobOut | undefined, c: ReturnType<typeof useI18n>['t']['settings']['corosSettings']) {
  if (!job) return c.syncTitle
  if (job.status === 'succeeded') return c.syncComplete
  if (job.status === 'failed') return c.syncFailed
  return c.syncRunning
}

function progressFor(job: ProviderSyncJobOut) {
  if (job.status === 'succeeded') return 100
  if (job.total_count > 0) return Math.max(5, Math.min(95, Math.round((job.processed_count / job.total_count) * 100)))
  if (job.status === 'running') return 12
  return 3
}

function isActiveJob(job: ProviderSyncJobOut | undefined) {
  return job?.status === 'queued' || job?.status === 'running'
}

function formatDateTime(value: string | null | undefined, language: 'en' | 'zh', fallback: string) {
  if (!value) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatError(error: unknown, fallback: string) {
  return error instanceof Error ? `${fallback}: ${error.message}` : fallback
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  height: 46,
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  background: 'var(--paper)',
  color: 'var(--ink)',
  padding: '0 12px',
  fontSize: 15,
  outline: 'none',
}

function primaryButtonStyle(enabled: boolean): React.CSSProperties {
  return {
    width: '100%',
    height: 48,
    border: '1px solid var(--accent)',
    borderRadius: 'var(--radius)',
    background: enabled ? 'var(--accent)' : 'var(--rule-soft)',
    color: enabled ? '#050505' : 'var(--ink-faint)',
    fontFamily: 'var(--font-hand)',
    fontSize: 15,
    cursor: enabled ? 'pointer' : 'not-allowed',
  }
}

function secondaryButtonStyle(enabled: boolean): React.CSSProperties {
  return {
    width: '100%',
    height: 48,
    border: '1px solid var(--rule)',
    borderRadius: 'var(--radius)',
    background: enabled ? 'var(--paper)' : 'var(--surface-low)',
    color: enabled ? 'var(--ink)' : 'var(--ink-faint)',
    fontFamily: 'var(--font-hand)',
    fontSize: 15,
    cursor: enabled ? 'pointer' : 'not-allowed',
  }
}
