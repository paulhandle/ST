import type { RegeneratePreviewOut } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  skillName: string
  preview: RegeneratePreviewOut
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

export default function SwitchSkillDialog({ skillName, preview, onConfirm, onCancel, loading }: Props) {
  const { t } = useI18n()
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 300,
      background: 'rgba(0,0,0,0.72)',
      display: 'flex', alignItems: 'flex-end',
    }}>
      <div style={{
        width: '100%',
        background: 'var(--surface-low)',
        border: '1px solid var(--rule)',
        borderRadius: 'var(--radius) var(--radius) 0 0',
        padding: '24px 20px 32px',
      }} className="fade-in">
        <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>
          {t.skills.switchTo} "{skillName}"
        </div>

        {!preview.applicable ? (
          <div style={{
            padding: '12px 14px', marginBottom: 16,
            background: 'var(--accent-light)',
            border: '1px solid var(--accent)',
            borderRadius: 'var(--radius)',
          }}>
            <div className="hand" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 700, marginBottom: 4 }}>
              {t.skills.notApplicable}
            </div>
            <div className="hand" style={{ fontSize: 13, color: 'var(--ink-mid)' }}>
              {preview.applicability_reason}
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
            <StatCell label={t.skills.regenerated} value={`${preview.regenerated_count} ${t.skills.sessions}`} />
            <StatCell label={t.skills.weeksAffected} value={`${preview.weeks_affected} ${t.common.weeks}`} />
            <StatCell label={t.skills.frozenCompleted} value={`${preview.frozen_completed} ${t.skills.sessions}`} />
            <StatCell label={t.skills.frozenMissed} value={`${preview.frozen_missed} ${t.skills.sessions}`} />
          </div>
        )}

        <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 20, lineHeight: 1.6 }}>
          {t.skills.switchNotice}
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onCancel}
            className="hand"
            style={{
              flex: 1, padding: '13px',
              border: '1px solid var(--rule)',
              borderRadius: 'var(--radius)', background: 'none',
              color: 'var(--ink)',
              fontSize: 15, cursor: 'pointer',
            }}
          >
            {t.skills.cancel}
          </button>
          <button
            onClick={onConfirm}
            disabled={!preview.applicable || loading}
            className="hand"
            style={{
              flex: 2, padding: '13px',
              background: preview.applicable ? 'var(--accent)' : 'var(--rule)',
              color: '#050505',
              border: 'none', borderRadius: 'var(--radius)',
              fontSize: 15,
              cursor: preview.applicable && !loading ? 'pointer' : 'default',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? t.skills.switching : t.skills.confirmSwitch}
          </button>
        </div>
      </div>
    </div>
  )
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      padding: '10px 12px',
      background: 'var(--surface)',
      borderRadius: 'var(--radius)',
      border: '1px solid var(--rule-soft)',
    }}>
      <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
      <div className="annot text-faint" style={{ fontSize: 11 }}>{label}</div>
    </div>
  )
}
