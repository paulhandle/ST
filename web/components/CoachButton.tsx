'use client'

import { useState } from 'react'
import CoachSheet from './CoachSheet'

export default function CoachButton() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button className="coach-fab" onClick={() => setOpen(true)} aria-label="打开教练">
        练
      </button>
      <CoachSheet open={open} onClose={() => setOpen(false)} />
    </>
  )
}
