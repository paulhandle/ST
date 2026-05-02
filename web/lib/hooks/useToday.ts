import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { TodayOut } from '@/lib/api/types'

const ATHLETE_ID = 1

export function useToday() {
  const { data, error, isLoading, mutate } = useSWR<TodayOut>(
    `/api/athletes/${ATHLETE_ID}/today`,
    fetcher,
    { refreshInterval: 120_000 },
  )
  return { today: data, error, isLoading, refresh: mutate }
}
