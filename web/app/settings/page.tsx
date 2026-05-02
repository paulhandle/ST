'use client'

import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { SkillManifestOut } from '@/lib/api/types'

export default function SettingsPage() {
  const { data: skills } = useSWR<SkillManifestOut[]>('/api/skills', fetcher)

  return (
    <div style={{ padding: '16px' }}>
      <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>设置</div>

      <div className="hand" style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>训练方法论</div>

      {skills?.map((s) => (
        <div
          key={s.slug}
          style={{
            padding: '12px 14px',
            border: s.is_active ? '1.5px solid var(--ink)' : '1px solid var(--rule)',
            borderRadius: 8,
            marginBottom: 8,
            background: s.is_active ? 'var(--paper)' : 'var(--paper-warm)',
          }}
        >
          <div className="between">
            <span className="hand" style={{ fontSize: 15, fontWeight: 700 }}>{s.name}</span>
            {s.is_active && <span className="sk-pill sk-pill--filled" style={{ fontSize: 11 }}>当前</span>}
          </div>
          <div className="annot text-faint" style={{ fontSize: 12, marginTop: 4 }}>
            {s.author ?? s.slug} · v{s.version} · {s.tags.join(', ')}
          </div>
          <div className="hand" style={{ fontSize: 13, marginTop: 6, lineHeight: 1.5 }}>
            {s.description}
          </div>
        </div>
      ))}
    </div>
  )
}
