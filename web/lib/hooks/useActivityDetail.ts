import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { ActivityDetailOut } from '@/lib/api/types'
import { getAthleteId } from '@/lib/auth'

export function useActivityDetail(activityId: string | number | null | undefined) {
  const athleteId = getAthleteId()
  const key = activityId
    ? `/api/athletes/${athleteId}/activities/${activityId}`
    : null
  const { data, error, isLoading, mutate } = useSWR<ActivityDetailOut>(key, fetcher)
  return { activity: data, isLoading, error, refresh: mutate }
}
