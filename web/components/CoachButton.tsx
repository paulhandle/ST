'use client'

import { useState } from 'react'
import CoachSheet from './CoachSheet'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function CoachButton() {
  const [open, setOpen] = useState(false)
  const { t } = useI18n()

  return (
    <>
      <button className="coach-fab" onClick={() => setOpen(true)} aria-label={t.nav.coachAria}>
        {t.nav.coachMark}
      </button>
      <CoachSheet open={open} onClose={() => setOpen(false)} />
    </>
  )
}
