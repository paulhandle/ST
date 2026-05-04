import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ replace: vi.fn(), back: vi.fn() }),
}))
vi.mock('next/link', () => ({
  default: ({ href, children, ...p }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    React.createElement('a', { href, ...p }, children),
}))
vi.mock('@/components/CoachButton', () => ({ default: () => null }))

import TabsLayout from '@/app/(tabs)/layout'

describe('Tab bar', () => {
  it('shows 运动 tab and no 今天 tab', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('运动')).toBeInTheDocument()
    expect(screen.queryByText('今天')).not.toBeInTheDocument()
  })

  it('shows 概览 本周 计划 tabs', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('概览')).toBeInTheDocument()
    expect(screen.getByText('本周')).toBeInTheDocument()
    expect(screen.getByText('计划')).toBeInTheDocument()
  })
})

vi.mock('@/lib/hooks/useWorkoutByDate', () => ({
  useWorkoutByDate: (date: string) => ({
    workout: date === '2026-05-04' ? {
      plan_id: 1, week_index: 3,
      workout: {
        id: 10, title: 'Easy Run', purpose: '轻松跑', duration_min: 50,
        distance_m: 10000, target_min: 330, target_max: 360,
        workout_type: 'easy_run', rpe_min: null, rpe_max: null,
        adaptation_notes: null, steps: [],
      },
      matched_activity_id: null,
      yesterday_workout: null, yesterday_activity: null, recovery_recommendation: null,
    } : { plan_id: null, workout: null },
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}))

import WorkoutDetailPage from '@/app/workouts/[date]/page'

describe('WorkoutDetailPage', () => {
  it('renders workout title for given date', () => {
    render(<WorkoutDetailPage params={{ date: '2026-05-04' }} />)
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
  })

  it('shows rest day when no workout', () => {
    render(<WorkoutDetailPage params={{ date: '2026-05-05' }} />)
    expect(screen.getByText(/休息/)).toBeInTheDocument()
  })
})

vi.mock('@/lib/auth', () => ({
  getToken: () => 'mock-token',
}))

describe('PlanGeneratePage', () => {
  it('shows loading state on mount while importing data', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ imported_count: 5, updated_count: 2, message: 'ok', metric_count: 1,
                           athlete_id: 1, provider: 'coros' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { default: PlanGeneratePage } = await import('@/app/plan/generate/page')
    render(<PlanGeneratePage />)
    expect(screen.getByText(/分析/)).toBeInTheDocument()
  })
})

vi.mock('@/lib/hooks/useCalendar', () => ({
  useCalendar: () => ({
    days: [
      { date: '2026-05-04', status: 'completed', title: '跑步 8.0km', sport: 'run',
        workout_type: 'easy_run', activity_id: 1, workout_id: 10,
        distance_km: 8.0, duration_min: 48 },
      { date: '2026-05-10', status: 'planned', title: 'Long Run', sport: 'run',
        workout_type: 'long_run', activity_id: null, workout_id: 20,
        distance_km: 18.0, duration_min: 110 },
    ],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}))

import MonthStrip from '@/components/activities/MonthStrip'

describe('MonthStrip', () => {
  it('renders today day number', () => {
    const today = new Date().getDate().toString()
    render(<MonthStrip days={[]} selectedDate={null} onSelectDate={vi.fn()} />)
    expect(screen.getAllByText(today).length).toBeGreaterThan(0)
  })

  it('calls onSelectDate when a day is clicked', () => {
    const onSelect = vi.fn()
    render(<MonthStrip days={[]} selectedDate={null} onSelectDate={onSelect} />)
    screen.getAllByRole('button')[0].click()
    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})

import ActivitiesPage from '@/app/(tabs)/activities/page'

describe('ActivitiesPage', () => {
  it('renders filter chips', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('跑步')).toBeInTheDocument()
    expect(screen.getByText('骑车')).toBeInTheDocument()
    expect(screen.getByText('力量')).toBeInTheDocument()
  })

  it('renders list items from calendar data', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('跑步 8.0km')).toBeInTheDocument()
    expect(screen.getByText('Long Run')).toBeInTheDocument()
  })

  it('renders MonthStrip with today visible', () => {
    render(<ActivitiesPage />)
    const today = new Date().getDate().toString()
    expect(screen.getAllByText(today).length).toBeGreaterThan(0)
  })
})
