import Link from 'next/link'
import type { SkillManifestOut } from '@/lib/api/types'

interface Props {
  skills: SkillManifestOut[]
  onSwitch: (slug: string) => void
}

export default function SkillList({ skills, onSwitch }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {skills.map((s) => (
        <div
          key={s.slug}
          style={{
            padding: '14px 16px',
            border: s.is_active ? '1.5px solid var(--ink)' : '1px solid var(--rule)',
            borderRadius: 10,
            background: 'var(--paper)',
          }}
        >
          <div className="between" style={{ marginBottom: 4 }}>
            <span className="hand" style={{ fontSize: 15, fontWeight: 700 }}>{s.name}</span>
            {s.is_active
              ? <span className="sk-pill sk-pill--filled" style={{ fontSize: 11 }}>当前</span>
              : (
                <button
                  onClick={() => onSwitch(s.slug)}
                  className="hand"
                  style={{
                    padding: '4px 12px',
                    border: '1.5px solid var(--ink)',
                    borderRadius: 999,
                    background: 'none',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  切换
                </button>
              )
            }
          </div>

          <div className="annot text-faint" style={{ fontSize: 12, marginBottom: 6 }}>
            {s.author && `${s.author} · `}v{s.version}
            {s.tags.length > 0 && ` · ${s.tags.join(', ')}`}
          </div>

          <div className="hand" style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--ink-mid)' }}>
            {s.description}
          </div>

          <Link
            href={`/skills/${s.slug}`}
            className="hand"
            style={{ fontSize: 12, color: 'var(--ink-faint)', display: 'inline-block', marginTop: 8, textDecoration: 'none' }}
          >
            查看方法论 →
          </Link>
        </div>
      ))}
    </div>
  )
}
