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
