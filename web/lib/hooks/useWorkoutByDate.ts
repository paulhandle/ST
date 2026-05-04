import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { TodayOut } from '@/lib/api/types'

const ATHLETE_ID = 1

export function useWorkoutByDate(date: string) {
  const { data, error, isLoading, mutate } = useSWR<TodayOut>(
    date ? `/api/athletes/${ATHLETE_ID}/workout/${date}` : null,
    fetcher,
  )
  return { workout: data, isLoading, error, refresh: mutate }
}
