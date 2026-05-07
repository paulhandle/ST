import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { TodayOut } from '@/lib/api/types'
import { getAthleteId } from '@/lib/auth'

export function useWorkoutByDate(date: string) {
  const athleteId = getAthleteId()
  const { data, error, isLoading, mutate } = useSWR<TodayOut>(
    date ? `/api/athletes/${athleteId}/workout/${date}` : null,
    fetcher,
  )
  return { workout: data, isLoading, error, refresh: mutate }
}
