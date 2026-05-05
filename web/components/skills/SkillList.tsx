import Link from 'next/link'
import type { SkillManifestOut } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'

interface Props {
  skills: SkillManifestOut[]
  onSwitch: (slug: string) => void
}

export default function SkillList({ skills, onSwitch }: Props) {
  const { t } = useI18n()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {skills.map((s) => (
        <div
          key={s.slug}
          style={{
            padding: '14px 16px',
            border: s.is_active ? '1px solid var(--accent)' : '1px solid var(--rule)',
            borderRadius: 'var(--radius)',
            background: s.is_active ? 'var(--accent-light)' : 'var(--surface-low)',
          }}
        >
          <div className="between" style={{ marginBottom: 4 }}>
            <span className="hand" style={{ fontSize: 15, fontWeight: 700 }}>{s.name}</span>
            {s.is_active
              ? <span className="sk-pill sk-pill--filled" style={{ fontSize: 11 }}>{t.skills.current}</span>
              : (
                <button
                  onClick={() => onSwitch(s.slug)}
                  className="hand"
                  style={{
                    padding: '4px 12px',
                    border: '1px solid var(--accent)',
                    borderRadius: 'var(--radius)',
                    background: 'none',
                    color: 'var(--accent)',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  {t.skills.switch}
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
            {t.skills.viewMethodology} →
          </Link>
        </div>
      ))}
    </div>
  )
}
