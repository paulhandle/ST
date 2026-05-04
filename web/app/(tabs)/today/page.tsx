'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TodayRedirect() {
  const router = useRouter()
  useEffect(() => {
    router.replace(`/workouts/${new Date().toISOString().slice(0, 10)}`)
  }, [router])
  return null
}
