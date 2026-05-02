import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { WeekOut } from '@/lib/api/types'

export function useWeek(planId: number | undefined, weekIndex: number | undefined) {
  const key = planId != null && weekIndex != null
    ? `/api/plans/${planId}/week?week_index=${weekIndex}`
    : null
  const { data, error, isLoading } = useSWR<WeekOut>(key, fetcher)
  return { week: data, error, isLoading }
}
