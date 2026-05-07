import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { TodayOut } from '@/lib/api/types'
import { getAthleteId } from '@/lib/auth'

export function useToday() {
  const athleteId = getAthleteId()
  const { data, error, isLoading, mutate } = useSWR<TodayOut>(
    `/api/athletes/${athleteId}/today`,
    fetcher,
    { refreshInterval: 120_000 },
  )
  return { today: data, error, isLoading, refresh: mutate }
}
