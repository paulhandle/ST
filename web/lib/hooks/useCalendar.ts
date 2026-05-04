import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { CalendarDay } from '@/lib/api/types'

const ATHLETE_ID = 1

export function useCalendar(fromDate: string, toDate: string) {
  const key =
    fromDate && toDate
      ? `/api/athletes/${ATHLETE_ID}/calendar?from_date=${fromDate}&to_date=${toDate}`
      : null
  const { data, error, isLoading, mutate } = useSWR<CalendarDay[]>(key, fetcher)
  return { days: data ?? [], isLoading, error, refresh: mutate }
}
