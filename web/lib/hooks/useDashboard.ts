import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { DashboardOut } from '@/lib/api/types'

const ATHLETE_ID = 1

export function useDashboard() {
  const { data, error, isLoading, mutate } = useSWR<DashboardOut>(
    `/api/athletes/${ATHLETE_ID}/dashboard`,
    fetcher,
    { refreshInterval: 60_000 },
  )
  return { dashboard: data, error, isLoading, refresh: mutate }
}
