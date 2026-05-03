'use client'

import { use } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { SkillDetailOut } from '@/lib/api/types'

export default function SkillDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const router = useRouter()
  const { data: skill, isLoading, error } = useSWR<SkillDetailOut>(
    `/api/skills/${slug}`,
    fetcher,
  )

  return (
    <div>
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="between">
          <button
            onClick={() => router.back()}
            className="hand text-faint"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14 }}
          >
            ‹ 返回
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="hand text-faint" style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
          加载中…
        </div>
      )}

      {error && (
        <div className="hand text-faint" style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
          {error.message}
        </div>
      )}

      {skill && (
        <div>
          <div style={{ padding: '16px 16px 12px' }}>
            <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
              {skill.name}
            </div>
            <div className="annot text-faint" style={{ fontSize: 13 }}>
              {skill.author && `${skill.author} · `}v{skill.version}
              {skill.tags.length > 0 && ` · ${skill.tags.join(', ')}`}
            </div>
          </div>

          {skill.methodology_md ? (
            <pre style={{
              margin: '0 16px 24px',
              padding: '16px',
              background: 'var(--paper-warm)',
              border: '1px solid var(--rule-soft)',
              borderRadius: 8,
              fontFamily: 'var(--font-hand)',
              fontSize: 13,
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              color: 'var(--ink)',
            }}>
              {skill.methodology_md}
            </pre>
          ) : (
            <div className="hand text-faint" style={{ padding: '16px', fontSize: 13 }}>
              暂无方法论说明
            </div>
          )}
        </div>
      )}
    </div>
  )
}
