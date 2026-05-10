'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useI18n } from '@/lib/i18n/I18nProvider'

const DISMISS_KEY = 'pp_coros_nudge_dismissed'

export default function CorosNudge() {
  const { language } = useI18n()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!canUseLocalStorage()) {
      setVisible(true)
      return
    }
    setVisible(localStorage.getItem(DISMISS_KEY) !== '1')
  }, [])

  function dismiss() {
    if (canUseLocalStorage()) {
      localStorage.setItem(DISMISS_KEY, '1')
    }
    setVisible(false)
  }

  if (!visible) return null

  const copy = language === 'zh'
    ? {
        title: '连接 COROS 可以稍后完成',
        body: '同步历史训练能帮助评估状态，也可以把训练计划导入到 COROS。',
        action: '去连接',
        later: '稍后',
      }
    : {
        title: 'Connect COROS when ready',
        body: 'Sync history for better context and import workouts into COROS.',
        action: 'Connect',
        later: 'Later',
      }

  return (
    <div className="coros-nudge" role="dialog" aria-label={copy.title}>
      <div>
        <div className="hand" style={{ fontSize: 15, fontWeight: 800 }}>{copy.title}</div>
        <div className="annot text-faint" style={{ fontSize: 12, lineHeight: 1.45, marginTop: 4 }}>
          {copy.body}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
        <Link href="/settings/coros" onClick={dismiss} className="coros-nudge__primary">
          {copy.action}
        </Link>
        <button onClick={dismiss} className="coros-nudge__secondary">
          {copy.later}
        </button>
      </div>
    </div>
  )
}

function canUseLocalStorage() {
  return typeof window !== 'undefined' &&
    typeof window.localStorage?.getItem === 'function' &&
    typeof window.localStorage?.setItem === 'function'
}
