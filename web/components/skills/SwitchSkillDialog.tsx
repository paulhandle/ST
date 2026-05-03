import type { RegeneratePreviewOut } from '@/lib/api/types'

interface Props {
  skillName: string
  preview: RegeneratePreviewOut
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

export default function SwitchSkillDialog({ skillName, preview, onConfirm, onCancel, loading }: Props) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 300,
      background: 'rgba(26,26,26,0.4)',
      display: 'flex', alignItems: 'flex-end',
    }}>
      <div style={{
        width: '100%',
        background: 'var(--paper)',
        borderRadius: '16px 16px 0 0',
        padding: '24px 20px 32px',
      }} className="fade-in">
        <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>
          切换到「{skillName}」
        </div>

        {!preview.applicable ? (
          <div style={{
            padding: '12px 14px', marginBottom: 16,
            background: 'var(--accent-light)',
            border: '1.5px solid var(--accent)',
            borderRadius: 8,
          }}>
            <div className="hand" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 700, marginBottom: 4 }}>
              暂不适用
            </div>
            <div className="hand" style={{ fontSize: 13, color: 'var(--ink-mid)' }}>
              {preview.applicability_reason}
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
            <StatCell label="将重新生成" value={`${preview.regenerated_count} 课`} />
            <StatCell label="影响周数" value={`${preview.weeks_affected} 周`} />
            <StatCell label="已完成保留" value={`${preview.frozen_completed} 课`} />
            <StatCell label="已缺训保留" value={`${preview.frozen_missed} 课`} />
          </div>
        )}

        <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 20, lineHeight: 1.6 }}>
          切换后今日起的未来课程将按新方法论重新生成，已完成训练不受影响。
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onCancel}
            className="hand"
            style={{
              flex: 1, padding: '13px',
              border: '1.5px solid var(--rule)',
              borderRadius: 8, background: 'none',
              fontSize: 15, cursor: 'pointer',
            }}
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={!preview.applicable || loading}
            className="hand"
            style={{
              flex: 2, padding: '13px',
              background: preview.applicable ? 'var(--ink)' : 'var(--rule)',
              color: 'var(--paper)',
              border: 'none', borderRadius: 8,
              fontSize: 15,
              cursor: preview.applicable && !loading ? 'pointer' : 'default',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? '切换中…' : '确认切换'}
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
      background: 'var(--paper-warm)',
      borderRadius: 8,
      border: '1px solid var(--rule-soft)',
    }}>
      <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
      <div className="annot text-faint" style={{ fontSize: 11 }}>{label}</div>
    </div>
  )
}
