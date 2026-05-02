import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('swr', () => ({
  default: vi.fn((_key: string) => ({
    data: undefined,
    error: undefined,
    isLoading: true,
    mutate: vi.fn(),
  })),
}))

// Must import swr AFTER mock is set up
import useSWR from 'swr'
import { useDashboard } from '@/lib/hooks/useDashboard'
import { useToday } from '@/lib/hooks/useToday'
import { useWeek } from '@/lib/hooks/useWeek'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useDashboard', () => {
  it('calls SWR with /api/athletes/1/dashboard', () => {
    useDashboard()
    expect(useSWR).toHaveBeenCalledWith(
      '/api/athletes/1/dashboard',
      expect.anything(),
      expect.anything(),
    )
  })
})

describe('useToday', () => {
  it('calls SWR with /api/athletes/1/today', () => {
    useToday()
    expect(useSWR).toHaveBeenCalledWith(
      '/api/athletes/1/today',
      expect.anything(),
      expect.anything(),
    )
  })
})

describe('useWeek', () => {
  it('calls SWR with /api/plans/1/week?week_index=3 when both ids provided', () => {
    useWeek(1, 3)
    expect(useSWR).toHaveBeenCalledWith(
      '/api/plans/1/week?week_index=3',
      expect.anything(),
    )
  })

  it('calls SWR with null when ids are missing', () => {
    useWeek(undefined, undefined)
    expect(useSWR).toHaveBeenCalledWith(
      null,
      expect.anything(),
    )
  })
})
