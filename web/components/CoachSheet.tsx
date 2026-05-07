'use client'

import { useRef, useState } from 'react'
import useSWR from 'swr'
import { fetcher, postJson } from '@/lib/api/client'
import type { CoachMessage } from '@/lib/api/types'
import { useI18n } from '@/lib/i18n/I18nProvider'
import { getAthleteId } from '@/lib/auth'

interface Props {
  open: boolean
  onClose: () => void
}

export default function CoachSheet({ open, onClose }: Props) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { t } = useI18n()
  const athleteId = getAthleteId()

  const { data, mutate } = useSWR<CoachMessage[]>(
    open ? `/api/coach/conversations/${athleteId}?limit=50` : null,
    fetcher,
  )

  const messages = data ?? []

  async function send() {
    const msg = text.trim()
    if (!msg || sending) return
    setSending(true)
    setText('')
    try {
      await postJson('/api/coach/message', { athlete_id: athleteId, text: msg })
      await mutate()
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } finally {
      setSending(false)
    }
  }

  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        display: 'flex', flexDirection: 'column',
        background: 'var(--paper)',
      }}
      className="fade-in"
    >
      {/* header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 16px',
        borderBottom: '1px solid var(--rule)',
      }}>
        <span className="hand" style={{ fontSize: 18, fontWeight: 700 }}>{t.coach.title}</span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 22, color: 'var(--ink-faint)' }}
        >×</button>
      </div>

      {/* messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.length === 0 && (
          <p className="hand text-faint" style={{ fontSize: 14, textAlign: 'center', marginTop: 40 }}>
            {t.coach.empty}
          </p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%',
            }}
          >
            <div
              className="hand"
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius)',
                background: m.role === 'user' ? 'var(--accent)' : 'var(--surface-low)',
                color: m.role === 'user' ? '#050505' : 'var(--ink)',
                border: m.role === 'coach' ? '1px solid var(--rule)' : 'none',
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              {m.text}
            </div>

            {m.suggested_actions && m.suggested_actions.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                {m.suggested_actions.map((a, i) => (
                  <button key={i} className="sk-pill sk-pill--accent" style={{ cursor: 'pointer', background: 'none', border: '1.2px solid var(--accent)' }}>
                    {a.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* input */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--rule-soft)',
        display: 'flex', gap: 8, alignItems: 'flex-end',
        paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))',
      }}>
        <textarea
          className="hand"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder={t.coach.placeholder}
          rows={1}
          style={{
            flex: 1,
            resize: 'none',
            border: '1px solid var(--rule)',
            borderRadius: 'var(--radius)',
            padding: '8px 12px',
            fontSize: 14,
            background: 'var(--paper)',
            color: 'var(--ink)',
            fontFamily: 'var(--font-hand)',
            outline: 'none',
          }}
        />
        <button
          onClick={send}
          disabled={!text.trim() || sending}
          style={{
            padding: '8px 16px',
            background: text.trim() ? 'var(--accent)' : 'var(--rule)',
            color: '#050505',
            border: 'none',
            borderRadius: 'var(--radius)',
            fontFamily: 'var(--font-hand)',
            fontSize: 14,
            cursor: text.trim() ? 'pointer' : 'default',
            transition: 'background 0.15s',
          }}
        >
          {t.coach.send}
        </button>
      </div>
    </div>
  )
}
