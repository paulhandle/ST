'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { useRouter } from 'next/navigation'
import { fetcher, postJson } from '@/lib/api/client'
import type { CorosStatusOut, DeviceAccountOut, HistoryImportOut } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

const ATHLETE_ID = 1

export default function CorosSettingsPage() {
  const router = useRouter()
  const { t, language } = useI18n()
  const c = t.settings.corosSettings
  const { data: status, isLoading, mutate } = useSWR<CorosStatusOut>(
    `/api/coros/status?athlete_id=${ATHLETE_ID}`,
    fetcher,
  )

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [importResult, setImportResult] = useState<HistoryImportOut | null>(null)

  async function connectCoros() {
    setConnecting(true)
    setError(null)
    setMessage(null)
    setImportResult(null)
    try {
      const account = await postJson<DeviceAccountOut>('/api/coros/connect', {
        athlete_id: ATHLETE_ID,
        username,
        password,
      })
      await mutate()
      if (account.auth_status !== 'connected') {
        setError(account.last_error || c.connectFailed)
        return
      }
      setPassword('')
      setMessage(c.connectSuccess)
    } catch (e) {
      setError(formatError(e, c.connectFailed))
    } finally {
      setConnecting(false)
    }
  }

  async function importHistory() {
    setImporting(true)
    setError(null)
    setMessage(null)
    setImportResult(null)
    try {
      const result = await postJson<HistoryImportOut>(
        `/api/coros/import?athlete_id=${ATHLETE_ID}`,
        { device_type: 'coros' },
      )
      setImportResult(result)
      setMessage(c.importSuccess)
      await mutate()
    } catch (e) {
      setError(formatError(e, c.importFailed))
    } finally {
      setImporting(false)
    }
  }

  const connected = status?.connected ?? false
  const statusLabel = statusLabelFor(status, c)
  const statusColor = connected ? 'var(--ink)' : status?.auth_status === 'failed' ? 'var(--accent)' : 'var(--ink-faint)'

  return (
    <div>
      <div style={{
        padding: '16px 16px 12px',
        borderBottom: '1px solid var(--rule-soft)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <button
          onClick={() => router.back()}
          aria-label={t.common.back}
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
        <div>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>{c.title}</div>
          <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>{c.subtitle}</div>
        </div>
      </div>

      <section style={{ borderBottom: '1px solid var(--rule-soft)' }}>
        <SectionLabel>{c.status}</SectionLabel>
        <InfoRow label={c.status} value={isLoading ? t.common.loading : statusLabel} valueColor={statusColor} />
        <InfoRow label={c.account} value={status?.username || c.never} />
        <InfoRow label={c.lastLogin} value={formatDateTime(status?.last_login_at, language, c.never)} />
        <InfoRow label={c.lastImport} value={formatDateTime(status?.last_import_at, language, c.never)} />
        <InfoRow label={c.lastSync} value={formatDateTime(status?.last_sync_at, language, c.never)} />
        {status?.last_error && <InfoRow label={c.failed} value={status.last_error} valueColor="var(--accent)" />}
      </section>

      <section style={{ borderBottom: '1px solid var(--rule-soft)', paddingBottom: 16 }}>
        <SectionLabel>{c.connectTitle}</SectionLabel>
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
      </section>

      <section style={{ padding: '16px' }}>
        <button
          onClick={importHistory}
          disabled={!connected || importing}
          style={secondaryButtonStyle(connected && !importing)}
        >
          {importing ? c.importing : c.importHistory}
        </button>
        {importResult && (
          <div className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)', marginTop: 12, lineHeight: 1.6 }}>
            {c.importSummary} {importResult.imported_count} · {c.updatedSummary} {importResult.updated_count} · {c.metricsSummary} {importResult.metric_count}
          </div>
        )}
      </section>

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

function statusLabelFor(status: CorosStatusOut | undefined, c: ReturnType<typeof useI18n>['t']['settings']['corosSettings']) {
  if (!status) return c.disconnected
  if (status.connected) return c.connected
  if (status.auth_status === 'failed') return c.failed
  return c.disconnected
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
