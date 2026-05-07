import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { DashboardOut } from '@/lib/api/types'
import { getAthleteId } from '@/lib/auth'

export function useDashboard() {
  const athleteId = getAthleteId()
  const { data, error, isLoading, mutate } = useSWR<DashboardOut>(
    `/api/athletes/${athleteId}/dashboard`,
    fetcher,
    { refreshInterval: 60_000 },
  )
  return { dashboard: data, error, isLoading, refresh: mutate }
}
