'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { fetcher, postJson } from '@/lib/api/client'
import { useDashboard } from '@/lib/hooks/useDashboard'
import type { SkillManifestOut, RegeneratePreviewOut } from '@/lib/api/types'
import SkillList from '@/components/skills/SkillList'
import SwitchSkillDialog from '@/components/skills/SwitchSkillDialog'

export default function SkillsPage() {
  const router = useRouter()
  const { dashboard, refresh } = useDashboard()
  const planId = dashboard?.today.plan_id

  const { data: skills, isLoading } = useSWR<SkillManifestOut[]>('/api/skills', fetcher)

  const [switchSlug, setSwitchSlug] = useState<string | null>(null)
  const [preview, setPreview] = useState<RegeneratePreviewOut | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [switching, setSwitching] = useState(false)

  async function handleSwitch(slug: string) {
    if (!planId) return
    setSwitchSlug(slug)
    setLoadingPreview(true)
    try {
      const data = await fetcher<RegeneratePreviewOut>(
        `/api/plans/${planId}/regenerate-preview?skill_slug=${slug}`
      )
      setPreview(data)
    } finally {
      setLoadingPreview(false)
    }
  }

  async function confirmSwitch() {
    if (!planId || !switchSlug) return
    setSwitching(true)
    try {
      await postJson(`/api/plans/${planId}/regenerate-from-today`, { skill_slug: switchSlug })
      await refresh()
      setSwitchSlug(null)
      setPreview(null)
      router.push('/dashboard')
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div>
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>训练方法论</div>
        <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>
          选择适合你的训练哲学
        </div>
      </div>

      <div style={{ padding: '16px' }}>
        {isLoading && (
          <div className="hand text-faint" style={{ textAlign: 'center', padding: '32px 0', fontSize: 14 }}>
            加载中…
          </div>
        )}
        {skills && (
          <SkillList
            skills={skills}
            onSwitch={handleSwitch}
          />
        )}
      </div>

      {switchSlug && (
        loadingPreview ? (
          <div style={{
            position: 'fixed', inset: 0, zIndex: 300,
            background: 'rgba(26,26,26,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span className="hand" style={{ color: 'var(--paper)', fontSize: 16 }}>加载预览…</span>
          </div>
        ) : preview ? (
          <SwitchSkillDialog
            skillName={skills?.find(s => s.slug === switchSlug)?.name ?? switchSlug}
            preview={preview}
            onConfirm={confirmSwitch}
            onCancel={() => { setSwitchSlug(null); setPreview(null) }}
            loading={switching}
          />
        ) : null
      )}
    </div>
  )
}
