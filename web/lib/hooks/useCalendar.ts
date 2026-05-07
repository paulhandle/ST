import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { CalendarDay } from '@/lib/api/types'
import { getAthleteId } from '@/lib/auth'

export function useCalendar(fromDate: string, toDate: string) {
  const athleteId = getAthleteId()
  const key =
    fromDate && toDate
      ? `/api/athletes/${athleteId}/calendar?from_date=${fromDate}&to_date=${toDate}`
      : null
  const { data, error, isLoading, mutate } = useSWR<CalendarDay[]>(key, fetcher)
  return { days: data ?? [], isLoading, error, refresh: mutate }
}
